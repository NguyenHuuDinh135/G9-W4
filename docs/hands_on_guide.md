# Hands-on Guide — GeekBrain AI Assistant (W4)

Hướng dẫn từng bước **thủ công trên AWS Console** — không dùng Terraform, không CLI.
Dành cho thành viên muốn hiểu rõ từng thành phần hoặc tái tạo hệ thống từ đầu.

> Thứ tự thực hiện rất quan trọng — các bước sau phụ thuộc bước trước.

---

## Mục lục

1. [Prerequisites](#1-prerequisites)
2. [Bước 1 — Tạo VPC & Networking](#bước-1--tạo-vpc--networking)
3. [Bước 2 — Tạo RDS PostgreSQL](#bước-2--tạo-rds-postgresql)
4. [Bước 3 — Seed Data vào Database](#bước-3--seed-data-vào-database)
5. [Bước 4 — Deploy Monitoring API](#bước-4--deploy-monitoring-api)
6. [Bước 5 — Tạo Knowledge Base](#bước-5--tạo-knowledge-base)
7. [Bước 6 — Tạo Action Group Lambda](#bước-6--tạo-action-group-lambda)
8. [Bước 7 — Tạo Bedrock Agent](#bước-7--tạo-bedrock-agent)
9. [Bước 8 — Tạo Lambda Chat + API Gateway](#bước-8--tạo-lambda-chat--api-gateway)
10. [Bước 9 — Deploy Frontend (S3 + CloudFront)](#bước-9--deploy-frontend)
11. [Bước 10 — Test End-to-End](#bước-10--test-end-to-end)
12. [Troubleshooting](#troubleshooting)

---

## 1. Prerequisites

- AWS Account với quyền Admin
- Python 3.12 cài trên máy local (để build Lambda zip)
- Bật model access trên Bedrock Console:
  - Vào **Amazon Bedrock** → **Model access** → Request access cho:
    - Amazon Titan Embed Text v2
    - DeepSeek V3.2

---

## Bước 1 — Tạo VPC & Networking

### 1.1 Tạo VPC

1. Vào **VPC Console** → **Your VPCs** → **Create VPC**
2. Cấu hình:
   - Name: `geekbrain-vpc`
   - IPv4 CIDR: `10.0.0.0/16`
   - DNS hostnames: **Enable**
   - DNS resolution: **Enable**
3. Click **Create VPC**

### 1.2 Tạo Private Subnets

**Subnet 1:**
1. VPC Console → **Subnets** → **Create subnet**
2. VPC: `geekbrain-vpc`
3. Name: `geekbrain-private-1`
4. AZ: `us-east-1a`
5. CIDR: `10.0.10.0/24`

**Subnet 2:**
1. Create subnet
2. VPC: `geekbrain-vpc`
3. Name: `geekbrain-private-2`
4. AZ: `us-east-1b`
5. CIDR: `10.0.11.0/24`

### 1.3 Tạo Security Groups

**Lambda SG:**
1. VPC Console → **Security Groups** → **Create security group**
2. Name: `geekbrain-lambda-sg`
3. VPC: `geekbrain-vpc`
4. Outbound rules: All traffic → `0.0.0.0/0` (default)
5. Inbound: không cần

**RDS SG:**
1. Create security group
2. Name: `geekbrain-rds-sg`
3. VPC: `geekbrain-vpc`
4. Inbound rules: **Add rule**
   - Type: PostgreSQL (port 5432)
   - Source: `geekbrain-lambda-sg` (chọn security group)
5. Outbound: All traffic (default)

**Endpoint SG:**
1. Create security group
2. Name: `geekbrain-endpoint-sg`
3. VPC: `geekbrain-vpc`
4. Inbound rules: **Add rule**
   - Type: HTTPS (port 443)
   - Source: `geekbrain-lambda-sg`
5. Outbound: All traffic (default)

### 1.4 Tạo VPC Interface Endpoint

1. VPC Console → **Endpoints** → **Create endpoint**
2. Name: `geekbrain-apigw-endpoint`
3. Service: tìm `com.amazonaws.us-east-1.execute-api`
4. VPC: `geekbrain-vpc`
5. Subnets: tick cả `geekbrain-private-1` và `geekbrain-private-2`
6. Security group: `geekbrain-endpoint-sg`
7. ✅ **Enable DNS name** (quan trọng!)
8. Create endpoint

> **Tại sao?** Action Group Lambda trong VPC cần gọi Monitoring API (qua API Gateway). Endpoint này cho phép gọi API Gateway mà không cần NAT Gateway — tiết kiệm ~$32/tháng.

---

## Bước 2 — Tạo RDS PostgreSQL

1. Vào **RDS Console** → **Create database**
2. Method: Standard create
3. Engine: **PostgreSQL** version 15
4. Template: **Free tier**
5. Settings:
   - DB instance identifier: `geekbrain-postgres`
   - Master username: `postgres`
   - Password: tự đặt (ghi lại!)
6. Instance: `db.t3.micro`
7. Storage: 20 GB gp2
8. Connectivity:
   - VPC: `geekbrain-vpc`
   - Subnet group: Create new → chọn 2 private subnets
   - Public access: **No**
   - Security group: chọn `geekbrain-rds-sg`
9. Database name: `geekbrain`
10. Create database

**Đợi 5-8 phút** cho status = Available.

📝 **Ghi lại:** Endpoint address (dạng `geekbrain-postgres.xxxxxxxx.us-east-1.rds.amazonaws.com`)

---

## Bước 3 — Seed Data vào Database

### 3.1 Build Seed Lambda trên máy local

```bash
cd seed_lambda
python build.py
```

Kết quả: thư mục `seed_lambda/.build/` chứa code + data + dependencies.

### 3.2 Zip file

```bash
cd seed_lambda/.build
zip -r ../../seed_lambda.zip .
cd ../..
```

### 3.3 Tạo IAM Role trên Console

1. **IAM Console** → **Roles** → **Create role**
2. Trusted entity: **Lambda**
3. Attach policy: `AWSLambdaVPCAccessExecutionRole`
4. Role name: `geekbrain-seed-lambda-role`
5. Create role

### 3.4 Tạo Lambda Function

1. **Lambda Console** → **Create function**
2. Name: `geekbrain-seed-db`
3. Runtime: Python 3.12
4. Execution role: `geekbrain-seed-lambda-role`
5. Click **Create function**

Sau khi tạo:

6. **Code** tab → Upload from → `.zip file` → upload `seed_lambda.zip`
7. **Configuration** tab:
   - General: Timeout = **2 minutes**, Memory = 256 MB
   - VPC: chọn `geekbrain-vpc`, 2 private subnets, security group `geekbrain-lambda-sg`
   - Environment variables:
     - `DB_HOST` = `geekbrain-postgres.xxxxxxxx.us-east-1.rds.amazonaws.com`
     - `DB_NAME` = `geekbrain`
     - `DB_USER` = `postgres`
     - `DB_PASSWORD` = (password bạn đặt ở bước 2)
8. Runtime settings: Handler = `handler.handler`

### 3.5 Invoke

1. Tab **Test** → Create test event (nội dung: `{}`)
2. Click **Test**
3. Phải thấy log: "Creating tables...", "Inserted X rows"

---

## Bước 4 — Deploy Monitoring API

### 4.1 Build trên local

```bash
cd monitoring_lambda
python build.py
cd .build
zip -r ../../monitoring_lambda.zip .
cd ../..
```

### 4.2 Tạo IAM Role

1. IAM → Roles → Create role
2. Trusted entity: Lambda
3. Attach policy: `AWSLambdaBasicExecutionRole`
4. Role name: `geekbrain-monitoring-role`

### 4.3 Tạo Lambda

1. Lambda Console → Create function
2. Name: `geekbrain-monitoring-api`
3. Runtime: Python 3.12
4. Role: `geekbrain-monitoring-role`
5. Create → Upload zip `monitoring_lambda.zip`
6. Configuration:
   - Timeout: 30s, Memory: 256 MB
   - **KHÔNG cần VPC** (monitoring API không cần connect RDS trực tiếp)
7. Runtime settings: Handler = `handler.handler`

### 4.4 Tạo API Gateway

1. **API Gateway Console** → Create API → **REST API** → Build
2. API name: `geekbrain-monitoring-api`
3. Create API

**Tạo proxy resource:**

4. Resources → Actions → **Create Resource**
   - ✅ Configure as proxy resource
   - Resource path: `/{proxy+}`
   - Click Create Resource
5. Setup method ANY:
   - Integration type: Lambda Function Proxy
   - Lambda Function: `geekbrain-monitoring-api`
   - Save → OK (add permission)

**Tạo root GET (cho `/services` endpoint):**

6. Click `/` root → Actions → Create Method → `ANY`
   - Integration: Lambda Function Proxy → `geekbrain-monitoring-api`

**Deploy:**

7. Actions → **Deploy API**
   - Stage: New Stage → name: `prod`
   - Deploy

📝 **Ghi lại Invoke URL:** `https://xxxxxxxx.execute-api.us-east-1.amazonaws.com/prod`

**Test trong browser:**
- Mở: `https://xxxxxxxx.execute-api.us-east-1.amazonaws.com/prod/services`
- Phải thấy: `["PaymentGW","OrderSvc","AuthSvc","NotificationSvc","ReportingSvc","FraudDetector"]`

---

## Bước 5 — Tạo Knowledge Base

### 5.1 Upload docs lên S3

1. **S3 Console** → Create bucket
   - Name: `geekbrain-kb-docs-<account-id>`
   - Region: us-east-1
   - Create bucket
2. Mở bucket → **Upload**
3. Upload tất cả 36 file `.md` từ `data_package/knowledge_base/`

### 5.2 Tạo Bedrock Knowledge Base

1. **Bedrock Console** → **Knowledge bases** → **Create knowledge base**
2. Name: `geekbrain-knowledge-base`
3. IAM: Create and use a new service role
4. **Data source:**
   - Type: S3
   - Bucket: `geekbrain-kb-docs-xxxxx`
   - Chọn toàn bộ bucket
5. **Embedding model:** Amazon Titan Embed Text v2
6. **Vector store:** Quick create (tự tạo OpenSearch Serverless)

   Hoặc nếu muốn custom:
   - Chọn OpenSearch Serverless
   - Tạo collection mới tên `geekbrain-kb` (type: Vector search)
   - Index: `bedrock-knowledge-base-default-index`
   - Vector field: `bedrock-knowledge-base-default-vector`
   - Text field: `AMAZON_BEDROCK_TEXT_CHUNK`
   - Metadata: `AMAZON_BEDROCK_METADATA`

7. **Chunking strategy:** Hierarchical
   - Parent max tokens: **1500**
   - Child max tokens: **300**
   - Overlap tokens: **60**
8. **Create knowledge base**

### 5.3 Sync Knowledge Base

1. Vào KB vừa tạo → Data source → Click **Sync**
2. Đợi 3-5 phút → Status: `Available`

📝 **Ghi lại:** Knowledge Base ID (dạng `XXXXXXXXXX`)

### 5.4 Test KB

1. Trong KB Console → tab **Test**
2. Hỏi: "Who leads Team Platform?"
3. Phải trả về chunks từ `team_platform.md`

---

## Bước 6 — Tạo Action Group Lambda

### 6.1 Build

```bash
cd lambda
python build.py
cd .build
zip -r ../../action_group.zip .
cd ../..
```

### 6.2 Tạo IAM Role

1. IAM → Roles → Create role → Lambda
2. Attach policy: `AWSLambdaVPCAccessExecutionRole`
3. Role name: `geekbrain-action-group-role`

### 6.3 Tạo Lambda

1. Lambda → Create function
2. Name: `geekbrain-action-group`
3. Runtime: Python 3.12
4. Role: `geekbrain-action-group-role`
5. Create → Upload zip `action_group.zip`
6. Configuration:
   - Timeout: **30s**, Memory: 256 MB
   - **VPC:** `geekbrain-vpc`, 2 private subnets, SG: `geekbrain-lambda-sg`
   - Environment variables:
     - `MONITORING_API_URL` = `https://xxxxxxxx.execute-api.us-east-1.amazonaws.com/prod`
     - `DB_HOST` = `geekbrain-postgres.xxxxxxxx.us-east-1.rds.amazonaws.com`
     - `DB_NAME` = `geekbrain`
     - `DB_USER` = `postgres`
     - `DB_PASSWORD` = (password RDS)
7. Runtime settings: Handler = `action_group_function.handler`

### 6.4 Add resource-based policy (cho Bedrock invoke)

1. Lambda → `geekbrain-action-group` → **Configuration** → **Permissions**
2. Scroll xuống **Resource-based policy statements** → **Add permissions**
3. Choose: AWS service → Service: `Other`
   - Statement ID: `AllowBedrockInvoke`
   - Principal: `bedrock.amazonaws.com`
   - Action: `lambda:InvokeFunction`
4. Save

---

## Bước 7 — Tạo Bedrock Agent

### 7.1 Create Agent

1. **Bedrock Console** → **Agents** → **Create Agent**
2. Agent name: `geekbrain-agent`
3. Agent description: "GeekBrain AI Assistant"
4. Model: **DeepSeek V3.2** (tìm trong dropdown hoặc chọn cross-region inference)
5. Instructions — paste:

```
You are GeekBrain AI Assistant. You answer questions about GeekBrain — a fintech startup in Ho Chi Minh City running six production services: PaymentGW, AuthSvc, OrderSvc, FraudDetector, NotificationSvc, ReportingSvc.

RULES:
1. Answer using ONLY the knowledge base and tool results. Do NOT guess or make up information.
2. Always cite the source document name(s) in your answer using [source: filename.md].
3. When documents conflict, prefer the most recent version and status="current" over "archived". State the conflict explicitly.
4. For questions about specific NUMBERS (costs, SLA targets, daily metrics, historical data), you MUST use the query_database tool. Never guess numbers.
5. For questions about CURRENT/LIVE status or real-time performance, use get_service_status or get_service_metrics tools.
6. For factual questions about people, policies, processes, architecture — answer from the knowledge base directly.
7. If you cannot find the answer, say so honestly. Do not hallucinate.
8. Be EXTREMELY concise. Keep your answers under 100 words to prevent system timeouts.
9. When comparing services, use the compare_services tool for accurate data.
10. To save time, if compare_services gives you the metric value, DO NOT also call get_service_metrics.

DATABASE SCHEMA (for query_database tool):
- monthly_costs: service, month, compute_cost, storage_cost, network_cost, third_party_cost, total_cost
- incidents: incident_id, service, date, severity, duration_minutes, root_cause, resolution, team_responsible, reported_by
- sla_targets: service, metric, target, measurement_window
- daily_metrics: date, service, latency_p99_ms, error_rate_percent, requests_per_minute, availability_percent

AVAILABLE SERVICES: PaymentGW, AuthSvc, OrderSvc, FraudDetector, NotificationSvc, ReportingSvc
```

6. Session timeout: **1800 seconds** (30 phút)
7. Create Agent

### 7.2 Add Knowledge Base

1. Trong Agent → **Knowledge bases** → **Add**
2. Chọn `geekbrain-knowledge-base`
3. State: Enabled
4. Save

### 7.3 Add Action Group

1. Trong Agent → **Action groups** → **Add**
2. Name: `geekbrain-tools`
3. Action group type: **Define with function details**
4. Lambda function: `geekbrain-action-group`

**Thêm 6 functions:**

---

**Function 1: `query_database`**

Description:
```
Execute a SQL SELECT query on GeekBrain's database containing HISTORICAL data. Tables: monthly_costs (service, month, compute_cost, storage_cost, network_cost, third_party_cost, total_cost), incidents (incident_id, service, date, severity, duration_minutes, root_cause, resolution, team_responsible, reported_by), sla_targets (service, metric, target, measurement_window), daily_metrics (date, service, latency_p99_ms, error_rate_percent, requests_per_minute, availability_percent). USE THIS for: past costs, historical trends, SLA targets, incident records, daily metrics history. DO NOT use for current/live/real-time data.
```

Parameters:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| sql_query | string | Yes | SQL SELECT query to execute. Only SELECT queries allowed. |

---

**Function 2: `get_service_status`**

Description:
```
Get the CURRENT operational status of ONE specific service. Returns: status (healthy/degraded/down), uptime_30d, uptime_90d, active_alerts count, last_incident ID. USE THIS for: "Is X running?", "What is the status of X?", "Is X healthy?", "Any alerts on X?"
```

Parameters:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| service_name | string | Yes | Exact service name: PaymentGW, AuthSvc, OrderSvc, FraudDetector, NotificationSvc, or ReportingSvc |

---

**Function 3: `get_service_metrics`**

Description:
```
Get CURRENT LIVE performance metrics for ONE specific service. Returns: latency_ms (p50/p95/p99), error_rate_percent, requests_per_minute, cpu_utilization_percent, memory_utilization_percent. USE THIS for: "What is X's current latency?", "How many requests does X handle?", "What is X's error rate right now?"
```

Parameters:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| service_name | string | Yes | Exact service name: PaymentGW, AuthSvc, OrderSvc, FraudDetector, NotificationSvc, or ReportingSvc |

---

**Function 4: `list_services`**

Description:
```
List all 6 monitored services in the GeekBrain system. Use when you need to know available service names.
```

Parameters: (none)

---

**Function 5: `get_incident_history`**

Description:
```
Get historical incident records from the monitoring system for a specific service or all services. Returns: incident_id, service, date, severity, duration_minutes, root_cause, resolution. USE THIS for: "What incidents happened to X?", "Show recent incidents", "What was the root cause of INC-005?"
```

Parameters:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| service_name | string | Yes | Service name to filter incidents, or 'all' for all services |

---

**Function 6: `compare_services`**

Description:
```
Rank ALL 6 services by a single metric and return them sorted highest-to-lowest. Available metrics: latency_p99, error_rate, requests_per_minute, cpu_utilization_percent, memory_utilization_percent. USE THIS for: "Which service has the highest X?", "Rank services by Y", "Compare all services on Z".
```

Parameters:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| metric | string | Yes | Metric to compare: latency_p99, error_rate, requests_per_minute, cpu_utilization_percent, memory_utilization_percent |

---

5. Save Action Group

### 7.4 Prepare & Alias

1. Click **Prepare** (góc trên phải)
2. Đợi status = `Prepared`
3. Tab **Aliases** → **Create alias**
   - Name: `prod`
   - Associate with version: chọn phiên bản mới nhất
4. Create alias

📝 **Ghi lại:**
- Agent ID (dạng `ABCDEFGHIJ`)
- Alias ID (dạng `XXXXXXXXXX`)

### 7.5 Test Agent

1. Trong Agent Console → panel **Test** bên phải
2. Hỏi: "Who leads Team Platform?"
3. Phải trả lời đúng + cite source

---

## Bước 8 — Tạo Lambda Chat + API Gateway

### 8.1 Tạo IAM Role

1. IAM → Roles → Create role → Lambda
2. Attach policies:
   - `AWSLambdaBasicExecutionRole`
3. Role name: `geekbrain-chat-lambda-role`
4. Create role

**Thêm inline policy cho Bedrock:**

5. Vào role vừa tạo → **Add permissions** → **Create inline policy**
6. JSON tab:
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": "bedrock:InvokeAgent",
    "Resource": "arn:aws:bedrock:us-east-1:<ACCOUNT_ID>:agent-alias/<AGENT_ID>/*"
  }]
}
```
7. Policy name: `bedrock-invoke` → Create

### 8.2 Tạo Lambda

1. Lambda → Create function
2. Name: `geekbrain-chat`
3. Runtime: Python 3.12
4. Role: `geekbrain-chat-lambda-role`
5. Create

Upload code:
6. Tab **Code** → copy-paste nội dung file `lambda/lambda_function.py` vào editor
   (hoặc zip file đó và upload)

7. Configuration:
   - Timeout: **2 minutes** (120s) — Agent cần thời gian orchestrate
   - Memory: 256 MB
   - **KHÔNG cần VPC** — gọi Bedrock trực tiếp qua AWS network
   - Environment variables:
     - `AGENT_ID` = (Agent ID từ bước 7)
     - `AGENT_ALIAS_ID` = (Alias ID từ bước 7)
     - `AWS_REGION_NAME` = `us-east-1`
8. Runtime settings: Handler = `lambda_function.handler`

### 8.3 Tạo API Gateway

1. **API Gateway Console** → Create API → **REST API** → Build
2. API name: `geekbrain-chat-api`
3. Create API

**Tạo resource `/chat`:**

4. Resources → Actions → **Create Resource**
   - Resource name: `chat`
   - Resource path: `/chat`
   - Create

**Tạo method POST:**

5. Chọn `/chat` → Actions → **Create Method** → `POST`
   - Integration type: **Lambda Function Proxy**
   - Lambda: `geekbrain-chat`
   - Save → OK

**Enable CORS:**

6. Chọn `/chat` → Actions → **Enable CORS**
   - Methods: POST, OPTIONS
   - Access-Control-Allow-Origin: `*`
   - Enable CORS → Yes, replace existing values

**Deploy:**

7. Actions → **Deploy API**
   - Stage: New Stage → `prod`
   - Deploy

📝 **Ghi lại:** `https://xxxxxxxx.execute-api.us-east-1.amazonaws.com/prod`

### 8.4 Test

Trong API Gateway Console → chọn `POST /chat` → **Test**:
- Request body: `{"question": "Who leads Team Platform?", "session_id": "test"}`
- Click Test
- Phải thấy response với answer + sources

---

## Bước 9 — Deploy Frontend

### 9.1 Tạo S3 Bucket

1. **S3 Console** → Create bucket
2. Name: `geekbrain-frontend-<any-unique-suffix>`
3. Region: us-east-1
4. Block all public access: **ON** (CloudFront sẽ access qua OAC)
5. Create bucket

### 9.2 Sửa index.html — inject API URL

Mở `frontend/index.html` trên máy local, thêm trước `</head>`:

```html
<script>window.GEEKBRAIN_API_URL='https://xxxxxxxx.execute-api.us-east-1.amazonaws.com/prod';</script>
```

(Thay URL bằng Chat API Gateway URL từ bước 8)

### 9.3 Upload files

1. Mở bucket → **Upload**
2. Upload 3 files:
   - `index.html` (đã sửa)
   - `style.css`
   - `app.js`
3. Với mỗi file, set Content-Type đúng:
   - `index.html` → `text/html`
   - `style.css` → `text/css`
   - `app.js` → `application/javascript`

### 9.4 Tạo CloudFront Distribution

1. **CloudFront Console** → Create distribution
2. Origin:
   - Origin domain: chọn S3 bucket vừa tạo
   - Origin access: **Origin access control settings (recommended)**
   - Create new OAC → Create
3. Default cache behavior:
   - Viewer protocol: **Redirect HTTP to HTTPS**
   - Allowed HTTP methods: GET, HEAD
4. Settings:
   - Default root object: `index.html`
   - Price class: Use only North America and Europe (tiết kiệm)
5. Create distribution

**Quan trọng:** CloudFront sẽ hiển thị thông báo "S3 bucket policy needs to be updated"

6. Copy policy statement → Vào S3 bucket → **Permissions** → **Bucket policy** → Paste → Save

**Custom error responses** (SPA routing):

7. Trong CloudFront → Error pages → Create custom error response:
   - Error code: 403 → Response page: `/index.html`, Response code: 200
   - Error code: 404 → Response page: `/index.html`, Response code: 200

**Đợi ~5 phút** cho distribution deploy. Status = `Enabled`.

📝 **Ghi lại URL:** `https://dxxxxxxxxxx.cloudfront.net`

---

## Bước 10 — Test End-to-End

Mở CloudFront URL trong browser. Status phải hiển thị "Connected".

### Test L1 — Simple RAG
```
Hỏi: "Who leads Team Platform and what services do they own?"
Expected: Alex Chen. Owns PaymentGW + AuthSvc
Verify: Source tag xanh hiển thị team_platform.md
```

### Test L2 — Conflict Resolution
```
Hỏi: "What is PaymentGW's API rate limit?"
Expected: 1000 req/min (mentions v2 supersedes v1)
Verify: Multiple source tags
```

### Test L3 — Tool Calling
```
Hỏi: "What was PaymentGW's total infrastructure cost in Q1 2026?"
Expected: $16,500
Verify: Tool badge tím "query_database"
```

```
Hỏi: "What is PaymentGW's current p99 latency?"
Expected: ~185ms
Verify: Tool badge "get_service_metrics"
```

### Test L4 — Memory (multi-turn, cùng session)
```
Turn 1: "Which service had the highest infrastructure cost in March 2026?"
→ PaymentGW $7,500

Turn 2: "Why did its costs spike?"
→ INC-005, circuit breaker stuck OPEN

Turn 3: "Which team is responsible?"
→ Team Platform, Alex Chen
```

---

## Troubleshooting

| Vấn đề | Nguyên nhân | Fix |
|--------|-------------|-----|
| Frontend "No API configured" | URL chưa inject vào index.html | Sửa index.html, re-upload lên S3, invalidate CloudFront cache |
| Agent timeout | Bedrock orchestration chậm | Tăng Lambda Chat timeout lên 180s |
| Agent không gọi tool | Description mơ hồ | Phải có "CURRENT" vs "HISTORICAL" trong description |
| DB connection refused | Lambda SG → RDS SG rule thiếu | Check RDS SG allow port 5432 từ Lambda SG |
| Monitoring API 502 | Lambda crash | Check Lambda logs trong CloudWatch |
| KB trả 0 chunks | Chưa sync / sync fail | Vào KB → Sync lại |
| CORS error frontend | OPTIONS method thiếu | Enable CORS trên API Gateway → re-deploy |
| Action Group Lambda fail | VPC Endpoint DNS chưa active | Đợi 2-3 phút sau khi tạo endpoint |
| CloudFront 403 | Bucket policy chưa update | Copy policy từ CloudFront → paste vào S3 bucket policy |

---

## Invalidate CloudFront Cache (khi update frontend)

1. CloudFront → Distribution → tab **Invalidations**
2. Create invalidation
3. Path: `/*`
4. Create

---

## Tổng thời gian

| Bước | Thời gian |
|------|-----------|
| VPC + Networking | 10 min |
| RDS | 10 min (đợi available) |
| Seed Data | 5 min |
| Monitoring API + API GW | 10 min |
| Knowledge Base + Sync | 15 min |
| Action Group Lambda | 10 min |
| Bedrock Agent (config tools) | 15 min |
| Lambda Chat + API Gateway | 10 min |
| Frontend + CloudFront | 10 min |
| **Total** | **~90 min** |

---

## Checklist final

- [ ] VPC + 2 private subnets + 3 SGs + VPC Endpoint created
- [ ] RDS running, seed data loaded (4 tables)
- [ ] Monitoring API responding (`/services` returns 6 services)
- [ ] Knowledge Base synced (36 docs)
- [ ] Action Group Lambda in VPC with env vars
- [ ] Bedrock Agent prepared + alias created + 6 tools defined
- [ ] Lambda Chat outside VPC with Agent ID/Alias ID
- [ ] Chat API Gateway deployed + CORS enabled
- [ ] Frontend on CloudFront with correct API URL
- [ ] All 4 levels working (L1-L4)
