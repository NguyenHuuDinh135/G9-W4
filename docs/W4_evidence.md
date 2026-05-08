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

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                         CloudFront (CDN)                                │
│                frontend/ → S3 Static Website                            │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │ POST /chat
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    API Gateway (Regional, /prod)                        │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│               Lambda: geekbrain-chat (lambda_function.py)               │
│               Invokes Bedrock Agent via InvokeAgent API                 │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     Bedrock Agent (DeepSeek V3.2)                       │
│  ┌──────────────────────┐        ┌────────────────────────────────────┐ │
│  │    Knowledge Base     │        │    Action Group (Tools)            │ │
│  │    36 markdown docs   │        │    → Lambda: geekbrain-action-group │ │
│  │    S3 → OpenSearch    │        │     (action_group_function.py)     │ │
│  │    Serverless (AOSS)  │        │                                    │ │
│  │    Titan Embed v2     │        │     Tools:                         │ │
│  │    Hierarchical chunks│        │     • query_database → RDS Postgre │ │
│  │                       │        │     • get_service_status → Mon API │ │
│  └──────────────────────┘        │     • list_services → Mon. API     │ │
│                                  └─────────────┬──────────────────────┘ │
└─────────────────────────────────────────────────┼────────────────────────┘
                                                  │
                          ┌───────────────────────┼───────────────────────┐
                          │                       │                       │
                          ▼                       ▼                       ▼
              ┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐
              │  RDS PostgreSQL  │   │  Monitoring API  │   │  VPC Network     │
              │  (Private Subnet)│   │  (FastAPI+Mangum)│   │  Private Subnets │
              │                  │   │  Lambda + APIGW  │   │  Security Groups │
              │  Tables:         │   │                  │   │  VPC Endpoint    │
              │  • monthly_costs │   │  Endpoints:      │   └──────────────────┘
              │  • incidents     │   │  /status/{svc}   │
              │  • sla_targets   │   │  /metrics/{svc}  │
              └──────────────────┘   └──────────────────┘

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

### L1 — Simple RAG (10 questions)

| ID | Question | Expected Answer | Source |
|----|----------|----------------|--------|
| L1-01 | What is the current API rate limit for PaymentGW? | 1000 req/min per merchant | api_reference_v2.md |
| L1-02 | Who leads Team Platform and what services do they own? | Alex Chen. Owns PaymentGW + AuthSvc | team_platform.md |
| L1-03 | What was the root cause of the March 5, 2026 PaymentGW outage? | Circuit breaker stuck OPEN due to health check misconfiguration | postmortem_INC005 |
| L1-04 | What is GeekBrain's data retention policy for transaction logs? | 7 years | security_policy.md |
| L1-05 | What are GeekBrain's production deployment windows? | Mon-Thu 09:00-17:00 VN. Freeze Fri 18:00 - Mon 08:00 | deployment_policy.md |
| L1-06 | What authentication method does the PaymentGW API use? | API key + HMAC-SHA256 signature | api_reference_v2.md |
| L1-07 | What message queue does NotificationSvc use? | Amazon SQS | service_notificationsvc.md |
| L1-08 | After March 5 incident, circuit breaker review deadline? | April 15, 2026 | postmortem_INC005 |
| L1-09 | What programming language is AuthSvc written in? | Go | service_authsvc.md |
| L1-10 | How often does GeekBrain rotate JWT signing keys? | Every 30 days | security_policy.md |

**Screenshots:**

<!-- TODO: Chụp 1 screenshot cho mỗi question (hoặc gộp nhiều questions/screenshot) -->
![L1-01](./screenshots/l1_01.png)
![L1-02](./screenshots/l1_02.png)
![L1-03](./screenshots/l1_03.png)
![L1-04](./screenshots/l1_04.png)
![L1-05](./screenshots/l1_05.png)
![L1-06](./screenshots/l1_06.png)
![L1-07](./screenshots/l1_07.png)
![L1-08](./screenshots/l1_08.png)
![L1-09](./screenshots/l1_09.png)
![L1-10](./screenshots/l1_10.png)

---

### L2 — Multi-Source Retrieval (8 questions)

| ID | Question | Expected Answer | Sources |
|----|----------|----------------|---------|
| L2-01 | What is PaymentGW's API rate limit? | 1000 (v2 supersedes v1's 500) | v2 + v1_archived |
| L2-02 | P1 bug in OrderSvc at 21:00 Friday — can they deploy? | Yes. Freeze active but P1 overrides with VP Mark Sullivan approval | deployment + incident_response + team |
| L2-03 | Which services affected if AuthSvc goes down? | PaymentGW + OrderSvc (direct dependencies) | service_architecture + authsvc |
| L2-04 | Top priorities for cost reduction and why? | PaymentGW (cost > revenue growth) + FraudDetector (expensive ML) | q1_review + cost_optimization |
| L2-05 | Common lessons from March 2026 incidents? | Both need automated monitoring/detection | INC005 + INC006 postmortems |
| L2-06 | What should new Team Data engineer know? | Ryan Blake lead, owns ReportingSvc + FraudDetector, PCI-DSS training | onboarding + team_data |
| L2-07 | NotificationSvc concerns + proposed fix? | Slow delivery → SQS consumer auto-scaling recommended | q1_review + capacity_planning + arch_review |
| L2-08 | Complete P1 escalation path for PaymentGW? | Alert → Alex Chen (15min) → Mark Sullivan (30min) → James Wright (1hr) | incident_response + team_platform |

**Screenshots:**

<!-- TODO: Chụp screenshot cho mỗi question -->
![L2-01](./screenshots/l2_01.png)
![L2-02](./screenshots/l2_02.png)
![L2-03](./screenshots/l2_03.png)
![L2-04](./screenshots/l2_04.png)
![L2-05](./screenshots/l2_05.png)
![L2-06](./screenshots/l2_06.png)
![L2-07](./screenshots/l2_07.png)
![L2-08](./screenshots/l2_08.png)

---

### L3 — Tool-Augmented RAG (10 questions)

| ID | Question | Expected Answer | Tool Needed |
|----|----------|----------------|-------------|
| L3-01 | What is PaymentGW's current p99 latency? | ~185ms | get_service_metrics |
| L3-02 | Total infrastructure cost across ALL services in Q1 2026? | $56,350 | query_database |
| L3-03 | Which service had highest total cost in March 2026? | PaymentGW at $7,500 | query_database |
| L3-04 | Is PaymentGW's current error rate within SLA target? | Yes. 0.08% vs target 0.1% | metrics + DB |
| L3-05 | Compare PaymentGW current p99 to Q1 daily average? | Current ~185ms vs avg ~183ms (slightly above) | metrics + DB |
| L3-06 | Is NotificationSvc meeting its SLA targets? | No. Latency 3200ms > 2000ms target, error 2.1% > 1.0% target | metrics + DB |
| L3-07 | PaymentGW cost increase Q4 2025 → Q1 2026? | Q4=$11,700 → Q1=$16,500. +$4,800 (+41%) | query_database |
| L3-08 | Which service handles most requests per minute? | AuthSvc at ~28,000 rpm | get_service_metrics (multiple) |
| L3-09 | FraudDetector CPU utilization vs other services? | FraudDetector 72%. NotificationSvc highest at 88% | get_service_metrics (multiple) |
| L3-10 | Total incidents in Q1 2026? Which service had most? | 7 incidents. PaymentGW had 3 (most) | query_database |

**Screenshots:**

<!-- TODO: Chụp screenshot cho mỗi question, showing tool badge + answer -->
![L3-01](./screenshots/l3_01.png)
![L3-02](./screenshots/l3_02.png)
![L3-03](./screenshots/l3_03.png)
![L3-04](./screenshots/l3_04.png)
![L3-05](./screenshots/l3_05.png)
![L3-06](./screenshots/l3_06.png)
![L3-07](./screenshots/l3_07.png)
![L3-08](./screenshots/l3_08.png)
![L3-09](./screenshots/l3_09.png)
![L3-10](./screenshots/l3_10.png)

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

<!-- TODO: Chụp screenshot showing full 4-turn conversation -->
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
