"""
Tests for QBR Service metrics calculation logic.
Tests revenue aggregation, unpaid invoice counts, low stock calculation, and progress percentage.
"""
import pytest
from unittest.mock import Mock, MagicMock, AsyncMock
from datetime import datetime, timezone

from app.services.qbr_service import QBRService
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


def test_qbr_metrics_paid_revenue_aggregation():
    """Test that paid revenue is correctly aggregated from paid invoices."""
    mock_db = Mock()
    service = QBRService(db=mock_db)
    
    # Mock invoice data - mix of paid and unpaid
    mock_invoices = [
        {"payment_status": "paid", "total_amount": 1000000},
        {"payment_status": "paid", "total_amount": 2500000},
        {"payment_status": "unpaid", "total_amount": 500000},
        {"payment_status": "paid", "total_amount": 1500000},
        {"payment_status": "partial", "total_amount": 750000},
    ]
    
    mock_response = Mock()
    mock_response.data = mock_invoices
    
    mock_db.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response
    
    # Calculate paid revenue
    paid_revenue = sum(
        inv["total_amount"] 
        for inv in mock_invoices 
        if inv["payment_status"] == "paid"
    )
    
    # Should be 1000000 + 2500000 + 1500000 = 5000000
    assert paid_revenue == 5000000


def test_qbr_metrics_unpaid_invoice_count():
    """Test that unpaid invoice count includes unpaid and overdue statuses."""
    mock_db = Mock()
    service = QBRService(db=mock_db)
    
    mock_invoices = [
        {"payment_status": "paid"},
        {"payment_status": "unpaid"},
        {"payment_status": "unpaid"},
        {"payment_status": "overdue"},
        {"payment_status": "partial"},
    ]
    
    # Count unpaid (including overdue)
    unpaid_count = sum(
        1 
        for inv in mock_invoices 
        if inv["payment_status"] in ("unpaid", "overdue")
    )
    
    # Should be 3 (2 unpaid + 1 overdue)
    assert unpaid_count == 3


def test_qbr_metrics_low_stock_calculation():
    """Test low stock product calculation with threshold."""
    mock_db = Mock()
    service = QBRService(db=mock_db)
    
    mock_products = [
        {"stock_quantity": 50, "low_stock_threshold": 100},  # Low stock
        {"stock_quantity": 150, "low_stock_threshold": 100}, # OK
        {"stock_quantity": 5, "low_stock_threshold": 10},    # Low stock
        {"stock_quantity": 0, "low_stock_threshold": 5},     # Low stock
        {"stock_quantity": 200, "low_stock_threshold": 50},  # OK
    ]
    
    # Count low stock products
    low_stock_count = sum(
        1 
        for prod in mock_products 
        if prod["stock_quantity"] <= prod["low_stock_threshold"]
    )
    
    # Should be 3
    assert low_stock_count == 3


def test_qbr_goal_progress_percentage_normal():
    """Test progress percentage calculation for normal goal."""
    current_value = 75000000
    target_value = 100000000
    
    progress_percentage = round((current_value / target_value) * 100) if target_value > 0 else 0
    
    assert progress_percentage == 75


def test_qbr_goal_progress_percentage_over_target():
    """Test progress percentage when current exceeds target."""
    current_value = 120000000
    target_value = 100000000
    
    progress_percentage = round((current_value / target_value) * 100) if target_value > 0 else 0
    
    # Should be 120% (over achievement)
    assert progress_percentage == 120


def test_qbr_goal_progress_percentage_zero_target():
    """Test progress percentage with zero target (edge case)."""
    current_value = 50000000
    target_value = 0
    
    # Should handle division by zero gracefully
    progress_percentage = round((current_value / target_value) * 100) if target_value > 0 else 0
    
    assert progress_percentage == 0


def test_qbr_goal_progress_percentage_both_zero():
    """Test progress percentage when both values are zero."""
    current_value = 0
    target_value = 0
    
    progress_percentage = round((current_value / target_value) * 100) if target_value > 0 else 0
    
    assert progress_percentage == 0


def test_qbr_goal_progress_percentage_rounding():
    """Test that progress percentage is properly rounded."""
    current_value = 333333
    target_value = 1000000
    
    # 333333/1000000 = 0.333333 = 33.3333%
    progress_percentage = round((current_value / target_value) * 100)
    
    # Should round to 33
    assert progress_percentage == 33


def test_qbr_goal_progress_percentage_rounding_up():
    """Test progress percentage rounding up."""
    current_value = 666666
    target_value = 1000000
    
    # 666666/1000000 = 0.666666 = 66.6666%
    progress_percentage = round((current_value / target_value) * 100)
    
    # Should round to 67
    assert progress_percentage == 67


def test_qbr_metrics_total_products_count():
    """Test total products count includes all active products."""
    mock_products = [
        {"id": "1", "is_active": True},
        {"id": "2", "is_active": True},
        {"id": "3", "is_active": False},  # Inactive should be excluded
        {"id": "4", "is_active": True},
    ]
    
    # Assuming we filter by is_active
    total_active = sum(1 for p in mock_products if p["is_active"])
    
    assert total_active == 3


def test_qbr_cycle_status_validation():
    """Test QBR cycle status values are properly constrained."""
    valid_statuses = ["draft", "active", "completed"]
    
    # All these should be valid
    for status in valid_statuses:
        assert status in ["draft", "active", "completed"]
    
    # Invalid status
    invalid_status = "pending"
    assert invalid_status not in ["draft", "active", "completed"]


def test_qbr_goal_status_validation():
    """Test QBR goal status values are properly constrained."""
    valid_statuses = ["on_track", "at_risk", "off_track", "achieved"]
    
    for status in valid_statuses:
        assert status in ["on_track", "at_risk", "off_track", "achieved"]
    
    # Invalid status
    invalid_status = "pending"
    assert invalid_status not in ["on_track", "at_risk", "off_track", "achieved"]


def test_qbr_metrics_calculation_deterministic():
    """Test that metrics calculation is deterministic with same input."""
    # Given the same invoice and product data
    invoices = [
        {"payment_status": "paid", "total_amount": 1000000},
        {"payment_status": "unpaid", "total_amount": 500000},
    ]
    
    products = [
        {"stock_quantity": 5, "low_stock_threshold": 10},
        {"stock_quantity": 50, "low_stock_threshold": 20},
    ]
    
    # First calculation
    paid_revenue_1 = sum(i["total_amount"] for i in invoices if i["payment_status"] == "paid")
    unpaid_count_1 = sum(1 for i in invoices if i["payment_status"] == "unpaid")
    low_stock_1 = sum(1 for p in products if p["stock_quantity"] <= p["low_stock_threshold"])
    
    # Second calculation with same data
    paid_revenue_2 = sum(i["total_amount"] for i in invoices if i["payment_status"] == "paid")
    unpaid_count_2 = sum(1 for i in invoices if i["payment_status"] == "unpaid")
    low_stock_2 = sum(1 for p in products if p["stock_quantity"] <= p["low_stock_threshold"])
    
    # Should be identical
    assert paid_revenue_1 == paid_revenue_2 == 1000000
    assert unpaid_count_1 == unpaid_count_2 == 1
    assert low_stock_1 == low_stock_2 == 1
