import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def create_user_table():
    connection = sqlite3.connect(os.path.join(BASE_DIR, "user_warnings.db"))
    cursor = connection.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS "user_per_guild" (
            "user_id" INTEGER,
            "warning_count" INTEGER,
            "guild_id" INTEGER,
            PRIMARY KEY("user_id","guild_id")
        )
    """)
    connection.commit()
    connection.close()

def increase_and_get_warnings(user_id: int, guild_id: int) -> int:
    connection = sqlite3.connect(os.path.join(BASE_DIR, "user_warnings.db"))
    cursor = connection.cursor()

    cursor.execute("""
        SELECT warning_count FROM user_per_guild
        WHERE user_id = ? AND guild_id = ?;
    """, (user_id, guild_id))
    result = cursor.fetchone()

    if result is None:
        cursor.execute("""
            INSERT INTO user_per_guild (user_id, warning_count, guild_id)
            VALUES (?, 1, ?);
        """, (user_id, guild_id))
        connection.commit()
        connection.close()
        return 1

    new_count = result[0] + 1
    cursor.execute("""
        UPDATE user_per_guild SET warning_count = ?
        WHERE user_id = ? AND guild_id = ?;
    """, (new_count, user_id, guild_id))
    connection.commit()
    connection.close()
    return new_count
