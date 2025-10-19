# Deployment Checklist - AWS Chatbot Slack Monitor

This checklist guides you through deploying the AWS Chatbot Slack Monitor project from scratch.

## Overview

The deployment process has 5 main phases:
1. **Prerequisites** - Set up AWS and Slack
2. **Configuration** - Configure project settings
3. **Secrets Deployment** - Deploy Slack credentials to AWS
4. **Infrastructure Deployment** - Deploy CDK stacks
5. **Validation** - Test the system end-to-end

Estimated time: **30-45 minutes** (first deployment)

---

## Phase 1: Prerequisites

### 1.1 AWS Account Setup

- [ ] Have an AWS account with administrative access
- [ ] Know your AWS Account ID (find at: https://console.aws.amazon.com/billing/)
- [ ] Decide on deployment region (recommend: `us-east-1` for full billing metrics)

### 1.2 AWS IAM User for Deployment

Create a dedicated IAM user for CDK deployments:

```bash
# Run the permission configuration script
bash scripts/aws-permissions-config.sh
```

This creates:
- IAM user: `cdk-deployment-user`
- Programmatic access credentials
- Required policies for CloudFormation, SNS, Budgets, Chatbot, etc.

**Important**: Save the Access Key ID and Secret Access Key shown at the end.

- [ ] IAM user created
- [ ] Access keys saved securely

### 1.3 AWS CLI Configuration

Configure AWS credentials in the container:

```bash
# Configure AWS CLI with your deployment user credentials
aws configure

# Verify access
aws sts get-caller-identity

# Should show:
# - UserId: Your IAM user ID
# - Account: Your AWS account number
# - Arn: arn:aws:iam::ACCOUNT_ID:user/cdk-deployment-user
```

- [ ] AWS CLI configured
- [ ] Credentials verified

### 1.4 Slack Workspace Setup

Follow the detailed guide: `docs/slack-setup.md`

**Quick checklist**:
- [ ] Slack workspace admin access
- [ ] Created `#aws-alerts-critical` channel
- [ ] Created `#aws-alerts-heartbeat` channel
- [ ] Obtained Workspace ID (starts with `T`)
- [ ] Obtained Critical Channel ID (starts with `C`)
- [ ] Obtained Heartbeat Channel ID (starts with `C`)

**How to get IDs**: See `docs/slack-setup.md` for detailed instructions.

---

## Phase 2: Configuration

### 2.1 Environment Variables

Create your `.env` file from the template:

```bash
# Copy the example
cp config/.env.example .env

# Edit with your actual values
vim .env  # or your preferred editor
```

**Required values** in `.env`:
```bash
# Slack Configuration (from Phase 1.4)
SLACK_WORKSPACE_ID=T01234ABCDE          # Your workspace ID
SLACK_CRITICAL_CHANNEL_ID=C01234ABCDE   # Critical channel ID
SLACK_HEARTBEAT_CHANNEL_ID=C56789FGHIJ  # Heartbeat channel ID

# Optional: Email notifications
NOTIFICATION_EMAILS=team@example.com,admin@example.com

# AWS Configuration (from Phase 1.3)
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
AWS_DEFAULT_REGION=us-east-1
CDK_DEFAULT_ACCOUNT=123456789012
CDK_DEFAULT_REGION=us-east-1
```

- [ ] `.env` file created
- [ ] All Slack IDs added
- [ ] AWS credentials added
- [ ] Region and account ID set

### 2.2 Project Configuration

Edit `config/config.yaml` with your budget and settings:

```bash
vim config/config.yaml
```

**Key settings to customize**:

```yaml
project:
  name: ChatbotMonitor          # Change if desired
  environment: production        # or dev, staging, etc.

aws:
  region: us-east-1             # Match your chosen region
  account_id: "123456789012"    # Your AWS account ID

budgets:
  daily_limit: 10.00            # YOUR daily budget (USD)
  monthly_limit: 300.00         # YOUR monthly budget (USD)
  monthly_threshold_warning: 80  # Warning at 80%
  monthly_threshold_critical: 100 # Alert at 100%
  currency: USD                  # USD, EUR, etc.
```

- [ ] Budget amounts set for your needs
- [ ] AWS account ID updated
- [ ] Region confirmed
- [ ] Project name customized (optional)

---

## Phase 3: Secrets Deployment

Deploy Slack credentials to AWS Secrets Manager:

```bash
# Make sure .env is configured first!
make deploy-secrets

# Or run directly:
# python scripts/deploy-secrets.py
```

**What this does**:
- Validates Slack IDs in `.env`
- Creates secret in AWS Secrets Manager
- Secret name: `{project_name}/{environment}/slack-config`
- Verifies secret can be read back

**Expected output**:
```
✅ Slack configuration validated
✅ Secret created: ChatbotMonitor/production/slack-config
✅ Secret verification successful
```

**Common issues**:
- "Missing required environment variable" → Check `.env` file
- "Invalid Slack ID format" → Workspace IDs start with `T`, Channel IDs with `C`
- "Access denied" → Check AWS credentials and IAM permissions

- [ ] Secrets deployed successfully
- [ ] Secret verification passed

---

## Phase 4: Infrastructure Deployment

### 4.1 Bootstrap CDK (First Time Only)

If this is your first CDK deployment in this AWS account/region:

```bash
cdk bootstrap aws://ACCOUNT_ID/REGION

# Example:
# cdk bootstrap aws://123456789012/us-east-1
```

This creates the CDK staging resources (S3 bucket, IAM roles).

- [ ] CDK bootstrapped (or already done previously)

### 4.2 Preview Changes

Review what will be deployed:

```bash
make synth

# Or see a deployment diff:
cdk diff --all
```

- [ ] Reviewed stack configurations
- [ ] No unexpected resources

### 4.3 Deploy SNS Stack (Foundation)

Deploy the SNS topics first:

```bash
cdk deploy ChatbotMonitorSnsStack

# Or use:
# make deploy
```

**What this creates**:
- 2 SNS topics (critical-alerts, heartbeat-alerts)
- Email subscriptions (if NOTIFICATION_EMAILS set)
- CloudFormation exports for topic ARNs

**Expected output**:
```
ChatbotMonitorSnsStack: creating CloudFormation changeset...
✅ ChatbotMonitorSnsStack

Outputs:
ChatbotMonitorSnsStack.CriticalTopicArn = arn:aws:sns:...
ChatbotMonitorSnsStack.HeartbeatTopicArn = arn:aws:sns:...
```

**Action required**: If email subscriptions were added, check your inbox and confirm the SNS subscription emails.

- [ ] SNS stack deployed
- [ ] Email subscriptions confirmed (if applicable)

### 4.4 Authorize Slack Workspace (One-Time Manual Step)

**IMPORTANT**: Before deploying the Chatbot stack, authorize your Slack workspace.

1. Go to AWS Chatbot Console: https://console.aws.amazon.com/chatbot/
2. Click **Configure new client**
3. Choose **Slack**
4. Click **Configure** next to Slack
5. Authorize your workspace when prompted
6. You should see your workspace listed with status "Authorized"

**Why**: AWS Chatbot requires manual OAuth authorization for Slack workspaces.

- [ ] Slack workspace authorized in AWS Console
- [ ] Workspace shows as "Authorized" in Chatbot console

### 4.5 Deploy Remaining Stacks

Deploy all remaining stacks together:

```bash
# Deploy all at once (recommended)
make deploy

# Or deploy individually:
# cdk deploy ChatbotMonitorBudgetStack
# cdk deploy ChatbotMonitorChatbotStack
# cdk deploy ChatbotMonitorMonitoringStack
```

**What this creates**:

**Budget Stack**:
- Daily budget ($10/day default)
- Monthly budget ($300/month default)
- Budget alerts to SNS topics

**Chatbot Stack**:
- IAM role for AWS Chatbot (read-only)
- Slack channel configuration for critical alerts
- Slack channel configuration for heartbeat alerts
- Subscriptions to SNS topics

**Monitoring Stack**:
- CloudWatch dashboard with cost widgets
- Monthly and daily spend trends
- Budget threshold annotations

**Expected output**:
```
✅ ChatbotMonitorBudgetStack
✅ ChatbotMonitorChatbotStack
✅ ChatbotMonitorMonitoringStack

Outputs:
ChatbotMonitorMonitoringStack.DashboardURL = https://...
```

- [ ] All stacks deployed successfully
- [ ] No errors in CloudFormation console

---

## Phase 5: Validation

### 5.1 Verify Slack Channels

Check your Slack channels:

- [ ] AWS Chatbot joined both channels (#aws-alerts-critical and #aws-alerts-heartbeat)
- [ ] You see a welcome message from AWS Chatbot

If AWS Chatbot didn't join automatically:
1. Type `/invite @AWS` in each channel
2. AWS Chatbot should join

### 5.2 Test Notifications

Test the notification system:

```bash
# Run the validation script
make validate

# Or manually:
# bash scripts/validate-notifications.sh
```

This sends test messages to both topics.

**Expected**: Messages appear in both Slack channels within 1-2 minutes.

- [ ] Test message received in #aws-alerts-critical
- [ ] Test message received in #aws-alerts-heartbeat

### 5.3 Test Interactive Commands

In either Slack channel, test AWS CLI commands:

```
@aws budgets describe-budgets
@aws cloudwatch describe-alarms
@aws sns list-topics
```

**Expected**: AWS Chatbot responds with results (formatted output).

- [ ] Interactive commands work
- [ ] AWS Chatbot has read-only access

### 5.4 View CloudWatch Dashboard

Open the dashboard URL from the deployment outputs:

```bash
# Get the dashboard URL
aws cloudformation describe-stacks \
  --stack-name ChatbotMonitorMonitoringStack \
  --query 'Stacks[0].Outputs[?OutputKey==`DashboardURL`].OutputValue' \
  --output text
```

**Expected**: Dashboard shows:
- Current month spend widget
- Monthly trend graph with budget lines
- Daily spend trend (last 30 days)

**Note**: Billing metrics take 6-24 hours to populate. Don't worry if widgets are empty initially.

- [ ] Dashboard accessible
- [ ] Widgets configured correctly

### 5.5 Verify Budget Alerts

Check AWS Budgets console:

1. Go to: https://console.aws.amazon.com/billing/home#/budgets
2. You should see:
   - `ChatbotMonitor-daily-budget`
   - `ChatbotMonitor-monthly-budget`

Click each budget and verify:
- Budget amount matches `config.yaml`
- Alert thresholds configured (80%, 100% for monthly)
- SNS topics subscribed correctly

- [ ] Budgets created
- [ ] Alert thresholds correct
- [ ] SNS topics subscribed

---

## Phase 6: Ongoing Operations

### Daily Operations

**What to expect**:
- Daily budget alerts in #aws-alerts-heartbeat (if you exceed daily limit)
- Monthly budget warnings at 80% and 100% thresholds

**Adjusting budgets**:
1. Edit `config/config.yaml`
2. Run `make update` to redeploy Budget stack
3. Budgets updated within minutes

### Monitoring

**CloudWatch Dashboard**:
- Check daily spend trends
- Monitor monthly spend vs budget
- View billing metrics (updated every 6 hours)

**Slack Channels**:
- Critical channel: Only severe alerts
- Heartbeat channel: Daily reports and warnings

**AWS Console**:
- Budgets: https://console.aws.amazon.com/billing/home#/budgets
- CloudWatch: https://console.aws.amazon.com/cloudwatch/
- AWS Chatbot: https://console.aws.amazon.com/chatbot/

### Updating Configuration

**To change budget amounts**:
```bash
vim config/config.yaml
make update
```

**To update Slack channel IDs**:
```bash
vim .env
make deploy-secrets
make deploy  # Redeploy Chatbot stack
```

---

## Troubleshooting

### Deployment Fails

**"Stack already exists"**:
```bash
# View differences before deploying
cdk diff ChatbotMonitorSnsStack

# Update existing stack
make deploy
```

**"Insufficient permissions"**:
- Verify IAM user has all policies from `scripts/aws-permissions-config.sh`
- Check CloudFormation console for detailed error

**"Secret not found"**:
```bash
# Verify secret exists
aws secretsmanager describe-secret \
  --secret-id ChatbotMonitor/production/slack-config

# Redeploy secrets if needed
make deploy-secrets
```

### No Slack Notifications

**Check these in order**:

1. **SNS Topic Subscriptions**:
```bash
aws sns list-subscriptions
# Should show subscriptions for both topics
```

2. **AWS Chatbot Configuration**:
- AWS Console → AWS Chatbot → Slack configurations
- Verify both channels listed
- Check "SNS topics" tab shows correct topics

3. **Slack Channel Settings**:
- AWS Chatbot should be in both channels
- If not: `/invite @AWS` in channel

4. **Test manually**:
```bash
make validate
```

### Dashboard Shows No Data

**Billing metrics delay**:
- Metrics take 6-24 hours to populate for new accounts
- Check again tomorrow

**Wrong region**:
- Billing metrics only available in `us-east-1`
- Verify: AWS Console top-right should show "N. Virginia"

**No spend yet**:
- Dashboard only shows data if you have AWS spend
- Deploy some resources or wait for natural billing

### Budget Alerts Not Working

**Email not confirmed**:
- Check inbox for "AWS Notification - Subscription Confirmation"
- Click confirmation link

**Wrong notification routing**:
```bash
aws budgets describe-budget \
  --account-id YOUR_ACCOUNT_ID \
  --budget-name ChatbotMonitor-monthly-budget
```
Verify `Subscribers` contains correct SNS topic ARNs.

---

## Cleanup / Uninstallation

To remove all resources:

```bash
# Destroy all stacks
make destroy

# Or manually:
# cdk destroy --all

# Delete secrets
aws secretsmanager delete-secret \
  --secret-id ChatbotMonitor/production/slack-config \
  --force-delete-without-recovery

# Deauthorize Slack workspace (manual)
# AWS Console → AWS Chatbot → Settings → Remove workspace
```

**Note**: Budgets and CloudFormation resources are deleted, but some CloudWatch Logs may remain.

---

## Next Steps

### Integrate Other AWS Infrastructure

See `docs/integration-guide.md` for examples of integrating other stacks:
- ECS service monitoring
- Lambda error alerts
- RDS database alerts
- S3 event notifications
- Custom application metrics

### Customize Alerts

Edit `cdk/stacks/budget_stack.py` to:
- Add more budget thresholds
- Create service-specific budgets
- Add forecasted budget alerts

### Enhance Dashboard

Edit `cdk/stacks/monitoring_stack.py` to:
- Add more CloudWatch widgets
- Create service-specific dashboards
- Add anomaly detection

---

## Success Criteria

Your deployment is successful when:

- [x] All 4 CDK stacks deployed without errors
- [x] AWS Chatbot joined both Slack channels
- [x] Test messages delivered to both channels
- [x] Interactive commands work in Slack (`@aws budgets describe-budgets`)
- [x] CloudWatch dashboard accessible
- [x] Budgets configured with correct thresholds
- [x] Email notifications confirmed (if configured)

**Congratulations!** Your AWS Chatbot Slack Monitor is now operational.

---

## Support Resources

- **Project Documentation**: `/workspace/docs/`
- **Slack Setup Guide**: `docs/slack-setup.md`
- **Integration Examples**: `docs/integration-guide.md`
- **AWS CDK Documentation**: https://docs.aws.amazon.com/cdk/
- **AWS Chatbot Documentation**: https://docs.aws.amazon.com/chatbot/
- **AWS Budgets Documentation**: https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/budgets-managing-costs.html

## Quick Reference Commands

```bash
# Deployment
make deploy              # Deploy all stacks
make deploy-secrets      # Deploy Slack credentials
make update              # Update existing deployment

# Testing
make validate            # Test notifications
make synth               # Validate CDK code
make diff                # Show pending changes

# Monitoring
cdk list                 # List all stacks
aws budgets list-budgets --account-id YOUR_ACCOUNT_ID
aws cloudwatch list-dashboards

# Cleanup
make destroy             # Remove all infrastructure
```
