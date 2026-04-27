# Terraform Deploy Runbook (CloudFront Default Domain)

This runbook covers the current AWS deployment flow in this repo:

- Frontend static assets on public-read S3 behind CloudFront
- Backend FastAPI on Lambda behind API Gateway (`/api/*` via CloudFront)
- No custom domain, no Route53, no ACM viewer cert setup
- `CORS_ORIGINS` automatically set from CloudFront domain in Terraform

## 1) Prerequisites

- Terraform `>= 1.6`
- AWS credentials configured (profile or env vars)
- Python 3.12
- `uv`
- Docker (for Lambda package build)
- AWS CLI v2 (for frontend sync/invalidation)

## 2) Configure variables

Create local vars:

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
```

Set required values in `terraform.tfvars`:

- `static_site_bucket_name`
- `uploads_bucket_name`
- `clerk_jwks_url`
- `clerk_issuer`
- `llm_base_url`
- `llm_model`
- at least one of `openrouter_api_key` or `openai_api_key`

Optional/commonly adjusted:

- `lambda_function_name`
- `deployment_environment`

Networking note:

- This stack uses your region's **default VPC** and the first two **default subnets** in that VPC for Lambda + EFS.
- Ensure your preferred region has a default VPC with at least two subnets before applying.

## 3) First infrastructure deploy

```bash
cd terraform
terraform init
terraform plan -var-file=terraform.tfvars
terraform apply -var-file=terraform.tfvars
```

Capture outputs:

```bash
terraform output cloudfront_url
terraform output lambda_function_name
terraform output cors_origin_value
```

Important post-step:

- Add `cloudfront_url` to Clerk allowed origins / redirect URLs.

## 4) Build and publish backend Lambda zip

From repo root:

```bash
python infra/scripts/build_lambda_deployment.py
python infra/scripts/deploy_lambda.py --function-name "$(terraform -chdir=terraform output -raw lambda_function_name)" --zip backend/lambda-deployment.zip --region "$(terraform -chdir=terraform output -raw aws_region)"
```

Notes:

- Terraform manages a bootstrap zip only.
- Application code updates are delivered through `update_function_code` in `deploy_lambda.py`.

## 5) Build and publish frontend static assets

From repo root:

```bash
cd frontend
npm ci
npm run build
cd ..
```

Sync `frontend/out` to the static bucket and invalidate CloudFront:

```bash
STATIC_BUCKET="$(terraform -chdir=terraform output -raw static_site_bucket_name)"
DIST_ID="$(terraform -chdir=terraform output -raw cloudfront_distribution_id)"

aws s3 sync frontend/out "s3://${STATIC_BUCKET}" --delete
aws cloudfront create-invalidation --distribution-id "${DIST_ID}" --paths "/*"
```

## 6) Ongoing deploy cadence

- Infra/config changes: `terraform plan/apply`
- Backend code changes: `build_lambda_deployment.py` + `deploy_lambda.py`
- Frontend code changes: `npm run build` + S3 sync + CloudFront invalidation

## 7) Sanity checks

- `terraform validate`
- `terraform plan -var-file=terraform.tfvars`
- `python -m py_compile infra/scripts/build_lambda_deployment.py infra/scripts/deploy_lambda.py`

