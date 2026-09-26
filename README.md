# FinFlow Backend

Бэкенд персонального финансового трекера **FinFlow** на FastAPI, SQLAlchemy и PostgreSQL.

---

## 🗄️ Резервное копирование и восстановление (Backup & Restore)

Для обеспечения безопасности данных созданы Python-скрипты, сохраняющие резервные копии базы данных прямо на ваш ПК в папку `backups/`.

### Особенности:
- **Умное окружение**: если на ПК не установлены утилиты PostgreSQL (`pg_dump`/`pg_restore`), скрипт автоматически использует **Docker** (`postgres:17-alpine`).
- **Сжатый формат**: дамп создается в нативном формате PostgreSQL (`-F c`), который оптимизирован по размеру и скорости восстановления.
- **Автоматическая ротация**: скрипт хранит последние 10 копий (настраивается флагом `--keep`), удаляя старые.
- **Безопасность**: директория `backups/` и файлы `*.dump` добавлены в `.gitignore` и `.dockerignore`, чтобы конфиденциальные данные случайно не попали в репозиторий.

---

### 1. Создание резервной копии (Backup)

Запуск с параметрами по умолчанию (берет настройки из `.env`):

```bash
# Через uv
uv run python scripts/backup.py

# Или через стандартный Python
python scripts/backup.py
```

**Дополнительные параметры:**
```bash
# Сохранить в другую папку и хранить 20 последних копий:
uv run python scripts/backup.py --keep 20 --output-dir "D:/FinFlowBackups"

# Переопределить параметры подключения вручную:
uv run python scripts/backup.py --host my-host.supabase.co --port 5432 --db postgres --user postgres
```

---

### 2. Восстановление базы данных (Restore)

```bash
# Посмотреть список всех доступных локальных бэкапов:
uv run python scripts/restore.py --list

# Посмотреть оглавление и таблицы внутри последнего бэкапа без восстановления:
uv run python scripts/restore.py --info

# Восстановить базу из САМОГО СВЕЖЕГО бэкапа (с подтверждением):
uv run python scripts/restore.py

# Восстановить из конкретного файла:
uv run python scripts/restore.py --file backups/finflow_backup_2026-09-26_16-20-00.dump

# Без интерактивного подтверждения (для автоматических скриптов):
uv run python scripts/restore.py --yes
```

---

### 3. Автоматизация в Windows (Планировщик задач)

Чтобы бэкап делался автоматически каждый день, можно добавить задачу в **Windows Task Scheduler**:

1. Откройте **Планировщик заданий** (`Task Scheduler`).
2. Нажмите **Создать простую задачу...** (`Create Basic Task`).
3. Триггер: **Ежедневно** (например, в `03:00`).
4. Действие: **Запустить программу**:
   - **Программа**: `uv` (или полный путь к `python.exe` в `.venv\Scripts\python.exe`)
   - **Аргументы**: `run python scripts/backup.py`
   - **Рабочая папка**: `E:\code-projects\my-projects\finflow\backend`
