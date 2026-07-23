import sqlite3
from datetime import datetime, timezone
from threading import Lock

from config import (
    DATABASE_FOLDER,
    GUILD_DATABASE_FILE,
)


_database_lock = Lock()


def initialize_guild_database():
    DATABASE_FOLDER.mkdir(
        parents=True,
        exist_ok=True
    )

    with _database_lock:
        with sqlite3.connect(
            GUILD_DATABASE_FILE,
            timeout=10
        ) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS guild_settings (
                    guild_id INTEGER PRIMARY KEY,
                    setup_complete INTEGER NOT NULL DEFAULT 0,
                    setup_user_id INTEGER,
                    setup_channel_id INTEGER,
                    joined_at TEXT,
                    updated_at TEXT NOT NULL
                )
                """
            )

            connection.commit()


def register_guild(guild_id):
    initialize_guild_database()

    now = datetime.now(
        timezone.utc
    ).isoformat()

    with _database_lock:
        with sqlite3.connect(
            GUILD_DATABASE_FILE,
            timeout=10
        ) as connection:
            connection.execute(
                """
                INSERT INTO guild_settings (
                    guild_id,
                    joined_at,
                    updated_at
                )
                VALUES (?, ?, ?)
                ON CONFLICT(guild_id) DO UPDATE SET
                    updated_at = excluded.updated_at
                """,
                (
                    int(guild_id),
                    now,
                    now
                )
            )

            connection.commit()


def mark_setup_complete(
    guild_id,
    user_id,
    channel_id
):
    initialize_guild_database()

    now = datetime.now(
        timezone.utc
    ).isoformat()

    with _database_lock:
        with sqlite3.connect(
            GUILD_DATABASE_FILE,
            timeout=10
        ) as connection:
            connection.execute(
                """
                INSERT INTO guild_settings (
                    guild_id,
                    setup_complete,
                    setup_user_id,
                    setup_channel_id,
                    joined_at,
                    updated_at
                )
                VALUES (?, 1, ?, ?, ?, ?)
                ON CONFLICT(guild_id) DO UPDATE SET
                    setup_complete = 1,
                    setup_user_id = excluded.setup_user_id,
                    setup_channel_id = excluded.setup_channel_id,
                    updated_at = excluded.updated_at
                """,
                (
                    int(guild_id),
                    int(user_id),
                    int(channel_id),
                    now,
                    now
                )
            )

            connection.commit()


def get_guild_settings(guild_id):
    initialize_guild_database()

    with _database_lock:
        with sqlite3.connect(
            GUILD_DATABASE_FILE,
            timeout=10
        ) as connection:
            row = connection.execute(
                """
                SELECT
                    setup_complete,
                    setup_user_id,
                    setup_channel_id,
                    joined_at,
                    updated_at
                FROM guild_settings
                WHERE guild_id = ?
                """,
                (int(guild_id),)
            ).fetchone()

    if row is None:
        return {
            "setup_complete": False,
            "setup_user_id": None,
            "setup_channel_id": None,
            "joined_at": None,
            "updated_at": None
        }

    return {
        "setup_complete": bool(row[0]),
        "setup_user_id": row[1],
        "setup_channel_id": row[2],
        "joined_at": row[3],
        "updated_at": row[4]
    }


def remove_guild(guild_id):
    initialize_guild_database()

    with _database_lock:
        with sqlite3.connect(
            GUILD_DATABASE_FILE,
            timeout=10
        ) as connection:
            connection.execute(
                """
                DELETE FROM guild_settings
                WHERE guild_id = ?
                """,
                (int(guild_id),)
            )

            connection.commit()
