import unittest
from unittest.mock import AsyncMock

from ai_service import AIService


class AIServiceTests(
    unittest.IsolatedAsyncioTestCase
):
    async def test_chat_prompt_contains_identity_context(self):
        service = AIService()
        service.system_prompt = "SYSTEM"
        service._generate = AsyncMock(
            return_value="Reply"
        )

        result = await service.generate_chat_reply(
            user_name="Discord Name",
            user_id=200,
            message="Hello",
            conversation_context="User: Earlier",
            memory_context="- favourite_game: Cyberpunk",
            identity_context=(
                "Preferred name: V\n"
                "Relationship tier: choom"
            ),
            server_name="Night City"
        )

        self.assertEqual(
            result,
            "Reply"
        )

        prompt = (
            service._generate.await_args.args[0]
        )

        self.assertIn(
            "Preferred name: V",
            prompt
        )
        self.assertIn(
            "Relationship tier: choom",
            prompt
        )
        self.assertIn(
            "Never quote relationship scores",
            prompt
        )
