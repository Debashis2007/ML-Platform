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


def test_control_plane_docs_and_workflows():
    assert Path("docs/CONTROL_PLANE.md").is_file()
    assert Path(".github/workflows/admin-run.yml").is_file()
    assert Path(".github/workflows/model-promote.yml").is_file()
    assert Path("infra/terraform/modules/stage_analytics/lambda/export_governance.py").is_file()
