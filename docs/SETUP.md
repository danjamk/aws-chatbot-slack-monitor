# AWS Chatbot Slack Monitor - Detailed Setup Guide

This guide walks you through deploying the AWS Chatbot Slack Monitor from scratch.

**Estimated Time**: 30-45 minutes (first time)

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Step 1: Clone and Setup Repository](#step-1-clone-and-setup-repository)
3. [Step 2: Configure AWS](#step-2-configure-aws)
4. [Step 3: Configure Slack](#step-3-configure-slack)
5. [Step 4: Configure Project Settings](#step-4-configure-project-settings)
6. [Step 5: Deploy to AWS](#step-5-deploy-to-aws)
7. [Step 6: Test and Validate](#step-6-test-and-validate)
8. [Next Steps](#next-steps)

---

## Prerequisites

### Required

- **AWS Account** with administrator access
  - Get AWS Account ID: `aws sts get-caller-identity`
- **Slack Workspace** with admin permissions
  - Ability to create channels and install apps
- **Development Environment** (choose one):
  - Docker Desktop + PyCharm Professional (DevContainer)
  - Docker Desktop + VS Code + Dev Containers extension
  - Local: Python 3.12+ and Node.js 18+
- **Git** installed

### Recommended

- **Anthropic API Key** for Claude Code (optional, for development assistance)
- Basic familiarity with AWS, Slack, and command line

---

## Step 1: Clone and Setup Repository

### Option A: Using This as a Template

**If you want to customize and maintain your own version:**

```bash
# Fork on GitHub, then clone your fork
git clone https://github.com/YOUR-USERNAME/aws-chatbot-slack-monitor.git
cd aws-chatbot-slack-monitor
```

### Option B: Clone Directly

**If you just want to deploy:**

```bash
git clone https://github.com/your-username/aws-chatbot-slack-monitor.git
cd aws-chatbot-slack-monitor
```

### Setup Development Environment

**Using DevContainer (Recommended)**:

**PyCharm Professional**:
1. Open PyCharm
2. File → Open → Select `aws-chatbot-slack-monitor` folder
3. PyCharm detects `.devcontainer/devcontainer.json`
4. Click **"Reopen in Container"** in notification
5. Wait 5-10 minutes for first build

**VS Code**:
1. Install "Dev Containers" extension
2. File → Open Folder → Select `aws-chatbot-slack-monitor`
3. Click **"Reopen in Container"** when prompted
4. Wait 5-10 minutes for first build

**Local Development** (without DevContainer):
```bash
# Install Python dependencies
pip install -r requirements.txt

# Install AWS CDK
npm install -g aws-cdk

# Verify installations
python --version  # Should be 3.12+
cdk --version     # Should be 2.x
aws --version     # AWS CLI
```

---

## Step 2: Configure AWS

### 2.1: Create Deployment IAM User

This creates a project-specific IAM user with minimal permissions:

```bash
# Run the IAM setup script
bash scripts/aws-permissions-config.sh
```

**What this does**:
- Creates IAM user: `aws-chatbot-slack-monitor-dev`
- Attaches policies for CDK deployment
- Generates access keys

**Save the output**:
```
Access Key ID: AKIA...
Secret Access Key: wJal...
```

### 2.2: Configure AWS CLI

```bash
aws configure
# AWS Access Key ID: [paste from above]
# AWS Secret Access Key: [paste from above]
# Default region: us-east-1 (recommended for billing metrics)
# Default output format: json
```

### 2.3: Verify AWS Access

```bash
aws sts get-caller-identity
```

**Expected output**:
```json
{
    "UserId": "AIDA...",
    "Account": "123456789012",
    "Arn": "arn:aws:iam::123456789012:user/aws-chatbot-slack-monitor-dev"
}
```

**Save your AWS Account ID** - you'll need it for configuration.

### 2.4: Bootstrap AWS CDK (First Time Only)

```bash
cdk bootstrap aws://YOUR-ACCOUNT-ID/us-east-1
```

Example:
```bash
cdk bootstrap aws://123456789012/us-east-1
```

**Note**: Only need to run once per AWS account/region.

---

## Step 3: Configure Slack

See detailed [Slack Setup Guide](slack-setup.md) for screenshots and step-by-step instructions.

### 3.1: Create Slack Channels

Create two channels in your Slack workspace:

**Critical Alerts Channel**:
- **Name**: `#aws-critical-alerts` (or your preference)
- **Purpose**: Budget overruns and critical infrastructure alerts
- **Members**: Team leads, on-call engineers
- **Noise Level**: LOW (< 5 messages/day ideal)

**Heartbeat/Monitoring Channel**:
- **Name**: `#aws-heartbeat` (or your preference)
- **Purpose**: Daily cost reports, warnings, monitoring
- **Members**: Development team, finance
- **Noise Level**: MEDIUM (daily reports acceptable)

### 3.2: Get Slack IDs

You need three IDs from Slack:

**Workspace ID**:
1. Open Slack in web browser
2. Look at URL: `https://app.slack.com/client/T01234ABCDE/...`
3. The part after `/client/` is your Workspace ID
4. Format: `T0123456789` (starts with `T`)

**Channel IDs** (for each channel):
1. Right-click channel name in Slack
2. Click **"View channel details"**
3. Scroll to bottom of modal
4. Copy the **Channel ID**
5. Format: `C0123456789` (starts with `C`)

**Save these IDs** - you'll add them to `config.yaml` next.

---

## Step 4: Configure Project Settings

### 4.1: Edit `config/config.yaml`

Open `config/config.yaml` and update:

```yaml
# AWS Configuration
aws:
  region: us-east-1                    # Your AWS region
  account_id: "123456789012"           # YOUR AWS account ID
  stack_prefix: ChatbotMonitor

# Budget Configuration
budgets:
  daily_limit: 10.00                   # YOUR daily budget (USD)
  monthly_limit: 300.00                # YOUR monthly budget (USD)
  monthly_threshold_warning: 80        # Warning at 80%
  monthly_threshold_critical: 100      # Alert at 100%
  currency: USD

# Slack Configuration
slack:
  workspace_id: T09MR3DRVG8            # YOUR Slack workspace ID
  critical_channel_id: C09N63G6F3J     # YOUR critical channel ID
  heartbeat_channel_id: C09MBQUPMK4    # YOUR heartbeat channel ID

# Daily Report Configuration
daily_report:
  enabled: true
  schedule_hour_utc: 8                 # 8 AM UTC (adjust for your timezone)
```

**Important**: Replace the example values with YOUR actual IDs!

### 4.2: (Optional) Configure Email Notifications

If you want email alerts in addition to Slack:

```bash
# Copy template
cp .env.example .env

# Edit .env
vim .env
```

Add email addresses:
```bash
NOTIFICATION_EMAILS=team@example.com,admin@example.com
```

**Note**: You'll need to confirm SNS subscriptions via email after deployment.

---

## Step 5: Deploy to AWS

### 5.1: Preview What Will Be Deployed

```bash
make synth
```

This validates your CDK code compiles correctly.

### 5.2: Deploy All Stacks

```bash
make deploy
```

**What happens**:
1. Prompts for confirmation
2. Type `y` and press Enter
3. CDK deploys 5 stacks (~10 minutes):
   - SnsStack (SNS topics)
   - BudgetStack (budget monitoring)
   - ChatbotStack (Slack integration)
   - MonitoringStack (CloudWatch dashboard)
   - DailyCostStack (daily cost reports)

**Expected output**:
```
✅ ChatbotMonitorSnsStack
✅ ChatbotMonitorBudgetStack
✅ ChatbotMonitorChatbotStack
✅ ChatbotMonitorMonitoringStack
✅ ChatbotMonitorDailyCostStack
```

### 5.3: Authorize Slack Workspace (One-Time)

**IMPORTANT**: Before Slack notifications work, authorize your workspace:

1. Go to: https://console.aws.amazon.com/chatbot/
2. Click **"Configure new client"**
3. Choose **Slack**
4. Click **"Configure"**
5. Sign in to Slack when redirected
6. Click **"Allow"** to authorize AWS Chatbot
7. Verify workspace shows as "Authorized"

### 5.4: Invite Amazon Q to Slack Channels

In each Slack channel (`#aws-critical-alerts` and `#aws-heartbeat`):

```
/invite @Amazon Q Developer
```

Or try:
```
/invite @AWS
```

**Expected**: Bot joins and confirms with a message.

---

## Step 6: Test and Validate

### 6.1: Test Slack Notifications

```bash
make validate
```

**What this does**:
- Creates a temporary CloudWatch alarm
- Triggers the alarm immediately
- Sends notification to your critical channel

**Expected**: Within 1-2 minutes, you see an alarm notification in `#aws-critical-alerts`.

### 6.2: Cleanup Test Alarm

```bash
aws cloudwatch delete-alarms --alarm-names ChatbotTest-DeleteMe
```

### 6.3: Verify Budget Alerts

Check AWS Budgets console:

1. Go to: https://console.aws.amazon.com/billing/home#/budgets
2. You should see:
   - `aws-chatbot-monitor-daily-budget`
   - `aws-chatbot-monitor-monthly-budget`
3. Click each to verify configuration

### 6.4: View CloudWatch Dashboard

Get dashboard URL from deployment outputs or visit:
- https://console.aws.amazon.com/cloudwatch/
- Click "Dashboards"
- Find "ChatbotMonitor-prod-CostMonitoring"

**Note**: Billing metrics take 6-24 hours to populate for new deployments.

### 6.5: Test Daily Cost Report (Optional)

**Option A** - Wait for scheduled run (tomorrow at 8 AM UTC)

**Option B** - Test now via AWS Console:
1. Go to: https://console.aws.amazon.com/lambda/
2. Find function: `ChatbotMonitorDailyCostSt-DailyCostFunction...`
3. Click **"Test"** tab
4. Click **"Test"** button
5. Check `#aws-heartbeat` channel for the report

---

## Next Steps

### Customize Your Deployment

**Change Budget Amounts**:
1. Edit `config/config.yaml`
2. Update `daily_limit` and `monthly_limit`
3. Run `make update`

**Change Daily Report Time**:
1. Edit `config/config.yaml`
2. Update `schedule_hour_utc` (0-23)
3. Run `cdk deploy ChatbotMonitorDailyCostStack`

**Disable Daily Reports**:
1. Edit `config/config.yaml`
2. Set `daily_report.enabled: false`
3. Run `make deploy`

### Integrate with Other Infrastructure

See [Integration Guide](integration-guide.md) for examples:
- ECS service monitoring
- Lambda error alerts
- RDS database health
- S3 event notifications
- Custom application metrics

### Monitoring and Maintenance

**Daily**: Check Slack channels for cost trends

**Weekly**: Review CloudWatch dashboard for anomalies

**Monthly**: Adjust budgets based on actual usage patterns

**As Needed**: Run `make update` after config changes

---

## Troubleshooting

For common issues and solutions, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md).

**Quick Checklist**:
- ✅ AWS credentials configured correctly
- ✅ Slack workspace authorized in AWS Console
- ✅ Amazon Q Developer bot invited to both channels
- ✅ Slack IDs in config.yaml are correct
- ✅ AWS Account ID in config.yaml matches your account
- ✅ All 5 stacks deployed successfully

---

## Getting Help

- **Documentation**: Check other docs in `docs/` folder
- **Issues**: [GitHub Issues](https://github.com/your-username/aws-chatbot-slack-monitor/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-username/aws-chatbot-slack-monitor/discussions)

---

**Congratulations!** 🎉 Your AWS cost monitoring is now live!
