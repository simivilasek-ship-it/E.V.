"""
JARVIS — Cache Manager System
Caching strategie pro LLM responses, API calls, atd.
"""

import logging
import json
import hashlib
import threading
from typing import Dict, Any, Optional, Callable, TypeVar, Generic
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

T = TypeVar('T')


@dataclass
class CacheEntry(Generic[T]):
    """Záznam v cache"""
    key: str
    value: T
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    hits: int = 0
    
    def is_expired(self) -> bool:
        """Kontroluj jestli je záznam prošlý"""
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at
    
    def touch(self) -> None:
        """Aktualizuj čas posledního přístupu"""
        self.hits += 1


class CacheBackend(ABC):
    """Abstraktní base třída pro cache backend"""
    
    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """Vrátí hodnotu z cache"""
        pass
    
    @abstractmethod
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Uloží hodnotu do cache"""
        pass
    
    @abstractmethod
    def delete(self, key: str) -> None:
        """Vymaž hodnotu z cache"""
        pass
    
    @abstractmethod
    def clear(self) -> None:
        """Vymaž všechno z cache"""
        pass


class MemoryCache(CacheBackend):
    """In-memory cache (dict-based)"""
    
    def __init__(self, max_size: int = 1000) -> None:
        self.max_size: int = max_size
        self._cache: Dict[str, CacheEntry] = {}
        self._lock: threading.Lock = threading.Lock()
    
    def get(self, key: str) -> Optional[Any]:
        """Vrátí hodnotu z cache"""
        with self._lock:
            if key not in self._cache:
                return None
            
            entry = self._cache[key]
            
            if entry.is_expired():
                del self._cache[key]
                return None
            
            entry.touch()
            return entry.value
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Uloží hodnotu do cache"""
        with self._lock:
            expires_at: Optional[datetime] = None
            if ttl:
                expires_at = datetime.now() + timedelta(seconds=ttl)
            
            entry = CacheEntry(
                key=key,
                value=value,
                expires_at=expires_at
            )
            
            self._cache[key] = entry
            
            # Vymaž nejstaší položky když je cache plný
            if len(self._cache) > self.max_size:
                # LRU eviction - vymaž položky s nejméně hitů
                oldest = min(self._cache.values(), key=lambda e: e.hits)
                del self._cache[oldest.key]
    
    def delete(self, key: str) -> None:
        """Vymaž hodnotu z cache"""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
    
    def clear(self) -> None:
        """Vymaž všechno z cache"""
        with self._lock:
            self._cache.clear()
    
    def stats(self) -> Dict[str, Any]:
        """Vrátí statistiky cache"""
        with self._lock:
            return {
                "size": len(self._cache),
                "max_size": self.max_size,
                "total_hits": sum(e.hits for e in self._cache.values()),
            }


class DiskCache(CacheBackend):
    """Disk-based cache (JSON files)"""
    
    def __init__(self, cache_dir: str = ".cache") -> None:
        self.cache_dir: Path = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self._lock: threading.Lock = threading.Lock()
    
    def _get_cache_path(self, key: str) -> Path:
        """Vrátí cestu k cache souboru"""
        # Hash key aby se vešel do filename
        key_hash = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"{key_hash}.json"
    
    def get(self, key: str) -> Optional[Any]:
        """Vrátí hodnotu z cache"""
        with self._lock:
            cache_path = self._get_cache_path(key)
            
            if not cache_path.exists():
                return None
            
            try:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                entry = CacheEntry(
                    key=data['key'],
                    value=data['value'],
                    created_at=datetime.fromisoformat(data['created_at']),
                    expires_at=datetime.fromisoformat(data['expires_at']) if data['expires_at'] else None,
                    hits=data['hits']
                )
                
                if entry.is_expired():
                    cache_path.unlink()
                    return None
                
                entry.touch()
                return entry.value
            except Exception as e:
                logger.error(f"Chyba při čtení cache: {e}")
                return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Uloží hodnotu do cache"""
        with self._lock:
            cache_path = self._get_cache_path(key)
            
            expires_at = None
            if ttl:
                expires_at = (datetime.now() + timedelta(seconds=ttl)).isoformat()
            
            data = {
                'key': key,
                'value': value,
                'created_at': datetime.now().isoformat(),
                'expires_at': expires_at,
                'hits': 0,
            }
            
            try:
                with open(cache_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            except Exception as e:
                logger.error(f"Chyba při zápisu cache: {e}")
    
    def delete(self, key: str) -> None:
        """Vymaž hodnotu z cache"""
        with self._lock:
            cache_path = self._get_cache_path(key)
            if cache_path.exists():
                cache_path.unlink()
    
    def clear(self) -> None:
        """Vymaž všechno z cache"""
        with self._lock:
            for f in self.cache_dir.glob("*.json"):
                f.unlink()


class CacheManager:
    """Hlavní cache manager"""
    
    def __init__(self, backends: Optional[Dict[str, CacheBackend]] = None) -> None:
        self.backends: Dict[str, CacheBackend] = backends or {
            "memory": MemoryCache(max_size=500),
            "disk": DiskCache(cache_dir=".cache"),
        }
        self._stats: Dict[str, Dict[str, int]] = {name: {"hits": 0, "misses": 0} for name in self.backends}
    
    def get(self, key: str, backend: str = "memory") -> Optional[Any]:
        """Vrátí hodnotu z cache"""
        if backend not in self.backends:
            logger.warning(f"Backend '{backend}' není dostupný")
            return None
        
        value = self.backends[backend].get(key)
        
        if value is not None:
            self._stats[backend]["hits"] += 1
        else:
            self._stats[backend]["misses"] += 1
        
        return value
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None, backend: str = "memory") -> None:
        """Uloží hodnotu do cache"""
        if backend not in self.backends:
            logger.warning(f"Backend '{backend}' není dostupný")
            return
        
        self.backends[backend].set(key, value, ttl)
    
    def delete(self, key: str, backend: Optional[str] = None) -> None:
        """Vymaž hodnotu z cache"""
        if backend:
            if backend in self.backends:
                self.backends[backend].delete(key)
        else:
            # Vymaž ze všech backendů
            for b in self.backends.values():
                b.delete(key)
    
    def clear(self, backend: Optional[str] = None) -> None:
        """Vymaž cache"""
        if backend:
            if backend in self.backends:
                self.backends[backend].clear()
        else:
            for b in self.backends.values():
                b.clear()
    
    def cache_response(self, func: Callable, *args, ttl: int = 3600, **kwargs) -> Any:
        """Decorator pro caching funkcí"""
        # Vytvoř cache key
        key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
        
        # Zkus memory cache
        result = self.get(key, backend="memory")
        if result is not None:
            logger.debug(f"Cache hit: {key}")
            return result
        
        # Zkus disk cache
        result = self.get(key, backend="disk")
        if result is not None:
            logger.debug(f"Cache hit (disk): {key}")
            self.set(key, result, ttl=ttl, backend="memory")  # Stáhni do memory
            return result
        
        # Zavolej funkci
        logger.debug(f"Cache miss: {key}")
        result = func(*args, **kwargs)
        
        # Ulož do cache
        self.set(key, result, ttl=ttl, backend="memory")
        self.set(key, result, ttl=ttl, backend="disk")
        
        return result
    
    def get_stats(self) -> Dict[str, Dict[str, Any]]:
        """Vrátí statistiky cache"""
        stats = {}
        for backend_name, backend in self.backends.items():
            stats[backend_name] = {
                "hits": self._stats[backend_name]["hits"],
                "misses": self._stats[backend_name]["misses"],
            }
            
            # Přidej backend-specific stats
            if hasattr(backend, 'stats'):
                stats[backend_name].update(backend.stats())
        
        return stats


# Singleton instance
_cache_manager: Optional[CacheManager] = None


def get_cache_manager(config: Optional[Dict[str, Any]] = None) -> CacheManager:
    """Vrátí singleton CacheManager"""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager
