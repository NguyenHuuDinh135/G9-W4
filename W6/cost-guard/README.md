# W6 Task 3 — Cost Guard Lambda & IAM Role

This folder implements the W6 automated cost-control Lambda.

## Acceptance criteria mapping

- Lambda scans EC2: `describe_instances` paginator in `lambda_function.py`.
- Lambda scans RDS: `describe_db_instances` paginator plus `list_tags_for_resource`.
- Lambda stops resources missing both approved runtime tags:
  - `keep=true`
  - `Environment=dev`
- IAM role is least-privilege for this task:
  - EC2/RDS inventory only: `ec2:DescribeInstances`, `rds:DescribeDBInstances`, `rds:ListTagsForResource`
  - Stop only: `ec2:StopInstances`, `rds:StopDBInstance`
  - CloudWatch Logs write permissions for Lambda execution logs
- EventBridge invokes the Lambda on a schedule so a real CloudTrail `StopInstances` or `StopDBInstance` event can be captured for the W6 evidence pack.
- AWS Budgets daily `$150` is wired to SNS, and the SNS topic invokes the same Lambda so the required cost-driven path exists. A real Budgets alert may be delayed by AWS cost-data latency, so demo it with a test SNS publish.

## Guard logic

A running resource is protected when either tag condition is true:

```text
keep=true OR Environment=dev
```

If neither condition is present, the Lambda calls the relevant stop API.

## Deploy

From this directory:

```bash
terraform init
terraform plan
terraform apply
```

For a fast classroom demo, temporarily override the schedule:

```bash
terraform apply -var='schedule_expression=rate(5 minutes)'
```

Return it to the daily schedule after collecting evidence:

```bash
terraform apply -var='schedule_expression=cron(0 18 * * ? *)'
```

The Terraform also creates the W6 cost-driven path:

```text
AWS Budgets daily $150 -> SNS topic -> Cost Guard Lambda
```

Demo the Budgets path without waiting for delayed cost data by publishing a test SNS message to the output topic ARN:

```bash
aws sns publish \
  --topic-arn "$(terraform output -raw budget_sns_topic_arn)" \
  --message '{"source":"manual-w6-budget-chain-test"}'
```

## Evidence to capture for W6

1. Screenshot the IAM policy showing only Describe/List, Stop, and Logs permissions.
2. Screenshot the EventBridge daily schedule.
3. Screenshot the AWS Budget (`$150`, `DAILY`) and SNS topic/subscription wired to the Lambda.
4. Create or use one EC2/RDS resource without `keep=true` and without `Environment=dev`.
5. Let the EventBridge rule invoke the Lambda, or run the SNS test publish above for the Budgets chain demo.
6. Capture before/after state: running/available → stopping/stopped.
7. Capture CloudTrail event:
   - EC2: `StopInstances`
   - RDS: `StopDBInstance`
8. Add the screenshots, the SNS test-publish result, and the latency ADR to `docs/W6_evidence.md`.

## Safety

`dry_run` defaults to `false` because W6 acceptance requires a real Stop API event. For rehearsal only:

```bash
terraform apply -var='dry_run=true'
```
