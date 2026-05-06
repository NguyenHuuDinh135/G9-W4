# L2 RAG Architecture Improvements

Tài liệu này giải thích chi tiết các cải tiến L2 đã được áp dụng vào kiến trúc RAG hiện tại.

## 1. File: `lambda/lambda_function.py`

**A. Cải thiện System Prompt (Conflict Resolution):**
Cập nhật `SYSTEM_PROMPT` để yêu cầu LLM ưu tiên tài liệu mới nhất hoặc có trạng thái `current` khi có sự mâu thuẫn:
```python
SYSTEM_PROMPT = """You are GeekBrain AI Assistant...

RULES:
...
3. When multiple documents provide DIFFERENT information about the same topic, ALWAYS rely on the metadata provided:
   - If sources conflict, prefer the most recent version (e.g. year=2026 over year=2025).
   - Prefer documents with status="current" over status="archived".
   - State the conflict explicitly in your answer (e.g. "Previously the timeout was X [source: old.md], but according to the latest standup it is now Y [source: new.md]").
...
"""
```

**B. Bật Tìm kiếm lai (Hybrid Search):**
Trong hàm `retrieve_chunks`, thêm tham số `"overrideSearchType": "HYBRID"`, kết hợp Vector Search và BM25 Keyword Search:
```python
    response = bedrock_agent_runtime.retrieve(
        knowledgeBaseId=KNOWLEDGE_BASE_ID,
        retrievalQuery={"text": question},
        retrievalConfiguration={
            "vectorSearchConfiguration": {
                "numberOfResults": RETRIEVAL_K,
                "overrideSearchType": "HYBRID" # <-- Tính năng HYBRID
            }
        },
    )
```

**C. Tiêm Metadata vào Context cho LLM:**
Trong hàm `format_context`, trích xuất metadata do Bedrock trả về (từ các file `.metadata.json`) và ghép thẳng vào đoạn text gửi cho LLM:
```python
    for i, chunk in enumerate(chunks, 1):
        meta_str = ", ".join(f"{k}={v}" for k, v in chunk.get("metadata", {}).items())
        meta_info = f" [metadata: {meta_str}]" if meta_str else ""
        parts.append(f"--- Document Chunk {i} [source: {chunk['source']}]{meta_info} ---\n{chunk['text']}")
```
*(LLM sẽ đọc được context dạng: `--- Document Chunk 1 [source: api_reference_v1_archived.md] [metadata: status=archived] ---`)*

---

## 2. File: `terraform/modules/ai_engine/main.tf`

**D. Upload file Metadata lên S3 & Tự động Trigger Ingestion:**
Thêm resource để Terraform đọc và upload tất cả các file có đuôi `.metadata.json` lên S3 Knowledge Base Bucket:
```terraform
resource "aws_s3_object" "kb_metadata" {
  for_each     = fileset(var.kb_docs_path, "*.metadata.json")
  bucket       = aws_s3_bucket.kb_docs.id
  key          = each.value
  source       = "${var.kb_docs_path}/${each.value}"
  etag         = filemd5("${var.kb_docs_path}/${each.value}")
  content_type = "application/json"
}
```

Và đưa thêm `meta_hash` vào block `triggers` của `null_resource.kb_sync`. Điều này đảm bảo mỗi khi file `.metadata.json` có sự thay đổi, Terraform sẽ tự động gọi lệnh AWS CLI để đồng bộ hoá (Sync) lại Knowledge Base thay vì chỉ quan tâm tới file `.md`:
```terraform
resource "null_resource" "kb_sync" {
  triggers = {
    kb_id     = aws_bedrockagent_knowledge_base.main.id
    ds_id     = local.data_source_id
    docs_hash = md5(join(",", [for f in fileset(var.kb_docs_path, "*.md") : filemd5("${var.kb_docs_path}/${f}")]))
    meta_hash = md5(join(",", [for f in fileset(var.kb_docs_path, "*.metadata.json") : filemd5("${var.kb_docs_path}/${f}")])) # <-- Bắt sự kiện thay đổi Metadata
  }
...
```
