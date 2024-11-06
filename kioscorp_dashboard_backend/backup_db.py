# backup_db.py
import os
import shutil
from datetime import datetime
from pathlib import Path
import time

# Adjust BASE_DIR to point to the project root
BASE_DIR = (
    Path(__file__).resolve().parent.parent
)  # Go up one more level to the project root
DB_FILE = BASE_DIR / "db.sqlite3"  # Correct path to the database file
BACKUP_DIR = BASE_DIR / "backups"  # Backup directory

BACKUP_INTERVAL = 30 * 60  # 30 minutes in seconds

BACKUP_DIR.mkdir(exist_ok=True)  # Ensure the backup directory exists


def backup_database():
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = BACKUP_DIR / f"db_backup_{timestamp}.sqlite3"
        shutil.copy(DB_FILE, backup_filename)
        print(f"Backup created: {backup_filename}")

        backups = sorted(BACKUP_DIR.glob("db_backup_*.sqlite3"), key=os.path.getmtime)
        if len(backups) > 5:
            for old_backup in backups[:-5]:
                old_backup.unlink()
                print(f"Deleted old backup: {old_backup}")
    except Exception as e:
        print(f"Error during backup: {e}")


def start_backup_loop():
    while True:
        backup_database()
        time.sleep(BACKUP_INTERVAL)
