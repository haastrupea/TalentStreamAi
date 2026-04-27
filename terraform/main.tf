terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.75"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.5"
    }
  }
}

locals {
  name                      = "${var.project_name}-${var.environment}"
  cloudfront_origin         = "https://${aws_cloudfront_distribution.main.domain_name}"
  api_origin_domain         = trimprefix(aws_apigatewayv2_api.http.api_endpoint, "https://")
  static_origin_id          = "static-s3-origin"
  api_origin_id             = "api-gateway-origin"
  cache_policy_optimized_id = "658327ea-f89d-4fab-a63d-7e88639e58f6"
  cache_policy_disabled_id  = "4135ea2d-6df8-44a3-9df3-4b5a84be39ad"
  all_viewer_except_host_id = "b689b0a8-53d0-40ab-baf2-68738e2966ac"
  default_subnet_ids        = slice(sort(data.aws_subnets.default.ids), 0, 2)
}


data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

resource "aws_s3_bucket" "static_site" {
  bucket = var.static_site_bucket_name
}

resource "aws_s3_bucket_ownership_controls" "static_site" {
  bucket = aws_s3_bucket.static_site.id

  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

resource "aws_s3_bucket_public_access_block" "static_site" {
  bucket = aws_s3_bucket.static_site.id

  block_public_acls       = true
  ignore_public_acls      = true
  block_public_policy     = false
  restrict_public_buckets = false
}

resource "aws_s3_bucket_versioning" "static_site" {
  bucket = aws_s3_bucket.static_site.id

  versioning_configuration {
    status = "Suspended"
  }
}

resource "aws_s3_bucket_policy" "static_site_public_read" {
  bucket = aws_s3_bucket.static_site.id
  policy = jsonencode(
    {
      Version = "2012-10-17"
      Statement = [
        {
          Sid       = "AllowPublicReadObjects"
          Effect    = "Allow"
          Principal = "*"
          Action    = ["s3:GetObject"]
          Resource  = "${aws_s3_bucket.static_site.arn}/*"
        }
      ]
    }
  )

  depends_on = [aws_s3_bucket_public_access_block.static_site]
}

resource "aws_s3_bucket" "uploads" {
  bucket = var.uploads_bucket_name
}

resource "aws_s3_bucket_ownership_controls" "uploads" {
  bucket = aws_s3_bucket.uploads.id

  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

resource "aws_s3_bucket_public_access_block" "uploads" {
  bucket = aws_s3_bucket.uploads.id

  block_public_acls       = true
  ignore_public_acls      = true
  block_public_policy     = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "uploads" {
  bucket = aws_s3_bucket.uploads.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
    bucket_key_enabled = true
  }
}

resource "aws_security_group" "lambda" {
  name        = "${local.name}-lambda-sg"
  description = "Lambda security group."
  vpc_id      = data.aws_vpc.default.id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group" "efs" {
  name        = "${local.name}-efs-sg"
  description = "EFS security group."
  vpc_id      = data.aws_vpc.default.id
}

resource "aws_security_group_rule" "efs_from_lambda" {
  type                     = "ingress"
  security_group_id        = aws_security_group.efs.id
  from_port                = 2049
  to_port                  = 2049
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.lambda.id
}

resource "aws_efs_file_system" "sqlite" {
  encrypted = true
}

resource "aws_efs_mount_target" "default" {
  count = 2

  file_system_id  = aws_efs_file_system.sqlite.id
  subnet_id       = local.default_subnet_ids[count.index]
  security_groups = [aws_security_group.efs.id]
}

resource "aws_efs_access_point" "sqlite" {
  file_system_id = aws_efs_file_system.sqlite.id

  root_directory {
    path = "/talentstreamai"

    creation_info {
      owner_gid   = 1000
      owner_uid   = 1000
      permissions = "755"
    }
  }

  posix_user {
    uid = 1000
    gid = 1000
  }
}

resource "aws_iam_role" "lambda_exec" {
  name = "${local.name}-lambda-exec"

  assume_role_policy = jsonencode(
    {
      Version = "2012-10-17"
      Statement = [
        {
          Effect = "Allow"
          Principal = {
            Service = "lambda.amazonaws.com"
          }
          Action = "sts:AssumeRole"
        }
      ]
    }
  )
}

resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy_attachment" "lambda_vpc_access" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

resource "aws_iam_role_policy" "lambda_inline" {
  name = "${local.name}-lambda-inline"
  role = aws_iam_role.lambda_exec.id
  policy = jsonencode(
    {
      Version = "2012-10-17"
      Statement = [
        {
          Sid      = "UploadsBucketAccess"
          Effect   = "Allow"
          Action   = ["s3:PutObject", "s3:GetObject", "s3:DeleteObject"]
          Resource = "${aws_s3_bucket.uploads.arn}/${var.uploads_s3_prefix}*"
        },
        {
          Sid    = "EfsClientAccess"
          Effect = "Allow"
          Action = [
            "elasticfilesystem:ClientMount",
            "elasticfilesystem:ClientWrite",
            "elasticfilesystem:ClientRootAccess"
          ]
          Resource = [
            aws_efs_file_system.sqlite.arn,
            aws_efs_access_point.sqlite.arn
          ]
        }
      ]
    }
  )
}

resource "aws_apigatewayv2_api" "http" {
  name          = "${local.name}-http-api"
  protocol_type = "HTTP"

   cors_configuration {
    allow_credentials = false  # Cannot be true when allow_origins is "*"
    allow_headers     = ["authorization", "content-type", "x-amz-date", "x-api-key", "x-amz-security-token"]
    allow_methods     = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    allow_origins     = ["*"]  # CORS is handled in Lambda via environment variables
    max_age           = 300
  }
}

resource "aws_cloudfront_distribution" "main" {
  enabled             = true
  is_ipv6_enabled     = true
  price_class         = "PriceClass_100"
  default_root_object = "index.html"

  origin {
    domain_name = aws_s3_bucket.static_site.bucket_regional_domain_name
    origin_id   = local.static_origin_id

    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "http-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }

  origin {
    domain_name = local.api_origin_domain
    origin_id   = local.api_origin_id

    custom_origin_config {
      http_port                = 80
      https_port               = 443
      origin_protocol_policy   = "https-only"
      origin_ssl_protocols     = ["TLSv1.2"]
    }
  }

  default_cache_behavior {
    target_origin_id       = local.static_origin_id
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD", "OPTIONS"]
    cached_methods         = ["GET", "HEAD"]
    compress               = true
    # cache_policy_id        = local.cache_policy_optimized_id

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }

    min_ttl                = 0
    default_ttl            = 3600
    max_ttl                = 86400
  }

  ordered_cache_behavior {
    path_pattern             = "/api/*"
    target_origin_id         = local.api_origin_id
    viewer_protocol_policy   = "redirect-to-https"
    allowed_methods          = ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"]
    cached_methods           = ["GET", "HEAD"]
    
    compress                 = true
    # cache_policy_id          = local.cache_policy_disabled_id
    # origin_request_policy_id = local.all_viewer_except_host_id

    forwarded_values {
      query_string = true
      headers      = ["Authorization", "Content-Type", "Accept"]
      cookies {
        forward = "all"
      }
    }

    min_ttl                = 0
    default_ttl            = 0
    max_ttl                = 0
  }

  custom_error_response {
    error_code            = 403
    response_code         = 200
    response_page_path    = "/index.html"
    error_caching_min_ttl = 0
  }

  custom_error_response {
    error_code            = 404
    response_code         = 200
    response_page_path    = "/index.html"
    error_caching_min_ttl = 0
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
  }
}

resource "aws_lambda_function" "api" {
  function_name = var.lambda_function_name
  role          = aws_iam_role.lambda_exec.arn
  runtime       = "python3.12"
  handler       = "lambda_handler.handler"
  architectures = ["x86_64"]
  timeout       = 120
  memory_size   = 1024

  filename         = "${path.module}/../backend/lambda-deployment.zip"
  source_code_hash = filebase64sha256("${path.module}/../backend/lambda-deployment.zip")

  vpc_config {
    subnet_ids         = local.default_subnet_ids
    security_group_ids = [aws_security_group.lambda.id]
  }

  file_system_config {
    arn              = aws_efs_access_point.sqlite.arn
    local_mount_path = "/mnt/data"
  }

  environment {
    variables = {
      DEPLOYMENT_ENVIRONMENT   = var.deployment_environment
      AUTH_MODE                = var.auth_mode
      CLERK_JWKS_URL           = var.clerk_jwks_url
      CLERK_ISSUER             = var.clerk_issuer
      CLERK_AUDIENCE           = var.clerk_audience
      AGENT_MODE               = var.agent_mode
      UPLOAD_STORAGE           = "s3"
      S3_BUCKET                = aws_s3_bucket.uploads.bucket
      S3_PREFIX                = var.uploads_s3_prefix
      S3_SSE                   = "AES256"
      SQLITE_PATH              = "/mnt/data/talentstreamai.sqlite3"
      SQLITE_BUSY_TIMEOUT_MS   = tostring(var.sqlite_busy_timeout_ms)
      SQLITE_ENABLE_WAL        = tostring(var.sqlite_enable_wal)
      CORS_ORIGINS             = local.cloudfront_origin
      LOG_JSON                 = tostring(var.log_json)
      LOG_LEVEL                = var.log_level
      ENABLE_PROMETHEUS        = tostring(var.enable_prometheus)
      LLM_BASE_URL             = var.llm_base_url
      LLM_MODEL                = var.llm_model
      LLM_TIMEOUT_SECONDS      = tostring(var.llm_timeout_seconds)
      LLM_MAX_TOKENS           = tostring(var.llm_max_tokens)
      LLM_TEMPERATURE          = tostring(var.llm_temperature)
      OPENROUTER_API_KEY       = var.openrouter_api_key
      OPENAI_API_KEY           = var.openai_api_key
      LANGFUSE_PUBLIC_KEY      = var.langfuse_public_key
      LANGFUSE_SECRET_KEY      = var.langfuse_secret_key
      LANGFUSE_BASE_URL        = var.langfuse_base_url
      LANGFUSE_TRACING_ENABLED = tostring(var.langfuse_tracing_enabled)
      OPENROUTER_REFERER       = var.openrouter_referer
      OPENROUTER_TITLE         = var.openrouter_title
    }
  }

  lifecycle {
    ignore_changes = [
      filename,
      source_code_hash,
      s3_bucket,
      s3_key,
      s3_object_version,
      image_uri
    ]
  }

  depends_on = [
    aws_efs_mount_target.default,
    aws_cloudfront_distribution.main
  ]
}

resource "aws_cloudwatch_log_group" "lambda_api" {
  name              = "/aws/lambda/${aws_lambda_function.api.function_name}"
  retention_in_days = 7
}

resource "aws_apigatewayv2_integration" "lambda_proxy" {
  api_id                 = aws_apigatewayv2_api.http.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.api.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "proxy" {
  api_id    = aws_apigatewayv2_api.http.id
  route_key = "ANY /{proxy+}"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_proxy.id}"
}

resource "aws_apigatewayv2_route" "api_any" {
  api_id    = aws_apigatewayv2_api.http.id
  route_key = "ANY /api/{proxy+}"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_proxy.id}"
}

resource "aws_apigatewayv2_route" "api_options" {
  api_id    = aws_apigatewayv2_api.http.id
  route_key = "OPTIONS /api/{proxy+}"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_proxy.id}"
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.http.id
  name        = "$default"
  auto_deploy = true

  default_route_settings {
    throttling_burst_limit = 100
    throttling_rate_limit  = 100
  }
}

resource "aws_lambda_permission" "allow_apigw_invoke" {
  statement_id  = "AllowHttpApiInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.api.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.http.execution_arn}/*/*"
}
