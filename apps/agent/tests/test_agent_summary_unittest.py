"""Unit tests for agent summary."""

import unittest

from app.services.agent_service import SoilAgentService
from support_repositories import SeedSoilRepository


class AgentSummaryTest(unittest.TestCase):
    """Test cases for agent summary."""
    def test_summary_payload_includes_devices(self):
        """Verify summary payload includes devices."""
        service = SoilAgentService(repository=SeedSoilRepository())
        summary = service.get_summary_payload()

        self.assertIn('latest_time', summary)
        self.assertIn('devices', summary)
        self.assertIn('device_count', summary)
        self.assertGreaterEqual(len(summary['devices']), 1)
        self.assertNotIn('display_label', summary['devices'][0])
        self.assertNotIn('soil_status', summary['devices'][0])


if __name__ == '__main__':
    unittest.main()
