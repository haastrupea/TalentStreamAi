variable "aws_region" {
  type        = string
  description = "Primary AWS region."
  default     = "us-east-1"
}

variable "project_name" {
  type        = string
  description = "Short name used in tagging and resource names."
  default     = "talentstreamai"
}

variable "environment" {
  type        = string
  description = "Deployment stage label."

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "environment must be one of: dev, staging, prod."
  }
}

variable "static_site_bucket_name" {
  type        = string
  description = "Public-read S3 bucket name for static frontend assets."
}

variable "uploads_bucket_name" {
  type        = string
  description = "Private S3 bucket name for uploaded resume files."
}

variable "uploads_s3_prefix" {
  type        = string
  description = "Uploads key prefix in the uploads bucket."
  default     = "uploads/"
}

variable "lambda_function_name" {
  type        = string
  description = "Lambda function name for the FastAPI backend."
  default     = "talentstreamai-api"
}

variable "deployment_environment" {
  type        = string
  description = "Backend DEPLOYMENT_ENVIRONMENT value."
  default     = "prod"
}

variable "auth_mode" {
  type        = string
  description = "Backend AUTH_MODE value."
  default     = "clerk_jwks"
}

variable "clerk_jwks_url" {
  type        = string
  description = "Clerk JWKS URL."
}

variable "clerk_issuer" {
  type        = string
  description = "Clerk JWT issuer."
}

variable "clerk_audience" {
  type        = string
  description = "Optional Clerk JWT audience."
  default     = ""
}

variable "agent_mode" {
  type        = string
  description = "Backend AGENT_MODE."
  default     = "llm"
}

variable "sqlite_busy_timeout_ms" {
  type        = number
  description = "SQLite busy timeout in milliseconds."
  default     = 5000
}

variable "sqlite_enable_wal" {
  type        = bool
  description = "Enable WAL mode for SQLite."
  default     = true
}

variable "log_json" {
  type        = bool
  description = "Enable JSON logging."
  default     = true
}

variable "log_level" {
  type        = string
  description = "Backend LOG_LEVEL."
  default     = "INFO"
}

variable "enable_prometheus" {
  type        = bool
  description = "Enable Prometheus endpoint."
  default     = false
}

variable "llm_base_url" {
  type        = string
  description = "LLM provider base URL."
}

variable "llm_model" {
  type        = string
  description = "LLM model id."
}

variable "llm_timeout_seconds" {
  type        = number
  description = "LLM request timeout seconds."
  default     = 90
}

variable "llm_max_tokens" {
  type        = number
  description = "LLM max tokens."
  default     = 1800
}

variable "llm_temperature" {
  type        = number
  description = "LLM temperature."
  default     = 0.2
}

variable "openrouter_api_key" {
  type        = string
  description = "OPENROUTER_API_KEY secret."
  default     = ""
  sensitive   = true
}

variable "openai_api_key" {
  type        = string
  description = "OPENAI_API_KEY secret."
  default     = ""
  sensitive   = true
}

variable "openrouter_referer" {
  type        = string
  description = "Optional OPENROUTER_REFERER."
  default     = ""
}

variable "openrouter_title" {
  type        = string
  description = "Optional OPENROUTER_TITLE."
  default     = ""
}

variable "langfuse_public_key" {
  type        = string
  description = "Optional Langfuse public key."
  default     = ""
  sensitive   = true
}

variable "langfuse_secret_key" {
  type        = string
  description = "Optional Langfuse secret key."
  default     = ""
  sensitive   = true
}

variable "langfuse_base_url" {
  type        = string
  description = "Optional Langfuse base URL."
  default     = ""
}

variable "langfuse_tracing_enabled" {
  type        = bool
  description = "Enable Langfuse tracing."
  default     = false
}
