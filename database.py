import aiosqlite

from config import CORE_DATABASE_FILE, DATABASE_FOLDER


async def connect():
    DATABASE_FOLDER.mkdir(
        parents=True,
        exist_ok=True
    )

    db = await aiosqlite.connect(
        CORE_DATABASE_FILE
    )
    return db


async def initialize():
    db = await connect()
    await db.commit()
    await db.close()
