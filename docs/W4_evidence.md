# W4 Evidence Pack — GeekBrain AI Assistant

## Section 1 — Cover

| Field | Value |
|-------|-------|
| **Group** | Group 9 |
| **Members** | <!-- TODO: Add member names --> |
| **LLM** | DeepSeek V3.2 via Amazon Bedrock |
| **Framework** | Amazon Bedrock Agents (managed orchestration) |
| **Repository** | <!-- TODO: Add repo URL --> |

---

## Section 2 — Architecture Overview

### System Architecture Diagram

> See `docs/diagrams/w4_architecture.drawio` — open in draw.io and export PNG for slides.

![System Architecture](./diagrams/w4_architecture.png)

### Request Flow Diagram

> See `docs/diagrams/w4_request_flow.drawio`

![Request Flow](./diagrams/w4_request_flow.png)

### Tool Routing Diagram

> See `docs/diagrams/w4_tool_routing.drawio`

![Tool Routing](./diagrams/w4_tool_routing.png)

### Component List

| Component | Scope | Role |
|-----------|-------|------|
| **CloudFront + S3** | Global | Hosts chat frontend (HTML/CSS/JS) |
| **API Gateway (Chat)** | Regional | REST endpoint, routes POST /chat to Lambda |
| **Lambda Chat** | Regional (outside VPC) | Invokes Bedrock Agent directly via AWS network |
| **Bedrock Agent** | Regional | Orchestrates KB retrieval + tool calling + LLM reasoning |
| **Knowledge Base** | Regional | RAG: S3 docs → Titan Embed v2 → OpenSearch Serverless |
| **OpenSearch Serverless** | Regional | Vector store (HNSW, 1024d) |
| **Action Group Lambda** | VPC (private subnet) | Executes 6 tools (DB queries, API calls) |
| **RDS PostgreSQL** | VPC (private subnet) | Structured data (costs, incidents, SLAs, metrics) |
| **Monitoring API Lambda** | VPC (private subnet) | FastAPI+Mangum returning live service metrics |
| **API Gateway (Monitoring)** | Regional | Exposes Monitoring API to Action Group Lambda |
| **VPC Interface Endpoint** | VPC border | Routes execute-api calls without internet/NAT |

### Data Flow

1. User types question in frontend → POST to API Gateway `/prod/chat`
2. API Gateway triggers `geekbrain-chat` Lambda (outside VPC)
3. Lambda calls `bedrock-agent-runtime.invoke_agent()` with question + session_id (AWS internal network, no NAT needed)
4. Bedrock Agent decides: retrieve from KB, call tool, or both
5. If KB needed → retrieves relevant chunks from OpenSearch Serverless
6. If tool needed → invokes Action Group Lambda (in VPC private subnet)
7. Action Group Lambda executes tool:
   - **query_database** → RDS PostgreSQL (same VPC, SG allows port 5432)
   - **get_service_metrics/status** → Monitoring API via VPC Interface Endpoint (no internet)
8. Agent synthesizes KB chunks + tool results → generates final answer
9. Response streams back through Lambda → API Gateway → frontend

**Key networking decisions:**
- Lambda Chat runs **outside VPC** (no `vpc_config`) — calls Bedrock API directly via AWS internal network
- Action Group Lambda runs **inside VPC** — reaches RDS directly, reaches Monitoring API via VPC Interface Endpoint (`com.amazonaws.us-east-1.execute-api`)
- **No NAT Gateway** needed — all external calls use VPC endpoints or run outside VPC

---

## Section 3 — Decision Log

### Decision 1: Bedrock Agents vs Custom RAG Pipeline

**Chose:** Amazon Bedrock Agents with managed orchestration

**What we learned:** Bedrock Agents handle the tool-calling loop automatically — the agent decides when to retrieve from KB vs call a tool. This eliminated the need to write custom routing logic. Trade-off: less control over exactly when tools are called, but faster to production.

### Decision 2: VPC Interface Endpoint vs NAT Gateway

**Chose:** VPC Interface Endpoint for API Gateway (`execute-api`) instead of NAT Gateway

**What we learned:** The Action Group Lambda needs to call the Monitoring API (behind a separate API Gateway). Instead of routing through NAT → internet → API GW, we use a VPC Interface Endpoint with `private_dns_enabled = true`. This keeps traffic on AWS backbone, removes NAT Gateway cost (~$32/month), and reduces latency.

### Decision 3: Lambda Chat Outside VPC

**Chose:** Lambda Chat without `vpc_config` (runs in AWS-managed network)

**What we learned:** Lambda Chat only calls Bedrock Agent API — it doesn't need VPC access. Running outside VPC avoids cold start delays from ENI attachment (~5-10s), eliminates NAT dependency, and simplifies the network architecture.

### What Didn't Work

**Tried:** DeepSeek V3.2 model configuration via Terraform `foundation_model` parameter.

**Failed because:** The Bedrock API returned errors when trying to set DeepSeek V3.2 programmatically.

**Switched to:** `lifecycle { ignore_changes = [foundation_model] }` in Terraform + manual console configuration.

---

## Section 4 — Per-Level Evidence

### L1 — Simple RAG (Retrieval)

**Test question:** "Who is the Team Platform lead?"

**Expected answer:** Alex Chen (from team_platform.md)

**Screenshot:**

<!-- TODO: Chụp screenshot frontend hiển thị answer + source tag -->
![L1 Answer](./screenshots/l1_answer.png)

**Proof — Retrieval happened:**

Frontend displays source document tags (green badges). Agent trace shows `knowledgeBaseLookupOutput` with references from `team_platform.md`.

<!-- TODO: Chụp screenshot frontend showing source tags -->
![L1 Proof](./screenshots/l1_retrieval_log.png)

---

### L2 — Multi-Source Retrieval (Conflict Resolution)

**Test question:** "What is GeekBrain's API rate limit for PaymentGW?"

**Expected answer:** 1000 requests/minute (from api_reference_v2.md, supersedes archived v1 at 500 req/min)

**Screenshot:**

<!-- TODO: Chụp screenshot answer showing "1000" with conflict explanation -->
![L2 Answer](./screenshots/l2_conflict_resolution.png)

**How the system handles conflicts:**

Agent instruction: *"When documents conflict, prefer the most recent version and status='current' over 'archived'. State the conflict explicitly."* KB contains both `api_reference_v1_archived.md` (500) and `api_reference_v2.md` (1000). Agent identifies v1 as archived and reports current value from v2.

---

### L3 — Tool-Augmented RAG

**Test question:** "What was PaymentGW's total infrastructure cost in Q1 2026?"

**Expected answer:** $16,500 (SQL: `SELECT SUM(total_cost) FROM monthly_costs WHERE service='PaymentGW' AND month IN ('2026-01','2026-02','2026-03')`)

**Screenshot:**

<!-- TODO: Chụp screenshot answer showing $16,500 + tool badge -->
![L3 Answer](./screenshots/l3_cost_answer.png)

**Proof — Tool call happened:**

Frontend shows:
- Purple tool badge: `query_database`
- Collapsible "Query Details" showing SQL executed

<!-- TODO: Chụp screenshot showing tool badge + expanded query details -->
![L3 Tool Call Proof](./screenshots/l3_tool_call_log.png)

**Additional L3 test:** "What is PaymentGW's current p99 latency?"

**Expected answer:** ~185ms (from `get_service_metrics` tool → Monitoring API)

<!-- TODO: Chụp screenshot -->
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
| 2 | "Why did its costs spike?" | Resolve "its" = PaymentGW → KB retrieval → postmortem INC-005 |
| 3 | "Which team is responsible?" | Resolve context → Team Platform, led by Alex Chen |
| 4 | "The postmortem mentioned a review deadline. Is it overdue?" | Retrieve deadline (April 15) → compare to current date → Yes |

**Screenshot:**

<!-- TODO: Chụp screenshot showing 4-turn conversation -->
![L4 Conversation](./screenshots/l4_multiturn.png)

**Memory strategy:** Bedrock Agent session management via `sessionId`. Each `invoke_agent()` call passes the same session ID. Agent maintains context within session (idle TTL: 1800s). Frontend generates unique session ID per browser session via `sessionStorage`.

---

### Bonus A — Observability Dashboard

Frontend displays pipeline internals alongside each answer:

- **Source tags** (green) — which KB documents were cited
- **Tool badges** (purple) — which tools were called
- **Query Details** (collapsible) — exact SQL/parameters passed to each tool

Implemented in `frontend/app.js` by parsing response fields: `sources`, `tools_used`, `tool_details`.

**Screenshot:**

<!-- TODO: Chụp screenshot showing tool badges + source tags + query details expanded -->
![Bonus A Observability](./screenshots/bonus_a_observability.png)

---

### Bonus C — Knowledge Base Sync

KB sync automated via Terraform:

1. Upload `.md` files to S3 (detected via MD5 hash)
2. `null_resource.kb_sync` calls `aws bedrock-agent start-ingestion-job`
3. Polls until status = COMPLETE (timeout: 10 min)

**Evidence:** `terraform/modules/ai_engine/main.tf` — `kb_sync` resource with `docs_hash` trigger.

---

## Section 5 — Reflection

**Hardest level:** L3 — Tool-Augmented RAG

**Why:** Getting the Bedrock Agent to route correctly between KB retrieval and tool calls required extremely precise tool descriptions. "Gets data" is useless — "Returns CURRENT live metrics; for HISTORICAL data use query_database" made the difference. We iterated on descriptions multiple times before the agent consistently chose the right tool.

**What we would do differently with one more day:**

- Add query rewriting for L4 to improve retrieval on follow-up questions with pronouns
- Implement automated testing with the provided question JSON files to measure accuracy
- Add fallback error messages when the Monitoring API is unreachable

---

## Appendix — Infrastructure as Code

```bash
cd terraform
terraform init
terraform plan
terraform apply   # ~15 min for full stack
```

| Module | Resources |
|--------|-----------|
| `ai_engine` | S3 bucket, OpenSearch Serverless, Bedrock KB + data source, ingestion |
| `backend` | Bedrock Agent + alias, Action Group, Lambda Chat, Lambda AG, API Gateway |
| `monitoring_api` | FastAPI Lambda, API Gateway (Monitoring) |
| `database` | RDS PostgreSQL, seed Lambda |
| `network` | VPC, 2 public + 2 private subnets, SGs, VPC Interface Endpoint (execute-api) |
| `frontend` | S3 bucket, CloudFront distribution |
