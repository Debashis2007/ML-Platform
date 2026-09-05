# IAM module removed — client-managed roles

This directory no longer creates IAM roles. The client provisions all roles
manually. Pass role ARNs into Terraform env roots (`hub-nonprod`, `hub-prod`,
`deploy-endpoint`).

See [`docs/CLIENT_MANAGED_IAM_ROLES.md`](../../../../docs/CLIENT_MANAGED_IAM_ROLES.md)
for the full role inventory, trust policies, and permission checklist.
