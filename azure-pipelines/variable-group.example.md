# Variable group template (create in Azure DevOps Library):
#   awsRegion: sa-east-1
#   ecrRepository: security-scan/scanners
#   tfVarsFile: environments/qa.tfvars
#   backendConfigFile: environments/qa.backend.hcl
#   ECS_CLUSTER_NAME: tf-qa-security-scan-cluster
#   ECS_TASK_FAMILY_ROUTE53: tf-qa-security-scan-route53
#   ECS_TASK_FAMILY_RDS: tf-qa-security-scan-rds
#   EVENTBRIDGE_RULE_ROUTE53: tf-qa-security-scan-route53-schedule
#   EVENTBRIDGE_RULE_RDS: tf-qa-security-scan-rds-schedule
#   ECS_SECURITY_GROUP_ID: sg-xxxxxxxx
#   ECS_SUBNET_IDS: subnet-aaa,subnet-bbb
#   ECS_ASSIGN_PUBLIC_IP: ENABLED
#
# Terraform outputs: name_prefix, task_definition_families, eventbridge_rule_names
# Do not store alarm emails in the group if avoidable — use environments/*.tfvars as secure files.
