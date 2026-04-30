"""Unit tests for agent api."""

import unittest

from fastapi import HTTPException

from app.api.routers.chat import chat, chat_v2
from app.api.routers.debug import summary
from app.repositories.soil_repository import DatabaseUnavailableError
from app.schemas.request import ChatRequest, ChatV2Request


class DatabaseFailingService:
    """Service helper for database failing."""
    async def achat(self, *args, **kwargs):
        """Handle achat on the database failing service."""
        del args, kwargs
        raise DatabaseUnavailableError("mysql down")

    def get_summary_payload(self):
        """Return summary payload."""
        raise DatabaseUnavailableError("mysql down")


class DatabaseFailingDataAnswerService:
    async def reply(self, *args, **kwargs):
        del args, kwargs
        raise DatabaseUnavailableError("mysql down")


class ChatV2GuidanceService:
    async def reply(self, *args, **kwargs):
        del args, kwargs
        return {
            "turn_id": 1,
            "answer_kind": "guidance",
            "capability": "none",
            "final_text": "我可以帮你查墒情概况、地区/点位/记录明细、按地区汇总，以及查看预警规则和模板。",
            "blocks": [
                {
                    "block_id": "block_guidance_1",
                    "block_type": "guidance_card",
                    "text": "我可以帮你查墒情概况、地区/点位/记录明细、按地区汇总，以及查看预警规则和模板。",
                    "guidance_reason": "safe_hint",
                }
            ],
            "topic": {"topic_family": None, "active_topic_turn_id": None, "primary_block_id": None},
            "turn_context": {},
            "query_ref": {"has_query": False, "snapshot_ids": []},
            "conversation_closed": False,
            "session_reset": False,
            "query_log_entries": [],
        }


class ChatV2ClosingService:
    async def reply(self, *args, **kwargs):
        del args, kwargs
        return {
            "turn_id": 2,
            "answer_kind": "guidance",
            "capability": "none",
            "final_text": "好的，这个话题先结束。有需要时你再继续问我即可。",
            "blocks": [
                {
                    "block_id": "block_guidance_2",
                    "block_type": "guidance_card",
                    "text": "好的，这个话题先结束。有需要时你再继续问我即可。",
                    "guidance_reason": "closing",
                }
            ],
            "topic": {"topic_family": None, "active_topic_turn_id": None, "primary_block_id": None},
            "turn_context": {"context_version": 3, "closed": True, "last_closed_turn_id": 2},
            "query_ref": {"has_query": False, "snapshot_ids": []},
            "conversation_closed": True,
            "session_reset": False,
            "query_log_entries": [],
        }


class ChatV2ValueErrorService:
    async def reply(self, *args, **kwargs):
        del args, kwargs
        raise ValueError("bad request")


class AgentApiTest(unittest.IsolatedAsyncioTestCase):
    """Test cases for agent api."""
    async def test_chat_returns_503_when_database_is_unavailable(self):
        """Verify chat returns 503 when database is unavailable."""
        request = ChatRequest(message="最近墒情怎么样", session_id="s1", turn_id=1)

        with self.assertRaises(HTTPException) as caught:
            await chat(request, service=DatabaseFailingService())

        self.assertEqual(caught.exception.status_code, 503)
        self.assertIn("数据库不可用", str(caught.exception.detail))

    async def test_summary_returns_503_when_database_is_unavailable(self):
        """Verify summary returns 503 when database is unavailable."""
        with self.assertRaises(HTTPException) as caught:
            summary(service=DatabaseFailingService())

        self.assertEqual(caught.exception.status_code, 503)
        self.assertIn("数据库不可用", str(caught.exception.detail))

    async def test_chat_v2_returns_guidance_payload_without_error(self):
        request = ChatV2Request(message="上岛咖啡京东卡", session_id="s1", turn_id=1)

        result = await chat_v2(request, service=ChatV2GuidanceService())

        self.assertEqual(result["answer_kind"], "guidance")
        self.assertEqual(result["blocks"][0]["guidance_reason"], "safe_hint")

    async def test_chat_v2_preserves_closing_payload_without_error(self):
        request = ChatV2Request(message="谢谢", session_id="s1", turn_id=2)

        result = await chat_v2(request, service=ChatV2ClosingService())

        self.assertEqual(result["answer_kind"], "guidance")
        self.assertTrue(result["conversation_closed"])
        self.assertTrue(result["turn_context"]["closed"])
        self.assertEqual(result["blocks"][0]["guidance_reason"], "closing")

    async def test_chat_v2_returns_503_when_database_is_unavailable(self):
        request = ChatV2Request(message="最近墒情怎么样", session_id="s1", turn_id=1)

        with self.assertRaises(HTTPException) as caught:
            await chat_v2(request, service=DatabaseFailingDataAnswerService())

        self.assertEqual(caught.exception.status_code, 503)
        self.assertIn("数据库不可用", str(caught.exception.detail))

    async def test_chat_v2_returns_400_when_value_error_is_raised(self):
        request = ChatV2Request(message="最近墒情怎么样", session_id="s1", turn_id=1)

        with self.assertRaises(HTTPException) as caught:
            await chat_v2(request, service=ChatV2ValueErrorService())

        self.assertEqual(caught.exception.status_code, 400)
        self.assertIn("bad request", str(caught.exception.detail))


if __name__ == "__main__":
    unittest.main()
