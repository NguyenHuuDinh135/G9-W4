# ADR — W6 Cost Guard cost-data latency

## Context

W6 MH-COST-A requires two paths for automated cost control:

1. A scheduled EventBridge rule invokes the Cost Guard Lambda daily and stops billable compute that should not keep running.
2. A cost-driven path wires AWS Budgets daily `$150` alerts to SNS and then to the same Lambda.

AWS Budgets and Cost Explorer depend on AWS cost data that is not real-time. In a short classroom account, actual cost notifications may lag by roughly 8–24 hours and may not fire during the 48-hour workshop window.

## Decision

Use the scheduled EventBridge path as the reliable enforcement mechanism for the demo and production baseline. Keep the AWS Budgets daily `$150` -> SNS -> Lambda path wired as the cost-driven escalation path, but demonstrate the wiring with a manual SNS test publish instead of waiting for cost data to arrive.

## Consequences

- The scheduled Lambda can produce deterministic evidence: a real EC2/RDS resource transitions from running/available to stopping/stopped and CloudTrail records `StopInstances` or `StopDBInstance`.
- The Budgets path still exists and can trigger the same Lambda when AWS publishes the budget notification.
- For W6 evidence, capture both:
  - EventBridge scheduled invocation and CloudTrail Stop API event.
  - SNS test publish result proving the Budgets topic/subscription invokes the Lambda.
- This avoids presenting a budget email as automation. The control only counts when a resource is actually stopped.
