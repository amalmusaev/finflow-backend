#!/usr/bin/env python3
"""
Скрипт восстановления базы данных PostgreSQL FinFlow из локального бэкапа.

Использование:
    # Восстановление из самого свежего бэкапа (с запросом подтверждения):
    python scripts/restore.py

    # Список доступных бэкапов:
    python scripts/restore.py --list

    # Восстановление из конкретного файла:
    python scripts/restore.py --file backups/finflow_backup_2026-09-26_16-20-00.dump

    # Без интерактивного подтверждения:
    python scripts/restore.py --yes
"""

import argparse
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# Добавляем корень проекта в путь для импорта настроек
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Попытка загрузить настройки проекта
try:
    from src.core.config import settings

    DEFAULT_HOST = settings.host
    DEFAULT_PORT = getattr(settings, "session_port", settings.port)
    DEFAULT_DB = settings.database
    DEFAULT_USER = settings.user
    DEFAULT_PASSWORD = settings.password
except Exception:
    DEFAULT_HOST = os.getenv("HOST", "localhost")
    DEFAULT_PORT = int(os.getenv("SESSION_PORT", os.getenv("PORT", "5432")))
    DEFAULT_DB = os.getenv("DATABASE", "postgres")
    DEFAULT_USER = os.getenv("USER", "postgres")
    DEFAULT_PASSWORD = os.getenv("PASSWORD", "")

DEFAULT_BACKUP_DIR = PROJECT_ROOT / "backups"


def check_tool_availability() -> tuple[str, str]:
    """
    Проверяет наличие локального pg_restore или Docker.
    Возвращает кортеж (режим, путь_к_утилите):
    - ('local', путь_к_pg_restore)
    - ('docker', 'docker')
    - ('none', '')
    """
    pg_restore_path = shutil.which("pg_restore")
    if pg_restore_path:
        return "local", pg_restore_path

    docker_path = shutil.which("docker")
    if docker_path:
        return "docker", docker_path

    return "none", ""


def get_available_backups(backup_dir: Path) -> list[Path]:
    """Возвращает список доступных непустых бэкапов, отсортированных по дате (свежие первые)."""
    if not backup_dir.exists():
        return []
    return sorted(
        [p for p in backup_dir.glob("finflow_backup_*.dump") if p.is_file() and p.stat().st_size > 0],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )


def format_size(size_bytes: float) -> str:
    """Форматирует размер в байтах в человекочитаемый вид."""
    for unit in ["Б", "КБ", "МБ", "ГБ"]:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} ТБ"


def list_backups(backup_dir: Path) -> None:
    """Выводит список всех доступных локальных резервных копий."""
    backups = get_available_backups(backup_dir)
    print("=" * 70)
    print(f" Доступные бэкапы в директории: {backup_dir.resolve()}")
    print("=" * 70)
    if not backups:
        print(" [!] Бэкапы не найдены.")
        return

    for idx, b in enumerate(backups, start=1):
        mtime = datetime.fromtimestamp(b.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        size = format_size(b.stat().st_size)
        mark = " (САМЫЙ СВЕЖИЙ)" if idx == 1 else ""
        print(f" {idx:2d}) {b.name}  |  {mtime}  |  {size:>8}{mark}")
    print("=" * 70)


def pluralize_rows(n: int) -> str:
    """Склонение слова 'строка' для чисел в русском языке."""
    n_abs = abs(n)
    if 11 <= (n_abs % 100) <= 19:
        return f"{n} строк"
    remainder = n_abs % 10
    if remainder == 1:
        return f"{n} строка"
    elif 2 <= remainder <= 4:
        return f"{n} строки"
    return f"{n} строк"


def inspect_backup(dump_file: Path, verbose: bool = False) -> bool:
    """Инспектирует содержимое дампа без подключения к базе данных, включая подсчет строк в таблицах."""
    if not dump_file.exists():
        print(f"\n[ОШИБКА] Файл бэкапа не найден: {dump_file.resolve()}")
        return False

    mode, tool_path = check_tool_availability()
    if mode == "none":
        print("\n[ОШИБКА] Не найден ни 'pg_restore', ни 'docker'!")
        return False

    try:
        if mode == "local":
            cmd_toc = [tool_path, "--list", str(dump_file.resolve())]
            cmd_data = [tool_path, "--data-only", "--schema=public", "-f", "-", str(dump_file.resolve())]
        else:
            parent_dir = dump_file.resolve().parent
            filename = dump_file.name
            cmd_toc = [
                "docker", "run", "--rm",
                "-v", f"{parent_dir}:/backups",
                "postgres:17-alpine",
                "pg_restore", "--list", f"/backups/{filename}",
            ]
            cmd_data = [
                "docker", "run", "--rm",
                "-v", f"{parent_dir}:/backups",
                "postgres:17-alpine",
                "pg_restore", "--data-only", "--schema=public", "-f", "-", f"/backups/{filename}",
            ]

        # 1. Читаем оглавление (TOC)
        proc_toc = subprocess.run(cmd_toc, capture_output=True, text=True, check=True)
        lines = proc_toc.stdout.splitlines()

        mtime = datetime.fromtimestamp(dump_file.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        size_str = format_size(dump_file.stat().st_size)

        tables = set()
        tables_data = set()
        total_objects = len(lines)

        for line in lines:
            if " TABLE public " in line:
                parts = line.split(" TABLE public ", 1)[1].split()
                if parts:
                    tables.add(parts[0])
            elif " TABLE DATA public " in line:
                parts = line.split(" TABLE DATA public ", 1)[1].split()
                if parts:
                    tables_data.add(parts[0])

        # 2. Подсчитываем строки данных в таблицах схемы public
        row_counts: dict[str, int] = {}
        try:
            proc_data = subprocess.run(
                cmd_data,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=True,
            )
            curr_table = None
            for d_line in proc_data.stdout.splitlines():
                if d_line.startswith("COPY public."):
                    curr_table = d_line.split("COPY public.")[1].split("(")[0].strip()
                    row_counts[curr_table] = 0
                elif d_line == r"\.":
                    curr_table = None
                elif curr_table is not None:
                    row_counts[curr_table] += 1
        except Exception:
            pass

        print("=" * 70)
        print("  Содержимое резервной копии (TOC & Data Stats)")
        print("=" * 70)
        print(f"[*] Файл         : {dump_file.name}")
        print(f"[*] Размер       : {size_str}")
        print(f"[*] Дата создания: {mtime}")
        print("-" * 70)
        print(f"[+] Таблицы FinFlow (схема public):")

        all_tables = sorted(tables | tables_data)
        if all_tables:
            for t in all_tables:
                if t in row_counts:
                    count_str = pluralize_rows(row_counts[t])
                    print(f"    - {t:<22} : {count_str:>14}")
                else:
                    has_struct = "структура" if t in tables else ""
                    has_data = "данные" if t in tables_data else "пусто"
                    status = f"{has_struct} + {has_data}".strip(" +")
                    print(f"    - {t:<22} : [{status}]")

            if row_counts:
                total_rows = sum(row_counts.values())
                print(f"    {' ' * 24}   {'-' * 14}")
                print(f"    {'Всего записей':<22} : {pluralize_rows(total_rows):>14}")
        else:
            print("    (Таблицы схемы public не обнаружены)")

        print("-" * 70)
        print(f"[*] Всего объектов в дампе: {total_objects} (схемы, таблицы, индексы, FK, RLS)")
        print("=" * 70)

        if verbose:
            print("\n--- Полное оглавление дампа ---")
            for line in lines:
                print(line)
        return True

    except Exception as e:
        print(f"[ОШИБКА] Не удалось прочитать дамп: {e}")
        return False


def run_restore(
    dump_file: Path,
    host: str,
    port: int,
    database: str,
    user: str,
    password: str,
    skip_confirm: bool = False,
) -> bool:
    """Восстанавливает базу данных из указанного файла дампа."""
    if not dump_file.exists():
        print(f"\n[ОШИБКА] Файл бэкапа не найден: {dump_file.resolve()}")
        return False

    mode, tool_path = check_tool_availability()
    if mode == "none":
        print("\n[ОШИБКА] Не найден ни 'pg_restore', ни 'docker'!")
        print("Для работы восстановления требуется Docker Desktop или PostgreSQL Client Tools.")
        return False

    mtime = datetime.fromtimestamp(dump_file.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
    size_str = format_size(dump_file.stat().st_size)

    print("=" * 70)
    print("  FinFlow Database Restore")
    print("=" * 70)
    print(f"[*] Целевая БД   : {database} на {host}:{port}")
    print(f"[*] Пользователь : {user}")
    print(f"[*] Файл бэкапа  : {dump_file.name}")
    print(f"[*] Дата бэкапа  : {mtime}")
    print(f"[*] Размер файла : {size_str}")
    print(f"[*] Режим запуска: {'pg_restore (локально)' if mode == 'local' else 'Docker (postgres:17-alpine)'}")
    print("=" * 70)

    if not skip_confirm:
        print("\n[ВНИМАНИЕ] Восстановление базы данных перезапишет или изменит")
        print(f"существующие таблицы в базе данных '{database}'!")
        confirm = input("Вы уверены, что хотите продолжить? [y/N]: ").strip().lower()
        if confirm not in ("y", "yes", "д", "да"):
            print("[*] Операция отменена пользователем.")
            return False

    start_time = time.time()
    env = os.environ.copy()
    if password:
        env["PGPASSWORD"] = password

    # Флаги pg_restore:
    # --clean: удалять объекты перед их созданием
    # --if-exists: избегать ошибок при первом удалении
    # --no-owner: не назначать исходных владельцев объектов
    # --no-acl: не восстанавливать права доступа
    restore_flags = ["--clean", "--if-exists", "--no-owner", "--no-acl"]

    try:
        if mode == "local":
            cmd = [
                tool_path,
                "-h", host,
                "-p", str(port),
                "-U", user,
                "-d", database,
                *restore_flags,
                str(dump_file.resolve()),
            ]
            print("\n[*] Запуск локального процесса pg_restore...")
            process = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
            )
        else:
            container_host = host
            if host in ("localhost", "127.0.0.1"):
                container_host = "host.docker.internal"

            parent_dir = dump_file.resolve().parent
            filename = dump_file.name

            cmd = [
                "docker", "run", "--rm",
                "-e", f"PGPASSWORD={password}",
                "-v", f"{parent_dir}:/backups",
                "postgres:17-alpine",
                "pg_restore",
                "-h", container_host,
                "-p", str(port),
                "-U", user,
                "-d", database,
                *restore_flags,
                f"/backups/{filename}",
            ]
            print("\n[*] Запуск pg_restore через Docker контейнер...")
            process = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
            )

        elapsed = time.time() - start_time

        # В pg_restore код возврата 0 означает полный успех,
        # а код 1 часто означает предупреждения (warnings), например, при отсутствии удаляемых таблиц.
        if process.returncode in (0, 1):
            print(f"\n[+] База данных успешно восстановлена за {elapsed:.2f} сек!")
            if process.returncode == 1 and process.stderr:
                print(f"[*] (Были выведены предупреждения/замечания):")
                print(process.stderr.strip()[:500])
            print("=" * 70)
            return True
        else:
            print("\n[ОШИБКА] Сбой при восстановлении:")
            if process.stderr:
                print(process.stderr.strip())
            return False

    except Exception as e:
        print(f"\n[ОШИБКА] Непредвиденное исключение: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Восстановление базы данных PostgreSQL FinFlow из резервной копии."
    )
    parser.add_argument(
        "--file",
        "-f",
        type=Path,
        default=None,
        help="Путь к конкретному файлу бэкапа (если не указан, берется самый свежий)",
    )
    parser.add_argument(
        "--list",
        "-l",
        action="store_true",
        help="Показать список всех доступных бэкапов и выйти",
    )
    parser.add_argument(
        "--info",
        "--inspect",
        "-i",
        action="store_true",
        help="Просмотреть содержимое дампа (таблицы, данные) без восстановления",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Подробный вывод всех объектов дампа при использовании --info",
    )
    parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="Пропустить интерактивный запрос подтверждения",
    )
    parser.add_argument("--host", default=DEFAULT_HOST, help="Хост базы данных")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Порт БД")
    parser.add_argument("--db", default=DEFAULT_DB, help="Имя базы данных")
    parser.add_argument("--user", default=DEFAULT_USER, help="Имя пользователя БД")
    parser.add_argument("--password", default=DEFAULT_PASSWORD, help="Пароль пользователя БД")
    parser.add_argument(
        "--backup-dir",
        type=Path,
        default=DEFAULT_BACKUP_DIR,
        help="Папка с бэкапами (по умолчанию: ./backups)",
    )

    args = parser.parse_args()

    if args.list:
        list_backups(args.backup_dir)
        sys.exit(0)

    # Выбор файла дампа
    if args.file:
        target_dump = args.file
    else:
        backups = get_available_backups(args.backup_dir)
        if not backups:
            print(f"[!] В директории '{args.backup_dir.resolve()}' не найдено ни одного файла бэкапа (*.dump).")
            print("    Сначала создайте резервную копию: python scripts/backup.py")
            sys.exit(1)
        target_dump = backups[0]
        if not args.info:
            print(f"[*] Файл не указан. Автоматически выбран самый свежий бэкап: {target_dump.name}")

    if args.info:
        success = inspect_backup(target_dump, verbose=args.verbose)
        sys.exit(0 if success else 1)

    success = run_restore(
        dump_file=target_dump,
        host=args.host,
        port=args.port,
        database=args.db,
        user=args.user,
        password=args.password,
        skip_confirm=args.yes,
    )
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
