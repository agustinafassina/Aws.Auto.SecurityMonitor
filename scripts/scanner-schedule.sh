#!/usr/bin/env bash
# Enable or disable a scanner's EventBridge schedule rule.
# Used by azure-pipelines/scanners-ops.yml (action: enable-schedule / disable-schedule).
set -euo pipefail

ACTION="${1:-}"
RULE_NAME="${2:-}"

if [[ -z "${ACTION}" || -z "${RULE_NAME}" ]]; then
  echo "Usage: $0 <enable|disable> <eventbridge-rule-name>" >&2
  exit 1
fi

: "${AWS_REGION:?AWS_REGION is required}"

case "${ACTION}" in
  enable)
    aws events enable-rule --region "${AWS_REGION}" --name "${RULE_NAME}"
    echo "Enabled EventBridge rule: ${RULE_NAME}"
    ;;
  disable)
    aws events disable-rule --region "${AWS_REGION}" --name "${RULE_NAME}"
    echo "Disabled EventBridge rule: ${RULE_NAME}"
    ;;
  *)
    echo "Unknown action: ${ACTION} (expected 'enable' or 'disable')" >&2
    exit 1
    ;;
esac
