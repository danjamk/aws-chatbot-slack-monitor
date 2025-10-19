#!/bin/bash
# aws-permissions-config.sh
#
# AWS Chatbot Slack Monitor Project - IAM Policies Configuration
#
# This file is sourced by setup-aws-iam-user.sh to determine which IAM policies
# to attach to the project's IAM user for CDK deployment.

# ============================================================================
# IAM Policies Configuration
# ============================================================================

# Array of AWS managed policy ARNs to attach to the IAM user
# These policies are required for deploying the AWS Chatbot Slack Monitor stack

POLICIES=(
    # ========================================================================
    # Core CDK Deployment Policies (Required)
    # ========================================================================

    # S3 - CDK uses S3 for storing deployment assets (CloudFormation templates, etc.)
    "arn:aws:iam::aws:policy/AmazonS3FullAccess"

    # SNS - For notification topics (critical-alerts, heartbeat-alerts)
    "arn:aws:iam::aws:policy/AmazonSNSFullAccess"

    # CloudWatch - For dashboards, metrics, and cost monitoring
    "arn:aws:iam::aws:policy/CloudWatchFullAccess"

    # Secrets Manager - For storing Slack workspace and channel IDs securely
    "arn:aws:iam::aws:policy/SecretsManagerReadWrite"

    # IAM - Required for CDK to create IAM roles for AWS Chatbot and other services
    # Note: This is a broad permission. In production, consider a custom policy.
    "arn:aws:iam::aws:policy/IAMFullAccess"
)

# ============================================================================
# Additional Inline Policy for CDK-Specific Permissions
# ============================================================================
# The setup script will also attach this inline policy for CDK, Chatbot, and Budgets

CDK_INLINE_POLICY_NAME="CDKChatbotBudgetsPolicy"

# Using cat with heredoc for better portability
CDK_INLINE_POLICY_DOCUMENT=$(cat <<'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "CloudFormationFullAccess",
      "Effect": "Allow",
      "Action": [
        "cloudformation:*"
      ],
      "Resource": "*"
    },
    {
      "Sid": "AWSChatbotFullAccess",
      "Effect": "Allow",
      "Action": [
        "chatbot:*"
      ],
      "Resource": "*"
    },
    {
      "Sid": "AWSBudgetsFullAccess",
      "Effect": "Allow",
      "Action": [
        "budgets:*"
      ],
      "Resource": "*"
    },
    {
      "Sid": "STSGetCallerIdentity",
      "Effect": "Allow",
      "Action": [
        "sts:GetCallerIdentity"
      ],
      "Resource": "*"
    },
    {
      "Sid": "SSMParameterStoreAccess",
      "Effect": "Allow",
      "Action": [
        "ssm:GetParameter",
        "ssm:GetParameters",
        "ssm:PutParameter",
        "ssm:DeleteParameter"
      ],
      "Resource": "arn:aws:ssm:*:*:parameter/cdk-bootstrap/*"
    }
  ]
}
EOF
)

# ============================================================================
# Notes on AWS Chatbot Slack Monitor Permissions
# ============================================================================
#
# This project requires the following AWS service permissions:
#
# 1. **S3**: CDK stores deployment assets (CloudFormation templates, Lambda code)
#            in an S3 bucket it creates automatically (CDK bootstrap)
#
# 2. **CloudFormation**: CDK synthesizes and deploys CloudFormation stacks
#
# 3. **SNS**: Creates notification topics for critical and heartbeat alerts
#
# 4. **CloudWatch**: Creates dashboards and accesses billing metrics
#
# 5. **AWS Chatbot**: Configures Slack channel integrations
#
# 6. **AWS Budgets**: Creates and manages daily and monthly budgets
#
# 7. **Secrets Manager**: Stores Slack workspace and channel IDs securely
#
# 8. **IAM**: CDK creates IAM roles for AWS Chatbot to access AWS services
#
# Security Considerations:
# - These are DEPLOYMENT permissions (not runtime)
# - The IAM user created will have broad permissions for CDK deployment
# - Consider using AWS Organizations SCPs for additional protection
# - For production, create a custom minimal policy instead of managed policies
# - The Chatbot itself will have READ-ONLY permissions (defined in CDK code)
#
# Production Best Practice:
# Instead of IAMFullAccess, create a custom policy that only allows:
# - iam:CreateRole
# - iam:AttachRolePolicy
# - iam:PutRolePolicy
# - iam:PassRole
# Only for roles with specific naming patterns (e.g., chatbot-monitor-*)
#
# ============================================================================
# How to Use This Configuration
# ============================================================================
#
# 1. Run the setup script from the project root:
#    bash scripts/setup-aws-iam-user.sh
#
# 2. Follow the prompts to create the IAM user
#
# 3. The script will output AWS credentials for your .env file
#
# 4. Test the deployment:
#    make synth    # Validate CDK code
#    make diff     # See what will be deployed
#    make deploy   # Deploy the stack
#
# ============================================================================
# Troubleshooting
# ============================================================================
#
# AccessDenied during deployment:
#   - Verify all policies are attached: aws iam list-attached-user-policies --user-name PROJECT-USER
#   - Check inline policies: aws iam list-user-policies --user-name PROJECT-USER
#
# CDK bootstrap fails:
#   - Ensure S3FullAccess and CloudFormationFullAccess are attached
#   - Run: cdk bootstrap aws://ACCOUNT-ID/REGION
#
# Chatbot configuration fails:
#   - Ensure you've manually configured Slack workspace in AWS Console first
#   - See docs/slack-setup.md for detailed instructions
#
