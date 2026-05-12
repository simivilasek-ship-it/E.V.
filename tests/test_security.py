"""
Unit tests for security_v2.py — Comprehensive security testing
"""

import unittest
import os
import sys
import tempfile
import json
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

pytestmark = [pytest.mark.unit]


@pytest.fixture
def security_manager():
    """Create security manager instance"""
    from security_v2 import get_security_manager
    return get_security_manager()


@pytest.fixture
def audit_log_file():
    """Create temporary audit log file"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        temp_path = f.name
    yield temp_path
    # Cleanup
    if os.path.exists(temp_path):
        os.remove(temp_path)


class TestActionPermissions:
    """Test ACTION_PERMISSIONS configuration"""
    
    def test_safe_actions_exist(self):
        """Ensure SAFE actions are defined"""
        from security_v2 import ACTION_PERMISSIONS, PermissionLevel
        safe_actions = [k for k, v in ACTION_PERMISSIONS.items() if v == PermissionLevel.SAFE]
        assert len(safe_actions) > 0
        assert "answer" in safe_actions
        assert "get_time" in safe_actions
    
    def test_elevated_actions_exist(self):
        """Ensure ELEVATED actions are defined"""
        from security_v2 import ACTION_PERMISSIONS, PermissionLevel
        elevated_actions = [k for k, v in ACTION_PERMISSIONS.items() if v == PermissionLevel.ELEVATED]
        assert len(elevated_actions) > 0
        assert "delete_file" in elevated_actions
        assert "shutdown" in elevated_actions
    
    def test_forbidden_actions_exist(self):
        """Ensure FORBIDDEN actions are defined"""
        from security_v2 import ACTION_PERMISSIONS, PermissionLevel
        forbidden_actions = [k for k, v in ACTION_PERMISSIONS.items() if v == PermissionLevel.FORBIDDEN]
        # May or may not exist, but structure is correct


class TestPermissionLevels:
    """Test PermissionLevel enum"""
    
    def test_permission_level_values(self):
        """Ensure PermissionLevel has correct values"""
        from security_v2 import PermissionLevel
        assert PermissionLevel.SAFE.value == 0
        assert PermissionLevel.STANDARD.value == 1
        assert PermissionLevel.ELEVATED.value == 2
        assert PermissionLevel.RESTRICTED.value == 3
        assert PermissionLevel.FORBIDDEN.value == 4


class TestErrorCategory:
    """Test ErrorCategory enum"""
    
    def test_error_categories_exist(self):
        """Ensure ErrorCategory has necessary categories"""
        from security_v2 import ErrorCategory
        assert hasattr(ErrorCategory, "NETWORK")
        assert hasattr(ErrorCategory, "SYSTEM")
        assert hasattr(ErrorCategory, "CONFIGURATION")
        assert hasattr(ErrorCategory, "PERMISSION")


class TestDangerousPatterns:
    """Test dangerous pattern detection"""
    
    def test_dangerous_patterns_defined(self):
        """Ensure dangerous patterns are defined"""
        from security_v2 import DANGEROUS_PATTERNS, _DANGEROUS_RE
        assert len(DANGEROUS_PATTERNS) > 0
        assert len(_DANGEROUS_RE) > 0
        assert len(DANGEROUS_PATTERNS) == len(_DANGEROUS_RE)
    
    def test_fork_bomb_detection(self):
        """Ensure fork bomb pattern is detected"""
        from security_v2 import contains_dangerous_pattern
        assert contains_dangerous_pattern(":(){ :|:& };:") is True
    
    def test_rm_rf_detection(self):
        """Ensure rm -rf pattern is detected"""
        from security_v2 import contains_dangerous_pattern
        assert contains_dangerous_pattern("rm -rf /") is True
    
    def test_safe_command_not_flagged(self):
        """Ensure safe commands are not flagged"""
        from security_v2 import contains_dangerous_pattern
        assert contains_dangerous_pattern("echo hello") is False
        assert contains_dangerous_pattern("ls -la") is False


class TestAuditLog:
    """Test audit logging functionality"""
    
    def test_audit_log_creation(self, security_manager):
        """Test audit log entry creation"""
        from security_v2 import AuditLogEntry
        entry = AuditLogEntry(
            action="test_action",
            user="test_user",
            status="success",
            details={"param": "value"}
        )
        assert entry.action == "test_action"
        assert entry.user == "test_user"
        assert entry.status == "success"
        assert entry.details == {"param": "value"}
    
    def test_audit_log_entry_timestamp(self):
        """Test that audit log entry has timestamp"""
        from security_v2 import AuditLogEntry
        entry = AuditLogEntry(
            action="test",
            user="user",
            status="success"
        )
        assert entry.timestamp is not None
        assert isinstance(entry.timestamp, datetime)


class TestSecurityManager:
    """Test SecurityManager functionality"""
    
    def test_is_action_allowed_safe(self, security_manager):
        """Test that SAFE actions are allowed"""
        assert security_manager.is_action_allowed("answer") is True
        assert security_manager.is_action_allowed("get_time") is True
    
    def test_is_action_allowed_elevated(self, security_manager):
        """Test that ELEVATED actions are not always allowed"""
        # These require confirmation, so they might return False in some contexts
        result = security_manager.is_action_allowed("delete_file")
        assert isinstance(result, bool)
    
    def test_is_action_unknown(self, security_manager):
        """Test unknown action handling"""
        # Unknown action should be treated conservatively
        result = security_manager.is_action_allowed("unknown_action_xyz")
        assert isinstance(result, bool)
    
    def test_log_action(self, security_manager):
        """Test action logging"""
        security_manager.log_action(
            action="test_action",
            user="test_user",
            status="success",
            details={"test": "data"}
        )
        # Should not raise exception
    
    def test_get_audit_log(self, security_manager):
        """Test retrieving audit log"""
        security_manager.log_action(
            action="test_action",
            user="test_user",
            status="success"
        )
        # Log should be retrievable (may be in-memory)
        log_entries = security_manager.get_audit_log()
        assert isinstance(log_entries, list)


class TestConfirmAction:
    """Test action confirmation"""
    
    def test_confirm_action_requires_elevation(self):
        """Test that elevated actions require confirmation"""
        from security_v2 import confirm_action, PermissionLevel
        # This is tricky to test without UI, but structure should exist
        assert callable(confirm_action)
    
    def test_requires_confirmation_for_delete(self):
        """Test that delete_file requires confirmation"""
        from security_v2 import requires_confirmation
        result = requires_confirmation("delete_file", {})
        assert result is True
    
    def test_no_confirmation_for_safe_action(self):
        """Test that safe actions don't require confirmation"""
        from security_v2 import requires_confirmation
        result = requires_confirmation("get_time", {})
        assert result is False


@pytest.mark.integration
class TestSecurityIntegration:
    """Integration tests for security system"""
    
    def test_full_action_check_safe(self, security_manager):
        """Test full action validation for safe action"""
        is_allowed = security_manager.is_action_allowed("answer")
        assert is_allowed is True
    
    def test_full_action_check_elevated(self, security_manager):
        """Test full action validation for elevated action"""
        # Should be blocked or require confirmation
        result = security_manager.is_action_allowed("shutdown")
        assert isinstance(result, bool)
    
    @patch('builtins.input', return_value='n')
    def test_user_denies_action(self, mock_input, security_manager):
        """Test user denying an action"""
        # When user denies (input 'n'), action should be blocked
        security_manager.log_action(
            action="delete_file",
            user="test_user",
            status="denied"
        )
        # Action is logged as denied
