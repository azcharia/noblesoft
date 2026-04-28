"""
Tests for Support Service SLA business logic.
Tests priority mapping, breach detection, and status transition timestamps.
"""
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, MagicMock

from app.services.support_service import SupportService, SLA_POLICY_HOURS
from app.core.dependencies import CurrentUser


def _build_mock_user() -> CurrentUser:
    """Build a mock CurrentUser for testing."""
    return CurrentUser(
        {
            "id": "user-1",
            "email": "test@noblesoft.test",
            "role": "admin",
            "tenant_id": "tenant-1",
            "tenants": {
                "company_name": "Test Co",
                "subscription_tier": "enterprise",
                "is_active": True,
                "max_users": 10,
            },
        }
    )


def test_sla_policy_hours_mapping():
    """Test that SLA policy hours are correctly defined for all priorities."""
    assert "p1" in SLA_POLICY_HOURS
    assert "p2" in SLA_POLICY_HOURS
    assert "p3" in SLA_POLICY_HOURS
    
    # P1: Critical - 1h response, 8h resolution
    assert SLA_POLICY_HOURS["p1"] == (1, 8)
    
    # P2: High - 4h response, 24h resolution
    assert SLA_POLICY_HOURS["p2"] == (4, 24)
    
    # P3: Normal - 8h response, 72h resolution
    assert SLA_POLICY_HOURS["p3"] == (8, 72)


def test_calculate_sla_deadlines_p1():
    """Test SLA deadline calculation for P1 (critical) tickets."""
    service = SupportService(db=Mock())
    created_at = datetime(2026, 4, 7, 12, 0, 0, tzinfo=timezone.utc)
    
    response_deadline, resolution_deadline = service._calculate_sla_deadlines("p1", created_at)
    
    # P1: 1 hour response, 8 hours resolution
    assert response_deadline == created_at + timedelta(hours=1)
    assert resolution_deadline == created_at + timedelta(hours=8)


def test_calculate_sla_deadlines_p2():
    """Test SLA deadline calculation for P2 (high) tickets."""
    service = SupportService(db=Mock())
    created_at = datetime(2026, 4, 7, 12, 0, 0, tzinfo=timezone.utc)
    
    response_deadline, resolution_deadline = service._calculate_sla_deadlines("p2", created_at)
    
    # P2: 4 hours response, 24 hours resolution
    assert response_deadline == created_at + timedelta(hours=4)
    assert resolution_deadline == created_at + timedelta(hours=24)


def test_calculate_sla_deadlines_p3():
    """Test SLA deadline calculation for P3 (normal) tickets."""
    service = SupportService(db=Mock())
    created_at = datetime(2026, 4, 7, 12, 0, 0, tzinfo=timezone.utc)
    
    response_deadline, resolution_deadline = service._calculate_sla_deadlines("p3", created_at)
    
    # P3: 8 hours response, 72 hours resolution
    assert response_deadline == created_at + timedelta(hours=8)
    assert resolution_deadline == created_at + timedelta(hours=72)


def test_calculate_sla_deadlines_unknown_priority_defaults_to_p3():
    """Test that unknown priority defaults to P3 SLA."""
    service = SupportService(db=Mock())
    created_at = datetime(2026, 4, 7, 12, 0, 0, tzinfo=timezone.utc)
    
    response_deadline, resolution_deadline = service._calculate_sla_deadlines("p99", created_at)
    
    # Should default to P3
    assert response_deadline == created_at + timedelta(hours=8)
    assert resolution_deadline == created_at + timedelta(hours=72)


def test_hydrate_sla_flags_response_breached_no_response():
    """Test response SLA breach when no first response and deadline passed."""
    service = SupportService(db=Mock())
    
    now = datetime.now(timezone.utc)
    response_deadline = now - timedelta(hours=1)
    
    ticket = {
        "status": "open",
        "first_response_at": None,
        "resolved_at": None,
        "sla_response_deadline": response_deadline.isoformat(),
        "sla_resolution_deadline": (now + timedelta(hours=7)).isoformat(),
        "is_sla_response_breached": False,
        "is_sla_resolution_breached": False,
    }
    
    hydrated = service._hydrate_sla_flags(ticket)
    
    assert hydrated["is_sla_response_breached"] is True
    assert hydrated["is_sla_resolution_breached"] is False


def test_hydrate_sla_flags_response_not_breached_with_response():
    """Test response SLA not breached when first response exists."""
    service = SupportService(db=Mock())
    
    now = datetime(2026, 4, 7, 14, 0, 0, tzinfo=timezone.utc)
    
    ticket = {
        "status": "in_progress",
        "first_response_at": datetime(2026, 4, 7, 12, 30, 0, tzinfo=timezone.utc).isoformat(),
        "resolved_at": None,
        "sla_response_deadline": datetime(2026, 4, 7, 13, 0, 0, tzinfo=timezone.utc).isoformat(),
        "sla_resolution_deadline": (now + timedelta(hours=6)).isoformat(),
        "is_sla_response_breached": False,
        "is_sla_resolution_breached": False,
    }
    
    hydrated = service._hydrate_sla_flags(ticket)
    
    # Should not be breached because first_response_at exists
    assert hydrated["is_sla_response_breached"] is False


def test_hydrate_sla_flags_resolution_breached_not_resolved():
    """Test resolution SLA breach when not resolved and deadline passed."""
    service = SupportService(db=Mock())

    now = datetime.now(timezone.utc)
    resolution_deadline = now - timedelta(hours=1)
    
    ticket = {
        "status": "in_progress",
        "first_response_at": datetime(2026, 4, 7, 12, 30, 0, tzinfo=timezone.utc).isoformat(),
        "resolved_at": None,
        "sla_response_deadline": (now - timedelta(hours=8)).isoformat(),
        "sla_resolution_deadline": resolution_deadline.isoformat(),
        "is_sla_response_breached": False,
        "is_sla_resolution_breached": False,
    }
    
    hydrated = service._hydrate_sla_flags(ticket)
    
    assert hydrated["is_sla_resolution_breached"] is True


def test_hydrate_sla_flags_resolution_not_breached_when_resolved():
    """Test resolution SLA not breached when status is resolved or closed."""
    service = SupportService(db=Mock())
    
    now = datetime(2026, 4, 7, 21, 0, 0, tzinfo=timezone.utc)
    
    ticket = {
        "status": "resolved",
        "first_response_at": datetime(2026, 4, 7, 12, 30, 0, tzinfo=timezone.utc).isoformat(),
        "resolved_at": datetime(2026, 4, 7, 19, 0, 0, tzinfo=timezone.utc).isoformat(),
        "sla_response_deadline": datetime(2026, 4, 7, 13, 0, 0, tzinfo=timezone.utc).isoformat(),
        "sla_resolution_deadline": datetime(2026, 4, 7, 20, 0, 0, tzinfo=timezone.utc).isoformat(),
        "is_sla_response_breached": False,
        "is_sla_resolution_breached": False,
    }
    
    hydrated = service._hydrate_sla_flags(ticket)
    
    # Should not be breached because status is resolved
    assert hydrated["is_sla_resolution_breached"] is False


def test_hydrate_sla_flags_preserves_existing_breach_flags():
    """Test that once a breach flag is set, it persists."""
    service = SupportService(db=Mock())
    
    now = datetime(2026, 4, 7, 14, 0, 0, tzinfo=timezone.utc)
    
    ticket = {
        "status": "in_progress",
        "first_response_at": datetime(2026, 4, 7, 13, 30, 0, tzinfo=timezone.utc).isoformat(),
        "resolved_at": None,
        "sla_response_deadline": datetime(2026, 4, 7, 13, 0, 0, tzinfo=timezone.utc).isoformat(),
        "sla_resolution_deadline": (now + timedelta(hours=6)).isoformat(),
        "is_sla_response_breached": True,  # Already marked as breached
        "is_sla_resolution_breached": False,
    }
    
    hydrated = service._hydrate_sla_flags(ticket)
    
    # Should preserve the breach flag
    assert hydrated["is_sla_response_breached"] is True


def test_parse_datetime_handles_various_formats():
    """Test datetime parsing handles different input formats."""
    service = SupportService(db=Mock())
    
    # ISO format with Z
    dt1 = service._parse_datetime("2026-04-07T12:00:00Z")
    assert dt1 is not None
    assert dt1.tzinfo is not None
    
    # ISO format with timezone
    dt2 = service._parse_datetime("2026-04-07T12:00:00+00:00")
    assert dt2 is not None
    assert dt2.tzinfo is not None
    
    # Datetime object without timezone
    dt3 = service._parse_datetime(datetime(2026, 4, 7, 12, 0, 0))
    assert dt3 is not None
    assert dt3.tzinfo is not None
    
    # None input
    dt4 = service._parse_datetime(None)
    assert dt4 is None
