#!/usr/bin/env bash
# Run a scanner ECS task on-demand (same task definition the schedule uses).
# Used by azure-pipelines/scanners-ops.yml (action: run-now).
set -euo pipefail

MODULE="${1:-}"
if [[ -z "${MODULE}" ]]; then
  echo "Usage: $0 <module>    # e.g. $0 route53" >&2
  exit 1
fi

: "${AWS_REGION:?AWS_REGION is required}"
: "${ECS_CLUSTER_NAME:?ECS_CLUSTER_NAME is required}"
: "${ECS_TASK_FAMILY:?ECS_TASK_FAMILY is required}"
: "${ECS_SUBNET_IDS:?ECS_SUBNET_IDS is required (comma-separated subnet ids)}"
: "${ECS_SECURITY_GROUP_ID:?ECS_SECURITY_GROUP_ID is required}"
ECS_ASSIGN_PUBLIC_IP="${ECS_ASSIGN_PUBLIC_IP:-ENABLED}"

echo "Running '${MODULE}' scanner: task=${ECS_TASK_FAMILY} cluster=${ECS_CLUSTER_NAME} region=${AWS_REGION}"

TASK_ARN="$(aws ecs run-task \
  --region "${AWS_REGION}" \
  --cluster "${ECS_CLUSTER_NAME}" \
  --task-definition "${ECS_TASK_FAMILY}" \
  --launch-type FARGATE \
  --count 1 \
  --network-configuration "awsvpcConfiguration={subnets=[${ECS_SUBNET_IDS}],securityGroups=[${ECS_SECURITY_GROUP_ID}],assignPublicIp=${ECS_ASSIGN_PUBLIC_IP}}" \
  --query 'tasks[0].taskArn' \
  --output text)"

echo "Started task: ${TASK_ARN}"
