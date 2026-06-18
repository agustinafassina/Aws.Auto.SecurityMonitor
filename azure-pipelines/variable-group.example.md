# 📦 Variable Group Template
Create in Azure DevOps Library as `aws-security-monitor-dev`:

```text
awsRegion: sa-east-1
ecrRepository: security-scan/scanners
namePrefix: tf-qa-security-scan
tfVarsFile: environments/qa.tfvars
backendConfigFile: environments/qa.backend.hcl
ECS_CLUSTER_NAME: tf-qa-security-scan-cluster
ECS_SECURITY_GROUP_ID: sg-xxxxxxxx
ECS_SUBNET_IDS: subnet-aaa,subnet-bbb
ECS_ASSIGN_PUBLIC_IP: ENABLED
```

- `namePrefix` = Terraform output `name_prefix` (used by `scanners-ops` for task family `{prefix}-{module}` and rule `{prefix}-{module}-schedule`).
- `ECS_CLUSTER_NAME` = output `ecs_cluster_name`.

See [README.md](README.md).
