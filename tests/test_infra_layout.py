"""Lightweight Terraform module structure checks (no AWS credentials required)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path("infra/terraform")


def test_required_modules_exist():
    expected = [
        "modules/kms",
        "modules/waf",
        "modules/storage",
        "modules/sns",
        "modules/secrets",
        "modules/governance",
        "modules/stage_analytics",
        "modules/bu_endpoints",
        "modules/promote",
        "modules/endpoint",
        "modules/monitoring",
        "modules/api_gateway",
        "modules/api_gateway_account",
        "modules/network",
        "envs/hub-nonprod",
        "envs/hub-prod",
        "envs/deploy-endpoint",
    ]
    for rel in expected:
        path = ROOT / rel
        assert path.is_dir(), f"missing {rel}"
        assert (path / "main.tf").is_file() or any(path.glob("*.tf")) or (path / "README.md").is_file(), f"no tf in {rel}"


def test_remote_backend_script_present():
    assert Path("scripts/terraform_remote_backend.sh").is_file()


def test_backend_examples_present():
    for env in ("hub-nonprod", "hub-prod", "deploy-endpoint"):
        assert (ROOT / "envs" / env / "backend.tf.example").is_file()


def test_iam_roles_are_client_managed():
    """Terraform must not create IAM roles; client supplies ARNs."""
    assert Path("docs/CLIENT_MANAGED_IAM_ROLES.md").is_file()
    assert (ROOT / "modules/iam/README.md").is_file()
    assert not (ROOT / "modules/iam/main.tf").exists()
    # No aws_iam_role resources under terraform modules (except none)
    for path in ROOT.rglob("*.tf"):
        text = path.read_text()
        assert "resource \"aws_iam_role\"" not in text, f"IAM role still created in {path}"


def test_network_vpc_endpoints_enabled_by_default():
    text = (ROOT / "modules/network/variables.tf").read_text()
    assert "enable_vpc_endpoints" in text
    assert "default     = true" in text or "default = true" in text


def test_lambda_sources_present():
    for name in (
        "capture_approval_event",
        "invoke_endpoint",
        "trigger_github_deploy",
        "promote_model_package",
    ):
        assert Path(f"lambdas/{name}/handler.py").is_file()


def test_platform_lambda_container_ci_assets():
    """Platform infra CI builds Lambda images → ECR before Terraform CD."""
    assert Path("scripts/build_push_platform_lambda_images.sh").is_file()
    assert (ROOT / "modules/platform_lambda_uris/outputs.tf").is_file()
    for rel in (
        "lambdas/capture_approval_event/Dockerfile",
        "lambdas/trigger_github_deploy/Dockerfile",
        "lambdas/promote_model_package/Dockerfile",
        "lambdas/invoke_endpoint/Dockerfile",
        "infra/terraform/modules/stage_analytics/lambda/Dockerfile",
    ):
        assert Path(rel).is_file(), f"missing {rel}"
    for env in ("hub-nonprod", "hub-prod", "deploy-endpoint"):
        text = (ROOT / "envs" / env / "platform_lambda.tf").read_text()
        assert "platform_lambda_uris" in text
        assert "platform_ecr_registry" in text


def test_lambda_modules_support_image_package_type():
    for mod in ("governance", "promote", "api_gateway", "stage_analytics", "bu_endpoints"):
        main = (ROOT / "modules" / mod / "main.tf").read_text()
        assert "package_type" in main or "image_uri" in main, f"{mod} missing image support"


def test_control_plane_docs_and_workflows():
    assert Path("docs/CONTROL_PLANE.md").is_file()
    assert Path(".github/workflows/ml-lifecycle.yml").is_file()
    assert Path(".github/workflows/platform-infra.yml").is_file()
    assert Path("infra/terraform/modules/stage_analytics/lambda/export_governance.py").is_file()
