import asyncio
import logging
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.db.session import get_engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def migrate():
    engine = get_engine()
    async with engine.begin() as conn:
        logger.info("Starting versioning migration...")
        
        # 1. Update existing messages to version = -1
        logger.info("Setting all existing messages to version -1 (Latest)...")
        await conn.execute(text("UPDATE message SET version = -1 WHERE version > 0"))
        
        # 2. Drop existing Primary Key constraint
        # Postgres default PK name is {tablename}_pkey
        logger.info("Dropping existing primary key constraint 'message_pkey'...")
        try:
            await conn.execute(text("ALTER TABLE message DROP CONSTRAINT IF EXISTS message_pkey"))
        except Exception as e:
            logger.error(f"Error dropping PK: {e}")
            raise

        # 3. Add new Composite Primary Key
        logger.info("Adding new composite primary key (id, version)...")
        try:
            await conn.execute(text("ALTER TABLE message ADD PRIMARY KEY (id, version)"))
        except Exception as e:
            logger.error(f"Error adding new PK: {e}")
            raise

    await engine.dispose()
    logger.info("Migration completed successfully.")

if __name__ == "__main__":
    asyncio.run(migrate())
