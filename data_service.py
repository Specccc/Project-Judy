import sqlite3

from config import (
    AMBIENT_DATABASE_FILE,
    CHAT_DATABASE_FILE,
    GUILD_DATABASE_FILE,
    MODERATION_DATABASE_FILE,
    XP_DATABASE_FILE,
)
from memory.memory_manager import (
    clear_guild_conversations,
    forget_guild,
)


GUILD_TABLES = {
    CHAT_DATABASE_FILE: (
        "chat_channels",
    ),
    AMBIENT_DATABASE_FILE: (
        "ambient_settings",
        "ambient_ignored_channels",
    ),
    XP_DATABASE_FILE: (
        "xp_users",
    ),
    MODERATION_DATABASE_FILE: (
        "warnings",
    ),
    GUILD_DATABASE_FILE: (
        "guild_settings",
    ),
}


def _table_exists(
    connection,
    table_name
):
    row = connection.execute(
        """
        SELECT 1
        FROM sqlite_master
        WHERE type = 'table'
        AND name = ?
        """,
        (table_name,)
    ).fetchone()

    return row is not None


def delete_guild_data(
    guild_id,
    channel_ids=()
):
    guild_id = int(guild_id)
    deleted_rows = 0

    for database_file, tables in (
        GUILD_TABLES.items()
    ):
        if not database_file.exists():
            continue

        with sqlite3.connect(
            database_file,
            timeout=10
        ) as connection:
            for table_name in tables:
                if not _table_exists(
                    connection,
                    table_name
                ):
                    continue

                cursor = connection.execute(
                    f"DELETE FROM {table_name} "
                    "WHERE guild_id = ?",
                    (guild_id,)
                )

                deleted_rows += max(
                    cursor.rowcount,
                    0
                )

            connection.commit()

    deleted_memories = forget_guild(
        guild_id
    )

    deleted_conversations = (
        clear_guild_conversations(
            channel_ids
        )
    )

    return {
        "database_rows": deleted_rows,
        "user_memory_profiles": (
            deleted_memories
        ),
        "conversation_channels": (
            deleted_conversations
        ),
    }
