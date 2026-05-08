# Hands-on Guide — GeekBrain AI Assistant (W4)

Hướng dẫn từng bước **thủ công** trên AWS Console + CLI — không dùng Terraform.
Dành cho thành viên muốn hiểu rõ từng thành phần hoặc tái tạo hệ thống từ đầu.

> Thứ tự thực hiện rất quan trọng — các bước sau phụ thuộc bước trước.

---

## Mục lục

1. [Prerequisites](#1-prerequisites)
2. [Bước 1 — Tạo VPC & Networking](#bước-1--tạo-vpc--networking)
3. [Bước 2 — Tạo RDS PostgreSQL](#bước-2--tạo-rds-postgresql)
4. [Bước 3 — Seed Data vào Database](#bước-3--seed-data-vào-database)
5. [Bước 4 — Deploy Monitoring API](#bước-4--deploy-monitoring-api)
6. [Bước 5 — Tạo Knowledge Base (OpenSearch + Bedrock KB)](#bước-5--tạo-knowledge-base)
7. [Bước 6 — Tạo Action Group Lambda](#bước-6--tạo-action-group-lambda)
8. [Bước 7 — Tạo Bedrock Agent](#bước-7--tạo-bedrock-agent)
9. [Bước 8 — Tạo Lambda Chat + API Gateway](#bước-8--tạo-lambda-chat--api-gateway)
10. [Bước 9 — Deploy Frontend (S3 + CloudFront)](#bước-9--deploy-frontend)
11. [Bước 10 — Test End-to-End](#bước-10--test-end-to-end)
12. [Troubleshooting](#troubleshooting)

---

## 1. Prerequisites

- AWS Account với quyền Admin
- AWS CLI v2 đã configure (`aws configure` → region `us-east-1`)
- Python 3.12 + pip
- Bật model access trên Bedrock Console:
  - Amazon Titan Embed Text v2
  - DeepSeek V3.2

```bash
# Verify AWS CLI
aws sts get-caller-identity
```

---

## Bước 1 — Tạo VPC & Networking

### 1.1 Tạo VPC

```bash
VPC_ID=$(aws ec2 create-vpc --cidr-block 10.0.0.0/16 \
  --query 'Vpc.VpcId' --output text)
aws ec2 modify-vpc-attribute --vpc-id $VPC_ID --enable-dns-support
aws ec2 modify-vpc-attribute --vpc-id $VPC_ID --enable-dns-hostnames
aws ec2 create-tags --resources $VPC_ID --tags Key=Name,Value=geekbrain-vpc
echo "VPC: $VPC_ID"
```

### 1.2 Tạo Subnets

```bash
# Private Subnet 1 (us-east-1a)
PRIV_SUB_1=$(aws ec2 create-subnet --vpc-id $VPC_ID \
  --cidr-block 10.0.10.0/24 --availability-zone us-east-1a \
  --query 'Subnet.SubnetId' --output text)

# Private Subnet 2 (us-east-1b)
PRIV_SUB_2=$(aws ec2 create-subnet --vpc-id $VPC_ID \
  --cidr-block 10.0.11.0/24 --availability-zone us-east-1b \
  --query 'Subnet.SubnetId' --output text)

echo "Private subnets: $PRIV_SUB_1, $PRIV_SUB_2"
```

### 1.3 Security Groups

```bash
# Lambda Security Group
LAMBDA_SG=$(aws ec2 create-security-group --group-name geekbrain-lambda-sg \
  --description "Lambda functions" --vpc-id $VPC_ID \
  --query 'GroupId' --output text)
aws ec2 authorize-security-group-egress --group-id $LAMBDA_SG \
  --protocol -1 --cidr 0.0.0.0/0

# RDS Security Group
RDS_SG=$(aws ec2 create-security-group --group-name geekbrain-rds-sg \
  --description "RDS PostgreSQL" --vpc-id $VPC_ID \
  --query 'GroupId' --output text)
aws ec2 authorize-security-group-ingress --group-id $RDS_SG \
  --protocol tcp --port 5432 --source-group $LAMBDA_SG

# VPC Endpoint Security Group
ENDPOINT_SG=$(aws ec2 create-security-group --group-name geekbrain-endpoint-sg \
  --description "VPC Interface Endpoints" --vpc-id $VPC_ID \
  --query 'GroupId' --output text)
aws ec2 authorize-security-group-ingress --group-id $ENDPOINT_SG \
  --protocol tcp --port 443 --source-group $LAMBDA_SG

echo "SGs: Lambda=$LAMBDA_SG, RDS=$RDS_SG, Endpoint=$ENDPOINT_SG"
```

### 1.4 VPC Interface Endpoint (cho API Gateway)

```bash
ENDPOINT_ID=$(aws ec2 create-vpc-endpoint \
  --vpc-id $VPC_ID \
  --vpc-endpoint-type Interface \
  --service-name com.amazonaws.us-east-1.execute-api \
  --subnet-ids $PRIV_SUB_1 $PRIV_SUB_2 \
  --security-group-ids $ENDPOINT_SG \
  --private-dns-enabled \
  --query 'VpcEndpoint.VpcEndpointId' --output text)
echo "VPC Endpoint: $ENDPOINT_ID"
```

> **Tại sao?** Action Group Lambda trong VPC cần gọi Monitoring API (qua API Gateway). VPC Endpoint cho phép gọi mà không cần NAT Gateway.

---

## Bước 2 — Tạo RDS PostgreSQL

### 2.1 Tạo Subnet Group

```bash
aws rds create-db-subnet-group \
  --db-subnet-group-name geekbrain-db-subnet \
  --db-subnet-group-description "GeekBrain private subnets" \
  --subnet-ids $PRIV_SUB_1 $PRIV_SUB_2
```

### 2.2 Tạo RDS Instance

```bash
DB_PASSWORD="YourSecurePassword123!"  # Thay bằng password mạnh

aws rds create-db-instance \
  --db-instance-identifier geekbrain-postgres \
  --db-instance-class db.t3.micro \
  --engine postgres \
  --engine-version 15 \
  --allocated-storage 20 \
  --db-name geekbrain \
  --master-username postgres \
  --master-user-password "$DB_PASSWORD" \
  --vpc-security-group-ids $RDS_SG \
  --db-subnet-group-name geekbrain-db-subnet \
  --no-publicly-accessible \
  --no-multi-az
```

Đợi ~5-8 phút:
```bash
aws rds wait db-instance-available --db-instance-identifier geekbrain-postgres
DB_HOST=$(aws rds describe-db-instances --db-instance-identifier geekbrain-postgres \
  --query 'DBInstances[0].Endpoint.Address' --output text)
echo "DB Host: $DB_HOST"
```

---

## Bước 3 — Seed Data vào Database

### 3.1 Build Seed Lambda

```bash
cd seed_lambda
python build.py
cd ..
```

### 3.2 Tạo IAM Role

```bash
aws iam create-role --role-name geekbrain-seed-lambda-role \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{"Effect": "Allow", "Principal": {"Service": "lambda.amazonaws.com"}, "Action": "sts:AssumeRole"}]
  }'

aws iam attach-role-policy --role-name geekbrain-seed-lambda-role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole
```

### 3.3 Zip & Deploy Lambda

```bash
cd seed_lambda/.build
zip -r ../../seed_lambda.zip .
cd ../..

ROLE_ARN=$(aws iam get-role --role-name geekbrain-seed-lambda-role --query 'Role.Arn' --output text)

# Đợi role propagate
sleep 10

aws lambda create-function \
  --function-name geekbrain-seed-db \
  --runtime python3.12 \
  --handler handler.handler \
  --role $ROLE_ARN \
  --zip-file fileb://seed_lambda.zip \
  --timeout 120 \
  --memory-size 256 \
  --vpc-config SubnetIds=$PRIV_SUB_1,$PRIV_SUB_2,SecurityGroupIds=$LAMBDA_SG \
  --environment "Variables={DB_HOST=$DB_HOST,DB_NAME=geekbrain,DB_USER=postgres,DB_PASSWORD=$DB_PASSWORD}"
```

### 3.4 Invoke Seed

```bash
aws lambda invoke --function-name geekbrain-seed-db response.json
cat response.json
```

Phải thấy: tables created + rows inserted (monthly_costs, incidents, sla_targets, daily_metrics).

---

## Bước 4 — Deploy Monitoring API

### 4.1 Build

```bash
cd monitoring_lambda
python build.py
cd ..
```

### 4.2 Tạo Role + Deploy Lambda

```bash
aws iam create-role --role-name geekbrain-monitoring-role \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{"Effect": "Allow", "Principal": {"Service": "lambda.amazonaws.com"}, "Action": "sts:AssumeRole"}]
  }'
aws iam attach-role-policy --role-name geekbrain-monitoring-role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

sleep 10

cd monitoring_lambda/.build
zip -r ../../monitoring_lambda.zip .
cd ../..

MON_ROLE_ARN=$(aws iam get-role --role-name geekbrain-monitoring-role --query 'Role.Arn' --output text)

aws lambda create-function \
  --function-name geekbrain-monitoring-api \
  --runtime python3.12 \
  --handler handler.handler \
  --role $MON_ROLE_ARN \
  --zip-file fileb://monitoring_lambda.zip \
  --timeout 30 \
  --memory-size 256
```

### 4.3 Tạo API Gateway cho Monitoring

1. AWS Console → API Gateway → Create API → REST API
2. Name: `geekbrain-monitoring-api`
3. Tạo resource `/{proxy+}` với method `ANY` → Integration: Lambda Proxy → function `geekbrain-monitoring-api`
4. Deploy to stage `prod`
5. Lưu URL: `https://xxxxxxxx.execute-api.us-east-1.amazonaws.com/prod`

```bash
MONITORING_API_URL="https://xxxxxxxx.execute-api.us-east-1.amazonaws.com/prod"
```

### 4.4 Test

```bash
curl $MONITORING_API_URL/services
curl $MONITORING_API_URL/metrics/PaymentGW
curl $MONITORING_API_URL/status/PaymentGW
curl $MONITORING_API_URL/incidents/PaymentGW
```

---

## Bước 5 — Tạo Knowledge Base

### 5.1 Upload docs lên S3

```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
BUCKET="geekbrain-kb-docs-${ACCOUNT_ID}"

aws s3 mb s3://$BUCKET
aws s3 sync data_package/knowledge_base/ s3://$BUCKET/ --exclude "*.metadata.json"
```

### 5.2 Tạo OpenSearch Serverless Collection

1. AWS Console → OpenSearch Service → Serverless → Collections
2. Create Collection:
   - Name: `geekbrain-kb`
   - Type: **Vector search**
   - Encryption: AWS-owned key
   - Network: Public
3. Đợi status = `ACTIVE` (~2 phút)
4. Lưu Collection endpoint: `https://xxxxxxxx.us-east-1.aoss.amazonaws.com`

### 5.3 Tạo Vector Index

Vào OpenSearch Dashboard (link trong collection) → Dev Tools:

```json
PUT bedrock-knowledge-base-default-index
{
  "settings": {
    "index.knn": true,
    "number_of_shards": 2,
    "number_of_replicas": 0,
    "index.knn.algo_param.ef_search": 512
  },
  "mappings": {
    "properties": {
      "bedrock-knowledge-base-default-vector": {
        "type": "knn_vector",
        "dimension": 1024,
        "method": {
          "name": "hnsw",
          "engine": "faiss",
          "space_type": "l2",
          "parameters": {
            "ef_construction": 512,
            "m": 16
          }
        }
      },
      "AMAZON_BEDROCK_METADATA": { "type": "text", "index": false },
      "AMAZON_BEDROCK_TEXT_CHUNK": { "type": "text" }
    }
  }
}
```

### 5.4 Tạo Bedrock Knowledge Base

1. AWS Console → Bedrock → Knowledge Bases → Create
2. Name: `geekbrain-knowledge-base`
3. Data source: S3 → bucket `geekbrain-kb-docs-xxxxx`
4. Embedding model: **Amazon Titan Embed Text v2**
5. Vector store: OpenSearch Serverless → collection `geekbrain-kb`
   - Index name: `bedrock-knowledge-base-default-index`
   - Vector field: `bedrock-knowledge-base-default-vector`
   - Text field: `AMAZON_BEDROCK_TEXT_CHUNK`
   - Metadata field: `AMAZON_BEDROCK_METADATA`
6. Chunking: **Hierarchical**
   - Parent: 1500 tokens
   - Child: 300 tokens
   - Overlap: 60 tokens
7. Create → **Sync** (đợi 3-5 phút)

```bash
KB_ID="<knowledge-base-id-from-console>"
```

---

## Bước 6 — Tạo Action Group Lambda

### 6.1 Build

```bash
cd lambda
python build.py
cd ..
```

### 6.2 Deploy

```bash
aws iam create-role --role-name geekbrain-action-group-role \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{"Effect": "Allow", "Principal": {"Service": "lambda.amazonaws.com"}, "Action": "sts:AssumeRole"}]
  }'
aws iam attach-role-policy --role-name geekbrain-action-group-role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole

sleep 10

cd lambda/.build
zip -r ../../action_group.zip .
cd ../..

AG_ROLE_ARN=$(aws iam get-role --role-name geekbrain-action-group-role --query 'Role.Arn' --output text)

aws lambda create-function \
  --function-name geekbrain-action-group \
  --runtime python3.12 \
  --handler action_group_function.handler \
  --role $AG_ROLE_ARN \
  --zip-file fileb://action_group.zip \
  --timeout 30 \
  --memory-size 256 \
  --vpc-config SubnetIds=$PRIV_SUB_1,$PRIV_SUB_2,SecurityGroupIds=$LAMBDA_SG \
  --environment "Variables={MONITORING_API_URL=$MONITORING_API_URL,DB_HOST=$DB_HOST,DB_NAME=geekbrain,DB_USER=postgres,DB_PASSWORD=$DB_PASSWORD}"
```

### 6.3 Cho phép Bedrock invoke

```bash
AG_ARN=$(aws lambda get-function --function-name geekbrain-action-group --query 'Configuration.FunctionArn' --output text)

aws lambda add-permission \
  --function-name geekbrain-action-group \
  --statement-id AllowBedrockInvoke \
  --action lambda:InvokeFunction \
  --principal bedrock.amazonaws.com
```

---

## Bước 7 — Tạo Bedrock Agent

### 7.1 Tạo Agent trên Console

1. AWS Console → Bedrock → Agents → Create Agent
2. Name: `geekbrain-agent`
3. Model: **DeepSeek V3.2** (hoặc cross-region inference profile)
4. Instructions — paste toàn bộ nội dung sau:

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

5. Session timeout: **1800 seconds**

### 7.2 Associate Knowledge Base

- Add Knowledge Base → chọn `geekbrain-knowledge-base`
- State: Enabled

### 7.3 Add Action Group

- Name: `geekbrain-tools`
- Lambda: `geekbrain-action-group`
- Define functions (6 tools):

**Tool 1: query_database**
- Description: `Execute a SQL SELECT query on GeekBrain's database containing HISTORICAL data. Tables: monthly_costs, incidents, sla_targets, daily_metrics. USE THIS for: past costs, historical trends, SLA targets, incident records. DO NOT use for current/live data.`
- Parameter: `sql_query` (string, required) — "SQL SELECT query to execute."

**Tool 2: get_service_status**
- Description: `Get the CURRENT operational status of ONE specific service. Returns: status, uptime, active_alerts, last_incident. USE THIS for: "Is X running?", "What is the status of X?"`
- Parameter: `service_name` (string, required) — "Exact service name: PaymentGW, AuthSvc, OrderSvc, FraudDetector, NotificationSvc, or ReportingSvc"

**Tool 3: get_service_metrics**
- Description: `Get CURRENT LIVE performance metrics for ONE specific service. Returns: latency_ms (p50/p95/p99), error_rate_percent, requests_per_minute, cpu/memory utilization. USE THIS for: "What is X's current latency?", "How many requests does X handle?"`
- Parameter: `service_name` (string, required)

**Tool 4: list_services**
- Description: `List all 6 monitored services in the GeekBrain system.`
- No parameters

**Tool 5: get_incident_history**
- Description: `Get historical incident records from monitoring system. USE THIS for: "What incidents happened to X?", "Show recent incidents"`
- Parameter: `service_name` (string, required) — "Service name or 'all'"

**Tool 6: compare_services**
- Description: `Rank ALL 6 services by a single metric (highest to lowest). Available metrics: latency_p99, error_rate, requests_per_minute, cpu_utilization_percent, memory_utilization_percent. USE THIS for: "Which service has the highest X?"`
- Parameter: `metric` (string, required)

### 7.4 Prepare & Create Alias

1. Click **Prepare**
2. Đợi status = Prepared
3. Create Alias: name = `prod`
4. Lưu Agent ID và Alias ID:

```bash
AGENT_ID="<agent-id>"
AGENT_ALIAS_ID="<alias-id>"
```

---

## Bước 8 — Tạo Lambda Chat + API Gateway

### 8.1 Deploy Lambda Chat

```bash
aws iam create-role --role-name geekbrain-chat-lambda-role \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{"Effect": "Allow", "Principal": {"Service": "lambda.amazonaws.com"}, "Action": "sts:AssumeRole"}]
  }'
aws iam attach-role-policy --role-name geekbrain-chat-lambda-role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

# Thêm quyền invoke Bedrock Agent
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
aws iam put-role-policy --role-name geekbrain-chat-lambda-role \
  --policy-name bedrock-invoke \
  --policy-document "{
    \"Version\": \"2012-10-17\",
    \"Statement\": [{
      \"Effect\": \"Allow\",
      \"Action\": \"bedrock:InvokeAgent\",
      \"Resource\": \"arn:aws:bedrock:us-east-1:${ACCOUNT_ID}:agent-alias/${AGENT_ID}/*\"
    }]
  }"

sleep 10

# Zip chỉ file lambda_function.py (không cần dependencies)
zip chat_lambda.zip -j lambda/lambda_function.py

CHAT_ROLE_ARN=$(aws iam get-role --role-name geekbrain-chat-lambda-role --query 'Role.Arn' --output text)

aws lambda create-function \
  --function-name geekbrain-chat \
  --runtime python3.12 \
  --handler lambda_function.handler \
  --role $CHAT_ROLE_ARN \
  --zip-file fileb://chat_lambda.zip \
  --timeout 120 \
  --memory-size 256 \
  --environment "Variables={AGENT_ID=$AGENT_ID,AGENT_ALIAS_ID=$AGENT_ALIAS_ID,AWS_REGION_NAME=us-east-1}"
```

> **Lưu ý:** Lambda Chat chạy NGOÀI VPC — không có `--vpc-config`. Gọi Bedrock trực tiếp qua AWS network.

### 8.2 Tạo API Gateway (Chat)

1. AWS Console → API Gateway → Create REST API
2. Name: `geekbrain-chat-api`
3. Create resource `/chat`
4. Create method `POST` → Integration: Lambda Proxy → `geekbrain-chat`
5. Create method `OPTIONS` → Mock integration (cho CORS)
6. Enable CORS trên resource `/chat`
7. Deploy → Stage: `prod`

```bash
CHAT_API_URL="https://xxxxxxxx.execute-api.us-east-1.amazonaws.com/prod"
```

### 8.3 Test

```bash
curl -X POST $CHAT_API_URL/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "Who leads Team Platform?", "session_id": "test-1"}'
```

---

## Bước 9 — Deploy Frontend

### 9.1 Tạo S3 Bucket

```bash
FRONTEND_BUCKET="geekbrain-frontend-${ACCOUNT_ID}"
aws s3 mb s3://$FRONTEND_BUCKET
```

### 9.2 Inject API URL vào index.html

```bash
# Thêm API URL vào frontend
sed "s|</head>|<script>window.GEEKBRAIN_API_URL='${CHAT_API_URL}';</script></head>|" \
  frontend/index.html > /tmp/index.html
```

### 9.3 Upload files

```bash
aws s3 cp /tmp/index.html s3://$FRONTEND_BUCKET/index.html --content-type "text/html"
aws s3 cp frontend/style.css s3://$FRONTEND_BUCKET/style.css --content-type "text/css"
aws s3 cp frontend/app.js s3://$FRONTEND_BUCKET/app.js --content-type "application/javascript"
```

### 9.4 Tạo CloudFront Distribution

1. AWS Console → CloudFront → Create Distribution
2. Origin: S3 bucket `geekbrain-frontend-xxxxx`
3. Origin Access: **Origin Access Control (OAC)** → Create new
4. Default root object: `index.html`
5. Viewer protocol: Redirect HTTP to HTTPS
6. Price class: Use only North America and Europe
7. Create Distribution
8. Copy the S3 bucket policy shown → paste vào S3 bucket policy

Đợi ~5 phút deploy. URL: `https://dxxxxxxxxxx.cloudfront.net`

---

## Bước 10 — Test End-to-End

Mở CloudFront URL trong browser.

### L1 Test
```
"Who leads Team Platform and what services do they own?"
→ Alex Chen. Owns PaymentGW + AuthSvc
→ Source tag: team_platform.md
```

### L2 Test
```
"What is PaymentGW's API rate limit?"
→ 1000 req/min (v2 supersedes v1's 500)
```

### L3 Test
```
"What was PaymentGW's total infrastructure cost in Q1 2026?"
→ $16,500 (tool badge: query_database)
```

```
"What is PaymentGW's current p99 latency?"
→ ~185ms (tool badge: get_service_metrics)
```

### L4 Test (multi-turn — cùng session)
```
Turn 1: "Which service had the highest infrastructure cost in March 2026?"
Turn 2: "Why did its costs spike?"
Turn 3: "Which team is responsible?"
```

---

## Troubleshooting

| Vấn đề | Nguyên nhân | Fix |
|--------|-------------|-----|
| Lambda timeout | Bedrock Agent chậm | Tăng timeout lên 120-180s |
| Agent không gọi tool | Tool description mơ hồ | Thêm "CURRENT" vs "HISTORICAL" vào description |
| DB connection refused | Lambda SG không reach RDS | Check RDS SG cho phép port 5432 từ Lambda SG |
| Monitoring API 503 | Lambda cold start | Gọi lại — lần 2 sẽ nhanh |
| KB trả về 0 chunks | Chưa sync | Vào KB Console → Sync |
| Frontend "No API" | URL chưa inject | Check `window.GEEKBRAIN_API_URL` trong page source |
| CORS error | OPTIONS method thiếu | Thêm CORS headers trên API Gateway |
| VPC Endpoint fail | private_dns chưa enable | Recreate endpoint với `--private-dns-enabled` |

---

## Tổng thời gian setup thủ công

| Bước | Thời gian |
|------|-----------|
| VPC + Networking | 5 min |
| RDS | 8 min (đợi available) |
| Seed Data | 3 min |
| Monitoring API | 5 min |
| Knowledge Base + Sync | 10 min |
| Action Group Lambda | 5 min |
| Bedrock Agent | 10 min (config tools) |
| Lambda Chat + API GW | 5 min |
| Frontend | 10 min (CloudFront deploy) |
| **Total** | **~60 min** |

---

## So sánh: Manual vs Terraform

| | Manual (guide này) | Terraform |
|---|---|---|
| Thời gian | ~60 min | ~15 min (apply) |
| Reproducible | Khó — phải nhớ từng bước | 1 lệnh `terraform apply` |
| Team collab | Mỗi người config khác nhau | State chung trên S3 |
| Khi nào dùng | Học, debug, hiểu hệ thống | Production, demo, CI/CD |
