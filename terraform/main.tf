terraform {
  required_version = ">= 1.5"

  backend "s3" {
    bucket         = "geekbrain-tfstate-809131193138"
    key            = "w4/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "geekbrain-tfstate-locks"
    encrypt        = true
  }

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    opensearch = {
      source  = "opensearch-project/opensearch"
      version = "~> 2.3"
    }
    time = {
      source  = "hashicorp/time"
      version = "~> 0.11"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

provider "opensearch" {
  url         = try(module.ai_engine.opensearch_collection_endpoint, "https://placeholder.us-east-1.aoss.amazonaws.com")
  aws_region  = var.aws_region
  healthcheck = false
}

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

locals {
  account_id  = data.aws_caller_identity.current.account_id
  region      = data.aws_region.current.name
  name_suffix = substr(local.account_id, -6, 6)
  project     = var.project_name
  tags = {
    Project     = "GeekBrain-W4"
    ManagedBy   = "Terraform"
    Environment = "demo"
  }
}

module "ai_engine" {
  source             = "./modules/ai_engine"
  project            = local.project
  name_suffix        = local.name_suffix
  tags               = local.tags
  region             = local.region
  account_id         = local.account_id
  embedding_model_id = var.embedding_model_id
  kb_docs_path       = var.kb_docs_path
}

module "monitoring_api" {
  source          = "./modules/monitoring_api"
  project         = local.project
  tags            = local.tags
  vpc_endpoint_id = module.network.vpc_endpoint_id
}

module "backend" {
  source             = "./modules/backend"
  project            = local.project
  tags               = local.tags
  region             = local.region
  account_id         = local.account_id
  llm_model_id       = var.llm_model_id
  retrieval_k        = var.retrieval_k
  knowledge_base_id  = module.ai_engine.knowledge_base_id
  monitoring_api_url = module.monitoring_api.api_url
  
  private_subnet_ids = module.network.private_subnet_ids
  lambda_sg_id       = module.network.lambda_sg_id
  db_host            = module.database.db_host
  db_name            = module.database.db_name
  db_user            = module.database.db_user
  db_password        = module.database.db_password
}

module "network" {
  source  = "./modules/network"
  project = local.project
  tags    = local.tags
}

module "database" {
  source             = "./modules/database"
  project            = local.project
  tags               = local.tags
  private_subnet_ids = module.network.private_subnet_ids
  rds_sg_id          = module.network.rds_sg_id
  lambda_sg_id       = module.network.lambda_sg_id
}

module "frontend" {
  source          = "./modules/frontend"
  project         = local.project
  name_suffix     = local.name_suffix
  tags            = local.tags
  api_gateway_url = module.backend.api_gateway_url
}
