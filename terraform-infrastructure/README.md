# 📘 Terraform Infrastructure for Scanner Jobs
This Terraform stack provisions a scalable baseline to run scanner containers recurrently on AWS.

## 🗺️ Workflow
![Terraform Infrastructure Workflow](./workflow.svg)

## 🧱 What It Creates
- One ECS Fargate cluster for scanner jobs.
- One ECR repository per scanner container.
- One ECS task definition per scanner.
- One EventBridge schedule rule + ECS target per scanner.
- One CloudWatch log group per scanner task.
- One CloudWatch alarm per scanner rule (`FailedInvocations` metric).
- IAM roles/policies for:
  - ECS task execution.
  - ECS task runtime access (Route53 + RDS discovery actions).
  - EventBridge triggering ECS tasks.

## 📈 Structure for scalability
Scalability is driven by `scanner_jobs` (map variable).  
To add a new scanner container, add a new entry in `scanner_jobs`; Terraform will create ECR, task definition, schedule, target, logs, and alarm for that scanner.

## ▶️ Usage
1. Initialize Terraform:
   ```bash
   terraform -chdir=terraform-infrastructure init
   ```

2. Copy and adjust vars:
   ```bash
   cp terraform-infrastructure/terraform.tfvars.example terraform-infrastructure/terraform.tfvars
   ```

3. Plan/apply:
   ```bash
   terraform -chdir=terraform-infrastructure plan
   terraform -chdir=terraform-infrastructure apply
   ```

4. Build and push scanner images to ECR:
   - Route53 image:
     ```bash
     docker build -f scan-resources/route53/Dockerfile -t route53-scanner:latest .
     ```
   - RDS image:
     ```bash
     docker build -f scan-resources/rds/Dockerfile -t rds-scanner:latest .
     ```

   Tag/push each image to the ECR URLs returned by Terraform output `ecr_repository_urls`.

## 📝 Notes
- The ECS tasks are configured to run with `--source aws`.
- Credentials are resolved by AWS SDK (`boto3`) through task role (no API keys).
- If `vpc_id`/`subnet_ids` are not defined, Terraform uses the default VPC and its subnets.

## 🔔 Notifications
- Set `alarm_notification_emails` in `terraform.tfvars` to enable alerting.
- When non-empty, Terraform creates an SNS topic and subscribes each email (each recipient must confirm the subscription email).
- Notifications are sent when:
  - an ECS task fails to start (`stopCode = TaskFailedToStart`), and
  - the per-scanner `FailedInvocations` CloudWatch alarm triggers.
- Alternatively, set `alarm_sns_topic_arn` to reuse a pre-existing topic (ignored when emails are provided).