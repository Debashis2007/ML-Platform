#!/usr/bin/env bash
# Enforce S3 remote state in CI. Writes backend.tf from required GitHub Variables.
set -euo pipefail

: "${MLP_TF_STATE_BUCKET:?MLP_TF_STATE_BUCKET (vars) is required for remote state}"
: "${AWS_REGION:?AWS_REGION is required}"

STATE_KEY="${MLP_TF_STATE_KEY:-ml-platform/${TF_ENV_NAME:-default}.tfstate}"
LOCK_TABLE="${MLP_TF_STATE_LOCK_TABLE:-}"

{
  echo 'terraform {'
  echo '  backend "s3" {'
  echo "    bucket  = \"${MLP_TF_STATE_BUCKET}\""
  echo "    key     = \"${STATE_KEY}\""
  echo "    region  = \"${AWS_REGION}\""
  echo '    encrypt = true'
  if [[ -n "${LOCK_TABLE}" ]]; then
    echo "    dynamodb_table = \"${LOCK_TABLE}\""
  fi
  echo '  }'
  echo '}'
} > backend.tf

echo "Wrote backend.tf (bucket=${MLP_TF_STATE_BUCKET} key=${STATE_KEY})"
