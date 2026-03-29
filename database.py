import sqlite3

def init_db():
    connection = sqlite3.connect('app.db')
    cursor = connection.cursor()

    # Create users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users(
            nic TEXT PRIMARY KEY,
            first_name TEXT,
            last_name TEXT,
            phone TEXT,
            language TEXT,
            district TEXT,
            ds TEXT
        )
    """)

    # Create applications table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS applications(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER,
            user_nic TEXT,
            status TEXT
        )
    """)

    # Create Skills table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS skills(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE
        )
    """)

    # Create  User-skills table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_skills(
            user_nic TEXT,
            skill_id INTEGER,
            PRIMARY KEY (user_nic, skill_id)
        )
    """)

    # Create Jobs table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS jobs(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            description TEXT,
            district TEXT,
            ds TEXT,
            employer_nic TEXT,
            status TEXT
        )
    """)

    # Create  Job-skills table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS job_skills(
            job_id INTEGER,
            skill_id INTEGER,
            PRIMARY KEY (job_id, skill_id)
        )
    """)

    connection.commit()
    connection.close()

def get_db():
    connection = sqlite3.connect('app.db')
    connection.row_factory = sqlite3.Row

    return connection
