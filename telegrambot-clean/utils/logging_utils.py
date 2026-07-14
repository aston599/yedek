"""
🔍 Log Sistemi Yardımcı Fonksiyonları
Circular import önlemek için ayrı modül
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# Global log sistemi instance'ı
_logging_system = None

def set_logging_system(logging_system_instance):
    """Log sistemi instance'ını set et"""
    global _logging_system
    _logging_system = logging_system_instance

async def log_database_operation(operation: str, table: str, success: bool, duration_ms: Optional[float] = None):
    """Veritabanı işlem logu"""
    if _logging_system:
        try:
            await _logging_system.log(
                level="SUCCESS" if success else "ERROR",
                category="DATABASE_OPERATION",
                message=f"🗄️ DB işlemi: {operation} - {table}",
                performance_data={"operation": operation, "table": table, "duration_ms": duration_ms}
            )
        except Exception as e:
            logger.error(f"Log sistemi hatası: {e}")

async def log_error(error: Exception, context: str = "", user_id: Optional[int] = None, username: Optional[str] = None):
    """Hata logu"""
    if _logging_system:
        try:
            await _logging_system.log(
                level="ERROR",
                category="ERROR_HANDLING",
                message=f"❌ Hata oluştu: {context}",
                user_id=user_id,
                username=username,
                error_details=str(error)
            )
        except Exception as e:
            logger.error(f"Log sistemi hatası: {e}")

async def log_missing_data(table: str, field: str, context: str = ""):
    """Eksik veri logu"""
    if _logging_system:
        try:
            await _logging_system.log(
                level="WARNING",
                category="MISSING_DATA",
                message=f"❓ Eksik veri: {table}.{field}",
                additional_data={"table": table, "field": field, "context": context}
            )
        except Exception as e:
            logger.error(f"Log sistemi hatası: {e}")

async def log_deadlock_detection(table: str, duration_ms: int):
    """Kilit tespiti logu"""
    if _logging_system:
        try:
            await _logging_system.log(
                level="CRITICAL",
                category="DEADLOCK_DETECTION",
                message=f"🔒 Kilit tespit edildi: {table}",
                additional_data={"table": table, "duration_ms": duration_ms}
            )
        except Exception as e:
            logger.error(f"Log sistemi hatası: {e}")

async def log_data_corruption(table: str, record_id: int, details: str):
    """Veri bozulması logu"""
    if _logging_system:
        try:
            await _logging_system.log(
                level="CRITICAL",
                category="DATA_CORRUPTION",
                message=f"💀 Veri bozulması: {table}.{record_id}",
                additional_data={"table": table, "record_id": record_id, "details": details}
            )
        except Exception as e:
            logger.error(f"Log sistemi hatası: {e}")

async def log_overflow_protection(operation: str, limit: int, actual: int):
    """Taşma koruması logu"""
    if _logging_system:
        try:
            await _logging_system.log(
                level="WARNING",
                category="OVERFLOW_PROTECTION",
                message=f"💥 Taşma koruması: {operation} limiti aşıldı",
                additional_data={"operation": operation, "limit": limit, "actual": actual}
            )
        except Exception as e:
            logger.error(f"Log sistemi hatası: {e}") 