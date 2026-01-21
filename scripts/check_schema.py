import asyncio
import logging
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.db.session import get_engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def check_schema():
    engine = get_engine()
    async with engine.connect() as conn:
        logger.info("Checking 'message' table Primary Key columns...")
        result = await conn.execute(text("""
            SELECT c.column_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.constraint_column_usage ccu 
                ON ccu.constraint_name = tc.constraint_name
            JOIN information_schema.columns c 
                ON c.table_name = tc.table_name AND c.column_name = ccu.column_name
            WHERE tc.table_name = 'message' 
            AND tc.constraint_type = 'PRIMARY KEY';
        """))
        columns = [row[0] for row in result.fetchall()]
        logger.info(f"Primary Key Columns: {columns}")
        
        if 'id' in columns and 'version' in columns:
            logger.info("✅ SUCCESS: Composite Primary Key (id, version) is active.")
        else:
            logger.error(f"❌ ERROR: Unexpected Primary Key structure: {columns}")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(check_schema())
