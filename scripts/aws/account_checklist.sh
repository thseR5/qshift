#!/usr/bin/env bash
set -euo pipefail

echo "QShift AWS read-only account checklist"
echo "No resources are created and no paid API is called."
if ! command -v aws >/dev/null 2>&1; then
  echo "AWS CLI: not installed"
  exit 0
fi
echo "AWS CLI: $(aws --version 2>&1)"
echo "Identity (credentials are not printed):"
aws sts get-caller-identity --query '{Account:Account,Arn:Arn,UserId:UserId}' --output table
echo "Configured region:"
aws configure get region || true
echo
echo "Founder must confirm manually in Billing console:"
echo "  Billing -> Credits: balance and expiry"
echo "  Billing -> Free Tier: current eligible services and limits"
echo "  Billing -> Plans: Free/Paid account plan"
echo "  Account/Region: intended region and service availability"
echo
echo "Before activation, create a zero-spend budget alert and set service quotas/limits."
