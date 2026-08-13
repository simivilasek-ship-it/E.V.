import os
import sys
import unittest
from unittest.mock import MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app_core import EVApp


class TestGuiLogic(unittest.TestCase):
    def test_gui_helper_enqueue(self):
        app = EVApp.__new__(EVApp)
        app.gui = MagicMock()
        app.gui.root = MagicMock()
        app._gui(lambda: None)
        app.gui.root.after.assert_called_once()
