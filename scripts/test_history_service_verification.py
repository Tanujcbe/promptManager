import asyncio
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from app.db.session import get_session_factory
from app.services import message_service
from app.schemas.message import MessageCreate, MessageUpdate, MessageType
from app.models.user import User
from sqlalchemy import select

async def test_version_history():
    session_factory = get_session_factory()
    async with session_factory() as db:
        print("Setting up test data...")
        # Get a user
        result = await db.execute(select(User).limit(1))
        user = result.scalar_one_or_none()
        if not user:
            print("No user found to test with.")
            return

        print(f"Using user: {user.id}")

        # Create a message
        print("Creating message...")
        msg_data = MessageCreate(
            title="History Test",
            content="Version 0",
            message_type=MessageType.PROMPT
        )
        message = await message_service.create_message(db, user.id, msg_data)
        message_id = message.id
        print(f"Created message {message_id} (Version {message.version})")

        # Update message multiple times to create history
        for i in range(1, 10):
            print(f"Updating message to version {i}...")
            update_data = MessageUpdate(content=f"Version {i}")
            await message_service.update_message(db, user.id, message_id, update_data)
        
        # Now we should have:
        # Latest: Version -1 (content="Version 9")
        # History: Versions 1-9 (contents "Version 0" to "Version 8")
        # Wait, the first create is version -1.
        # Update 1: 
        #   - Archives current -1 as Version 1 (content="Version 0")
        #   - Updates -1 to content="Version 1"
        # Update 2:
        #   - Archives current -1 as Version 2 (content="Version 1")
        #   - Updates -1 to content="Version 2"
        # ...
        # Update 9:
        #   - Archives current -1 as Version 9 (content="Version 8")
        #   - Updates -1 to content="Version 9"
        
        # So history should contain versions 1 to 9.
        
        print("\nTesting History API via Service...")
        
        # Test Page 1 (default size 5)
        # Should return versions 9, 8, 7, 6, 5 (descending order)
        messages, total = await message_service.get_message_history(
            db, user.id, message_id, page=1, page_size=5
        )
        print(f"Page 1: Got {len(messages)} messages. Total: {total}")
        for m in messages:
            print(f"- Version {m.version}: {m.content}")
            
        assert len(messages) == 5
        assert messages[0].version == 9
        assert messages[4].version == 5
        
        # Test Page 2
        # Should return versions 4, 3, 2, 1
        messages, total = await message_service.get_message_history(
            db, user.id, message_id, page=2, page_size=5
        )
        print(f"Page 2: Got {len(messages)} messages. Total: {total}")
        for m in messages:
            print(f"- Version {m.version}: {m.content}")

        assert len(messages) == 4
        assert messages[0].version == 4
        assert messages[3].version == 1
        
        # Clean up
        print("\nCleaning up...")
        await message_service.delete_message(db, user.id, message_id)
        print("Test passed successfully!")

if __name__ == "__main__":
    asyncio.run(test_version_history())
