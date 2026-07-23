import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import data_service


class DataServiceTests(
    unittest.TestCase
):
    def test_guild_deletion_includes_identity_tables(self):
        with tempfile.TemporaryDirectory() as directory:
            database_file = (
                Path(directory) / "identity.db"
            )

            with sqlite3.connect(
                database_file
            ) as connection:
                for table_name in (
                    "user_profiles",
                    "relationships"
                ):
                    connection.execute(
                        f"""
                        CREATE TABLE {table_name} (
                            guild_id INTEGER NOT NULL,
                            user_id INTEGER NOT NULL
                        )
                        """
                    )

                    connection.executemany(
                        f"""
                        INSERT INTO {table_name} (
                            guild_id,
                            user_id
                        )
                        VALUES (?, ?)
                        """,
                        (
                            (100, 200),
                            (101, 200),
                        )
                    )

                connection.commit()

            tables = {
                database_file: (
                    "user_profiles",
                    "relationships",
                )
            }

            with (
                patch.object(
                    data_service,
                    "GUILD_TABLES",
                    tables
                ),
                patch.object(
                    data_service,
                    "forget_guild",
                    return_value=0
                ),
                patch.object(
                    data_service,
                    "clear_guild_conversations",
                    return_value=0
                )
            ):
                result = (
                    data_service.delete_guild_data(
                        100
                    )
                )

            self.assertEqual(
                result["database_rows"],
                2
            )

            with sqlite3.connect(
                database_file
            ) as connection:
                for table_name in (
                    "user_profiles",
                    "relationships"
                ):
                    rows = connection.execute(
                        f"""
                        SELECT guild_id
                        FROM {table_name}
                        """
                    ).fetchall()

                    self.assertEqual(
                        rows,
                        [(101,)]
                    )
