import unittest

from fastapi import HTTPException

from app.api.routers.chat import chat
from app.api.routers.debug import summary
from app.repositories.soil_repository import DatabaseUnavailableError
from app.schemas.request import ChatRequest


class DatabaseFailingService:
    async def achat(self, *args, **kwargs):
        del args, kwargs
        raise DatabaseUnavailableError("mysql down")

    def get_summary_payload(self):
        raise DatabaseUnavailableError("mysql down")


class AgentApiTest(unittest.IsolatedAsyncioTestCase):
    async def test_chat_returns_503_when_database_is_unavailable(self):
        request = ChatRequest(message="最近墒情怎么样", session_id="s1", turn_id=1)

        with self.assertRaises(HTTPException) as caught:
            await chat(request, service=DatabaseFailingService())

        self.assertEqual(caught.exception.status_code, 503)
        self.assertIn("数据库不可用", str(caught.exception.detail))

    async def test_summary_returns_503_when_database_is_unavailable(self):
        with self.assertRaises(HTTPException) as caught:
            summary(service=DatabaseFailingService())

        self.assertEqual(caught.exception.status_code, 503)
        self.assertIn("数据库不可用", str(caught.exception.detail))


if __name__ == "__main__":
    unittest.main()
