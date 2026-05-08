# Kịch bản thuyết trình W4 — Group 9

> Tổng thời gian: ~10-12 phút
> Format: Architecture (3 min) → Q&A (3 min) → Live Demo (4-5 min) → Lessons (1 min)

---

## Phần 1 — Architecture (3 phút)

### Slide 1: Title (15s)

> *Người trình bày mở đầu*

"Xin chào mọi người, nhóm 9 xin trình bày project tuần 4 — GeekBrain AI Assistant. Đây là một hệ thống RAG kết hợp Tool Calling và Memory, xây dựng trên Amazon Bedrock Agents với model DeepSeek V3.2."

### Slide 2: Agenda (15s)

"Hôm nay chúng em sẽ trình bày 4 phần: Architecture, Q&A, Live Demo các level L1 đến L4, và Lessons Learned."

### Slide 3: Divider (skip nhanh)

### Slide 4: System Architecture (60s)

> *Chỉ vào diagram*

"Đây là tổng quan kiến trúc hệ thống:

- **Frontend** host trên S3 + CloudFront — user gửi câu hỏi qua POST /chat
- **API Gateway** route request đến **Lambda Chat** — Lambda này chạy NGOÀI VPC, gọi thẳng Bedrock Agent qua AWS internal network
- **Bedrock Agent** là trung tâm — nó quyết định: lấy từ Knowledge Base, gọi tool, hoặc cả hai
- **Knowledge Base**: 36 markdown docs được embed bởi Titan v2 (1024 chiều), lưu trong OpenSearch Serverless
- **Action Group Lambda** chạy TRONG VPC private subnet — gọi được RDS PostgreSQL trực tiếp, gọi Monitoring API qua VPC Interface Endpoint
- Điểm quan trọng: **không có NAT Gateway** — tất cả traffic đi qua VPC Endpoint hoặc AWS internal network"

### Slide 5: Key Decisions (45s)

"3 quyết định quan trọng:

1. **Bedrock Agents thay vì custom pipeline** — Agent tự handle routing giữa KB và tools. Trade-off: ít control hơn nhưng nhanh hơn nhiều.

2. **VPC Interface Endpoint thay vì NAT Gateway** — Action Group Lambda cần gọi Monitoring API. Thay vì đi qua NAT ra internet rồi vòng lại, dùng VPC Endpoint giữ traffic trong AWS, tiết kiệm ~32$/tháng.

3. **Lambda Chat ngoài VPC** — chỉ gọi Bedrock API, không cần VPC. Tránh cold start 5-10 giây do ENI attachment.

Một điều **không hoạt động**: cấu hình DeepSeek V3.2 qua Terraform bị lỗi API, phải dùng lifecycle ignore_changes và config thủ công trên console."

### Slide 6-7: Request Flow & Tool Routing (30s)

"Flow chi tiết: request đi từ user → API GW → Lambda → Agent. Agent có orchestration loop — phân tích câu hỏi, quyết định retrieve KB hay gọi tool, lặp lại cho đến khi đủ thông tin, rồi generate answer.

Tool routing: Agent có 6 tools — query_database cho data lịch sử, get_service_metrics/status cho data realtime, list_services, get_incident_history, compare_services."

---

## Phần 2 — Individual Q&A (3 phút)

> *Trainer chọn 2-3 người random hỏi*

### Câu hỏi có thể gặp + gợi ý trả lời:

**Q: Bedrock Agent hoạt động như thế nào?**
> "Agent nhận câu hỏi, phân tích xem cần retrieve từ KB hay gọi tool. Nó tự viết query/tool call, nhận kết quả, rồi generate answer. Tất cả trong 1 orchestration loop. Dùng enableTrace=True để xem từng bước."

**Q: Knowledge Base chunk documents như thế nào?**
> "Hierarchical chunking — parent chunk 1500 tokens, child chunk 300 tokens, overlap 60 tokens. Embedding bằng Titan Embed v2 ra vector 1024 chiều, lưu trong OpenSearch Serverless dùng HNSW index."

**Q: Tại sao không dùng NAT Gateway?**
> "Lambda Chat không cần VPC nên gọi Bedrock trực tiếp. Action Group Lambda trong VPC cần gọi Monitoring API — dùng VPC Interface Endpoint cho execute-api, traffic đi qua AWS backbone mà không cần internet. Tiết kiệm cost và giảm latency."

**Q: Memory (L4) hoạt động thế nào?**
> "Bedrock Agent có session management built-in. Frontend generate 1 session_id per browser session, gửi kèm mỗi request. Agent giữ context 1800 giây (30 phút). Follow-up questions như 'its costs' được resolve nhờ conversation history trong session."

**Q: Tool nào gọi cho câu hỏi 'PaymentGW cost Q1 2026'?**
> "query_database — vì đó là data lịch sử. Agent generate SQL: SELECT SUM(total_cost) FROM monthly_costs WHERE service='PaymentGW' AND month BETWEEN '2026-01' AND '2026-03'. Trả về $16,500."

**Q: Tool nào cho 'current p99 latency'?**
> "get_service_metrics — vì đó là data realtime. Gọi Monitoring API endpoint GET /metrics/PaymentGW, trả về ~185ms."

**Q: Làm sao đảm bảo Agent chọn đúng tool?**
> "Tool descriptions phải cực kỳ chính xác. Ví dụ: 'Returns CURRENT live metrics; for HISTORICAL data use query_database'. Mơ hồ như 'Gets data' thì Agent gọi nhầm."

**Q: Observability Dashboard hoạt động thế nào?**
> "Lambda trả về trace info: tools_used, sources, tool_details, pipeline_traces. Frontend render ra: source tags xanh, tool badges tím, query details collapsible, và full orchestration trace."

**Q: KB Sync (Bonus C) hoạt động thế nào?**
> "Terraform detect khi file .md thay đổi qua MD5 hash. Trigger null_resource chạy aws bedrock-agent start-ingestion-job. Poll status mỗi 10 giây, timeout 10 phút. Tự động mỗi lần terraform apply."

---

## Phần 3 — Live Demo (4-5 phút)

> *Mở https://d1alut1mvmxglj.cloudfront.net/*

### Demo L1 — Simple RAG (45s)

**Hỏi:** "Who leads Team Platform and what services do they own?"

> "Đây là câu hỏi L1 — chỉ cần 1 document. Các bạn thấy câu trả lời 'Alex Chen, owns PaymentGW + AuthSvc' — và bên dưới có source tag xanh hiển thị file team_platform.md. Đó là bằng chứng retrieval đã xảy ra."

### Demo L2 — Multi-Source (45s)

**Hỏi:** "What is PaymentGW's API rate limit?"

> "Câu này có conflict — v1 nói 500, v2 nói 1000. Hệ thống retrieve cả 2 documents, nhận ra conflict, và chọn v2 (1000) vì là phiên bản current. Nó cũng explain tại sao — đây là L2."

### Demo L3 — Tool Calling (90s)

**Hỏi:** "What was PaymentGW's total infrastructure cost in Q1 2026?"

> "Câu này không có trong documents nào. Hệ thống phải gọi query_database tool. Các bạn thấy tool badge tím hiển thị 'query_database', và expand Query Details thấy SQL query thực tế. Kết quả: $16,500 — đúng với data trong database."

**Hỏi thêm (nếu có thời gian):** "What is PaymentGW's current p99 latency?"

> "Câu này cần data realtime — hệ thống gọi get_service_metrics thay vì database. Trả về ~185ms. Hai câu hỏi khác nhau, hai tools khác nhau — Agent routing đúng."

### Demo L4 — Memory (60s)

**Hỏi lần lượt:**
1. "Which service had the highest infrastructure cost in March 2026?"
2. "Why did its costs spike?"
3. "Which team is responsible?"

> "Chú ý câu 2 dùng 'its' — hệ thống biết đang nói về PaymentGW từ câu 1. Câu 3 dùng context từ cả 2 câu trước. Đây là L4 — memory across turns, không cần nhắc lại context."

### Demo Bonus A — Observability (30s)

> *Expand phần 'Observability Pipeline (Traces)' trong 1 câu trả lời*

"Bonus A — mỗi câu trả lời đều hiển thị pipeline internals: step 1 Model Input, step 2 KB Query hoặc Tool Invocation, step 3 Observation với actual data, step 4 Final Response. Trainer có thể thấy toàn bộ reasoning process."

---

## Phần 4 — Lessons Learned (1 phút)

### Slide 15: Lessons

"Level khó nhất: **L3 — Tool-Augmented RAG**.

Lý do: Tool descriptions phải cực kỳ precise. Ban đầu viết mơ hồ, Agent gọi nhầm tool liên tục. Sau khi iterate nhiều lần — thêm 'CURRENT' vs 'HISTORICAL', thêm ví dụ khi nào dùng tool nào — Agent mới route đúng consistently.

Nếu có thêm 1 ngày: thêm query rewriting cho L4 (biến pronouns thành explicit), automated testing với file question JSON, và fallback khi Monitoring API down."

### Slide 16: Thank You

"Cảm ơn mọi người đã lắng nghe. Evidence Pack tại docs/W4_evidence.md trong repo. Mời trainer đặt câu hỏi."

---

## Tips

- Nếu live demo fail → nói "Hệ thống đôi khi timeout do cold start Lambda, em có screenshot trong Evidence Pack"
- Nếu được hỏi về cost → "Toàn bộ infra chạy dưới $5/ngày, không có NAT Gateway"
- Nếu được hỏi tại sao DeepSeek → "Được assign bởi course, config qua Bedrock cross-region inference profile"
- **Đừng nói "em không biết"** — nói "theo hiểu biết của em thì..." rồi trả lời best effort
