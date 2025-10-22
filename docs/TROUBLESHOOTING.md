# Troubleshooting Guide

This guide helps you diagnose and fix common issues when deploying and using the AWS Chatbot Slack Monitor.

---

## Table of Contents

1. [Quick Diagnostics](#quick-diagnostics)
2. [Deployment Issues](#deployment-issues)
3. [AWS Chatbot / Slack Integration](#aws-chatbot--slack-integration)
4. [Budget Alerts Not Working](#budget-alerts-not-working)
5. [CloudWatch Dashboard Issues](#cloudwatch-dashboard-issues)
6. [Daily Cost Report Issues](#daily-cost-report-issues)
7. [DevContainer Issues](#devcontainer-issues)
8. [AWS CDK Issues](#aws-cdk-issues)
9. [Configuration Problems](#configuration-problems)
10. [Getting Help](#getting-help)

---

## Quick Diagnostics

Run these commands to check your setup:

```bash
# Check AWS credentials and account
aws sts get-caller-identity

# Verify CDK is installed
cdk --version

# Check Python version
python --version  # Should be 3.12+

# List deployed stacks
cdk list

# Check AWS region
aws configure get region

# Verify config file exists
cat config/config.yaml

# Check if stacks are deployed
aws cloudformation list-stacks --stack-status-filter CREATE_COMPLETE UPDATE_COMPLETE
```

---

## Deployment Issues

### Error: "Need to perform AWS calls for account X, but no credentials configured"

**Cause**: AWS credentials not configured or expired.

**Solution**:
```bash
# Configure AWS credentials
aws configure

# Verify credentials work
aws sts get-caller-identity

# If using IAM user, check access keys are valid
aws iam get-user
```

### Error: "This stack uses assets, so the toolkit stack must be deployed"

**Cause**: AWS CDK not bootstrapped in your account/region.

**Solution**:
```bash
# Bootstrap CDK (replace with your account ID)
cdk bootstrap aws://123456789012/us-east-1

# Or use make command
make bootstrap
```

### Error: "CREATE_FAILED: User: arn:aws:iam::XXX:user/YYY is not authorized to perform: budgets:CreateBudget"

**Cause**: IAM user lacks required permissions.

**Solution**:
```bash
# Re-run the permissions setup script
bash scripts/aws-permissions-config.sh

# Or manually add the required policy to your IAM user in AWS Console:
# - PowerUserAccess (for full deployment)
# - OR specific policies for Budgets, SNS, Chatbot, CloudWatch, Lambda, EventBridge
```

### Error: "Stack named ChatbotMonitorSnsStack already exists"

**Cause**: Stack already deployed.

**Solution**:
```bash
# If you want to update the stack
make update

# If you want to see what would change
make diff

# If you want to completely redeploy
make destroy  # CAUTION: This deletes everything
make deploy
```

### Deployment Hangs or Times Out

**Cause**: Network issues, AWS service problems, or resource conflicts.

**Solution**:
```bash
# Cancel the deployment (Ctrl+C)
# Check CloudFormation console for specific errors
aws cloudformation describe-stack-events --stack-name ChatbotMonitorSnsStack --max-items 10

# Try deploying one stack at a time
cdk deploy ChatbotMonitorSnsStack
cdk deploy ChatbotMonitorBudgetStack
cdk deploy ChatbotMonitorChatbotStack
cdk deploy ChatbotMonitorMonitoringStack
cdk deploy ChatbotMonitorDailyCostStack
```

---

## AWS Chatbot / Slack Integration

### No Notifications Appearing in Slack

**Checklist**:
1. ✅ Slack workspace authorized in AWS Chatbot Console?
   - Go to: https://console.aws.amazon.com/chatbot/
   - Verify workspace shows as "Authorized"
   - If not, click "Configure new client" → Slack → Authorize

2. ✅ Amazon Q Developer bot invited to channels?
   ```
   /invite @Amazon Q Developer
   ```
   - Try in BOTH #aws-critical-alerts and #aws-heartbeat channels

3. ✅ Slack Channel IDs correct in config.yaml?
   ```bash
   # Verify IDs match what's in Slack
   cat config/config.yaml | grep -A3 "slack:"
   ```
   - Channel IDs start with "C" (e.g., C09N63G6F3J)
   - Workspace ID starts with "T" (e.g., T09MR3DRVG8)

4. ✅ Test with CloudWatch alarm (not plain SNS)?
   ```bash
   make validate
   ```
   - Wait 1-2 minutes
   - Check #aws-critical-alerts channel
   - Delete test alarm after: `aws cloudwatch delete-alarms --alarm-names ChatbotTest-DeleteMe`

### Error: "The Slack channel could not be found in the authorized workspace"

**Cause**: Channel ID is incorrect or bot not invited to channel.

**Solution**:
1. Get the correct Channel ID:
   - Right-click channel name in Slack
   - Click "View channel details"
   - Scroll to bottom → Copy Channel ID

2. Update config.yaml:
   ```yaml
   slack:
     workspace_id: T09MR3DRVG8
     critical_channel_id: C0123456789  # Update this
     heartbeat_channel_id: C9876543210  # Update this
   ```

3. Redeploy:
   ```bash
   cdk deploy ChatbotMonitorChatbotStack
   ```

4. Invite bot to channel:
   ```
   /invite @Amazon Q Developer
   ```

### Notifications Go to Wrong Channel

**Cause**: SNS topic ARN mismatch between stacks.

**Solution**:
```bash
# Check SNS topic ARNs
aws sns list-topics | grep ChatbotMonitor

# Verify budget subscriptions
aws sns list-subscriptions | grep ChatbotMonitor

# Check which channel is subscribed to which topic
aws chatbot describe-slack-channel-configurations
```

**Fix**: Ensure budget notifications use correct SNS topic:
- Daily budget → heartbeat topic
- Monthly 80% → heartbeat topic
- Monthly 100% → critical topic

### Error: "Cannot find Slack workspace"

**Cause**: Slack workspace not authorized in AWS Chatbot.

**Solution**:
1. Go to AWS Chatbot Console: https://console.aws.amazon.com/chatbot/
2. Click "Configure new client"
3. Select "Slack"
4. Sign in to Slack and authorize
5. Verify workspace appears in list
6. Redeploy Chatbot stack:
   ```bash
   cdk deploy ChatbotMonitorChatbotStack
   ```

---

## Budget Alerts Not Working

### No Budget Alert Emails Received

**Cause**: SNS email subscriptions not confirmed.

**Solution**:
1. Check your email inbox (including spam folder)
2. Look for "AWS Notification - Subscription Confirmation"
3. Click the confirmation link
4. Verify subscription:
   ```bash
   aws sns list-subscriptions-by-topic --topic-arn arn:aws:sns:us-east-1:123456789012:ChatbotMonitor-critical-alerts
   ```
   - Status should be "Confirmed", not "PendingConfirmation"

### Budget Alerts Not Triggering at Right Threshold

**Cause**: Budget configuration incorrect.

**Solution**:
```bash
# Check budget configuration
aws budgets describe-budgets --account-id YOUR_ACCOUNT_ID

# Verify thresholds in config.yaml
cat config/config.yaml | grep -A10 "budgets:"

# Update and redeploy
vim config/config.yaml
make update
```

**Expected Configuration**:
- Daily budget: 100% threshold → heartbeat channel
- Monthly budget: 80% threshold → heartbeat channel
- Monthly budget: 100% threshold → critical channel

### Budget Shows Wrong Amount

**Cause**: config.yaml not updated before deployment.

**Solution**:
1. Edit config.yaml:
   ```yaml
   budgets:
     daily_limit: 10.00      # Change to your amount
     monthly_limit: 300.00   # Change to your amount
   ```

2. Redeploy budget stack:
   ```bash
   cdk deploy ChatbotMonitorBudgetStack
   ```

3. Verify in AWS Console:
   - https://console.aws.amazon.com/billing/home#/budgets

---

## CloudWatch Dashboard Issues

### Dashboard Shows No Data

**Cause**: Billing metrics take 6-24 hours to populate for new accounts.

**Solution**:
- Wait 24 hours after first deployment
- Billing metrics are only available in **us-east-1** region
- Verify region in config.yaml:
  ```yaml
  aws:
    region: us-east-1  # Must be us-east-1 for billing metrics
  ```

### Dashboard Not Found

**Cause**: Monitoring stack not deployed or failed.

**Solution**:
```bash
# Check if stack exists
aws cloudformation describe-stacks --stack-name ChatbotMonitorMonitoringStack

# If not deployed, deploy it
cdk deploy ChatbotMonitorMonitoringStack

# Get dashboard name
aws cloudwatch list-dashboards | grep ChatbotMonitor
```

### Metrics Show Zero or Incorrect Values

**Cause**: AWS hasn't recorded billing data yet, or wrong time range selected.

**Solution**:
- Billing metrics update every 6 hours
- Check AWS Cost Explorer for same time period: https://console.aws.amazon.com/cost-management/home#/cost-explorer
- Ensure dashboard time range is set to "Last 30 days" or "Month to date"

---

## Daily Cost Report Issues

### No Daily Cost Reports in Slack

**Checklist**:
1. ✅ Daily report enabled in config?
   ```yaml
   daily_report:
     enabled: true
     schedule_hour_utc: 8
   ```

2. ✅ DailyCostStack deployed?
   ```bash
   aws cloudformation describe-stacks --stack-name ChatbotMonitorDailyCostStack
   ```

3. ✅ Lambda function exists?
   ```bash
   aws lambda list-functions | grep DailyCostFunction
   ```

4. ✅ EventBridge rule enabled?
   ```bash
   aws events list-rules | grep DailyCost
   ```

### Test Daily Report Manually

```bash
# Find Lambda function name
aws lambda list-functions | grep DailyCostFunction

# Invoke function manually (replace with actual function name)
aws lambda invoke --function-name ChatbotMonitorDailyCostSt-DailyCostFunctionXXXXX-YYYY /tmp/output.json

# Check output
cat /tmp/output.json

# Check Slack channel for report
```

### Daily Report Shows Wrong Time

**Cause**: Schedule hour is in UTC, not local time.

**Solution**:
1. Determine your desired local time in UTC:
   - 8 AM EST = 13:00 UTC
   - 8 AM PST = 16:00 UTC
   - 8 AM GMT = 8:00 UTC

2. Update config.yaml:
   ```yaml
   daily_report:
     schedule_hour_utc: 13  # For 8 AM EST
   ```

3. Redeploy:
   ```bash
   cdk deploy ChatbotMonitorDailyCostStack
   ```

### Error: "User is not authorized to perform: ce:GetCostAndUsage"

**Cause**: Lambda execution role lacks Cost Explorer permissions.

**Solution**:
```bash
# This should be automatic, but verify IAM role exists
aws iam get-role --role-name ChatbotMonitorDailyCostStack-DailyCostFunctionRole

# Check if the role has Cost Explorer permissions
aws iam list-role-policies --role-name ChatbotMonitorDailyCostStack-DailyCostFunctionRole

# If missing, redeploy the stack
cdk deploy ChatbotMonitorDailyCostStack --force
```

---

## DevContainer Issues

### Container Won't Start in PyCharm

**Cause**: Docker not running or PyCharm plugin issue.

**Solution**:
1. Verify Docker Desktop is running
2. Check Docker is accessible:
   ```bash
   docker ps
   ```
3. In PyCharm: File → Settings → Plugins → Ensure "Dev Containers" plugin installed
4. Try rebuilding: PyCharm → Tools → Dev Containers → Rebuild Container

### Container Won't Start in VS Code

**Cause**: Dev Containers extension not installed or Docker issue.

**Solution**:
1. Install "Dev Containers" extension in VS Code
2. Check Docker Desktop is running
3. Open Command Palette (Cmd/Ctrl+Shift+P)
4. Run: "Dev Containers: Rebuild Container"
5. Check logs: View → Output → Select "Dev Containers" from dropdown

### Permission Denied Errors in Container

**Cause**: File ownership issues or volume mount problems.

**Solution**:
```bash
# Inside container, check current user
whoami  # Should be "developer"

# Check file ownership
ls -la /workspace

# Fix ownership if needed (run on host machine)
sudo chown -R 1000:1000 .
```

### Container Build Fails

**Cause**: Network issues, base image problems, or Dockerfile errors.

**Solution**:
1. Check Docker logs for specific error
2. Try rebuilding with no cache:
   ```bash
   # In VS Code: Cmd/Ctrl+Shift+P → "Dev Containers: Rebuild Without Cache"
   # In PyCharm: Similar option in Dev Containers menu
   ```
3. Check internet connection
4. Try pulling base image manually:
   ```bash
   docker pull python:3.12-slim
   ```

---

## AWS CDK Issues

### Error: "cdk: command not found"

**Cause**: AWS CDK not installed.

**Solution**:
```bash
# Install CDK globally
npm install -g aws-cdk

# Verify installation
cdk --version

# If npm not found, install Node.js first
```

### Error: "Cannot find module 'aws-cdk-lib'"

**Cause**: Python dependencies not installed.

**Solution**:
```bash
# Install all Python dependencies
pip install -r requirements.txt

# Verify installation
pip list | grep aws-cdk
```

### Error: "This CDK CLI is not compatible with the CDK library used by your application"

**Cause**: Version mismatch between CDK CLI and Python libraries.

**Solution**:
```bash
# Check versions
cdk --version
pip show aws-cdk-lib

# Upgrade CDK CLI to match library version
npm install -g aws-cdk@latest

# Or downgrade library to match CLI version
pip install aws-cdk-lib==X.X.X  # Match CLI version
```

### Error: "NoSuchBucket: The specified bucket does not exist"

**Cause**: CDK bootstrap not run in target region.

**Solution**:
```bash
# Bootstrap the region (replace with your account and region)
cdk bootstrap aws://123456789012/us-east-1

# Verify bootstrap stack exists
aws cloudformation describe-stacks --stack-name CDKToolkit
```

---

## Configuration Problems

### How to Find Slack Workspace ID

**In Web Browser**:
1. Open Slack in browser
2. Look at URL: `https://app.slack.com/client/T01234ABCDE/...`
3. The part after `/client/` is your Workspace ID
4. Format: `T0123456789` (starts with `T`)

### How to Find Slack Channel ID

**For Each Channel**:
1. Right-click channel name in Slack
2. Click "View channel details"
3. Scroll to bottom of modal
4. Copy the Channel ID
5. Format: `C0123456789` (starts with `C`)

### How to Find AWS Account ID

```bash
# Using AWS CLI
aws sts get-caller-identity --query Account --output text

# Or from AWS Console
# Click your username → Account (top right)
```

### Invalid YAML Syntax in config.yaml

**Symptoms**: Deployment fails with "YAMLError" or "ParserError"

**Solution**:
```bash
# Validate YAML syntax
python -c "import yaml; yaml.safe_load(open('config/config.yaml'))"

# Common issues:
# - Incorrect indentation (use spaces, not tabs)
# - Missing quotes around numbers that should be strings
# - Colons in values need quotes

# Example CORRECT syntax:
aws:
  account_id: "123456789012"  # Quoted because it's a string, not number
```

---

## Getting Help

### Before Asking for Help

1. **Check logs**:
   ```bash
   # CloudFormation stack events
   aws cloudformation describe-stack-events --stack-name ChatbotMonitorSnsStack --max-items 20

   # Lambda function logs
   aws logs tail /aws/lambda/ChatbotMonitorDailyCostSt-DailyCostFunction --follow

   # CDK synthesis output
   cdk synth 2>&1 | less
   ```

2. **Verify configuration**:
   ```bash
   # Check all config values
   cat config/config.yaml

   # Verify AWS credentials
   aws sts get-caller-identity

   # Check region
   aws configure get region
   ```

3. **Run diagnostics**:
   ```bash
   # Test Slack notifications
   make validate

   # Check deployed stacks
   aws cloudformation list-stacks --stack-status-filter CREATE_COMPLETE UPDATE_COMPLETE

   # Verify budgets exist
   aws budgets describe-budgets --account-id YOUR_ACCOUNT_ID
   ```

### Where to Get Help

**GitHub Issues**:
- Bug reports: https://github.com/your-username/aws-chatbot-slack-monitor/issues
- Feature requests: Use issue templates
- Include: AWS region, CDK version, error messages, config.yaml (sanitized)

**GitHub Discussions**:
- Questions: https://github.com/your-username/aws-chatbot-slack-monitor/discussions
- Best practices and tips
- Community support

**AWS Support**:
- AWS Chatbot issues: https://console.aws.amazon.com/support/
- Billing/budget questions: AWS Support Center
- CDK issues: https://github.com/aws/aws-cdk/issues

### Information to Include When Reporting Issues

1. **Environment**:
   ```bash
   cdk --version
   python --version
   aws --version
   aws configure get region
   ```

2. **Error messages**: Full stack trace or CloudFormation error

3. **Config** (sanitized):
   ```yaml
   # Remove actual account IDs, Slack IDs, etc.
   # But show structure and types
   ```

4. **Steps to reproduce**: What commands did you run?

5. **Expected vs actual behavior**: What should happen vs what does happen

---

## Common Quick Fixes

| Symptom | Quick Fix |
|---------|-----------|
| No Slack notifications | Run `make validate` to test with CloudWatch alarm |
| Budget not found | Check AWS Account ID matches in config.yaml |
| Dashboard empty | Wait 24 hours, ensure region is us-east-1 |
| CDK command not found | `npm install -g aws-cdk` |
| Permission denied | Run `bash scripts/aws-permissions-config.sh` |
| Stack already exists | Run `make diff` then `make update` |
| Container won't start | Ensure Docker Desktop is running, rebuild container |
| Daily report not arriving | Check `daily_report.enabled: true` in config.yaml |
| Wrong Slack channel | Verify Channel IDs in config.yaml, invite bot to channel |
| Deployment hangs | Check CloudFormation console for specific error |

---

**Still stuck?** Open an issue with full details: https://github.com/your-username/aws-chatbot-slack-monitor/issues
