"""
JARVIS v3.0 — Idle detektor
Detekuje nečinnost uživatele a přepíná do úsporného režimu.
"""

import time
import logging
import threading
from datetime import datetime

logger = logging.getLogger(__name__)


class IdleDetector:
    """
    Detekuje nečinnost uživatele.
    
    Po uplynutí idle_timeout bez resetu zavolá on_idle callback.
    Při resetu (uživatel něco dělá) zavolá on_active callback.
    """
    
    def __init__(
        self,
        idle_timeout: int = 30,  # vteřin
        on_idle: callable = None,
        on_active: callable = None,
        check_interval: float = 1.0,
    ):
        self.idle_timeout = idle_timeout
        self.on_idle = on_idle
        self.on_active = on_active
        self.check_interval = check_interval
        
        self._last_activity = time.time()
        self._is_idle = False
        self._running = False
        self._thread = None
    
    def start(self):
        """Spustí detekci nečinnosti"""
        if self._running:
            return
        self._running = True
        self._last_activity = time.time()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        logger.debug(f"Idle detektor spuštěn (timeout: {self.idle_timeout}s)")
    
    def stop(self):
        """Zastaví detekci"""
        self._running = False
        logger.debug("Idle detektor zastaven")
    
    def reset(self):
        """Resetuje časovač nečinnosti"""
        self._last_activity = time.time()
        if self._is_idle:
            self._is_idle = False
            if self.on_active:
                self.on_active()
    
    def _run(self):
        """Hlavní smyčka detekce"""
        while self._running:
            elapsed = time.time() - self._last_activity
            
            if not self._is_idle and elapsed >= self.idle_timeout:
                self._is_idle = True
                if self.on_idle:
                    self.on_idle()
                logger.debug(f"Nečinnost: {elapsed:.0f}s")
            
            time.sleep(self.check_interval)