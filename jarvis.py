"""
JARVIS — Desktop aplikace
Ovládá celý počítač hlasem nebo textem.
"""

from config import __version__
from app_core import JarvisApp


if __name__ == "__main__":
    print(f"JARVIS v{__version__}")
    JarvisApp().run()
