"""
GeekBrain AI — Bedrock Agent Action Group Lambda
Handles tool execution: SQLite database queries + Monitoring API (hardcoded data)
"""

import json
import os
import random
import sqlite3
from datetime import datetime, timezone

DB_PATH = os.path.join(os.path.dirname(__file__), "geekbrain.db")

# ═══════════════════════════════════════
# Monitoring Data (from monitoring_api.py)
# ═══════════════════════════════════════

SERVICES = ["PaymentGW", "AuthSvc", "OrderSvc", "FraudDetector", "NotificationSvc", "ReportingSvc"]

SERVICE_STATUS = {
    "PaymentGW": {"service": "PaymentGW", "status": "healthy", "uptime_30d": 99.85, "uptime_90d": 99.72, "active_alerts": 0, "last_incident": "INC-005"},
    "AuthSvc": {"service": "AuthSvc", "status": "healthy", "uptime_30d": 99.98, "uptime_90d": 99.95, "active_alerts": 0, "last_incident": "INC-004"},
    "OrderSvc": {"service": "OrderSvc", "status": "healthy", "uptime_30d": 99.95, "uptime_90d": 99.90, "active_alerts": 0, "last_incident": None},
    "FraudDetector": {"service": "FraudDetector", "status": "healthy", "uptime_30d": 99.90, "uptime_90d": 99.88, "active_alerts": 0, "last_incident": "INC-006"},
    "NotificationSvc": {"service": "NotificationSvc", "status": "degraded", "uptime_30d": 99.50, "uptime_90d": 99.20, "active_alerts": 2, "last_incident": "INC-007",
                         "active_alert_details": ["SQS queue depth above threshold (> 10,000 messages)", "Consumer processing latency elevated"]},
    "ReportingSvc": {"service": "ReportingSvc", "status": "healthy", "uptime_30d": 99.80, "uptime_90d": 99.75, "active_alerts": 0, "last_incident": "INC-008"},
}

BASE_METRICS = {
    "PaymentGW": {"latency_ms": {"p50": 45, "p95": 120, "p99": 185}, "error_rate_percent": 0.08, "requests_per_minute": 12500, "cpu_utilization_percent": 62, "memory_utilization_percent": 71},
    "AuthSvc": {"latency_ms": {"p50": 12, "p95": 30, "p99": 45}, "error_rate_percent": 0.005, "requests_per_minute": 28000, "cpu_utilization_percent": 45, "memory_utilization_percent": 40},
    "OrderSvc": {"latency_ms": {"p50": 85, "p95": 210, "p99": 320}, "error_rate_percent": 0.2, "requests_per_minute": 4200, "cpu_utilization_percent": 38, "memory_utilization_percent": 55},
    "FraudDetector": {"latency_ms": {"p50": 35, "p95": 85, "p99": 120}, "error_rate_percent": 0.03, "requests_per_minute": 12500, "cpu_utilization_percent": 72, "memory_utilization_percent": 65},
    "NotificationSvc": {"latency_ms": {"p50": 800, "p95": 2100, "p99": 3200}, "error_rate_percent": 2.1, "requests_per_minute": 1800, "cpu_utilization_percent": 88, "memory_utilization_percent": 92},
    "ReportingSvc": {"latency_ms": {"p50": 450, "p95": 1200, "p99": 2100}, "error_rate_percent": 0.5, "requests_per_minute": 350, "cpu_utilization_percent": 55, "memory_utilization_percent": 68},
}

INCIDENTS = [
    {"incident_id": "INC-001", "service": "PaymentGW", "date": "2026-01-15", "severity": "P2", "duration_minutes": 45,
     "root_cause": "Database connection pool exhausted under peak load", "resolution": "Increased pool from 20 to 50 connections"},
    {"incident_id": "INC-004", "service": "AuthSvc", "date": "2026-02-22", "severity": "P2", "duration_minutes": 60,
     "root_cause": "JWT key rotation script failed silently — exit code 0 despite error", "resolution": "Manual rotation + fixed error handling"},
    {"incident_id": "INC-005", "service": "PaymentGW", "date": "2026-03-05", "severity": "P1", "duration_minutes": 180,
     "root_cause": "Circuit breaker stuck OPEN due to misconfigured health check", "resolution": "Hotfix to decouple reset from health check"},
    {"incident_id": "INC-006", "service": "FraudDetector", "date": "2026-03-12", "severity": "P2", "duration_minutes": 90,
     "root_cause": "Model drift from Lunar New Year spending patterns", "resolution": "Retrained model + threshold 0.70 to 0.75"},
    {"incident_id": "INC-007", "service": "NotificationSvc", "date": "2026-03-20", "severity": "P3", "duration_minutes": 45,
     "root_cause": "SQS dead letter queue overflow", "resolution": "Increased DLQ retention, added alarm, deployed consumer fix"},
    {"incident_id": "INC-008", "service": "ReportingSvc", "date": "2026-04-02", "severity": "P2", "duration_minutes": 120,
     "root_cause": "ETL pipeline timeout — full table scan on grown dataset", "resolution": "Optimized Redshift query with sort keys + pagination"},
]


def _jitter(value, pct=0.05):
    return round(value * (1.0 + random.uniform(-pct, pct)), 4)


def _jitter_int(value, pct=0.05):
    return int(round(value * (1.0 + random.uniform(-pct, pct))))


# ═══════════════════════════════════════
# Tool Functions
# ═══════════════════════════════════════

def query_database(sql_query):
    """Execute a SELECT query on the GeekBrain SQLite database."""
    try:
        if not sql_query.strip().upper().startswith("SELECT"):
            return {"error": "Only SELECT queries are allowed."}

        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(sql_query)
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return {"columns": columns, "rows": rows, "row_count": len(rows)}
    except Exception as e:
        return {"error": str(e)}


def get_service_status(service_name):
    if service_name not in SERVICE_STATUS:
        return {"error": f"Service '{service_name}' not found. Available: {SERVICES}"}
    return SERVICE_STATUS[service_name]


def get_service_metrics(service_name):
    if service_name not in BASE_METRICS:
        return {"error": f"Service '{service_name}' not found. Available: {SERVICES}"}
    base = BASE_METRICS[service_name]
    return {
        "service": service_name,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "latency_ms": {"p50": _jitter_int(base["latency_ms"]["p50"]), "p95": _jitter_int(base["latency_ms"]["p95"]), "p99": _jitter_int(base["latency_ms"]["p99"])},
        "error_rate_percent": _jitter(base["error_rate_percent"]),
        "requests_per_minute": _jitter_int(base["requests_per_minute"]),
        "cpu_utilization_percent": _jitter(base["cpu_utilization_percent"]),
        "memory_utilization_percent": _jitter(base["memory_utilization_percent"]),
    }


def list_services():
    return {"services": SERVICES}


def get_incident_history(service_name):
    if service_name == "all":
        return {"incidents": INCIDENTS}
    filtered = [i for i in INCIDENTS if i["service"] == service_name]
    return {"incidents": filtered, "service": service_name}


def compare_services(metric):
    results = {}
    for svc in SERVICES:
        m = get_service_metrics(svc)
        if metric == "latency_p99":
            results[svc] = m["latency_ms"]["p99"]
        elif metric == "error_rate":
            results[svc] = m["error_rate_percent"]
        elif metric == "requests_per_minute":
            results[svc] = m["requests_per_minute"]
    sorted_results = dict(sorted(results.items(), key=lambda x: x[1], reverse=True))
    return {"metric": metric, "ranking": sorted_results}


# ═══════════════════════════════════════
# Bedrock Agent Action Group Handler
# ═══════════════════════════════════════

def handler(event, context):
    """Bedrock Agent Action Group Lambda handler."""
    print(f"Action Group Event: {json.dumps(event)}")

    function_name = event.get("function", "")
    parameters = {p["name"]: p["value"] for p in event.get("parameters", [])}

    # Dispatch to the correct tool function
    if function_name == "query_database":
        result = query_database(parameters.get("sql_query", ""))
    elif function_name == "get_service_status":
        result = get_service_status(parameters.get("service_name", ""))
    elif function_name == "get_service_metrics":
        result = get_service_metrics(parameters.get("service_name", ""))
    elif function_name == "list_services":
        result = list_services()
    elif function_name == "get_incident_history":
        result = get_incident_history(parameters.get("service_name", "all"))
    elif function_name == "compare_services":
        result = compare_services(parameters.get("metric", "latency_p99"))
    else:
        result = {"error": f"Unknown function: {function_name}"}

    return {
        "messageVersion": "1.0",
        "response": {
            "actionGroup": event.get("actionGroup", ""),
            "function": function_name,
            "functionResponse": {
                "responseBody": {
                    "TEXT": {"body": json.dumps(result, default=str)}
                }
            }
        }
    }
