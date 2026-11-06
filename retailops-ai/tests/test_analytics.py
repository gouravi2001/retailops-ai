from datetime import date, timedelta
from retailops.analytics import metrics
from retailops.anomalies import inventory_exception, delivery_exception, build_issues


def test_inventory_thresholds():
    assert inventory_exception(100, 87)
    assert not inventory_exception(100, 98)
    assert not inventory_exception(0, 0)
    assert inventory_exception(0, 3)


def test_late_deliveries():
    due = date(2026, 10, 10)
    assert delivery_exception(due, due + timedelta(days=3), due + timedelta(days=3))
    assert not delivery_exception(due, due + timedelta(days=1), due + timedelta(days=3))
    assert delivery_exception(due, None, due + timedelta(days=4))


def test_metrics_by_region(populated):
    all_stores = metrics(populated)
    germany = metrics(populated, "Germany")
    assert all_stores["summary"]["stores_tracked"] == 9
    assert germany["summary"]["stores_tracked"] == 3
    assert all_stores["summary"]["revenue_eur"] > germany["summary"]["revenue_eur"]
    assert 0 <= germany["summary"]["inventory_accuracy_pct"] <= 100


def test_issue_creation_is_idempotent(populated):
    assert build_issues(populated) == 0
