# Slack Setup Guide for AWS Chatbot

This guide walks you through setting up Slack integration for the AWS Chatbot Slack Monitor project.

## Prerequisites

- Slack workspace with admin access
- AWS account with deployment permissions
- Project deployed (at least the SNS stack)

## Step 1: Create Slack Channels

Create two Slack channels in your workspace:

### Critical Alerts Channel (Low Noise)
```
Name: #aws-critical-alerts (or your preference)
Purpose: Budget overruns and severe infrastructure issues
Members: Team leads, on-call engineers
Noise Level: LOW - only critical alerts
```

### Heartbeat Channel (Monitoring)
```
Name: #aws-heartbeat (or your preference)
Purpose: Daily reports, warnings, and system health
Members: Development team, interested stakeholders
Noise Level: MEDIUM - may be noisy
```

## Step 2: Get Slack IDs

You need three IDs from Slack:

### 2.1 Get Workspace ID

1. Open Slack in your web browser
2. Look at the URL: `https://app.slack.com/client/T01234ABCDE/...`
3. The part after `/client/` and before the next `/` is your Workspace ID
4. Format: `T01234ABCDE` (starts with T)

**Example URL**:
```
https://app.slack.com/client/T01234ABCDE/C56789FGHIJ
                              └─────────┘
                              Workspace ID
```

### 2.2 Get Channel IDs

For each channel:

1. Right-click on the channel name in Slack
2. Select **"View channel details"**
3. Scroll to the bottom
4. Copy the **Channel ID**
5. Format: `C01234ABCDE` (starts with C)

## Step 3: Configure .env File

Copy the example environment file and add your Slack IDs:

```bash
# In your project root
cp config/.env.example .env
```

Edit `.env` and add your Slack configuration:

```bash
# Slack Configuration
SLACK_WORKSPACE_ID=T01234ABCDE              # Your workspace ID (from step 2.1)
SLACK_CRITICAL_CHANNEL_ID=C01234ABCDE       # Critical channel ID
SLACK_HEARTBEAT_CHANNEL_ID=C56789FGHIJ     # Heartbeat channel ID

# Email Notifications (optional)
NOTIFICATION_EMAILS=team@example.com,admin@example.com

# AWS Credentials (from aws-permissions-config.sh)
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
AWS_DEFAULT_REGION=us-east-1
CDK_DEFAULT_ACCOUNT=123456789012
CDK_DEFAULT_REGION=us-east-1
```

**Important**: Never commit the `.env` file to git! It's already in `.gitignore`.

## Step 4: Deploy Secrets to AWS

Deploy your Slack configuration to AWS Secrets Manager:

```bash
make deploy-secrets
```

Or directly:
```bash
python scripts/deploy-secrets.py
```

This will:
1. Read your `.env` file
2. Validate the Slack IDs
3. Create/update a secret in AWS Secrets Manager
4. Verify the deployment

**Expected output**:
```
==================================================================
AWS Secrets Manager - Deploy Slack Configuration
==================================================================

✓ Loaded environment from /workspace/.env
✓ All required secrets are present and valid
  Secret name: aws-chatbot-monitor/prod/slack-config
✓ Authenticated to AWS as: arn:aws:iam::123456789012:user/...
  Account: 123456789012
  Region: us-east-1

  Deploying secrets to AWS Secrets Manager...
✓ Created secret: aws-chatbot-monitor/prod/slack-config

✓ Secret verification:
  - Workspace ID: T01234ABCDE
  - Critical Channel ID: C01234ABCDE
  - Heartbeat Channel ID: C56789FGHIJ

==================================================================
✓ Secrets Deployed Successfully
==================================================================
```

## Step 5: Authorize AWS Chatbot in Slack (One-Time)

**This step must be done manually in the AWS Console**:

1. Go to the AWS Console → **AWS Chatbot**
2. Click **"Configure new client"**
3. Choose **Slack**
4. Click **"Configure Slack workspace"**
5. You'll be redirected to Slack to authorize AWS
6. Sign in to your Slack workspace
7. Click **"Allow"** to grant AWS Chatbot permissions
8. You'll be redirected back to AWS Console

**Note**: You only need to do this once per Slack workspace. After authorization, the CDK stack can configure channels automatically.

## Step 6: Deploy the Chatbot Stack

Now deploy the CDK stack:

```bash
make deploy
```

This will:
1. Deploy the SNS stack (notification topics)
2. Deploy the Budget stack (cost monitoring)
3. Deploy the Chatbot stack (Slack integration)
4. Deploy the Monitoring stack (CloudWatch dashboard)

## Step 7: Verify Integration

Test that notifications are working:

```bash
make validate
```

This will send test messages to both Slack channels:
- Test message to #aws-critical-alerts
- Test message to #aws-heartbeat

**You should see**:
- Two messages appear in your Slack channels
- Messages formatted nicely by AWS Chatbot
- Confirmation in terminal that messages were published

## Step 8: Test Interactive Commands (Optional)

In your Slack channels, you can now use AWS CLI commands:

```
@aws cloudwatch describe-alarms
@aws budgets describe-budgets --account-id 123456789012
@aws sns list-topics
```

**Note**: Only read-only commands work (by design for security).

## Troubleshooting

### "Workspace not found" error

**Problem**: CDK deployment fails with "Workspace not found"

**Solution**:
1. Make sure you completed Step 5 (authorize workspace in AWS Console)
2. Verify workspace ID in `.env` is correct
3. Re-run `make deploy-secrets`

### No messages in Slack

**Problem**: `make validate` succeeds but no Slack messages appear

**Possible causes**:
1. **Chatbot stack not deployed**: Run `make deploy`
2. **Wrong channel IDs**: Verify channel IDs in `.env`
3. **Workspace not authorized**: Complete Step 5
4. **SNS subscription pending**: Check if AWS Chatbot subscribed to topics

**Check subscriptions**:
```bash
aws sns list-subscriptions-by-topic \
  --topic-arn <TOPIC_ARN_FROM_OUTPUTS>
```

### Invalid Slack ID format

**Problem**: `deploy-secrets.py` reports invalid ID format

**Solution**:
- Workspace ID must start with `T`
- Channel IDs must start with `C`
- No spaces or extra characters
- Example: `T01234ABCDE`, `C01234ABCDE`

### Permission denied errors

**Problem**: Cannot create secrets in AWS

**Solution**:
1. Verify AWS credentials: `aws sts get-caller-identity`
2. Check IAM permissions include `secretsmanager:CreateSecret`
3. Re-run `bash scripts/setup-aws-iam-user.sh`

## Security Notes

- ✅ Secrets stored in AWS Secrets Manager (encrypted at rest)
- ✅ AWS Chatbot has read-only IAM permissions
- ✅ Slack IDs are not sensitive, but workspace access is controlled
- ✅ `.env` file never committed to git
- ⚠️  Anyone with access to your Slack workspace can see notifications

## Next Steps

Once Slack is set up:

1. **Monitor costs**: Watch your Slack channels for budget alerts
2. **Customize budgets**: Edit `config/config.yaml` and run `make update`
3. **Add more integrations**: Use SNS topics from other stacks
4. **Review CloudWatch dashboard**: See cost trends and forecasts

## Resources

- [AWS Chatbot Documentation](https://docs.aws.amazon.com/chatbot/)
- [Slack App Directory - AWS Chatbot](https://slack.com/apps/A6L22LZNH-aws-chatbot)
- [AWS Budgets Documentation](https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-managing-costs.html)
