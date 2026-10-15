#!/usr/bin/env python3
"""
Скрипт автоматического создания резервной копии базы данных PostgreSQL FinFlow.
Сохраняет дампы в локальную директорию на ПК и производит ротацию устаревших копий.

Использование:
    python scripts/backup.py
    uv run python scripts/backup.py
    python scripts/backup.py --keep 15 --output-dir "D:/FinFlowBackups"
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
    # Фолбэк на переменные окружения напрямую
    DEFAULT_HOST = os.getenv("HOST", "localhost")
    DEFAULT_PORT = int(os.getenv("SESSION_PORT", os.getenv("PORT", "5432")))
    DEFAULT_DB = os.getenv("DATABASE", "postgres")
    DEFAULT_USER = os.getenv("USER", "postgres")
    DEFAULT_PASSWORD = os.getenv("PASSWORD", "")

DEFAULT_BACKUP_DIR = PROJECT_ROOT / "backups"


def check_tool_availability() -> tuple[str, str]:
    """
    Проверяет наличие локального pg_dump или Docker.
    Возвращает кортеж (режим, путь_к_утилите):
    - ('local', путь_к_pg_dump)
    - ('docker', 'docker')
    - ('none', '')
    """
    pg_dump_path = shutil.which("pg_dump")
    if pg_dump_path:
        return "local", pg_dump_path

    docker_path = shutil.which("docker")
    if docker_path:
        return "docker", docker_path

    return "none", ""


def rotate_backups(backup_dir: Path, keep_count: int) -> list[Path]:
    """Удаляет старые бэкапы, оставляя только keep_count самых свежих."""
    if keep_count <= 0:
        return []

    # Ищем файлы *.dump в директории
    dumps = sorted(
        backup_dir.glob("finflow_backup_*.dump"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    removed = []
    if len(dumps) > keep_count:
        for old_dump in dumps[keep_count:]:
            try:
                old_dump.unlink()
                removed.append(old_dump)
            except OSError as e:
                print(f"[!] Не удалось удалить старый файл {old_dump.name}: {e}")

    return removed


def format_size(size_bytes: float) -> str:
    """Форматирует размер в байтах в человекочитаемый вид."""
    for unit in ["Б", "КБ", "МБ", "ГБ"]:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} ТБ"


def run_backup(
    host: str,
    port: int,
    database: str,
    user: str,
    password: str,
    output_dir: Path,
    keep_count: int,
) -> bool:
    """Выполняет снятие дампа БД и сохраняет его на диск."""
    mode, tool_path = check_tool_availability()

    if mode == "none":
        print("\n[ОШИБКА] Не найден ни 'pg_dump', ни 'docker'!")
        print("Для работы бэкапа требуется один из следующих компонентов:")
        print(" 1) Docker Desktop (должен быть запущен)")
        print(" 2) Установленный PostgreSQL Client Tools (pg_dump в системном PATH)\n")
        return False

    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_filename = f"finflow_backup_{timestamp}.dump"
    backup_filepath = output_dir / backup_filename

    print("=" * 65)
    print("  FinFlow Database Backup")
    print("=" * 65)
    print(f"[*] База данных : {database}")
    print(f"[*] Хост         : {host}:{port}")
    print(f"[*] Пользователь : {user}")
    print(f"[*] Режим запуска: {'pg_dump (локально)' if mode == 'local' else 'Docker (postgres:17-alpine)'}")
    print(f"[*] Файл бэкапа  : {backup_filepath}")
    print("=" * 65)

    start_time = time.time()
    env = os.environ.copy()
    if password:
        env["PGPASSWORD"] = password

    try:
        if mode == "local":
            cmd = [
                tool_path,
                "-h", host,
                "-p", str(port),
                "-U", user,
                "-d", database,
                "-F", "c",  # Custom формат (сжатый бинарный дамп)
                "-f", str(backup_filepath),
            ]
            print("[*] Создание дампа базы данных...")
            process = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                check=True,
            )
        else:
            # Для Docker на Windows localhost перенаправляется на host.docker.internal
            container_host = host
            if host in ("localhost", "127.0.0.1"):
                container_host = "host.docker.internal"

            abs_output_dir = output_dir.resolve()
            cmd = [
                "docker", "run", "--rm",
                "-e", f"PGPASSWORD={password}",
                "-v", f"{abs_output_dir}:/backups",
                "postgres:17-alpine",
                "pg_dump",
                "-h", container_host,
                "-p", str(port),
                "-U", user,
                "-d", database,
                "-F", "c",
                "-f", f"/backups/{backup_filename}",
            ]
            print(f"[*] Запуск pg_dump через Docker контейнер...")
            process = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
            )

        elapsed = time.time() - start_time
        if backup_filepath.exists() and backup_filepath.stat().st_size > 0:
            size_str = format_size(backup_filepath.stat().st_size)
            print(f"\n[+] Бэкап успешно создан за {elapsed:.2f} сек!")
            print(f"[+] Размер файла : {size_str}")
            print(f"[+] Расположение : {backup_filepath.resolve()}")

            # Ротация
            removed_files = rotate_backups(output_dir, keep_count)
            if removed_files:
                print(f"[*] Ротация: удалено старых копий: {len(removed_files)}")
                for f in removed_files:
                    print(f"    - Удален: {f.name}")
            else:
                current_count = len(list(output_dir.glob("finflow_backup_*.dump")))
                print(f"[*] Всего сохранено копий: {current_count} (лимит хранения: {keep_count})")

            print("=" * 65)
            return True
        else:
            print("\n[!] Ошибка: файл бэкапа не был создан или имеет нулевой размер.")
            if backup_filepath.exists() and backup_filepath.stat().st_size == 0:
                backup_filepath.unlink()
            return False

    except subprocess.CalledProcessError as e:
        if backup_filepath.exists() and backup_filepath.stat().st_size == 0:
            backup_filepath.unlink()
        print("\n[ОШИБКА] Процесс завершился сбоем:")
        if e.stderr:
            print(e.stderr.strip())
        elif e.stdout:
            print(e.stdout.strip())
        return False
    except Exception as e:
        if backup_filepath.exists() and backup_filepath.stat().st_size == 0:
            backup_filepath.unlink()
        print(f"\n[ОШИБКА] Непредвиденная ошибка: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Создание резервной копии базы данных PostgreSQL FinFlow на ПК."
    )
    parser.add_argument("--host", default=DEFAULT_HOST, help="Хост базы данных")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Порт БД")
    parser.add_argument("--db", default=DEFAULT_DB, help="Имя базы данных")
    parser.add_argument("--user", default=DEFAULT_USER, help="Имя пользователя БД")
    parser.add_argument("--password", default=DEFAULT_PASSWORD, help="Пароль пользователя БД")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_BACKUP_DIR,
        help="Папка для сохранения бэкапов (по умолчанию: ./backups)",
    )
    parser.add_argument(
        "--keep",
        type=int,
        default=10,
        help="Сколько последних бэкапов хранить (по умолчанию: 10)",
    )

    args = parser.parse_args()

    success = run_backup(
        host=args.host,
        port=args.port,
        database=args.db,
        user=args.user,
        password=args.password,
        output_dir=args.output_dir,
        keep_count=args.keep,
    )
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
