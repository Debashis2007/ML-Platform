#!/usr/bin/env bash
# Build and push platform Lambda container images to ECR (CI step before Terraform CD).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REGISTRY="${MLP_PLATFORM_ECR_REGISTRY:?Set MLP_PLATFORM_ECR_REGISTRY (e.g. 123456789.dkr.ecr.us-east-1.amazonaws.com)}"
REPOSITORY="${MLP_PLATFORM_LAMBDA_ECR_REPOSITORY:-mlp-platform-lambdas}"
TAG="${MLP_PLATFORM_LAMBDA_IMAGE_TAG:?Set MLP_PLATFORM_LAMBDA_IMAGE_TAG (e.g. git SHA)}"

build_push() {
  local name="$1"
  local context="$2"
  local dockerfile="${3:-Dockerfile}"
  local image="${REGISTRY}/${REPOSITORY}:${name}-${TAG}"
  echo "==> Building ${image}"
  docker build -f "${context}/${dockerfile}" -t "${image}" "${context}"
  docker push "${image}"
  echo "${name}_uri=${image}"
}

build_push capture-approval "${ROOT}/lambdas/capture_approval_event"
build_push github-dispatch "${ROOT}/lambdas/trigger_github_deploy"
build_push promote-model "${ROOT}/lambdas/promote_model_package"
build_push invoke-endpoint "${ROOT}/lambdas/invoke_endpoint"
build_push register-candidate "${ROOT}/lambdas/register_candidate"
build_push approval-api "${ROOT}/lambdas/approval_api"
build_push okta-authorizer "${ROOT}/lambdas/okta_authorizer"
build_push governance-export "${ROOT}/infra/terraform/modules/stage_analytics/lambda"

echo "Platform Lambda images pushed to ${REGISTRY}/${REPOSITORY} with tag suffix ${TAG}"
