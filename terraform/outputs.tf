output "stack_name" {
  value       = local.name
  description = "Composite name (project + environment)."
}

output "aws_region" {
  value       = var.aws_region
  description = "AWS region."
}

output "cloudfront_domain_name" {
  value       = aws_cloudfront_distribution.main.domain_name
  description = "CloudFront distribution domain."
}

output "cloudfront_distribution_id" {
  value       = aws_cloudfront_distribution.main.id
  description = "CloudFront distribution id."
}

output "cloudfront_url" {
  value       = local.cloudfront_origin
  description = "Primary frontend origin URL. Configure this in Clerk allowed origins and redirects."
}

output "api_gateway_endpoint" {
  value       = aws_apigatewayv2_api.http.api_endpoint
  description = "HTTP API execute-api endpoint."
}

output "lambda_function_name" {
  value       = aws_lambda_function.api.function_name
  description = "Backend Lambda function name for deploy scripts."
}

output "lambda_deploy_command_hint" {
  value       = "python infra/scripts/deploy_lambda.py --function-name ${aws_lambda_function.api.function_name} --zip backend/lambda-deployment.zip"
  description = "Example command to publish the real backend zip after infrastructure apply."
}

output "cors_origin_value" {
  value       = local.cloudfront_origin
  description = "CORS_ORIGINS value wired into Lambda env."
}

output "static_site_bucket_name" {
  value       = aws_s3_bucket.static_site.bucket
  description = "Static site bucket name."
}

output "uploads_bucket_name" {
  value       = aws_s3_bucket.uploads.bucket
  description = "Uploads bucket name."
}
