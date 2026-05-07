"""
GeekBrain AI — Bedrock Agent Action Group Lambda
Handles tool execution:
  - Monitoring tools → HTTP calls to Monitoring API (FastAPI on Lambda+APIGW)
  - Database queries → SQLite (will be migrated to RDS in step 2)
"""

import json
import os
import psycopg2
import urllib.request
from datetime import datetime, timezone

# Monitoring API endpoint (deployed as separate Lambda + API Gateway)
MONITORING_API_URL = os.environ.get("MONITORING_API_URL", "")

# RDS PostgreSQL Configuration
DB_HOST = os.environ.get("DB_HOST", "")
DB_NAME = os.environ.get("DB_NAME", "")
DB_USER = os.environ.get("DB_USER", "")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "")


# ═══════════════════════════════════════
# HTTP helper for Monitoring API calls
# ═══════════════════════════════════════

def _api_get(path):
    """Call the Monitoring API and return parsed JSON response."""
    url = f"{MONITORING_API_URL.rstrip('/')}/{path.lstrip('/')}"
    print(f"[Tool] HTTP GET {url}")
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = resp.read().decode("utf-8")
            print(f"[Tool] Response: {resp.status} ({len(body)} bytes)")
            return json.loads(body)
    except Exception as e:
        print(f"[Tool] HTTP Error: {e}")
        return {"error": f"Monitoring API call failed: {str(e)}"}


# ═══════════════════════════════════════
# Tool Functions
# ═══════════════════════════════════════

def query_database(sql_query):
    """Execute a SELECT query on the GeekBrain RDS PostgreSQL database."""
    try:
        if not sql_query.strip().upper().startswith("SELECT"):
            return {"error": "Only SELECT queries are allowed."}

        conn = psycopg2.connect(
            host=DB_HOST,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        cursor = conn.cursor()
        cursor.execute(sql_query)
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
        conn.close()
        return {"columns": columns, "rows": rows, "row_count": len(rows)}
    except Exception as e:
        return {"error": str(e)}


def get_service_status(service_name):
    """Get current operational status from the Monitoring API."""
    return _api_get(f"status/{service_name}")


def get_service_metrics(service_name):
    """Get current live performance metrics from the Monitoring API."""
    return _api_get(f"metrics/{service_name}")


def list_services():
    """List all monitored services from the Monitoring API."""
    services = _api_get("services")
    if isinstance(services, list):
        return {"services": services}
    return services  # error case


def get_incident_history(service_name):
    """Get incident history from the Monitoring API."""
    if service_name == "all":
        incidents = _api_get("incidents")
    else:
        incidents = _api_get(f"incidents/{service_name}")

    if isinstance(incidents, list):
        return {"incidents": incidents}
    return incidents  # error case or dict with error


def compare_services(metric):
    """Rank all services by a single metric using the Monitoring API."""
    services = _api_get("services")
    if not isinstance(services, list):
        return services  # error case

    results = {}
    for svc in services:
        m = _api_get(f"metrics/{svc}")
        if "error" in m:
            continue
        if metric == "latency_p99":
            results[svc] = m.get("latency_ms", {}).get("p99", 0)
        elif metric == "error_rate":
            results[svc] = m.get("error_rate_percent", 0)
        elif metric == "requests_per_minute":
            results[svc] = m.get("requests_per_minute", 0)
        elif metric == "cpu_utilization_percent":
            results[svc] = m.get("cpu_utilization_percent", 0)
        elif metric == "memory_utilization_percent":
            results[svc] = m.get("memory_utilization_percent", 0)

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
