# Deployment Guide - AI Alert Intelligence System

## Quick Start

**Deploy Phase 1 in 30 minutes:**

```bash
# 1. Clone and configure
git clone https://github.com/your-username/aws-alert-intelligence.git
cd aws-alert-intelligence
cp config/.env.example .env
vim config/config.yaml  # Update account ID, Slack IDs

# 2. Deploy secrets
python scripts/deploy-secrets.py

# 3. Deploy infrastructure
make deploy

# 4. Test
make test-alert
```

---

## Prerequisites

### Required

- ✅ AWS Account with admin access
- ✅ AWS CLI configured
- ✅ Python 3.12+
- ✅ Node.js 18+ (for CDK)
- ✅ Slack workspace with admin access

### Optional

- DevContainer support (PyCharm/VS Code)
- Docker for local testing

---

## Step-by-Step Deployment

### 1. AWS Setup

#### Create IAM Deployment User

```bash
# Run the IAM setup script
bash scripts/setup-aws-iam-user.sh

# This creates:
# - IAM user: aws-alert-intelligence-dev
# - Required policies for deployment
# - Access keys (saved to .env)
```

**Required Permissions:**
- CloudFormation (full)
- Lambda (create/update functions)
- IAM (create roles for Lambda)
- SNS (create topics)
- EventBridge (create rules)
- Secrets Manager (create/read secrets)
- Bedrock (invoke models)

#### Bootstrap CDK

```bash
# First time only
cdk bootstrap aws://ACCOUNT_ID/us-east-1

# Example:
cdk bootstrap aws://123456789012/us-east-1
```

---

### 2. Slack Setup

#### Create Slack Webhooks

**Critical Alerts Channel:**
1. Create channel: `#aws-critical-alerts`
2. Add Slack app: Incoming Webhooks
3. Copy webhook URL: `https://hooks.slack.com/services/T.../B.../xxx`

**Heartbeat Channel:**
1. Create channel: `#aws-heartbeat`
2. Add Slack app: Incoming Webhooks
3. Copy webhook URL: `https://hooks.slack.com/services/T.../B.../yyy`

#### Get Slack IDs

**Workspace ID:**
```
Open Slack in browser
URL: https://app.slack.com/client/T01234ABCDE/...
                                  ^^^^^^^^^^^
                                  Workspace ID
```

**Channel IDs:**
```
Right-click channel → View channel details → Copy Channel ID
```

---

### 3. Configuration

#### Edit `.env`

```bash
cp config/.env.example .env
vim .env
```

**Required values:**
```bash
# AWS Configuration
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
AWS_DEFAULT_REGION=us-east-1
CDK_DEFAULT_ACCOUNT=123456789012
CDK_DEFAULT_REGION=us-east-1

# Slack Webhooks (will be deployed to Secrets Manager)
SLACK_CRITICAL_WEBHOOK=https://hooks.slack.com/services/T.../B.../xxx
SLACK_HEARTBEAT_WEBHOOK=https://hooks.slack.com/services/T.../B.../yyy

# Optional: Email notifications
NOTIFICATION_EMAILS=team@example.com
```

#### Edit `config/config.yaml`

```yaml
# AWS Configuration
aws:
  region: us-east-1
  account_id: "123456789012"  # YOUR account ID
  stack_prefix: AlertIntel

# LLM Configuration
llm:
  provider: bedrock
  model_id: "anthropic.claude-3-5-sonnet-20250514-v2:0"
  temperature: 0.3
  max_tokens: 2000

# Slack Configuration
slack:
  workspace_id: T01234ABCDE     # YOUR workspace ID
  critical_channel_id: C012345  # YOUR critical channel ID
  heartbeat_channel_id: C678901 # YOUR heartbeat channel ID

# Analysis Rules
analysis_rules:
  analyze_budget_warning: true        # ≥80%
  analyze_budget_critical: true       # ≥100%
  analyze_daily_budget_report: false  # Skip AI
  analyze_cloudwatch_alarm_error: true
  analyze_cloudwatch_alarm_warning: true
  analyze_cloudwatch_alarm_info: false

# Budget Configuration (from existing setup)
budgets:
  daily_limit: 10.00
  monthly_limit: 300.00
  monthly_threshold_warning: 80
  monthly_threshold_critical: 100
  currency: USD
```

---

### 4. Deploy Secrets

```bash
# Deploy Slack webhooks to Secrets Manager
python scripts/deploy-secrets.py \
  --critical-webhook "$SLACK_CRITICAL_WEBHOOK" \
  --heartbeat-webhook "$SLACK_HEARTBEAT_WEBHOOK"
```

**What this creates:**
```
AWS Secrets Manager:
  aws-alert-intel/prod/slack-critical
  aws-alert-intel/prod/slack-heartbeat
```

**Verify:**
```bash
aws secretsmanager list-secrets | grep aws-alert-intel
```

---

### 5. Deploy Infrastructure

#### Option A: Deploy Everything

```bash
make deploy
```

This deploys:
- SNS Stack (topics for routing)
- Alert Analyzer Stack (Phase 1 Lambda + LangGraph)
- Budget Stack (existing budgets)
- Chatbot Stack (existing AWS Chatbot - optional, can remove)
- Monitoring Stack (existing dashboards)

#### Option B: Deploy Only AI Alert System

```bash
cdk deploy AlertIntelSnsStack
cdk deploy AlertIntelAlertAnalyzerStack
```

**Expected Output:**
```
✨ Synthesis time: 5s

AlertIntelSnsStack
AlertIntelSnsStack: deploying...
✅  AlertIntelSnsStack

Outputs:
AlertIntelSnsStack.CriticalTopicArn = arn:aws:sns:...
AlertIntelSnsStack.HeartbeatTopicArn = arn:aws:sns:...

AlertIntelAlertAnalyzerStack
AlertIntelAlertAnalyzerStack: deploying...
✅  AlertIntelAlertAnalyzerStack

Outputs:
AlertIntelAlertAnalyzerStack.FunctionArn = arn:aws:lambda:...

✨ Deployment time: 2m 15s
```

---

### 6. Connect Budget Alerts to AI System

#### Update Budget Notifications

**Current setup** probably uses AWS Chatbot SNS topics.

**New setup** sends budget alerts to AI analyzer:

```bash
# Get new SNS topic ARN
CRITICAL_TOPIC=$(aws cloudformation describe-stacks \
  --stack-name AlertIntelSnsStack \
  --query 'Stacks[0].Outputs[?OutputKey==`CriticalTopicArn`].OutputValue' \
  --output text)

# Update budget to use new topic
# (This would be done via CDK or AWS Console)
```

**OR** - Keep existing budgets, create EventBridge rule:

```yaml
# In CDK
rule = events.Rule(
    self,
    "BudgetAlertRouter",
    event_pattern=events.EventPattern(
        source=["aws.budgets"],
        detail_type=["AWS Budget Notification"],
        detail={
            "thresholdPercentage": [{"numeric": [">=", 80]}]
        }
    )
)

rule.add_target(targets.SnsTopic(critical_topic))
```

---

### 7. Test the System

#### Test Budget Alert (Simulated)

```bash
# Send test budget event
make test-budget-alert

# Or manually:
aws sns publish \
  --topic-arn $CRITICAL_TOPIC \
  --subject "Budget Alert Test" \
  --message file://tests/fixtures/budget_warning.json
```

#### Test CloudWatch Alarm

```bash
# Create test alarm that triggers immediately
make test-cloudwatch-alarm

# Or manually:
aws cloudwatch put-metric-alarm \
  --alarm-name TestAlarm-DeleteMe \
  --alarm-description "Test for AI alert system" \
  --metric-name CPUUtilization \
  --namespace AWS/EC2 \
  --statistic Average \
  --period 300 \
  --threshold 0 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 1 \
  --alarm-actions $CRITICAL_TOPIC

# Trigger it
aws cloudwatch set-alarm-state \
  --alarm-name TestAlarm-DeleteMe \
  --state-value ALARM \
  --state-reason "Testing AI alert system"
```

#### Check Slack

Within 1-2 minutes, you should see:
- 🔴 Formatted message in `#aws-critical-alerts`
- Root cause analysis
- Diagnostic commands
- Remediation suggestions

#### Check CloudWatch Logs

```bash
# View Lambda execution logs
aws logs tail /aws/lambda/AlertIntel-AlertAnalyzer --follow
```

---

### 8. Integration with Existing System

#### Replace AWS Chatbot (Optional)

**If you want to fully replace the old system:**

1. **Update SNS subscriptions:**
   ```bash
   # Remove AWS Chatbot subscriptions
   # Add AlertAnalyzer Lambda subscriptions
   ```

2. **Keep budget/alarm creation:**
   - Budgets still work the same
   - CloudWatch alarms still work
   - Just route to new SNS topics

3. **Remove old Chatbot stack:**
   ```bash
   cdk destroy ChatbotMonitorChatbotStack
   ```

#### Hybrid Approach (Recommended Initially)

**Keep both systems during transition:**

- Old system: AWS Chatbot for basic notifications
- New system: AI analysis for critical alerts

**Route alerts:**
- Critical (≥80% budget) → AI analyzer
- Routine (daily reports) → Old system

**Benefits:**
- Gradual migration
- Fallback if AI system has issues
- Compare outputs side-by-side

---

## Project Structure (After Deployment)

```
aws-alert-intelligence/
├── cdk/
│   ├── app.py
│   ├── stacks/
│   │   ├── sns_stack.py                # SNS topics
│   │   ├── alert_analyzer_stack.py     # NEW: AI alert analyzer
│   │   ├── budget_stack.py             # Existing budgets
│   │   └── ...
│   │
│   └── lambda/
│       └── alert_analyzer/             # NEW: Phase 1 Lambda
│           ├── index.py                # Handler
│           ├── agents/
│           │   └── alert_workflow.py   # LangGraph workflow
│           ├── tools/
│           │   ├── cost_tools.py
│           │   ├── compute_tools.py
│           │   ├── logging_tools.py
│           │   └── infrastructure_tools.py
│           └── requirements.txt
│
├── config/
│   ├── config.yaml        # Main config (edit this!)
│   └── .env               # Secrets (gitignored)
│
├── scripts/
│   ├── deploy-secrets.py
│   ├── setup-aws-iam-user.sh
│   └── test-alert.py
│
├── tests/
│   ├── test_workflow.py
│   ├── test_tools.py
│   └── fixtures/
│       ├── budget_warning.json
│       └── cloudwatch_alarm.json
│
├── phase2-docs/           # This documentation!
│   ├── OVERVIEW.md
│   ├── ARCHITECTURE.md
│   ├── PHASE1.md
│   ├── TOOLS.md
│   ├── COST_ANALYSIS.md
│   └── DEPLOYMENT.md      # This file
│
├── Makefile
└── README.md
```

---

## Makefile Commands

```makefile
# Deployment
deploy:          # Deploy all stacks
deploy-secrets:  # Deploy Slack webhooks to Secrets Manager
update:          # Update existing deployment
destroy:         # Destroy all stacks (DANGEROUS!)

# Testing
test-alert:      # Send test alert
test-budget-alert: # Send test budget alert
test-cloudwatch-alarm: # Create test CloudWatch alarm
validate:        # Run validation tests

# Development
synth:           # Synthesize CloudFormation templates
diff:            # Show deployment changes
lint:            # Lint Python code
format:          # Format Python code with black

# Monitoring
logs:            # Tail Lambda logs
metrics:         # Show CloudWatch metrics
costs:           # Show current month costs
```

---

## Troubleshooting

### Deployment Fails

**"Stack already exists":**
```bash
# Update instead of create
make update
```

**"Insufficient permissions":**
```bash
# Re-run IAM setup
bash scripts/setup-aws-iam-user.sh

# Verify permissions
aws iam get-user-policy --user-name aws-alert-intelligence-dev --policy-name DeploymentPolicy
```

**"Secret not found":**
```bash
# Redeploy secrets
python scripts/deploy-secrets.py --critical-webhook "..." --heartbeat-webhook "..."
```

### No Slack Messages

**Check webhook URLs:**
```bash
# Test webhook manually
curl -X POST https://hooks.slack.com/services/T.../B.../xxx \
  -H 'Content-Type: application/json' \
  -d '{"text":"Test message"}'
```

**Check Lambda logs:**
```bash
aws logs tail /aws/lambda/AlertIntel-AlertAnalyzer --follow
```

**Check SNS subscriptions:**
```bash
aws sns list-subscriptions-by-topic --topic-arn arn:aws:sns:...
```

### Lambda Timeout

**Increase timeout in CDK:**
```python
# cdk/stacks/alert_analyzer_stack.py

alert_analyzer = lambda_.Function(
    self,
    "AlertAnalyzer",
    timeout=Duration.seconds(90),  # Increase from 60
    ...
)
```

**Redeploy:**
```bash
cdk deploy AlertIntelAlertAnalyzerStack
```

### LLM Errors

**"Rate limit exceeded":**
- Bedrock has default quotas
- Request quota increase in AWS Console

**"Invalid model ID":**
- Verify model ID in config.yaml
- Check Bedrock model access in AWS Console

**High costs:**
- Check CloudWatch metrics for token usage
- Reduce token count in prompts
- Consider using Claude Haiku for simpler queries

---

## Monitoring

### CloudWatch Dashboard

**Create custom dashboard:**
```bash
# View existing dashboards
aws cloudwatch list-dashboards

# Or create via CDK in monitoring_stack.py
```

**Key metrics to monitor:**
- Lambda invocations
- Lambda errors
- Lambda duration
- Estimated LLM costs (based on logs)

### Cost Tracking

**Set up budget for AI system:**
```yaml
# In config/config.yaml
budgets:
  ai_alert_system:
    monthly_limit: 15.00  # $15/month ceiling
    warning_threshold: 80  # Alert at $12
```

**Track costs:**
```bash
# Get current month spend
make costs

# Or manually:
aws ce get-cost-and-usage \
  --time-period Start=2025-10-01,End=2025-10-31 \
  --granularity MONTHLY \
  --metrics UnblendedCost \
  --filter file://cost-filter.json
```

### Alerts on Alerts

**Meta-monitoring - alert if the alert system fails:**

```yaml
# CloudWatch alarm for alert system
alert_system_health:
  metric: Lambda Errors
  threshold: > 3 errors in 5 minutes
  action: Send to ops-team Slack channel
```

---

## Updating

### Configuration Changes

**Update config.yaml:**
```bash
vim config/config.yaml
# Change analysis rules, LLM settings, etc.

# Redeploy (quick, just updates Lambda env vars)
cdk deploy AlertIntelAlertAnalyzerStack
```

### Code Changes

**Update Lambda code:**
```bash
# Edit files in lambda/alert_analyzer/
vim lambda/alert_analyzer/agents/alert_workflow.py

# Redeploy
cdk deploy AlertIntelAlertAnalyzerStack

# CDK automatically packages and uploads new code
```

### Adding New Tools

**Add tool:**
```python
# lambda/alert_analyzer/tools/new_tools.py

@tool
def my_new_tool(param: str) -> dict:
    """New tool description."""
    # Implementation
    return {"result": "..."}
```

**Register:**
```python
# lambda/alert_analyzer/tools/__init__.py

from .new_tools import my_new_tool

ALL_TOOLS.append(my_new_tool)
```

**Redeploy:**
```bash
cdk deploy AlertIntelAlertAnalyzerStack
```

---

## Rollback

### To Previous Version

**CDK doesn't have built-in rollback, but:**

```bash
# Option 1: Git revert
git log  # Find previous commit
git checkout <commit-hash>
cdk deploy AlertIntelAlertAnalyzerStack

# Option 2: Use CloudFormation console
# AWS Console → CloudFormation → Stack → Actions → Rollback
```

### Complete Removal

```bash
# Remove all infrastructure
make destroy

# Or selectively:
cdk destroy AlertIntelAlertAnalyzerStack
cdk destroy AlertIntelSnsStack

# Delete secrets
aws secretsmanager delete-secret \
  --secret-id aws-alert-intel/prod/slack-critical \
  --force-delete-without-recovery
```

---

## Production Checklist

Before going live:

- [ ] Tested with real alerts (budget, CloudWatch)
- [ ] Verified Slack messages are formatted correctly
- [ ] Reviewed LLM analysis quality (≥80% helpful)
- [ ] Set up cost budget alerts for AI system
- [ ] Documented any custom tools added
- [ ] Configured CloudWatch dashboard
- [ ] Trained team on how to interpret AI suggestions
- [ ] Set up monitoring alerts for system failures
- [ ] Backed up configuration files
- [ ] Documented runbook for common issues

---

## Next Steps

### After Successful Phase 1 Deployment:

1. **Monitor for 1 week**
   - Collect feedback on AI analysis quality
   - Check costs vs. estimates
   - Identify false positives

2. **Tune configuration**
   - Adjust analysis rules
   - Optimize prompts
   - Add/remove tools as needed

3. **Plan Phase 2** (if desired)
   - Interactive Slack bot
   - Conversation history
   - Multi-agent workflows

---

**Status:** Deployment Guide Complete
**Ready for:** Production deployment
**Support:** See docs/TROUBLESHOOTING.md
