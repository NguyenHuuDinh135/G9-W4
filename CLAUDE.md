# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

GeekBrain AI Assistant — a RAG-based chatbot for a fictional fintech startup. It uses AWS Bedrock Agent with a Knowledge Base (36 markdown docs) + Action Group (tool calling) to answer questions about company services, policies, incidents, and live metrics.

**Services monitored:** PaymentGW, AuthSvc, OrderSvc, FraudDetector, NotificationSvc, ReportingSvc

## Architecture

```
frontend/ (S3 + CloudFront)
    ↓ POST /chat
API Gateway (Regional)
    ↓
lambda/lambda_function.py (invokes Bedrock Agent)
    ↓
Bedrock Agent (DeepSeek V3.2)
    ├── Knowledge Base (OpenSearch Serverless + S3 markdown docs)
    └── Action Group → lambda/action_group_function.py
                          ├── query_database (RDS PostgreSQL)
                          └── get_service_*/list_services/compare_services → monitoring_lambda/ (FastAPI + Mangum)
```

**Terraform modules** (`terraform/modules/`):
- `ai_engine` — S3 bucket for KB docs, OpenSearch Serverless collection + index, Bedrock Knowledge Base + data source + ingestion
- `backend` — Bedrock Agent + alias, Action Group, main Lambda, action group Lambda (VPC), API Gateway
- `monitoring_api` — FastAPI Lambda behind its own API Gateway
- `database` — RDS PostgreSQL instance
- `network` — VPC, subnets, security groups, VPC endpoint
- `frontend` — S3 bucket + CloudFront distribution

## Build & Deploy

### Lambda packages

Each Lambda has a `build.py` that installs deps into `.build/` with manylinux wheels:

```bash
cd lambda && python build.py        # Main + Action Group Lambda
cd monitoring_lambda && python build.py  # Monitoring API Lambda
```

Terraform's `null_resource` runs `lambda/build.py` automatically during `terraform apply`.

### Terraform

```bash
cd terraform
terraform init
terraform plan
terraform apply
```

State stored in S3 (`geekbrain-tfstate-*`) with DynamoDB locking. Region: `us-east-1`.

### Database seeding

`seed_lambda/handler.py` is invoked once to create tables and load CSVs from `data_package/structured_data/` into RDS PostgreSQL. Tables: `monthly_costs`, `incidents`, `sla_targets`, `daily_metrics`.

### Knowledge Base sync

Terraform triggers `aws bedrock-agent start-ingestion-job` whenever KB docs change (detected via md5 hash).

## Key Design Decisions

- **Action Group Lambda runs in VPC** to reach RDS PostgreSQL via private subnets
- **Monitoring API returns jittered metrics** (±5%) to simulate live data
- **Hierarchical chunking** for KB: parent chunks 1500 tokens, child chunks 300 tokens, 60 token overlap
- **Embedding model:** Amazon Titan Embed Text v2 (1024 dimensions)
- **Frontend API URL** is injected as `window.GEEKBRAIN_API_URL` by Terraform into `index.html`
- **Only SELECT queries** are allowed via `query_database` tool (enforced in action_group_function.py)

## Local Development

### Monitoring API (standalone)

```bash
cd monitoring_lambda
pip install -r requirements.txt uvicorn
uvicorn monitoring_api:app --reload --port 8000
```

### Frontend

Open `frontend/index.html` directly or serve with any static server. Set `window.GEEKBRAIN_API_URL` to point at your API Gateway.

## Data Package

`data_package/knowledge_base/` — 36 markdown documents ingested into Bedrock KB (company policies, service docs, postmortems, runbooks, API references, team info, planning docs).

`data_package/structured_data/` — CSV files seeded into PostgreSQL (daily_metrics, incidents, monthly_costs, sla_targets).
