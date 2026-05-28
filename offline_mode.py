"""
JARVIS v4.2 — Offline Mode System
Umožňuje fungovat offline s fallback LLM a queued commands
"""

import logging
import json
import threading
import time
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from enum import Enum
from queue import Queue

logger = logging.getLogger(__name__)


class OfflineStatus(Enum):
    """Status online/offline režimu"""
    ONLINE = "online"
    OFFLINE = "offline"
    DEGRADED = "degraded"  # Částečný offline


@dataclass
class QueuedCommand:
    """Příkaz čekající na synchronizaci"""
    id: str
    action: str
    params: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    synced: bool = False
    synced_at: Optional[datetime] = None
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "action": self.action,
            "params": self.params,
            "timestamp": self.timestamp.isoformat(),
            "synced": self.synced,
            "synced_at": self.synced_at.isoformat() if self.synced_at else None,
            "error": self.error,
        }


class OfflineManager:
    """Správuje offline režim a command queueing"""
    
    def __init__(self, config: Dict[str, Any]) -> None:
        self.config: Dict[str, Any] = config
        self._status: OfflineStatus = OfflineStatus.ONLINE
        self._command_queue: Queue[QueuedCommand] = Queue()
        self._synced_commands: List[QueuedCommand] = []
        self._lock: threading.Lock = threading.Lock()
        
        # Offline knowledge base
        self._knowledge_base: Dict[str, Any] = self._load_knowledge_base()
        
        # Persist queue do souboru — absolutní cesta vedle offline_mode.py
        self._queue_file: Path = Path(__file__).parent / ".offline_queue.json"
        self._load_queued_commands()
    
    def set_status(self, status: OfflineStatus) -> None:
        """Nastav offline status"""
        with self._lock:
            self._status = status
            logger.info(f"Offline status změněn na: {status.value}")
    
    def get_status(self) -> OfflineStatus:
        """Vrátí aktuální offline status"""
        with self._lock:
            return self._status
    
    def queue_command(self, action: str, params: Dict[str, Any]) -> str:
        """Zařadí příkaz do fronty (offline mode)"""
        import uuid
        cmd_id = str(uuid.uuid4())
        
        cmd = QueuedCommand(
            id=cmd_id,
            action=action,
            params=params
        )
        
        with self._lock:
            self._command_queue.put(cmd)
            self._persist_queue()
        
        logger.info(f"Příkaz {action} zařazen do fronty (ID: {cmd_id})")
        return cmd_id
    
    def get_queued_commands(self) -> List[QueuedCommand]:
        """Vrátí všechny zařazené příkazy"""
        with self._lock:
            commands = []
            while not self._command_queue.empty():
                commands.append(self._command_queue.get())
            return commands
    
    def sync_commands(self, sync_func: Callable[[str, Dict[str, Any]], bool]) -> Dict[str, Any]:
        """Synchronizuj frontu zařazených příkazů"""
        commands = self.get_queued_commands()
        
        stats = {
            "total": len(commands),
            "synced": 0,
            "failed": 0,
            "errors": []
        }
        
        for cmd in commands:
            try:
                success = sync_func(cmd.action, cmd.params)
                
                if success:
                    cmd.synced = True
                    cmd.synced_at = datetime.now()
                    stats["synced"] += 1
                else:
                    cmd.error = "Synchronizace selhala"
                    stats["failed"] += 1
                    stats["errors"].append(cmd.error)
            except Exception as e:
                cmd.error = str(e)
                stats["failed"] += 1
                stats["errors"].append(str(e))
                logger.error(f"Sync chyba pro {cmd.action}: {e}")
            
            with self._lock:
                self._synced_commands.append(cmd)
        
        # Vymaž peristent queue po sync
        with self._lock:
            self._queue_file.unlink(missing_ok=True)
        
        logger.info(f"Sync completed: {stats['synced']}/{stats['total']} synced")
        return stats
    
    def get_offline_response(self, query: str) -> str:
        """Vrátí offline response z knowledge base"""
        # Jednoduchý keyword-based lookup
        query_lower = query.lower()
        
        # Kontroluj common queries
        if "čas" in query_lower or "kolik" in query_lower:
            return f"Čas (offline): {time.strftime('%H:%M:%S')}"
        
        elif "datum" in query_lower or "jaké je datum" in query_lower:
            return f"Datum (offline): {time.strftime('%d.%m.%Y')}"
        
        elif "co je" in query_lower or "definice" in query_lower:
            # Zkus knowledge base
            for key, value in self._knowledge_base.items():
                if key.lower() in query_lower:
                    return f"(Offline) {value}"
        
        return "Offline: Nemohu odpovědět. Připoj se k internetu pro úplnější odpovědi."
    
    def _load_knowledge_base(self) -> Dict[str, Any]:
        """Načti offline knowledge base"""
        kb_file = Path(__file__).parent / ".offline_kb.json"
        
        if not kb_file.exists():
            # Vytvoř výchozí knowledge base
            kb = {
                "Python": "Python je programovací jazyk zaměřený na čitelnost a jednoduchost.",
                "JARVIS": "JARVIS je hlasový AI asistent poháněný Ollama.",
                "Offline": "Offline režim umožňuje fungovat bez internetu s omezenou funkčností.",
            }
            try:
                with open(kb_file, 'w', encoding='utf-8') as f:
                    json.dump(kb, f, ensure_ascii=False, indent=2)
            except Exception as e:
                logger.error(f"Chyba při vytváření KB: {e}")
            return kb
        
        try:
            with open(kb_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Chyba při načítání KB: {e}")
            return {}
    
    def _persist_queue(self) -> None:
        """Ulož frontu do souboru"""
        try:
            commands = []
            while not self._command_queue.empty():
                cmd = self._command_queue.get()
                commands.append(asdict(cmd))
                self._command_queue.put(cmd)  # Vrátí zpět do fronty
            
            with open(self._queue_file, 'w', encoding='utf-8') as f:
                json.dump(commands, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Chyba při persist queue: {e}")
    
    def _load_queued_commands(self) -> None:
        """Načti zařazené příkazy z souboru"""
        if not self._queue_file.exists():
            return
        
        try:
            with open(self._queue_file, 'r', encoding='utf-8') as f:
                commands_data = json.load(f)
            
            for cmd_data in commands_data:
                # Rekonstruuj datetime objekty
                cmd_data['timestamp'] = datetime.fromisoformat(cmd_data['timestamp'])
                if cmd_data.get('synced_at'):
                    cmd_data['synced_at'] = datetime.fromisoformat(cmd_data['synced_at'])
                
                cmd = QueuedCommand(**cmd_data)
                self._command_queue.put(cmd)
            
            logger.info(f"Načteno {len(commands_data)} zařazených příkazů")
        except Exception as e:
            logger.error(f"Chyba při načítání queue: {e}")


class OfflineLLMFallback:
    """Fallback LLM pro offline režim"""
    
    def __init__(self, config: Dict[str, Any]) -> None:
        self.config = config
        self.offline_manager = OfflineManager(config)
    
    def chat(self, user_message: str) -> str:
        """Vrátí offline odpověď"""
        if self.offline_manager.get_status() == OfflineStatus.ONLINE:
            return None  # Fallback není potřeba
        
        return self.offline_manager.get_offline_response(user_message)
    
    def is_offline_mode(self) -> bool:
        """Vrátí jestli je offline režim"""
        return self.offline_manager.get_status() in [OfflineStatus.OFFLINE, OfflineStatus.DEGRADED]


# Singleton instance
_offline_manager: Optional[OfflineManager] = None


def get_offline_manager(config: Optional[Dict[str, Any]] = None) -> OfflineManager:
    """Vrátí singleton OfflineManager"""
    global _offline_manager
    if _offline_manager is None:
        from config import CONFIG
        _offline_manager = OfflineManager(config or CONFIG)
    return _offline_manager
