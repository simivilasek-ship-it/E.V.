"""
JARVIS v4.4 — Health Check System
Monitorování zdraví a dostupnosti komponent
"""

import logging
import psutil
import requests
import threading
import time
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Status zdraví komponent"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    """Výsledek health check testu"""
    component: str
    status: HealthStatus
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
    response_time_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Konvertuj na dict"""
        return {
            "component": self.component,
            "status": self.status.value,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "response_time_ms": self.response_time_ms,
            "metadata": self.metadata,
        }


class HealthChecker:
    """Systém pro monitorování zdraví komponent"""
    
    def __init__(self, config: Dict[str, Any]) -> None:
        self.config: Dict[str, Any] = config
        self._results: List[HealthCheckResult] = []
        self._lock: threading.Lock = threading.Lock()
        self._checks: Dict[str, Callable] = {}
        self._register_default_checks()
    
    def _register_default_checks(self) -> None:
        """Zaregistruj výchozí kontroly"""
        self.register_check("ollama", self._check_ollama)
        self.register_check("memory", self._check_memory)
        self.register_check("disk", self._check_disk)
        self.register_check("cpu", self._check_cpu)
        self.register_check("network", self._check_network)
    
    def register_check(self, name: str, check_func: Callable) -> None:
        """Zaregistruj novu health check funkci"""
        self._checks[name] = check_func
        logger.info(f"Health check zaregistrován: {name}")
    
    def check_all(self) -> Dict[str, HealthCheckResult]:
        """Spusť všechny health checks"""
        results: Dict[str, HealthCheckResult] = {}
        
        for name, check_func in self._checks.items():
            try:
                start_time: float = time.time()
                result: HealthCheckResult = check_func()
                result.response_time_ms = (time.time() - start_time) * 1000
                
                with self._lock:
                    results[name] = result
                    self._results.append(result)
                
                logger.debug(f"Health check '{name}': {result.status.value}")
            except Exception as e:
                logger.error(f"Health check '{name}' selhalo: {e}")
                result = HealthCheckResult(
                    component=name,
                    status=HealthStatus.UNHEALTHY,
                    message=f"Chyba: {str(e)}"
                )
                with self._lock:
                    results[name] = result
                    self._results.append(result)
        
        return results
    
    def check(self, component: str) -> Optional[HealthCheckResult]:
        """Spusť health check konkrétní komponenty"""
        if component not in self._checks:
            return None
        
        try:
            start_time: float = time.time()
            result: HealthCheckResult = self._checks[component]()
            result.response_time_ms = (time.time() - start_time) * 1000
            
            with self._lock:
                self._results.append(result)
            
            return result
        except Exception as e:
            logger.error(f"Health check '{component}' selhalo: {e}")
            return HealthCheckResult(
                component=component,
                status=HealthStatus.UNHEALTHY,
                message=f"Chyba: {str(e)}"
            )
    
    def get_status(self) -> HealthStatus:
        """Vrátí celkový status"""
        if not self._results:
            return HealthStatus.UNKNOWN
        
        with self._lock:
            recent_results = self._results[-len(self._checks):]
        
        statuses: List[HealthStatus] = [r.status for r in recent_results]
        
        if any(s == HealthStatus.UNHEALTHY for s in statuses):
            return HealthStatus.UNHEALTHY
        elif any(s == HealthStatus.DEGRADED for s in statuses):
            return HealthStatus.DEGRADED
        else:
            return HealthStatus.HEALTHY
    
    def get_results(self, limit: int = 50) -> List[HealthCheckResult]:
        """Vrátí poslední N výsledků"""
        with self._lock:
            return self._results[-limit:]
    
    # ── Default Health Checks ──────────────────────────────────
    
    def _check_ollama(self) -> HealthCheckResult:
        """Kontrola Ollama API"""
        base = self.config.get("ollama_url", "http://localhost:11434/api/chat")
        # /api/chat je POST endpoint — pro health check vždy používáme /api/tags (GET)
        url: str = base.replace("/api/chat", "/api/tags").rstrip("/")
        if not url.endswith("/api/tags"):
            url = base.rsplit("/", 1)[0] + "/api/tags"

        try:
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                return HealthCheckResult(
                    component="ollama",
                    status=HealthStatus.HEALTHY,
                    message="Ollama dostupný",
                    metadata={"status_code": response.status_code}
                )
            else:
                return HealthCheckResult(
                    component="ollama",
                    status=HealthStatus.UNHEALTHY,
                    message=f"Ollama neodpovídá správně (status {response.status_code})",
                    metadata={"status_code": response.status_code}
                )
        except requests.ConnectionError:
            return HealthCheckResult(
                component="ollama",
                status=HealthStatus.UNHEALTHY,
                message="Nemohu se připojit k Ollama"
            )
        except Exception as e:
            return HealthCheckResult(
                component="ollama",
                status=HealthStatus.UNHEALTHY,
                message=f"Chyba: {str(e)}"
            )
    
    def _check_memory(self) -> HealthCheckResult:
        """Kontrola paměti"""
        try:
            mem = psutil.virtual_memory()
            
            if mem.percent > 90:
                status = HealthStatus.UNHEALTHY
                message = f"Kriticky nízká RAM ({mem.percent}%)"
            elif mem.percent > 75:
                status = HealthStatus.DEGRADED
                message = f"RAM je high ({mem.percent}%)"
            else:
                status = HealthStatus.HEALTHY
                message = f"RAM v pořádku ({mem.percent}%)"
            
            return HealthCheckResult(
                component="memory",
                status=status,
                message=message,
                metadata={
                    "percent": mem.percent,
                    "available_gb": mem.available / (1024**3),
                    "total_gb": mem.total / (1024**3),
                }
            )
        except Exception as e:
            return HealthCheckResult(
                component="memory",
                status=HealthStatus.UNKNOWN,
                message=f"Chyba: {str(e)}"
            )
    
    def _check_disk(self) -> HealthCheckResult:
        """Kontrola disku"""
        try:
            disk = psutil.disk_usage('/')
            
            if disk.percent > 90:
                status = HealthStatus.UNHEALTHY
                message = f"Disk je skoro plný ({disk.percent}%)"
            elif disk.percent > 75:
                status = HealthStatus.DEGRADED
                message = f"Disk je dost plný ({disk.percent}%)"
            else:
                status = HealthStatus.HEALTHY
                message = f"Disk v pořádku ({disk.percent}%)"
            
            return HealthCheckResult(
                component="disk",
                status=status,
                message=message,
                metadata={
                    "percent": disk.percent,
                    "free_gb": disk.free / (1024**3),
                    "total_gb": disk.total / (1024**3),
                }
            )
        except Exception as e:
            return HealthCheckResult(
                component="disk",
                status=HealthStatus.UNKNOWN,
                message=f"Chyba: {str(e)}"
            )
    
    def _check_cpu(self) -> HealthCheckResult:
        """Kontrola CPU"""
        try:
            cpu_percent: float = psutil.cpu_percent(interval=1)
            
            if cpu_percent > 80:
                status = HealthStatus.DEGRADED
                message = f"CPU je vytížené ({cpu_percent}%)"
            else:
                status = HealthStatus.HEALTHY
                message = f"CPU v pořádku ({cpu_percent}%)"
            
            return HealthCheckResult(
                component="cpu",
                status=status,
                message=message,
                metadata={"percent": cpu_percent}
            )
        except Exception as e:
            return HealthCheckResult(
                component="cpu",
                status=HealthStatus.UNKNOWN,
                message=f"Chyba: {str(e)}"
            )
    
    def _check_network(self) -> HealthCheckResult:
        """Kontrola sítě"""
        try:
            # Zkus připojit se na Google DNS
            response = requests.get("https://8.8.8.8", timeout=3)
            
            return HealthCheckResult(
                component="network",
                status=HealthStatus.HEALTHY,
                message="Síť dostupná"
            )
        except requests.ConnectionError:
            return HealthCheckResult(
                component="network",
                status=HealthStatus.UNHEALTHY,
                message="Bez internetového připojení"
            )
        except Exception as e:
            return HealthCheckResult(
                component="network",
                status=HealthStatus.DEGRADED,
                message=f"Síť problém: {str(e)}"
            )


# Singleton instance
_health_checker: Optional[HealthChecker] = None


def get_health_checker(config: Optional[Dict[str, Any]] = None) -> HealthChecker:
    """Vrátí singleton HealthChecker"""
    global _health_checker
    if _health_checker is None:
        from config import CONFIG
        _health_checker = HealthChecker(config or CONFIG)
    return _health_checker
