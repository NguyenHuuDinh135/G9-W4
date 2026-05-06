terraform {
  required_providers {
    opensearch = {
      source  = "opensearch-project/opensearch"
      version = "~> 2.3"
    }
  }
}

resource "aws_iam_role" "bedrock_kb" {
  name = "${var.project}-bedrock-kb-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "bedrock.amazonaws.com" }
      Action    = "sts:AssumeRole"
      Condition = {
        StringEquals = {
          "aws:SourceAccount" = var.account_id
        }
      }
    }]
  })

  tags = var.tags
}

resource "aws_iam_role_policy" "bedrock_kb_s3" {
  name = "${var.project}-kb-s3-access"
  role = aws_iam_role.bedrock_kb.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["s3:GetObject", "s3:ListBucket"]
        Resource = [
          aws_s3_bucket.kb_docs.arn,
          "${aws_s3_bucket.kb_docs.arn}/*"
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy" "bedrock_kb_aoss" {
  name = "${var.project}-kb-aoss-access"
  role = aws_iam_role.bedrock_kb.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = "aoss:APIAccessAll"
      Resource = aws_opensearchserverless_collection.kb.arn
    }]
  })
}

resource "aws_iam_role_policy" "bedrock_kb_model" {
  name = "${var.project}-kb-model-access"
  role = aws_iam_role.bedrock_kb.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = "bedrock:InvokeModel"
      Resource = "arn:aws:bedrock:${var.region}::foundation-model/${var.embedding_model_id}"
    }]
  })
}

resource "aws_s3_bucket" "kb_docs" {
  bucket        = "${var.project}-kb-docs-${var.name_suffix}"
  force_destroy = true
  tags          = var.tags
}

resource "aws_s3_bucket_server_side_encryption_configuration" "kb_docs" {
  bucket = aws_s3_bucket.kb_docs.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_object" "kb_files" {
  for_each     = fileset(var.kb_docs_path, "*.md")
  bucket       = aws_s3_bucket.kb_docs.id
  key          = each.value
  source       = "${var.kb_docs_path}/${each.value}"
  etag         = filemd5("${var.kb_docs_path}/${each.value}")
  content_type = "text/markdown"
}

resource "aws_s3_object" "kb_metadata" {
  for_each     = fileset(var.kb_docs_path, "*.metadata.json")
  bucket       = aws_s3_bucket.kb_docs.id
  key          = each.value
  source       = "${var.kb_docs_path}/${each.value}"
  etag         = filemd5("${var.kb_docs_path}/${each.value}")
  content_type = "application/json"
}

resource "aws_opensearchserverless_security_policy" "encryption" {
  name = "${var.project}-enc"
  type = "encryption"
  policy = jsonencode({
    Rules = [{
      ResourceType = "collection"
      Resource     = ["collection/${var.project}-kb"]
    }]
    AWSOwnedKey = true
  })
}

resource "aws_opensearchserverless_security_policy" "network" {
  name = "${var.project}-net"
  type = "network"
  policy = jsonencode([{
    Rules = [{
      ResourceType = "collection"
      Resource     = ["collection/${var.project}-kb"]
    }, {
      ResourceType = "dashboard"
      Resource     = ["collection/${var.project}-kb"]
    }]
    AllowFromPublic = true
  }])
}

data "aws_caller_identity" "current" {}

resource "aws_opensearchserverless_access_policy" "data" {
  name = "${var.project}-data"
  type = "data"
  policy = jsonencode([{
    Rules = [
      {
        ResourceType = "index"
        Resource     = ["index/${var.project}-kb/*"]
        Permission   = ["aoss:CreateIndex", "aoss:UpdateIndex", "aoss:DescribeIndex", "aoss:ReadDocument", "aoss:WriteDocument"]
      },
      {
        ResourceType = "collection"
        Resource     = ["collection/${var.project}-kb"]
        Permission   = ["aoss:CreateCollectionItems", "aoss:DescribeCollectionItems", "aoss:UpdateCollectionItems"]
      }
    ]
    Principal = [
      aws_iam_role.bedrock_kb.arn,
      data.aws_caller_identity.current.arn
    ]
  }])
}

resource "time_sleep" "wait_for_policies" {
  depends_on      = [
    aws_opensearchserverless_security_policy.encryption,
    aws_opensearchserverless_security_policy.network,
    aws_opensearchserverless_access_policy.data,
  ]
  create_duration = "60s"
}

resource "aws_opensearchserverless_collection" "kb" {
  name = "${var.project}-kb"
  type = "VECTORSEARCH"
  tags = var.tags
  depends_on = [time_sleep.wait_for_policies]
}

resource "time_sleep" "wait_for_collection" {
  depends_on      = [aws_opensearchserverless_collection.kb]
  create_duration = "120s"
}

resource "opensearch_index" "kb_index" {
  name                           = "bedrock-knowledge-base-default-index"
  number_of_shards               = "2"
  number_of_replicas             = "0"
  index_knn                      = true
  index_knn_algo_param_ef_search = "512"

  mappings = jsonencode({
    properties = {
      "bedrock-knowledge-base-default-vector" = {
        type      = "knn_vector"
        dimension = 1024
        method = {
          name      = "hnsw"
          engine    = "faiss"
          space_type = "l2"
          parameters = {
            ef_construction = 512
            m               = 16
          }
        }
      }
      "AMAZON_BEDROCK_METADATA" = { type = "text", index = false }
      "AMAZON_BEDROCK_TEXT_CHUNK" = { type = "text" }
    }
  })

  force_destroy = true
  depends_on    = [time_sleep.wait_for_collection]
  lifecycle {
    ignore_changes = [mappings]
  }
}

resource "aws_bedrockagent_knowledge_base" "main" {
  name     = "${var.project}-knowledge-base"
  role_arn = aws_iam_role.bedrock_kb.arn

  knowledge_base_configuration {
    type = "VECTOR"
    vector_knowledge_base_configuration {
      embedding_model_arn = "arn:aws:bedrock:${var.region}::foundation-model/${var.embedding_model_id}"
    }
  }

  storage_configuration {
    type = "OPENSEARCH_SERVERLESS"
    opensearch_serverless_configuration {
      collection_arn    = aws_opensearchserverless_collection.kb.arn
      vector_index_name = opensearch_index.kb_index.name
      field_mapping {
        vector_field   = "bedrock-knowledge-base-default-vector"
        text_field     = "AMAZON_BEDROCK_TEXT_CHUNK"
        metadata_field = "AMAZON_BEDROCK_METADATA"
      }
    }
  }

  tags = var.tags

  depends_on = [
    opensearch_index.kb_index,
    aws_iam_role_policy.bedrock_kb_s3,
    aws_iam_role_policy.bedrock_kb_aoss,
    aws_iam_role_policy.bedrock_kb_model,
  ]
}

resource "aws_bedrockagent_data_source" "s3" {
  knowledge_base_id = aws_bedrockagent_knowledge_base.main.id
  name              = "${var.project}-s3-docs"

  data_source_configuration {
    type = "S3"
    s3_configuration {
      bucket_arn = aws_s3_bucket.kb_docs.arn
    }
  }

  vector_ingestion_configuration {
    chunking_configuration {
      chunking_strategy = "FIXED_SIZE"
      fixed_size_chunking_configuration {
        max_tokens         = 300
        overlap_percentage = 20
      }
    }
  }

  depends_on = [aws_s3_object.kb_files]
}

locals {
  data_source_id = split(",", aws_bedrockagent_data_source.s3.id)[0]
}

resource "null_resource" "kb_sync" {
  triggers = {
    kb_id = aws_bedrockagent_knowledge_base.main.id
    ds_id = local.data_source_id
    docs_hash = md5(join(",", [for f in fileset(var.kb_docs_path, "*.md") : filemd5("${var.kb_docs_path}/${f}")]))
    meta_hash = md5(join(",", [for f in fileset(var.kb_docs_path, "*.metadata.json") : filemd5("${var.kb_docs_path}/${f}")]))
  }

  provisioner "local-exec" {
    command = <<-EOT
      echo "Starting KB ingestion job..."
      JOB=$(aws bedrock-agent start-ingestion-job         --knowledge-base-id ${aws_bedrockagent_knowledge_base.main.id}         --data-source-id ${local.data_source_id}         --query 'ingestionJob.ingestionJobId' --output text)
      echo "Ingestion job ID: $JOB"
      echo "Waiting for ingestion to complete..."
      for i in $(seq 1 60); do
        STATUS=$(aws bedrock-agent get-ingestion-job           --knowledge-base-id ${aws_bedrockagent_knowledge_base.main.id}           --data-source-id ${local.data_source_id}           --ingestion-job-id $JOB           --query 'ingestionJob.status' --output text)
        echo "  Status: $STATUS"
        if [ "$STATUS" = "COMPLETE" ]; then
          echo "Ingestion complete!"
          exit 0
        elif [ "$STATUS" = "FAILED" ]; then
          echo "Ingestion FAILED!"
          exit 1
        fi
        sleep 10
      done
      echo "Timeout waiting for ingestion"
      exit 1
    EOT
  }
}
