import unittest
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from security import is_action_allowed, requires_confirmation


class TestSecurity(unittest.TestCase):
    def test_is_action_allowed(self):
        self.assertTrue(is_action_allowed('open_app'))
        self.assertFalse(is_action_allowed('unknown_action'))

    def test_requires_confirmation(self):
        self.assertTrue(requires_confirmation('delete_file', {}))
        self.assertFalse(requires_confirmation('open_app', {}))
