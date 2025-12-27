import asyncio
import logging
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from app.db.session import get_engine, get_session_factory
from app.services import message_service
from app.schemas.message import MessageCreate, MessageUpdate, MessageType
from app.models.user import User

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_versioning():
    engine = get_engine()
    SessionLocal = get_session_factory()
    
    async with SessionLocal() as db:
        logger.info("Starting versioning test...")
        
        # 1. Get a user
        result = await db.execute(select(User).limit(1))
        user = result.scalar_one_or_none()
        if not user:
            logger.error("No users found in DB. Create a user first.")
            return
        logger.info(f"Using user: {user.id}")
        
        # 2. Create Message
        data = MessageCreate(
            title="Version Test",
            content="Content v1",
            message_type=MessageType.PROMPT
        )
        msg = await message_service.create_message(db, user.id, data)
        logger.info(f"Created Message: id={msg.id}, version={msg.version}, content='{msg.content}'")
        assert msg.version == -1
        assert msg.content == "Content v1"
        
        msg_id = msg.id
        
        # 3. Update Message
        update_data = MessageUpdate(content="Content v2")
        updated_msg = await message_service.update_message(db, user.id, msg_id, update_data)
        logger.info(f"Updated Message: id={updated_msg.id}, version={updated_msg.version}, content='{updated_msg.content}'")
        assert updated_msg.version == -1
        assert updated_msg.content == "Content v2"
        assert updated_msg.id == msg_id
        
        # 4. Check History (Expect version 1 with "Content v1")
        # We need to manually query for version 1 since list filters it out
        history_msg = await message_service.get_message_by_id(db, user.id, msg_id, version=1)
        logger.info(f"History Message: id={history_msg.id}, version={history_msg.version}, content='{history_msg.content}'")
        assert history_msg.version == 1
        assert history_msg.content == "Content v1"
        assert history_msg.id == msg_id
        
        # 5. List Messages (Should only see version -1)
        messages, total = await message_service.list_messages(db, user.id)
        found = False
        for m in messages:
            if m.id == msg_id:
                logger.info(f"List found: id={m.id}, version={m.version}")
                assert m.version == -1
                found = True
        assert found
        
        # 6. Cleanup
        await message_service.delete_message(db, user.id, msg_id)
        logger.info("Test message deleted.")
        
    await engine.dispose()
    logger.info("Verification passed!")

if __name__ == "__main__":
    asyncio.run(test_versioning())
