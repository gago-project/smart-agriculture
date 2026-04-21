import unittest

from app.services.agent_service import SoilAgentService
from support_repositories import SeedSoilRepository


class AgentSummaryTest(unittest.TestCase):
    def test_summary_payload_includes_devices(self):
        service = SoilAgentService(repository=SeedSoilRepository())
        summary = service.get_summary_payload()

        self.assertIn('latest_time', summary)
        self.assertIn('devices', summary)
        self.assertGreaterEqual(len(summary['devices']), 1)
        self.assertIn('display_label', summary['devices'][0])


if __name__ == '__main__':
    unittest.main()
