# Infrastructure

## Terraform (primary)

See **[terraform/README.md](terraform/README.md)** for module layout, apply order, and evaluation-pipeline wiring.

Quick start:

```bash
cd terraform/envs/hub-nonprod
cp terraform.tfvars.example terraform.tfvars
terraform init && terraform apply
```

## CloudFormation

Templates in [`../deployment/`](../deployment/) — hub/spoke SageMaker domains, model package sharing, governance, KMS.

Deploy order: step1a → 1b → 1c (hub), step2/3 (spokes), step4 → 5 → 6 (KMS).

Use CloudFormation for initial rollout or Terraform factory modules when ready to cut over.
