# 📊 Phân tích & Đề xuất Chunking Strategy cho 36 file Knowledge Base

## 1. Tổng quan 36 file

### Thống kê kích thước

| Nhóm | Số file | Kích thước range | Avg lines |
|------|---------|-----------------|-----------|
| Công ty & Tổ chức | 3 | 3.0–6.5 KB | ~90 |
| Các Team | 4 | 3.0–3.8 KB | ~75 |
| Các Service | 6 | 3.2–4.7 KB | ~80 |
| Chính sách | 5 | 4.4–5.3 KB | ~115 |
| Postmortem | 5 | 3.8–7.5 KB | ~130 |
| Runbooks | 2 | 5.3–5.8 KB | ~140 |
| Meeting Notes | 4 | 3.6–6.4 KB | ~100 |
| API & Tech | 4 | 3.8–8.3 KB | ~150 |
| Capacity & Cost | 3 | 6.3–6.9 KB | ~143 |
| **On-call Handbook** | 1 | 6.4 KB | 173 |

**Tổng:** 36 file + 1 file bổ sung (on_call_handbook.md) = **37 file thực tế** (summary liệt kê 36 nhưng có thêm on_call_handbook)

### Đặc điểm chung

- **Kích thước nhỏ**: 3–8 KB (57–194 dòng), trung bình ~5 KB (~100 dòng)
- **Markdown có cấu trúc rõ**: Tất cả đều dùng YAML frontmatter + heading hierarchy (H1→H2→H3)
- **Nội dung tự chứa**: Mỗi file là 1 "đơn vị kiến thức" hoàn chỉnh (1 service, 1 team, 1 policy, 1 postmortem...)
- **Cross-reference giữa các file**: Nhiều file tham chiếu chéo (ví dụ: `deployment_policy.md` nhắc đến `incident_response_policy.md`, postmortem nhắc đến runbook...)
- **Metadata phong phú**: YAML frontmatter chứa `doc_id`, `tags`, `category`, `owner`, `status`

---

## 2. Đánh giá 5 loại Chunking

### ❌ Default Chunking (~300 tokens)
> *Tự động chia thành chunk ~300 tokens*

| Tiêu chí | Đánh giá |
|-----------|----------|
| Phù hợp? | **KHÔNG khuyến khích** |
| Lý do | 300 tokens ≈ 15-20 dòng. Sẽ cắt ngang giữa section, phá vỡ ngữ cảnh. Ví dụ: Timeline của postmortem_INC005 (25 dòng) sẽ bị cắt đôi → mất logic cause-effect. API endpoint spec sẽ bị tách request body khỏi response → mất nghĩa. |

### ❌ Fixed-size Chunking (custom token size)
> *Chia theo kích thước token cố định do bạn chọn*

| Tiêu chí | Đánh giá |
|-----------|----------|
| Phù hợp? | **KHÔNG khuyến khích** |
| Lý do | Dù set 500-800 tokens vẫn có risk cắt ngang section. File nhỏ nhất (~57 dòng ≈ 400 tokens) thì 1 chunk đủ, nhưng file lớn (~194 dòng ≈ 1200+ tokens) lại bị cắt tùy tiện. Không tận dụng được cấu trúc heading rõ ràng của Markdown. |

### ⭐ Hierarchical Chunking — **ĐỀ XUẤT SỐ 1**
> *Tổ chức chunk theo cấu trúc parent-child, mỗi child node có reference đến parent*

| Tiêu chí | Đánh giá |
|-----------|----------|
| Phù hợp? | **RẤT PHÙ HỢP ✅** |
| Lý do chi tiết | Xem bên dưới |

**Tại sao Hierarchical là tốt nhất cho 36 file này:**

1. **Cấu trúc Markdown hoàn hảo cho hierarchy:**
   - Mỗi file có H1 (document title) → H2 (major sections) → H3 (subsections)
   - Ví dụ `postmortem_INC005_paymentgw_mar.md`:
     ```
     H1: Postmortem: INC-005
       H2: Summary          → chunk con 1
       H2: Timeline          → chunk con 2  
       H2: Root Cause        → chunk con 3
       H2: Contributing Factors → chunk con 4
       H2: Impact            → chunk con 5
       H2: Lessons Learned   → chunk con 6
       H2: Action Items      → chunk con 7
     ```
   - Mỗi chunk con tự động **kế thừa context từ parent** (biết đây là postmortem INC-005, PaymentGW, P1)

2. **Giải quyết bài toán L2 (Multi-Source RAG):**
   - Khi hỏi "Why did PaymentGW cost increase?", hệ thống cần kết hợp:
     - `postmortem_INC005` → section "Impact" (retry storms)
     - `q1_2026_review_notes` → section "Cost concerns"
     - `cost_optimization_initiative` → section "PaymentGW"
   - Hierarchical giữ mỗi section là 1 chunk có context đầy đủ → RAG retrieval chính xác hơn

3. **Giữ nguyên vẹn semantic unit:**
   - API endpoint spec (request + response + notes) nằm trọn trong 1 H3 section
   - Timeline postmortem nằm trọn trong 1 H2 section
   - Team member list + on-call nằm trọn trong 1 file/section

4. **YAML frontmatter → metadata enrichment:**
   - `tags`, `category`, `owner` từ frontmatter sẽ được parse thành metadata
   - Giúp filtering khi retrieval (ví dụ: chỉ tìm trong tag `postmortem` khi hỏi về incidents)

### ✅ Semantic Chunking — ĐỀ XUẤT SỐ 2 (backup)
> *Nhóm câu/đoạn theo semantic similarity*

| Tiêu chí | Đánh giá |
|-----------|----------|
| Phù hợp? | **PHÙ HỢP** nhưng không tối ưu bằng Hierarchical |
| Ưu điểm | Tự động nhóm nội dung liên quan mà không cần cấu trúc Markdown |
| Nhược điểm | (1) Chậm hơn, tốn compute hơn để xử lý. (2) Có thể nhóm sai khi 1 section đề cập nhiều topic (ví dụ: `architecture_review_feb_2026.md` có 5 topic khác nhau). (3) Không tận dụng được cấu trúc heading đã có sẵn — "reinvent the wheel" |

### ❌ No Chunking
> *Không chia chunk, mỗi document = 1 chunk*

| Tiêu chí | Đánh giá |
|-----------|----------|
| Phù hợp? | **CÓ THỂ DÙNG** nhưng **KHÔNG khuyến khích** |
| Ưu điểm | File nhỏ (3-8KB), mỗi file là 1 topic rõ ràng → về lý thuyết có thể dùng nguyên file |
| Nhược điểm | (1) Khi retrieve, trả về nguyên file 150+ dòng → LLM context window bị lãng phí. (2) Precision thấp — hỏi 1 fact nhỏ nhưng trả về toàn bộ document. (3) Không thể trả về nhiều chunk từ nhiều file khác nhau nếu context window hạn chế. (4) **Đặc biệt bất lợi cho L2 multi-source questions** — cần ghép info từ 3-4 file nhưng mỗi file nguyên vẹn sẽ chiếm quá nhiều token. |

---

## 3. Kết luận & Đề xuất

> [!IMPORTANT]
> ### 🏆 Đề xuất: **Hierarchical Chunking**
> 
> Đây là lựa chọn tối ưu nhất vì:
> 1. **36 file đều có cấu trúc Markdown heading rõ ràng** → Hierarchical parser sẽ chia chunk chính xác theo section
> 2. **Mỗi section là 1 đơn vị ngữ nghĩa hoàn chỉnh** (timeline, root cause, action items, API endpoint...)
> 3. **Parent-child reference** giữ context không bị mất (biết chunk này thuộc postmortem nào, service nào)
> 4. **Tối ưu cho cả L1 (single-doc lookup) và L2 (multi-source synthesis)**
> 5. **YAML frontmatter metadata** được tận dụng tốt nhất với Hierarchical

### Cấu hình đề xuất khi setup Hierarchical Chunking:

| Tham số | Giá trị đề xuất | Lý do |
|---------|-----------------|-------|
| Max chunk size | 500-800 tokens | Đủ chứa 1 H2 section lớn nhất (Timeline ~25 dòng ≈ 500 tokens) |
| Overlap | 1-2 câu | Giữ context transition giữa các section |
| Parsing | Markdown heading-based | Tận dụng H1/H2/H3 hierarchy có sẵn |
| Metadata | Extract YAML frontmatter | `tags`, `category`, `owner`, `status` → filter khi retrieval |

---

## 4. So sánh tổng hợp

| Tiêu chí | Default | Fixed | **Hierarchical** | Semantic | No chunk |
|----------|---------|-------|:-----------:|----------|----------|
| Giữ ngữ cảnh section | ❌ | ❌ | ✅ | ✅ | ✅ |
| Tận dụng Markdown structure | ❌ | ❌ | ✅ | ❌ | ❌ |
| Precision cho L1 | ⚠️ | ⚠️ | ✅ | ✅ | ❌ |
| Multi-source L2 | ❌ | ❌ | ✅ | ✅ | ❌ |
| Tốc độ parse | ✅ | ✅ | ✅ | ❌ | ✅ |
| Metadata enrichment | ❌ | ❌ | ✅ | ❌ | ⚠️ |
| **Tổng đánh giá** | 2/6 | 2/6 | **6/6** | 4/6 | 3/6 |
