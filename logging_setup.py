"""
JARVIS — Structured Logging Setup
Logování s loguru pro JSON structured logs
"""

import sys
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

try:
    from loguru import logger as loguru_logger
    HAS_LOGURU = True
except ImportError:
    HAS_LOGURU = False

from config import CONFIG


def setup_logging(log_file: str = "jarvis.log", 
                  json_format: bool = True,
                  level: Optional[str] = None) -> None:
    """
    Inicializuje structured logging s loguru.
    
    Args:
        log_file: Cesta k log souboru
        json_format: Pokud True, loguje ve formátu JSON
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    
    if not HAS_LOGURU:
        _setup_standard_logging(level)
        return
    
    # Odeber default handler
    loguru_logger.remove()
    
    # Zjisti log level
    log_level = (level or CONFIG.get("log_level", "INFO")).upper()
    
    # ── Console output (čitelný formát) ──
    console_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}:{function}:{line}</cyan> - "
        "<level>{message}</level>"
    )
    
    loguru_logger.add(
        sys.stderr,
        format=console_format,
        level=log_level,
        colorize=True,
        backtrace=True,
        diagnose=True,
    )
    
    # ── File output (JSON pro analýzu) ──
    if json_format:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        def json_sink(message):
            """Loguje do JSON formátu"""
            record = message.record
            log_dict = {
                "timestamp": record["time"].isoformat(),
                "level": record["level"].name,
                "module": record["name"],
                "function": record["function"],
                "line": record["line"],
                "message": record["message"],
                "process_id": record["process"]["id"],
                "thread_id": record["thread"]["id"],
            }
            
            # Přidej exception info pokud existuje
            if record["exception"]:
                log_dict["exception"] = {
                    "type": record["exception"][0].__name__,
                    "value": str(record["exception"][1]),
                    "traceback": record["exc_info"][2] is not None,
                }
            
            # Přidej custom fields (context)
            if record["extra"]:
                log_dict["context"] = record["extra"]
            
            print(json.dumps(log_dict, ensure_ascii=False), file=open(log_path, "a", encoding="utf-8"))
        
        loguru_logger.add(
            json_sink,
            level=log_level,
            format="{message}",
        )
    else:
        # Plain text file output
        loguru_logger.add(
            log_file,
            format="{time} | {level: <8} | {name}:{function}:{line} - {message}",
            level=log_level,
            rotation="500 MB",
            retention="7 days",
            encoding="utf-8",
        )
    
    # Propoj loguru s Python logging
    _redirect_logging_to_loguru()
    
    loguru_logger.info("JARVIS logging inicializován", extra={
        "log_level": log_level,
        "json_format": json_format,
        "log_file": log_file,
    })


def _setup_standard_logging(level: Optional[str] = None) -> None:
    """Fallback na standardní Python logging pokud loguru není dostupný"""
    log_level = (level or CONFIG.get("log_level", "INFO")).upper()
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format="%(asctime)s %(levelname)s: %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("jarvis.log", encoding="utf-8"),
        ],
    )


def _redirect_logging_to_loguru() -> None:
    """Propoj Python logging s loguru"""
    
    class LoguruHandler(logging.Handler):
        """Handler pro Python logging který posílá do loguru"""
        
        def emit(self, record: logging.LogRecord) -> None:
            # Zjisti level loguru
            try:
                level = loguru_logger.level(record.levelname).name
            except ValueError:
                level = record.levelno
            
            # Loguj s contextem
            loguru_logger.log(level, record.getMessage(), extra={
                "logger": record.name,
                "module": record.module,
            })
    
    # Odeber standardní handlery a přidej LoguruHandler
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    
    logging.root.addHandler(LoguruHandler())
    logging.root.setLevel(logging.DEBUG)


def get_logger(name: str):
    """Vrátí logger (loguru nebo Python logging)"""
    if HAS_LOGURU:
        return loguru_logger.bind(module=name)
    else:
        return logging.getLogger(name)
