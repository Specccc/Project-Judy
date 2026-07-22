import aiosqlite
from pathlib import Path

DATABASE_PATH = Path("database/judy.db")


async def connect():
    DATABASE_PATH.parent.mkdir(exist_ok=True)

    db = await aiosqlite.connect(DATABASE_PATH)
    return db


async def initialize():
    db = await connect()
    await db.commit()
    await db.close()
