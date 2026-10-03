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
        "modules/promote",
        "modules/management_api",
        "modules/platform_function",
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
        "register_candidate",
        "approval_api",
        "okta_authorizer",
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
        "lambdas/register_candidate/Dockerfile",
        "lambdas/approval_api/Dockerfile",
        "lambdas/okta_authorizer/Dockerfile",
        "infra/terraform/modules/stage_analytics/lambda/Dockerfile",
    ):
        assert Path(rel).is_file(), f"missing {rel}"
    for env in ("hub-nonprod", "hub-prod", "deploy-endpoint"):
        text = (ROOT / "envs" / env / "platform_lambda.tf").read_text()
        assert "platform_lambda_uris" in text
        assert "platform_ecr_registry" in text


def test_lambda_modules_support_image_package_type():
    for mod in ("governance", "promote", "api_gateway", "stage_analytics", "platform_function"):
        main = (ROOT / "modules" / mod / "main.tf").read_text()
        assert "package_type" in main or "image_uri" in main, f"{mod} missing image support"


def test_control_plane_docs_and_workflows():
    assert Path("docs/CONTROL_PLANE.md").is_file()
    assert Path(".github/workflows/ml-lifecycle.yml").is_file()
    assert Path(".github/workflows/platform-infra.yml").is_file()
    assert Path("infra/terraform/modules/stage_analytics/lambda/export_governance.py").is_file()


def _tf(rel: str) -> str:
    return (ROOT / rel).read_text()


def test_no_step_functions_or_control_plane_bu_endpoints():
    assert not (ROOT / "modules/step_functions").exists()
    assert not (ROOT / "modules/bu_endpoints").exists()
    for path in ROOT.rglob("*.tf"):
        text = path.read_text()
        assert "aws_sfn_state_machine" not in text, f"Step Functions in {path}"
        assert "modules/bu_endpoints" not in text


def test_governance_has_four_protected_tables():
    text = _tf("modules/governance/main.tf")
    for table in ("ml_lifecycle", "ml_decision_log", "ml_identity", "ml_locks"):
        assert table in text
    assert "deletion_protection_enabled" in text
    assert "point_in_time_recovery" in text
    assert 'stream_view_type            = "NEW_AND_OLD_IMAGES"' in text
    assert "SageMaker Model Building Pipeline Execution Status Change" in text


def test_object_lock_buckets_governance_730_days():
    main = _tf("modules/storage/main.tf")
    assert "object_lock_enabled = true" in main
    assert 'mode = "GOVERNANCE"' in main
    assert "s3:BypassGovernanceRetention" in main
    assert "aws:SecureTransport" in main
    assert "default     = 730" in _tf("modules/storage/variables.tf")


def test_endpoint_blue_green_release_policy():
    main = _tf("modules/endpoint/main.tf")
    assert '"CANARY" : "ALL_AT_ONCE"' in main
    assert "CAPACITY_PERCENT" in main
    assert "auto_rollback_configuration" in main
    assert "instance_count >= 2" in main
    assert "aws_appautoscaling_target" in main
    assert "create_before_destroy = true" in main
    variables = _tf("modules/endpoint/variables.tf")
    assert 'variable "live_canary_wait_seconds"' in variables and "default = 900" in variables


def test_management_api_private_okta_no_cognito():
    main = _tf("modules/management_api/main.tf")
    assert '"PRIVATE"' in main
    assert 'type                             = "TOKEN"' in main
    assert "aws:SourceVpce" in main
    assert "waf_web_acl_arn" in main
    for path in ROOT.rglob("*.tf"):
        assert "aws_cognito" not in path.read_text(), f"Cognito in {path}"


def test_network_plane_endpoint_sets():
    main = _tf("modules/network/main.tf")
    for svc in ("execute-api", "events", "lambda", "sagemaker.runtime", "ecr.dkr"):
        assert f'"{svc}"' in main
    assert "dynamodb" in main
    assert 'cidr_blocks = ["0.0.0.0/0"]' not in main.split("HTTPS via NAT")[0]


def test_envs_set_default_tags():
    for env in ("hub-nonprod", "hub-prod", "deploy-endpoint"):
        text = _tf(f"envs/{env}/main.tf")
        assert "default_tags" in text
        for key in ("bu", "project", "version"):
            assert f"{key} " in text
