import os
import psycopg2
import csv

DB_HOST = os.environ.get("DB_HOST")
DB_NAME = os.environ.get("DB_NAME")
DB_USER = os.environ.get("DB_USER")
DB_PASSWORD = os.environ.get("DB_PASSWORD")

# The CSV files will be bundled into the zip alongside this handler
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

def handler(event, context):
    try:
        print(f"Connecting to {DB_HOST}...")
        conn = psycopg2.connect(
            host=DB_HOST,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        conn.autocommit = True
        cursor = conn.cursor()
        
        print("Creating tables...")
        # Schema definition from seed_data.py
        cursor.execute("DROP TABLE IF EXISTS monthly_costs CASCADE;")
        cursor.execute("""
            CREATE TABLE monthly_costs (
                id SERIAL PRIMARY KEY,
                service VARCHAR(50),
                month VARCHAR(10),
                compute_cost DECIMAL(10, 2),
                storage_cost DECIMAL(10, 2),
                network_cost DECIMAL(10, 2),
                third_party_cost DECIMAL(10, 2),
                total_cost DECIMAL(10, 2)
            )
        """)
        
        cursor.execute("DROP TABLE IF EXISTS incidents CASCADE;")
        cursor.execute("""
            CREATE TABLE incidents (
                incident_id VARCHAR(20) PRIMARY KEY,
                service VARCHAR(50),
                date DATE,
                severity VARCHAR(10),
                duration_minutes INT,
                root_cause TEXT,
                resolution TEXT,
                team_responsible VARCHAR(50),
                reported_by VARCHAR(50)
            )
        """)
        
        cursor.execute("DROP TABLE IF EXISTS sla_targets CASCADE;")
        cursor.execute("""
            CREATE TABLE sla_targets (
                id SERIAL PRIMARY KEY,
                service VARCHAR(50),
                metric VARCHAR(50),
                target VARCHAR(50),
                measurement_window VARCHAR(50)
            )
        """)
        
        cursor.execute("DROP TABLE IF EXISTS daily_metrics CASCADE;")
        cursor.execute("""
            CREATE TABLE daily_metrics (
                id SERIAL PRIMARY KEY,
                date DATE,
                service VARCHAR(50),
                latency_p99_ms DECIMAL(10, 2),
                error_rate_percent DECIMAL(5, 2),
                requests_per_minute DECIMAL(15, 2),
                availability_percent DECIMAL(5, 2)
            )
        """)
        
        # No need to TRUNCATE since we dropped the tables

        print("Loading data from CSVs...")
        # 1. monthly_costs
        with open(os.path.join(DATA_DIR, "monthly_costs.csv"), "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                cursor.execute("""
                    INSERT INTO monthly_costs (service, month, compute_cost, storage_cost, network_cost, third_party_cost, total_cost)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (row["service"], row["month"], row["compute_cost"], row["storage_cost"], row["network_cost"], row["third_party_cost"], row["total_cost"]))
                
        # 2. incidents
        with open(os.path.join(DATA_DIR, "incidents.csv"), "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                cursor.execute("""
                    INSERT INTO incidents (incident_id, service, date, severity, duration_minutes, root_cause, resolution, team_responsible, reported_by)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (row["incident_id"], row["service"], row["date"], row["severity"], row["duration_minutes"], row["root_cause"], row["resolution"], row["team_responsible"], row["reported_by"]))
                
        # 3. sla_targets
        with open(os.path.join(DATA_DIR, "sla_targets.csv"), "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                cursor.execute("""
                    INSERT INTO sla_targets (service, metric, target, measurement_window)
                    VALUES (%s, %s, %s, %s)
                """, (row["service"], row["metric"], row["target"], row["measurement_window"]))
                
        # 4. daily_metrics
        with open(os.path.join(DATA_DIR, "daily_metrics.csv"), "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                cursor.execute("""
                    INSERT INTO daily_metrics (date, service, latency_p99_ms, error_rate_percent, requests_per_minute, availability_percent)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (row["date"], row["service"], row["latency_p99_ms"], row["error_rate_percent"], row["requests_per_minute"], row["availability_percent"]))

        conn.close()
        print("Seed completed successfully!")
        return {"status": "success", "message": "Database seeded successfully"}
        
    except Exception as e:
        print(f"Error during seed: {e}")
        return {"status": "error", "message": str(e)}
