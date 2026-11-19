import os
import sqlite3
from pathlib import Path


DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()

DATABASE = Path(
    os.environ.get(
        "DATABASE_PATH",
        str(Path(__file__).resolve().parent / "enquiries.db")
    )
)


class PostgreSQLConnection:
    def __init__(self, connection):
        self.connection = connection

    def execute(self, query, parameters=()):
        from psycopg2.extras import DictCursor

        cursor = self.connection.cursor(cursor_factory=DictCursor)
        cursor.execute(query.replace("?", "%s"), parameters)
        return cursor

    def commit(self):
        self.connection.commit()

    def close(self):
        self.connection.close()


def get_db_connection():
    if DATABASE_URL:
        import psycopg2

        connection = psycopg2.connect(DATABASE_URL)
        return PostgreSQLConnection(connection)

    connection = sqlite3.connect(str(DATABASE))
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():
    connection = get_db_connection()

    try:
        if DATABASE_URL:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS enquiries (
                    id BIGSERIAL PRIMARY KEY,
                    name TEXT NOT NULL,
                    email TEXT NOT NULL,
                    book_title TEXT,
                    amazon_link TEXT,
                    service TEXT,
                    message TEXT NOT NULL,
                    source TEXT DEFAULT 'Contact',
                    status TEXT DEFAULT 'New',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    genre TEXT,
                    publishing_status TEXT,
                    service_interest TEXT,
                    package TEXT
                )
            """)

            for column in (
                "genre",
                "publishing_status",
                "service_interest",
                "package"
            ):
                connection.execute(
                    f"ALTER TABLE enquiries ADD COLUMN IF NOT EXISTS {column} TEXT"
                )

        else:
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
                for row in connection.execute(
                    "PRAGMA table_info(enquiries)"
                ).fetchall()
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
    finally:
        connection.close()


def initialize_admin_table():
    connection = get_db_connection()

    try:
        if DATABASE_URL:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS admins (
                    id BIGSERIAL PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL
                )
            """)
        else:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS admins (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL
                )
            """)

        connection.commit()
    finally:
        connection.close()


if __name__ == "__main__":
    initialize_database()
    initialize_admin_table()
    print("Database tables initialized successfully.")
