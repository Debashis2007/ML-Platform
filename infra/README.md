# Infrastructure

## CloudFormation (available now)

Use the templates in [`../deployment/`](../deployment/) for hub/spoke SageMaker domains, model package sharing, governance resources, and cross-account KMS.

Deploy order: step1a → 1b → 1c (hub), step2/3 (spokes), step4 → 5 → 6 (KMS).

## Terraform (planned)

Terraform modules for the shared ML factory (networking, ECR, registry, endpoint deploy) are **not implemented in this repo yet**.

When added, they will live here, for example:

```
infra/terraform/
  modules/
    endpoint/
    registry/
  envs/
    dev/
    prod/
```

Workflow B (`.github/workflows/model-deploy.yml`) will call `terraform apply` once those modules exist.
