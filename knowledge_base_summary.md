# 📚 Tổng hợp 36 file Knowledge Base — GeekBrain

## 🏢 NHÓM 1: Công ty & Tổ chức (3 files)

### 1. `company_overview.md`
- **GeekBrain** = fintech startup ở HCM, thành lập 2021
- ~200 nhân viên, Series C $45M (2024)
- **3 sản phẩm:** GeekPay (payment gateway), GeekCommerce (quản lý đơn hàng), GeekShield (chống gian lận ML)
- **Lãnh đạo:** CEO Kevin Park, CTO James Wright, VP Engineering Mark Sullivan

### 2. `onboarding_guide.md`
- Hướng dẫn cho nhân viên mới: setup VPN, GitHub, AWS, PagerDuty
- Slack channels: `#incidents`, `#deployments`, `#engineering`
- Local dev dùng Docker + PostgreSQL 15
- GeekBrain tuân thủ **PCI-DSS Level 1** (tiêu chuẩn bảo mật thanh toán cao nhất)

### 3. `security_policy.md`
- **Mã hóa:** AES-256 (data at rest), TLS 1.3 (data in transit)
- **API key** phải rotate mỗi **90 ngày**
- **JWT signing key** rotate mỗi **30 ngày**
- Không SSH trực tiếp vào production — mọi thứ qua CI/CD

---

## 👥 NHÓM 2: Các Team (4 files)

### 4. `team_platform.md` — ⭐ TEAM QUAN TRỌNG NHẤT
- **Lead: Alex Chen** (8 thành viên)
- Quản lý: **PaymentGW** + **AuthSvc**
- On-call: rotation hàng tuần
- Thành viên chính: Ben Torres (AuthSvc/security), Chris Park (bank API), Frank Liu (circuit breaker)

### 5. `team_commerce.md`
- **Lead: Jake Morgan** (6 thành viên)
- Quản lý: **OrderSvc**
- On-call: rotation 2 tuần/lần
- Thành viên: Kyle Reed (validation), Leo Brooks (payment integration), Maya Scott (fulfillment)

### 6. `team_data.md`
- **Lead: Ryan Blake** (5 thành viên)
- Quản lý: **FraudDetector** + **ReportingSvc**
- Sarah Wells: model monitoring, Tom Hayes: ETL/Redshift

### 7. `team_engagement.md`
- **Lead: Nina Shah** (4 thành viên — team NHỎ NHẤT)
- Quản lý: **NotificationSvc**
- **Đang gặp vấn đề:** thiếu nhân lực, message volume tăng → latency cao → merchant phàn nàn

---

## ⚙️ NHÓM 3: Các Service (6 files)

### 8. `service_paymentgw.md` — 💰 Service quan trọng nhất
- Payment gateway, xử lý thẻ + chuyển khoản
- **Tech:** Node.js, Express, PostgreSQL
- Kết nối 3 ngân hàng: **VCB** (chính), **Techcombank**, **BIDV**
- Có **circuit breaker** cho mỗi bank API
- **Flow:** AuthSvc validate token → FraudDetector score → chọn bank → xử lý
- Chi phí CAO NHẤT, đang tăng nhanh hơn revenue

### 9. `service_authsvc.md` — 🔐 Service nền tảng
- Xác thực OAuth2/JWT cho TẤT CẢ service khác
- **Tech:** Go, Redis (session cache)
- **Nếu AuthSvc chết → TOÀN BỘ platform chết**
- SLA cao nhất (99.99%)
- Redis hiện tại là **single node** = SPOF (điểm lỗi đơn)

### 10. `service_ordersvc.md` — 📦 Quản lý đơn hàng
- **Tech:** Java, Spring Boot, PostgreSQL
- State machine: create → validate → payment → fulfill → complete
- Phụ thuộc AuthSvc + PaymentGW + NotificationSvc
- SLA 99.9%

### 11. `service_frauddetector.md` — 🛡️ Chống gian lận ML
- **Tech:** Python, SageMaker, DynamoDB
- Mỗi giao dịch được score 0-1, ngưỡng hiện tại **0.75** (trước là 0.70)
- Latency SLA: **< 150ms p99**
- Retrain theo quý (đang muốn chuyển sang hàng tháng)
- Chi phí CAO thứ 2

### 12. `service_notificationsvc.md` — 📧 Thông báo
- **Tech:** Python, SQS, SES (email), SNS (SMS/push)
- Async — message vào queue → consumer xử lý
- **ĐANG GẶP VẤN ĐỀ LỚN:** consumer không auto-scale → queue dồn → latency tăng → merchant phàn nàn

### 13. `service_reportingsvc.md` — 📊 Báo cáo
- **Tech:** Python, Redshift, S3
- ETL chạy hàng đêm, báo cáo ad-hoc
- SLA thấp nhất (không critical)
- Query performance đang xuống do data lớn

---

## 📜 NHÓM 4: Chính sách (5 files)

### 14. `deployment_policy.md`
- Deploy chỉ **Thứ Hai–Thứ Năm, 09:00–17:00** Vietnam time
- ⛔ **FREEZE: Thứ Sáu 18:00 → Thứ Hai 08:00** (không deploy cuối tuần)
- Ngoại lệ: chỉ P1 hotfix, cần VP Engineering phê duyệt
- Canary deployment 5% traffic, giữ 15 phút trước khi 100%
- Cần 2 reviewer approve PR

### 15. `incident_response_policy.md`
- **P1 (Critical):** 15 phút phản hồi, notify VP 30 phút, CTO 1 giờ
- **P2 (High):** 30 phút phản hồi
- **P3 (Low):** ngày làm việc tiếp theo
- Postmortem bắt buộc cho P1/P2 trong 48 giờ
- Kênh chính: `#incidents` trên Slack

### 16. `sla_policy.md`
- 3 metric: Availability, Latency (p99), Error rate
- SLA nghiêm nhất → lỏng nhất: AuthSvc > PaymentGW > FraudDetector > OrderSvc > NotificationSvc > ReportingSvc
- **Số cụ thể nằm trong `sla_targets.csv`** (database), KHÔNG có trong file này

### 17. `change_management_policy.md`
- Mọi thay đổi infra phải có Change Request trong Jira
- CAB (Change Advisory Board) họp Thứ Ba 10:00
- Emergency Change chỉ cho P1, VP phê duyệt

### 18. `security_policy.md` *(đã tóm tắt ở trên)*

---

## 🔥 NHÓM 5: Postmortem sự cố (5 files)

### 19. `postmortem_INC001_paymentgw_jan.md` — PaymentGW P2, 15/01/2026
- **Vấn đề:** Database connection pool hết (20/20)
- **Thời gian:** 45 phút
- **Fix:** Tăng pool từ 20 → 50
- **Bài học:** Cần review capacity định kỳ

### 20. `postmortem_INC004_authsvc.md` — AuthSvc P2, 22/02/2026
- **Vấn đề:** JWT key rotation script FAIL THẦM — exit code 0 nhưng không rotate
- **Thời gian:** 60 phút (phát hiện muộn 4.5 giờ!)
- **Fix:** Sửa error handling, thêm sign-and-verify trước khi swap key
- **Bài học:** Exit code 0 ≠ success, cần end-to-end verification

### 21. `postmortem_INC005_paymentgw_mar.md` — ⭐ PaymentGW P1, 05/03/2026 (SỰ CỐ LỚN NHẤT Q1)
- **Vấn đề:** VCB bank timeout → circuit breaker open → BỊ KẸT vì health check sai
- **Thời gian:** 3 TIẾNG, 40% giao dịch fail
- **Nguyên nhân:** Health check parse sai HTTP 503 thành "healthy"
- **Fix:** Sửa health check, tách manual reset khỏi health check
- **Hậu quả:** Chi phí PaymentGW tháng 3 tăng vọt (retry storms, batch processing)

### 22. `postmortem_INC006_frauddetector.md` — FraudDetector P2, 12/03/2026
- **Vấn đề:** Model drift do Tết Nguyên Đán — false positive từ 2% → 15%
- **Thời gian:** 90 phút
- **Fix:** Retrain model + đổi threshold 0.70 → 0.75
- **Bài học:** Cần data mùa vụ trong training, cần drift detection tự động

### 23. `postmortem_INC008_reportingsvc.md` — ReportingSvc P2, 02/04/2026
- **Vấn đề:** ETL pipeline timeout vì full table scan trên Redshift
- **Thời gian:** 2 giờ
- **Fix:** Thêm sort keys + pagination
- **Bài học:** Query cần optimize khi data lớn

---

## 📋 NHÓM 6: Runbooks (2 files)

### 24. `runbook_paymentgw_circuit_breaker.md`
- Hướng dẫn xử lý circuit breaker: check status, force reset, force open
- 3 trạng thái: CLOSED (bình thường) → OPEN (chặn traffic) → HALF_OPEN (test recovery)
- Sau INC-005: reset endpoint không gọi health check nữa

### 25. `runbook_frauddetector_model_retraining.md`
- 7 bước retrain: export data → train SageMaker → evaluate → staging → A/B test → promote → adjust threshold
- Threshold hiện tại: **0.75**
- Retrain khi false positive > 5% hoặc false negative > 1% (sustained 30 phút)
- Toàn bộ quy trình: 4-6 giờ

---

## 📊 NHÓM 7: Meeting Notes & Planning (4 files)

### 26. `q4_2025_planning_notes.md`
- Plan Q4 2025: circuit breaker cho PaymentGW, JWT rotation automation, PCI-DSS audit prep

### 27. `q1_2026_review_notes.md`
- Concern: PaymentGW chi phí tăng nhanh hơn revenue
- FraudDetector monitoring gap → cần alert tự động
- NotificationSvc: merchant phàn nàn, team thiếu người
- Positive: Refund API launch thành công

### 28. `weekly_standup_mar10_2026.md`
- PaymentGW đang clear backlog sau P1
- FraudDetector false positive đang tăng
- NotificationSvc latency tăng do volume growth

### 29. `architecture_review_feb_2026.md`
- 5 topics: FraudDetector scaling, AuthSvc Redis SPOF, PaymentGW circuit breaker, NotificationSvc SQS, observability gaps

---

## 📖 NHÓM 8: API & Tech (4 files)

> [!IMPORTANT]
> ### ⚠️ CONFLICT QUAN TRỌNG CHO L2
> **`api_reference_v1_archived.md`:** Rate limit = **500 req/min** — ĐÃ ARCHIVED
> **`api_reference_v2.md`:** Rate limit = **1000 req/min** — CURRENT
> 
> Khi hỏi "What is the API rate limit?", hệ thống PHẢI trả lời **1000** (v2) và acknowledge v1 nói 500 nhưng đã archived.

### 30. `api_reference_v1_archived.md`
- Version cũ, đã retired. Auth: Bearer token đơn giản. Rate limit 500/min

### 31. `api_reference_v2.md`
- Version hiện tại. Auth: **API key + HMAC-SHA256**. Rate limit **1000/min**
- Thêm `/refunds` endpoint (không có trong v1)

### 32. `api_webhooks.md`
- Webhook events: `payment.completed`, `payment.failed`, `payment.refunded`, `payment.disputed`
- Retry: 3 lần với exponential backoff
- Endpoint phải trả 200 trong 5 giây

### 33. `tech_radar_2026.md`
- **ADOPT:** Node.js (PaymentGW), Java (OrderSvc), Go (AuthSvc), Python (FraudDetector/ReportingSvc/NotificationSvc)
- **ADOPT:** PostgreSQL, DynamoDB, Redis, SQS/SES, SageMaker, ECS Fargate, CloudWatch, Grafana
- **TRIAL:** Amazon Bedrock (đang thử cho AI features!), OpenSearch Serverless, Step Functions, Graviton
- **HOLD:** Kubernetes (ECS Fargate đủ dùng), MongoDB (standardized trên PostgreSQL + DynamoDB)

---

## 📈 NHÓM 9: Capacity & Cost (3 files)

### 34. `capacity_planning_q2_2026.md`
- Transaction growth dự kiến **15% QoQ**
- PaymentGW: cần horizontal scaling (PRIORITY HIGH)
- AuthSvc: Redis cluster migration 3 nodes (PRIORITY HIGH)
- NotificationSvc: auto-scaling SQS consumers (PRIORITY CRITICAL — đang gây degradation)
- ReportingSvc: Redshift resize

### 35. `cost_optimization_initiative.md`
- Mục tiêu: **giảm 15% chi phí infra** cuối Q2 2026
- PaymentGW + FraudDetector = 2 service đắt nhất
- Strategies: Reserved Instances, right-sizing, ElastiCache caching, dev env consolidation

### 36. `monitoring_dashboard_guide.md`
- Grafana: Service Health Overview, PaymentGW Transaction Dashboard, FraudDetector Model Dashboard, Cost Dashboard
- CloudWatch alarms cho latency, error rate, availability
- PaymentGW thêm: circuit breaker state, connection pool utilization
- FraudDetector thêm: false positive/negative rate

---

# 🗺️ DATA SOURCE MAP — Cái gì ở đâu?

> [!IMPORTANT]
> Đây là thông tin quan trọng nhất! Biết data ở đâu quyết định bạn build đúng hay sai.

| Loại câu hỏi | Ví dụ | Trả lời từ đâu |
|---|---|---|
| Người, team, quy trình | "Ai lead Team Platform?" → Alex Chen | 📄 Knowledge base (RAG) |
| Chính sách | "Deployment freeze khi nào?" → Fri 18:00 – Mon 08:00 | 📄 Knowledge base (RAG) |
| API specs | "Rate limit bao nhiêu?" → 1000 (v2, conflict với v1: 500) | 📄 Knowledge base (RAG + conflict resolution) |
| Sự cố | "PaymentGW P1 tháng 3 là gì?" → Circuit breaker stuck | 📄 Knowledge base (RAG) |
| **Chi phí cụ thể** | "PaymentGW Q1 cost?" → **$16,500** | 🗄️ **Database** (tool) |
| **SLA target numbers** | "NotificationSvc latency SLA?" → **2000ms** | 🗄️ **Database** (tool) |
| **Daily metrics lịch sử** | "Average error rate tháng 2?" | 🗄️ **Database** (tool) |
| **Trạng thái hiện tại** | "PaymentGW latency bây giờ?" → ~184ms | 🌐 **API** (tool) |
| **Status hiện tại** | "NotificationSvc có ổn không?" → degraded! | 🌐 **API** (tool) |
| **So sánh SLA** | "NotificationSvc đạt SLA?" → CẢ HAI sources | 🗄️ DB + 🌐 API |

---

# 🧪 HƯỚNG DẪN TEST — Câu hỏi mẫu cho từng level

## L1 — Simple RAG (tìm 1 fact trong 1 doc)

| Câu hỏi test | Đáp án đúng | File nguồn |
|---|---|---|
| "Who is the Team Platform lead?" | Alex Chen | `team_platform.md` |
| "What is the deployment freeze window?" | Friday 18:00 to Monday 08:00 | `deployment_policy.md` |
| "What authentication method does PaymentGW API v2 use?" | API key + HMAC-SHA256 | `api_reference_v2.md` |
| "What language is AuthSvc written in?" | Go | `service_authsvc.md` |
| "What is FraudDetector's decision threshold?" | 0.75 | `service_frauddetector.md` |
| "How often are JWT signing keys rotated?" | Every 30 days | `security_policy.md` |

## L2 — Multi-Source RAG (nhiều doc, xử lý conflict)

| Câu hỏi test | Đáp án đúng | Cần tổng hợp từ |
|---|---|---|
| "What is PaymentGW's API rate limit?" | **1000/min** (v2 current), v1 nói 500 nhưng đã archived | `api_reference_v2.md` + `api_reference_v1_archived.md` |
| "Can Team Commerce deploy on Friday night for a P1 bug?" | Có, nhưng cần: P1 declared + VP Mark Sullivan approval + team lead present | `deployment_policy.md` + `incident_response_policy.md` + `team_commerce.md` |
| "What caused the PaymentGW cost increase in March?" | Circuit breaker stuck (INC-005) → retry storms + catch-up processing | `postmortem_INC005_paymentgw_mar.md` + `q1_2026_review_notes.md` + `cost_optimization_initiative.md` |

## L3 — Tool-Augmented RAG (cần query DB hoặc gọi API)

| Câu hỏi test | Đáp án đúng | Tool cần gọi |
|---|---|---|
| "What was PaymentGW's total infrastructure cost in Q1 2026?" | **$16,500** | 🗄️ `query_database` → SQL: `SELECT SUM(total_cost) FROM monthly_costs WHERE service='PaymentGW' AND month IN ('2026-01','2026-02','2026-03')` |
| "Which service had the highest cost in March 2026?" | **PaymentGW at $7,500** | 🗄️ `query_database` → SQL: `SELECT service, total_cost FROM monthly_costs WHERE month='2026-03' ORDER BY total_cost DESC LIMIT 1` |
| "What is PaymentGW's current p99 latency?" | ~185ms (giá trị live) | 🌐 `get_service_metrics("PaymentGW")` |
| "Is NotificationSvc meeting its latency SLA?" | **KHÔNG** (latency ~3200ms vs target 2000ms) | 🌐 API (metrics hiện tại) + 🗄️ DB (SLA target) |
| "What is NotificationSvc's SLA latency target?" | **2000ms** | 🗄️ `query_database` → SQL: `SELECT target FROM sla_targets WHERE service='NotificationSvc' AND metric='latency_p99_ms'` |

## L4 — Memory (multi-turn conversation)

```
Turn 1: "Which service had the highest cost in March?"
→ PaymentGW at $7,500 (DB query)

Turn 2: "Why did its costs spike?"
→ Hệ thống phải hiểu "its" = PaymentGW
→ INC-005 circuit breaker incident → retry storms (RAG)

Turn 3: "Which team is responsible?"
→ Vẫn biết đang nói về PaymentGW → Team Platform, led by Alex Chen (RAG)
```

---

# 🔑 CONFLICT & TRICKY POINTS (cần nhớ cho L2)

> [!WARNING]
> Những điểm này sẽ bị hỏi khi demo. Hệ thống phải xử lý đúng!

1. **Rate limit conflict:** v1 = 500, v2 = 1000. v1 đã ARCHIVED → đáp án đúng là 1000
2. **Auth method khác nhau:** v1 dùng Bearer token, v2 dùng API key + HMAC-SHA256
3. **FraudDetector threshold thay đổi:** 0.70 → 0.75 (sau INC-006)
4. **SLA policy nói framework nhưng KHÔNG nói số cụ thể** → số nằm trong CSV (database)
5. **Docs nói "costs are rising" nhưng KHÔNG nói bao nhiêu** → số cụ thể nằm trong CSV
6. **NotificationSvc đang degraded** — chỉ API monitoring biết, docs chỉ nói "under strain"
