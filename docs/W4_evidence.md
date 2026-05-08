# W4 Evidence Pack — GeekBrain AI Assistant

## Section 1 — Cover

| Field | Value |
|-------|-------|
| **Group** | Group 9 |
| **Members** | 1. Lê Hoàng Trung Kiên<br>2. Trần Đình Bảo Long<br>3. Nguyễn Đức Chinh<br>4. Nguyễn Hữu Định<br>5. Trương Thị Mỹ Quyên<br>6. Trần Văn Đức<br>7.Hoàng Trọng Tấn
| **Mentor** | Anh Quang Phùng (Quality Assurance Lead, TechX) |
| **LLM** | DeepSeek V3.2 via Amazon Bedrock |
| **Framework** | Amazon Bedrock Agents (managed orchestration) |
| **Repository** | |

---

## Section 2 — Architecture Overview

### System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         CloudFront (CDN)                                  │
│                    frontend/ → S3 Static Website                          │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │ POST /chat
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    API Gateway (Regional, /prod)                          │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│              Lambda: geekbrain-chat (lambda_function.py)                  │
│              Invokes Bedrock Agent via InvokeAgent API                    │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     Bedrock Agent (DeepSeek V3.2)                         │
│  ┌──────────────────────┐        ┌────────────────────────────────────┐ │
│  │   Knowledge Base      │        │   Action Group (Tools)              │ │
│  │   36 markdown docs    │        │   → Lambda: geekbrain-action-group │ │
│  │   S3 → OpenSearch     │        │     (action_group_function.py)     │ │
│  │   Serverless (AOSS)   │        │                                    │ │
│  │   Titan Embed v2      │        │   Tools:                           │ │
│  │   Hierarchical chunks │        │   • query_database → RDS PostgreSQL│ │
│  └──────────────────────┘        │   • get_service_status → Mon. API  │ │
│                                   │   • get_service_metrics → Mon. API │ │
│                                   │   • list_services → Mon. API       │ │
│                                   │   • get_incident_history → Mon. API│ │
│                                   │   • compare_services → Mon. API    │ │
│                                   └─────────────┬──────────────────────┘ │
└─────────────────────────────────────────────────┼────────────────────────┘
                                                  │
                          ┌───────────────────────┼───────────────────────┐
                          │                       │                       │
                          ▼                       ▼                       ▼
              ┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐
              │  RDS PostgreSQL   │   │  Monitoring API   │   │  VPC Network     │
              │  (Private Subnet) │   │  (FastAPI+Mangum) │   │  Private Subnets │
              │                   │   │  Lambda + APIGW   │   │  Security Groups │
              │  Tables:          │   │                   │   │  VPC Endpoint    │
              │  • monthly_costs  │   │  Endpoints:       │   └──────────────────┘
              │  • incidents      │   │  /status/{svc}    │
              │  • sla_targets    │   │  /metrics/{svc}   │
              │  • daily_metrics  │   │  /services        │
              └──────────────────┘   │  /incidents       │
                                     └──────────────────┘
```

### Component List

| Component | Role |
|-----------|------|
| **CloudFront + S3** | Hosts chat frontend (HTML/CSS/JS) |
| **API Gateway** | REST API endpoint, routes POST /chat to Lambda |
| **Lambda (chat)** | Entry point — invokes Bedrock Agent with user question |
| **Bedrock Agent** | Orchestrates KB retrieval + tool calling + LLM reasoning |
| **Knowledge Base** | RAG pipeline: S3 docs → Titan Embed v2 → OpenSearch Serverless → vector search |
| **Action Group Lambda** | Executes tools (DB queries, API calls) in VPC |
| **RDS PostgreSQL** | Stores structured data (costs, incidents, SLAs, daily metrics) |
| **Monitoring API Lambda** | FastAPI app returning live service metrics via Mangum |
| **VPC + Subnets** | Network isolation for RDS access from Action Group Lambda |

### Data Flow

1. User types question in frontend → POST to API Gateway `/prod/chat`
2. API Gateway triggers `geekbrain-chat` Lambda
3. Lambda calls `bedrock-agent-runtime.invoke_agent()` with question + session_id
4. Bedrock Agent decides: retrieve from KB, call tool, or both
5. If KB needed → retrieves relevant chunks from OpenSearch Serverless
6. If tool needed → invokes Action Group Lambda with function name + params
7. Action Group Lambda executes tool (SQL query or HTTP to Monitoring API)
8. Agent synthesizes KB chunks + tool results → generates final answer
9. Response streams back through Lambda → API Gateway → frontend

**Screenshot of system running:**

<!-- TODO: Insert screenshot of deployed frontend or CloudFront URL -->
![System Running](./screenshots/system_running.png)

---

## Section 3 — Decision Log

### Decision 1: Bedrock Agents vs Custom RAG Pipeline

**Chose:** Amazon Bedrock Agents with managed orchestration

**What we learned:** Bedrock Agents handle the tool-calling loop automatically — the agent decides when to retrieve from KB vs call a tool. This eliminated the need to write custom routing logic. Trade-off: less control over exactly when tools are called, but faster to production.

### Decision 2: RDS PostgreSQL vs SQLite/DynamoDB

**Chose:** RDS PostgreSQL in private subnets, accessed via VPC-connected Lambda

**What we learned:** PostgreSQL gives full SQL capability for complex queries (JOINs, aggregations, date ranges). The VPC setup was more complex than SQLite-in-Lambda but matches production architecture. Required configuring security groups and private subnets correctly.

### Decision 3: Hierarchical Chunking Strategy

**Chose:** Hierarchical chunking (parent: 1500 tokens, child: 300 tokens, 60 token overlap)

**What we learned:** Initial testing with fixed-size chunks (300 tokens) caused context loss for long policy documents. Hierarchical chunking preserves document structure — the parent chunk provides broader context while child chunks enable precise retrieval. This improved L2 multi-doc synthesis significantly.

### What Didn't Work

**Tried:** DeepSeek V3.2 model configuration via Terraform `foundation_model` parameter.

**Failed because:** The Bedrock API returned errors when trying to set DeepSeek V3.2 programmatically — the model required console configuration.

**Switched to:** Setting `lifecycle { ignore_changes = [foundation_model] }` in Terraform and configuring the model manually in the Bedrock console. This hybrid approach works but means model changes aren't fully IaC-managed.

---

## Section 4 — Per-Level Evidence

### L1 — Simple RAG (Retrieval)

**Test question:** "Who is the Team Platform lead?"

**Expected answer:** Alex Chen (from team_platform.md)

**Screenshot:**

<!-- TODO: Insert screenshot of L1 answer -->
![L1 Answer](./screenshots/l1_answer.png)

**Proof — Retrieval happened:**

The frontend displays source document tags (green badges) below each answer. CloudWatch logs show the Bedrock Agent trace with `knowledgeBaseLookupOutput` containing retrieved references from `team_platform.md`.

<!-- TODO: Insert screenshot of CloudWatch logs or frontend source tags -->
![L1 Proof](./screenshots/l1_retrieval_log.png)

---

### L2 — Multi-Source Retrieval (Conflict Resolution)

**Test question:** "What is GeekBrain's API rate limit for PaymentGW?"

**Expected answer:** 1000 requests/minute (from api_reference_v2.md, which supersedes the archived v1 at 500 req/min)

**Screenshot:**

<!-- TODO: Insert screenshot of L2 answer showing conflict resolution -->
![L2 Answer](./screenshots/l2_conflict_resolution.png)

**How the system handles conflicts:**

The Bedrock Agent instruction includes: *"When documents conflict, prefer the most recent version and status='current' over 'archived'. State the conflict explicitly."* The KB contains both `api_reference_v1_archived.md` (500 req/min) and `api_reference_v2.md` (1000 req/min). The agent retrieves both, identifies v1 as archived, and reports the current value from v2.

---

### L3 — Tool-Augmented RAG

**Test question:** "What was PaymentGW's total infrastructure cost in Q1 2026?"

**Expected answer:** $16,500 (from database: `SELECT SUM(total_cost) FROM monthly_costs WHERE service='PaymentGW' AND month IN ('2026-01','2026-02','2026-03')`)

**Screenshot:**

<!-- TODO: Insert screenshot of L3 answer with correct number -->
![L3 Answer](./screenshots/l3_cost_answer.png)

**Proof — Tool call happened:**

The frontend shows:
- Purple tool badge: `query_database`
- Collapsible "Query Details" section showing the exact SQL executed

CloudWatch logs show the Action Group event with `function=query_database` and the SQL parameter.

<!-- TODO: Insert screenshot showing tool badge + query details in frontend -->
![L3 Tool Call Proof](./screenshots/l3_tool_call_log.png)

**Additional L3 test:** "What is PaymentGW's current p99 latency?"

**Expected answer:** ~185ms (from Monitoring API via `get_service_metrics` tool)

<!-- TODO: Insert screenshot -->
![L3 Metrics Answer](./screenshots/l3_metrics_answer.png)

**Tools registered with Bedrock Agent Action Group:**

| Tool | Function | Data Source |
|------|----------|-------------|
| `query_database` | SQL SELECT on PostgreSQL | RDS (monthly_costs, incidents, sla_targets, daily_metrics) |
| `get_service_status` | Current health/uptime | Monitoring API `/status/{svc}` |
| `get_service_metrics` | Live latency/error/requests | Monitoring API `/metrics/{svc}` |
| `list_services` | List all 6 services | Monitoring API `/services` |
| `get_incident_history` | Past incident records | Monitoring API `/incidents/{svc}` |
| `compare_services` | Rank services by metric | Monitoring API (aggregates all) |

---

### L4 — Memory (Multi-turn Conversation)

**Test conversation:**

| Turn | User Question | Expected Resolution |
|------|--------------|-------------------|
| 1 | "Which service had the highest infrastructure cost in March 2026?" | → query_database → PaymentGW at $7,500 |
| 2 | "Why did its costs spike?" | Resolve "its" = PaymentGW → KB retrieval → postmortem INC-005 (circuit breaker incident) |
| 3 | "Which team is responsible?" | Resolve context = PaymentGW → Team Platform, led by Alex Chen |
| 4 | "The postmortem mentioned a review deadline. Is it overdue?" | Retrieve deadline (April 15) → compare to current date → Yes, overdue |

**Screenshot:**

<!-- TODO: Insert screenshot showing multi-turn conversation -->
![L4 Conversation](./screenshots/l4_multiturn.png)

**Memory strategy:** Bedrock Agent session management via `sessionId` parameter. Each `invoke_agent()` call passes the same session ID, and the agent maintains conversation context automatically within the session (idle TTL: 1800 seconds). The frontend generates a unique session ID per browser session via `sessionStorage`.

---

### Bonus A — Observability Dashboard

The frontend itself acts as a lightweight observability layer. Each assistant response displays:

- **Source tags** (green) — which KB documents were cited
- **Tool badges** (purple) — which tools were called
- **Query Details** (collapsible) — exact parameters passed to each tool (e.g., SQL query text)

This is implemented in `frontend/app.js` by parsing the API response fields: `sources`, `tools_used`, and `tool_details` returned by the chat Lambda.

**Screenshot:**

<!-- TODO: Insert screenshot of frontend showing tool badges, source tags, and query details -->
![Bonus A Observability](./screenshots/bonus_a_observability.png)

---

### Bonus C — Knowledge Base Sync

KB sync is automated via Terraform. When documents in S3 change (detected via MD5 hash comparison), `terraform apply` triggers:

1. Upload updated `.md` files to S3
2. `null_resource.kb_sync` calls `aws bedrock-agent start-ingestion-job`
3. Polls until ingestion status = COMPLETE (timeout: 10 minutes)

This ensures the KB stays current with document changes without manual intervention.

**Evidence:** See `terraform/modules/ai_engine/main.tf` — the `kb_sync` resource with `docs_hash` trigger.

---

## Section 5 — Reflection

**Hardest level:** L3 — Tool-Augmented RAG

**Why:** The challenge was not writing the tool functions themselves, but getting the Bedrock Agent to route correctly between KB retrieval and tool calls. Tool descriptions had to be extremely precise about when to use each tool (current/live data vs historical data). Vague descriptions caused the agent to guess numbers from documents instead of querying the database. We iterated on tool descriptions multiple times before the agent consistently chose `query_database` for cost questions.

**What we would do differently with one more day:**

- Add query rewriting for L4 to improve retrieval accuracy on follow-up questions with pronouns
- Implement automated testing using the provided question JSON files (`W4/questions/student/`) to measure accuracy across all levels before the demo
- Add fallback error messages when the Monitoring API is unreachable instead of letting the agent hallucinate

---

## Appendix — Infrastructure as Code

All infrastructure managed via Terraform (`terraform/` directory):

```bash
cd terraform
terraform init    # Initialize providers + backend
terraform plan    # Preview changes
terraform apply   # Deploy all resources (~15 min for full stack)
```

| Module | Resources Created |
|--------|-------------------|
| `ai_engine` | S3 bucket, OpenSearch Serverless, Bedrock KB + data source, ingestion job |
| `backend` | Bedrock Agent + alias, Action Group, 2 Lambdas, API Gateway |
| `monitoring_api` | FastAPI Lambda, API Gateway |
| `database` | RDS PostgreSQL, seed Lambda |
| `network` | VPC, 2 private subnets, security groups, VPC endpoint |
| `frontend` | S3 bucket, CloudFront distribution |
