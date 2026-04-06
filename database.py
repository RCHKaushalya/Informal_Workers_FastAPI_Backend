import sqlite3
from contextlib import contextmanager


DB_PATH = "app.db"


def _column_exists(cursor: sqlite3.Cursor, table: str, column: str) -> bool:
    cols = cursor.execute(f"PRAGMA table_info({table})").fetchall()
    return any(row[1] == column for row in cols)


def _table_exists(cursor: sqlite3.Cursor, table: str) -> bool:
    row = cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name = ?",
        (table,),
    ).fetchone()
    return row is not None


def init_db() -> None:
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()

    # Core users table (PIN-based auth for app + volunteer/admin role)
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users(
            nic TEXT PRIMARY KEY,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            phone TEXT NOT NULL,
            language TEXT NOT NULL,
            district TEXT NOT NULL,
            ds_area TEXT NOT NULL,
            pin TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user',
            rating REAL NOT NULL DEFAULT 0
        )
        """
    )

    # Ensure critical columns exist for new auth system
    if not _column_exists(cursor, "users", "pin"):
        cursor.execute("ALTER TABLE users ADD COLUMN pin TEXT DEFAULT '1234'")
    
    if not _column_exists(cursor, "users", "role"):
        cursor.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'user'")
        
    if not _column_exists(cursor, "users", "rating"):
        cursor.execute("ALTER TABLE users ADD COLUMN rating REAL DEFAULT 0")

    # Jobs table migration
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS jobs(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            district TEXT NOT NULL,
            ds_area TEXT NOT NULL,
            location TEXT,
            date TEXT,
            time TEXT,
            status TEXT NOT NULL DEFAULT 'open',
            employer_nic TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    if not _column_exists(cursor, "jobs", "created_at"):
        cursor.execute("ALTER TABLE jobs ADD COLUMN created_at TEXT DEFAULT (datetime('now'))")
    if not _column_exists(cursor, "jobs", "ds_area"):
        cursor.execute("ALTER TABLE jobs ADD COLUMN ds_area TEXT DEFAULT ''")

    # Applications table migration
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS applications(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER NOT NULL,
            worker_nic TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'applied',
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(job_id, worker_nic)
        )
        """
    )
    if not _column_exists(cursor, "applications", "worker_nic"):
        cursor.execute("ALTER TABLE applications ADD COLUMN worker_nic TEXT DEFAULT ''")
    if not _column_exists(cursor, "applications", "created_at"):
        cursor.execute("ALTER TABLE applications ADD COLUMN created_at TEXT DEFAULT (datetime('now'))")

    # Reviews table migration
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS reviews(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER NOT NULL,
            worker_nic TEXT NOT NULL,
            employer_nic TEXT NOT NULL,
            rating INTEGER NOT NULL,
            comment TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(job_id, worker_nic)
        )
        """
    )
    if not _column_exists(cursor, "reviews", "worker_nic"):
        cursor.execute("ALTER TABLE reviews ADD COLUMN worker_nic TEXT DEFAULT ''")
    if not _column_exists(cursor, "reviews", "created_at"):
        cursor.execute("ALTER TABLE reviews ADD COLUMN created_at TEXT DEFAULT (datetime('now'))")

    # Skill codes matching the mobile app constants (string ids)

    # Skill codes matching the mobile app constants (string ids)
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS user_skill_codes(
            user_nic TEXT NOT NULL,
            skill_code TEXT NOT NULL,
            PRIMARY KEY (user_nic, skill_code)
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS job_skill_codes(
            job_id INTEGER NOT NULL,
            skill_code TEXT NOT NULL,
            PRIMARY KEY (job_id, skill_code)
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS system_skills(
            code TEXT PRIMARY KEY,
            name TEXT NOT NULL
        )
        """
    )

    # Likes (optional): employer can like/bookmark workers per job
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS job_liked_workers(
            job_id INTEGER NOT NULL,
            worker_nic TEXT NOT NULL,
            PRIMARY KEY (job_id, worker_nic)
        )
        """
    )

    # If the old tables exist we keep them; app uses the *_codes tables.
    if not _table_exists(cursor, "skills"):
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS skills(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE
            )
            """
        )
    if not _table_exists(cursor, "user_skills"):
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS user_skills(
                user_nic TEXT,
                skill_id INTEGER,
                PRIMARY KEY (user_nic, skill_id)
            )
            """
        )
    if not _table_exists(cursor, "job_skills"):
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS job_skills(
                job_id INTEGER,
                skill_id INTEGER,
                PRIMARY KEY (job_id, skill_id)
            )
            """
        )

    connection.commit()
    connection.close()


@contextmanager
def get_db():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
    finally:
        connection.close()
