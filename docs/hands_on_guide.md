# Hands-on Guide — GeekBrain AI Assistant (W4)

Hướng dẫn từng bước deploy toàn bộ hệ thống từ zero đến production.

---

## Mục lục

1. [Prerequisites](#1-prerequisites)
2. [Clone Repository](#2-clone-repository)
3. [Cấu trúc Project](#3-cấu-trúc-project)
4. [Tạo S3 Backend cho Terraform](#4-tạo-s3-backend-cho-terraform)
5. [Deploy Infrastructure](#5-deploy-infrastructure)
6. [Cấu hình DeepSeek V3.2 (Manual)](#6-cấu-hình-deepseek-v32-manual)
7. [Verify Deployment](#7-verify-deployment)
8. [Test từng Level](#8-test-từng-level)
9. [Update Knowledge Base](#9-update-knowledge-base)
10. [Troubleshooting](#10-troubleshooting)
11. [Teardown](#11-teardown)

---

## 1. Prerequisites

### Tools cần cài

| Tool | Version | Cách cài |
|------|---------|----------|
| AWS CLI | v2 | `curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" && unzip awscliv2.zip && sudo ./aws/install` |
| Terraform | >= 1.5 | `brew install terraform` hoặc download từ hashicorp.com |
| Python | 3.12 | `brew install python@3.12` |
| pip | latest | `python -m pip install --upgrade pip` |

### AWS Account

- Có IAM user/role với quyền Admin (hoặc ít nhất: Bedrock, Lambda, API Gateway, S3, CloudFront, RDS, OpenSearch Serverless, VPC, IAM)
- Region: **us-east-1** (bắt buộc — DeepSeek V3.2 chỉ available ở đây)
- Enable model access: vào Bedrock console → Model access → Enable:
  - Amazon Titan Embed Text v2
  - DeepSeek V3.2 (cross-region inference)

### Cấu hình AWS CLI

```bash
aws configure
# AWS Access Key ID: <your-key>
# AWS Secret Access Key: <your-secret>
# Default region: us-east-1
# Default output: json

# Verify
aws sts get-caller-identity
```

---

## 2. Clone Repository

```bash
git clone https://github.com/hoang-trong-tan/G9-W4.git
cd G9-W4
```

---

## 3. Cấu trúc Project

```
G9-W4/
├── terraform/              # Infrastructure as Code
│   ├── main.tf            # Root module — wires everything together
│   ├── variables.tf       # Input variables (region, model IDs, etc.)
│   ├── outputs.tf         # Output values (URLs, IDs)
│   └── modules/
│       ├── ai_engine/     # S3 + OpenSearch + Bedrock KB + ingestion
│       ├── backend/       # Bedrock Agent + Action Group + Lambda + API GW
│       ├── monitoring_api/# FastAPI Lambda + API Gateway
│       ├── database/      # RDS PostgreSQL + Seed Lambda
│       ├── network/       # VPC, subnets, SGs, VPC Endpoint
│       └── frontend/      # S3 + CloudFront
├── lambda/                 # Lambda Chat + Action Group handler
│   ├── lambda_function.py     # Invokes Bedrock Agent
│   ├── action_group_function.py  # Executes 6 tools
│   ├── requirements.txt
│   └── build.py
├── monitoring_lambda/      # FastAPI Monitoring API
│   ├── monitoring_api.py
│   ├── handler.py         # Mangum wrapper
│   ├── requirements.txt
│   └── build.py
├── seed_lambda/            # Database seeder
│   ├── handler.py
│   ├── requirements.txt
│   └── build.py
├── frontend/               # Chat UI (HTML/CSS/JS)
│   ├── index.html
│   ├── style.css
│   └── app.js
├── data_package/
│   ├── knowledge_base/    # 36 markdown docs
│   └── structured_data/   # CSV files (costs, incidents, SLAs, metrics)
└── docs/
    ├── W4_evidence.md
    └── diagrams/
```

---

## 4. Tạo S3 Backend cho Terraform

Terraform state cần lưu trên S3 để team collaborate. Chạy **1 lần duy nhất**:

```bash
# Lấy account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Tạo S3 bucket cho state
aws s3 mb s3://geekbrain-tfstate-${ACCOUNT_ID} --region us-east-1

# Tạo DynamoDB table cho state locking
aws dynamodb create-table \
  --table-name geekbrain-tfstate-locks \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region us-east-1
```

Sau đó update `terraform/main.tf` line 5:
```hcl
bucket = "geekbrain-tfstate-<YOUR_ACCOUNT_ID>"
```

---

## 5. Deploy Infrastructure

### Bước 1: Init Terraform

```bash
cd terraform
terraform init
```

Output: "Terraform has been successfully initialized!"

### Bước 2: Plan (review changes)

```bash
terraform plan
```

Sẽ tạo ~40-50 resources. Review và confirm không có gì bất thường.

### Bước 3: Apply

```bash
terraform apply
```

Nhập `yes` khi được hỏi. **Thời gian: ~15-20 phút** vì:
- OpenSearch Serverless collection cần ~2 phút wait
- RDS instance cần ~5 phút
- Bedrock Agent preparation cần ~30s
- KB ingestion cần ~3-5 phút

### Bước 4: Lưu outputs

```bash
terraform output
```

Kết quả quan trọng:
```
frontend_cloudfront_url = "https://d1xxxxxxxx.cloudfront.net"
api_gateway_url = "https://xxxxxxxx.execute-api.us-east-1.amazonaws.com/prod"
knowledge_base_id = "XXXXXXXXXX"
monitoring_api_url = "https://xxxxxxxx.execute-api.us-east-1.amazonaws.com/prod"
```

---

## 6. Cấu hình DeepSeek V3.2 (Manual)

> DeepSeek V3.2 không thể set qua Terraform API — phải config thủ công.

1. Vào AWS Console → Amazon Bedrock → Agents
2. Click agent `geekbrain-agent`
3. Trong Agent builder → Model details → Edit
4. Chọn model: **DeepSeek V3.2** (hoặc cross-region inference profile)
5. Save → Prepare Agent → Create alias (hoặc update alias `prod`)

Terraform có `lifecycle { ignore_changes = [foundation_model] }` nên lần apply sau sẽ không override config này.

---

## 7. Verify Deployment

### Check frontend

Mở CloudFront URL trong browser:
```
https://d1xxxxxxxx.cloudfront.net
```

Phải thấy chat interface với status "Connected".

### Check API Gateway

```bash
curl -X POST https://xxxxxxxx.execute-api.us-east-1.amazonaws.com/prod/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "Who leads Team Platform?", "session_id": "test-1"}'
```

### Check Monitoring API

```bash
curl https://xxxxxxxx.execute-api.us-east-1.amazonaws.com/prod/services
curl https://xxxxxxxx.execute-api.us-east-1.amazonaws.com/prod/metrics/PaymentGW
curl https://xxxxxxxx.execute-api.us-east-1.amazonaws.com/prod/status/PaymentGW
```

### Check Database (via Lambda logs)

```bash
aws logs tail /aws/lambda/geekbrain-seed-db --since 1h
```

---

## 8. Test từng Level

### L1 — Simple RAG

```
"Who leads Team Platform and what services do they own?"
→ Expected: Alex Chen. Owns PaymentGW + AuthSvc
→ Verify: Source tag hiển thị team_platform.md
```

```
"What is GeekBrain's data retention policy for transaction logs?"
→ Expected: 7 years
```

### L2 — Multi-Source / Conflict

```
"What is PaymentGW's API rate limit?"
→ Expected: 1000 (v2 supersedes v1's 500)
→ Verify: Mentions conflict between v1 and v2
```

```
"If Team Commerce has a P1 bug in OrderSvc on Friday night, can they deploy?"
→ Expected: Yes, P1 overrides freeze with VP approval
→ Verify: Cites deployment_policy.md + incident_response_policy.md
```

### L3 — Tool Calling

```
"What was PaymentGW's total infrastructure cost in Q1 2026?"
→ Expected: $16,500
→ Verify: Tool badge "query_database" + SQL query visible
```

```
"What is PaymentGW's current p99 latency?"
→ Expected: ~185ms (±5% jitter)
→ Verify: Tool badge "get_service_metrics"
```

```
"Is PaymentGW's error rate within SLA?"
→ Expected: Yes. 0.08% vs 0.1% target
→ Verify: Both get_service_metrics AND query_database called
```

### L4 — Memory (multi-turn)

```
Turn 1: "Which service had the highest infrastructure cost in March 2026?"
→ PaymentGW $7,500

Turn 2: "Why did its costs spike?"
→ References INC-005 postmortem (circuit breaker stuck OPEN)

Turn 3: "Which team is responsible?"
→ Team Platform, Alex Chen

Turn 4: "The postmortem mentioned a review deadline. Is it overdue?"
→ April 15, 2026 — Yes, overdue
```

---

## 9. Update Knowledge Base

Khi thêm/sửa docs trong `data_package/knowledge_base/`:

### Cách 1: Tự động qua Terraform (khuyến nghị)

```bash
cd terraform
terraform apply
```

Terraform tự detect MD5 hash change → upload files mới → trigger ingestion job → poll until complete.

### Cách 2: Trigger thủ công

```bash
KB_ID=$(terraform output -raw knowledge_base_id)
DS_ID=$(aws bedrock-agent list-data-sources \
  --knowledge-base-id $KB_ID \
  --query 'dataSourceSummaries[0].dataSourceId' --output text)

aws bedrock-agent start-ingestion-job \
  --knowledge-base-id $KB_ID \
  --data-source-id $DS_ID
```

Check status:
```bash
aws bedrock-agent list-ingestion-jobs \
  --knowledge-base-id $KB_ID \
  --data-source-id $DS_ID \
  --query 'ingestionJobSummaries[0].status'
```

---

## 10. Troubleshooting

### Lambda timeout (>30s)

- Action Group Lambda timeout = 30s. Nếu RDS query chậm → tăng `timeout` trong `terraform/modules/backend/main.tf`
- Lambda Chat timeout = 120s. Bedrock Agent đôi khi chậm do orchestration loop

### Agent không gọi tool

- Kiểm tra tool descriptions trong `terraform/modules/backend/main.tf` (line 266-355)
- Description phải phân biệt rõ "CURRENT/live" vs "HISTORICAL"
- Test: hỏi "What is PaymentGW's total cost?" — nếu Agent trả lời từ KB thay vì tool → description chưa precise

### OpenSearch index error

```bash
aws opensearchserverless batch-get-collection \
  --names geekbrain-kb \
  --query 'collectionDetails[0].status'
```

Status phải là `ACTIVE`. Nếu `CREATING` → đợi thêm 2-3 phút.

### KB ingestion failed

```bash
KB_ID=$(terraform output -raw knowledge_base_id)
DS_ID=$(aws bedrock-agent list-data-sources \
  --knowledge-base-id $KB_ID \
  --query 'dataSourceSummaries[0].dataSourceId' --output text)

aws bedrock-agent list-ingestion-jobs \
  --knowledge-base-id $KB_ID \
  --data-source-id $DS_ID
```

### Frontend hiển thị "No API configured"

- Check page source → tìm `window.GEEKBRAIN_API_URL`
- Nếu trống → redeploy frontend:
```bash
terraform apply -target=module.frontend
```

### Cold start chậm (5-10s lần đầu)

- Bình thường với Lambda. Lần gọi tiếp sẽ nhanh hơn (<1s)
- Action Group Lambda trong VPC có thêm ENI attachment time (~2-5s)
- Tip: "warm up" trước khi demo bằng cách gửi 1 câu hỏi đơn giản

### Agent trả lời sai số liệu

- Kiểm tra database đã seed chưa:
```bash
aws logs tail /aws/lambda/geekbrain-seed-db --since 24h
```
- Nếu chưa seed → invoke lại:
```bash
aws lambda invoke --function-name geekbrain-seed-db response.json
cat response.json
```

---

## 11. Teardown

```bash
cd terraform
terraform destroy
```

Nhập `yes`. Tất cả resources sẽ bị xóa (~5 phút).

Xóa thêm S3 state bucket nếu không cần:
```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
aws s3 rb s3://geekbrain-tfstate-${ACCOUNT_ID} --force
aws dynamodb delete-table --table-name geekbrain-tfstate-locks
```

---

## Tổng quan Chi phí

| Resource | Cost/month (estimate) |
|----------|----------------------|
| RDS db.t3.micro | ~$15 |
| OpenSearch Serverless (2 OCU min) | ~$48 |
| Lambda (low traffic) | < $1 |
| CloudFront | < $1 |
| S3 | < $1 |
| API Gateway | < $1 |
| Bedrock Agent (per request) | ~$0.001/request |
| **Total** | **~$65-70/month** |

> Tip: `terraform destroy` khi không dùng. OpenSearch Serverless là phần tốn nhất (~$48/month cho 2 OCU minimum).

---

## Kiến trúc tổng quan (Quick Reference)

```
User → CloudFront → S3 (frontend)
                         ↓ POST /chat
                    API Gateway
                         ↓
                    Lambda Chat (outside VPC)
                         ↓
                    Bedrock Agent (DeepSeek V3.2)
                    ├── Knowledge Base → OpenSearch Serverless
                    └── Action Group → Lambda (in VPC)
                                        ├── query_database → RDS PostgreSQL
                                        └── get_metrics/status → Monitoring API
                                                                  (via VPC Endpoint)
```

**Key: Không có NAT Gateway.** Lambda Chat gọi Bedrock trực tiếp. Action Group dùng VPC Interface Endpoint.
