import os
import sqlite3
from pathlib import Path

DATABASE = Path(
    os.environ.get(
        "DATABASE_PATH",
        str(Path(__file__).resolve().parent / "enquiries.db")
    )
)

def get_db_connection():
    connection = sqlite3.connect(str(DATABASE))
    connection.row_factory = sqlite3.Row
    return connection

def initialize_database():
    connection = get_db_connection()

    connection.execute("""
        CREATE TABLE IF NOT EXISTS enquiries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            book_title TEXT,
            amazon_link TEXT,
            service TEXT,
            message TEXT NOT NULL,
            source TEXT DEFAULT 'Contact',
            status TEXT DEFAULT 'New',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    existing_columns = {
        row["name"]
        for row in connection.execute("PRAGMA table_info(enquiries)").fetchall()
    }

    new_columns = {
        "genre": "TEXT",
        "publishing_status": "TEXT",
        "service_interest": "TEXT",
        "package": "TEXT"
    }

    for column, data_type in new_columns.items():
        if column not in existing_columns:
            connection.execute(
                f"ALTER TABLE enquiries ADD COLUMN {column} {data_type}"
            )

    connection.commit()
    connection.close()

if __name__ == "__main__":
    initialize_database()
    print("Enquiries database created successfully.")

def initialize_admin_table():
    connection = get_db_connection()

    connection.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
    """)

    connection.commit()
    connection.close()
