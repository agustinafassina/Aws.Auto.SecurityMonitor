# Azure DevOps Pipelines

Pipelines are **per scanner module** for build/deploy and manual operations, plus one shared infrastructure pipeline.

| Pipeline | File | Trigger |
|----------|------|---------|
| Route53 build | `modules/route53-build.yml` | `scan-resources/route53/**` + shared files on `main` |
| RDS build | `modules/rds-build.yml` | `scan-resources/rds/**` + shared files on `main` |
| Route53 ops | `modules/route53-ops.yml` | Manual only |
| RDS ops | `modules/rds-ops.yml` | Manual only |
| Terraform | `infrastructure.yml` | `terraform-infrastructure/**` on `main` |

Shared step templates live in `templates/` (`module-build-steps.yml`, `module-ops-steps.yml`).

## Setup

1. Create an **AWS service connection** named `aws-security-monitor` in Azure DevOps.
2. Create a **variable group** `aws-security-monitor-dev` — see `variable-group.example.md`.
3. Create an **environment** `security-monitor-dev` for Terraform apply approval.
4. Register each YAML under `modules/` plus `infrastructure.yml` as separate pipelines.

## Deploy flow (per module)

1. Change code under `scan-resources/route53/` → run or wait for `route53-build`:
   - Login AWS (`aws sts get-caller-identity` via service connection)
   - Login ECR (`aws ecr get-login-password` + `docker login`)
   - Build image → push `security-scan/scanners:route53`
2. Change code under `scan-resources/rds/` → `rds-build` → pushes `:rds` tag.
3. Fargate task definitions reference `{module}` as ECR tag (default in `scanner_jobs`); no terraform apply needed for scanner-only changes.
4. Run `route53-ops` / `rds-ops` manually to **run now**, **enable schedule**, or **disable schedule**.

## Ops pipeline actions

| Action | What it does |
|--------|----------------|
| `run-now` | `aws ecs run-task` (same task definition as EventBridge) |
| `enable-schedule` | `aws events enable-rule` for that module's schedule |
| `disable-schedule` | `aws events disable-rule` (on-demand only) |

## Adding a new module

1. Add `modules/<module>-build.yml` and `modules/<module>-ops.yml` (copy from route53/rds).
2. Add variable group entries: `ECS_TASK_FAMILY_<MODULE>`, `EVENTBRIDGE_RULE_<MODULE>`.
3. Reuse `templates/module-build-steps.yml` and `templates/module-ops-steps.yml`.

## Image model

- **One ECR repo**: `{project_name}/scanners`.
- **One tag per module**: `route53`, `rds`, etc. (each module has its own Dockerfile).
- ECS tasks use `image_tag` from `scanner_jobs` (defaults to module key).
