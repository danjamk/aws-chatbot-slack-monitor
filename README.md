# AWS Chatbot Slack Monitor

> A comprehensive AWS cost monitoring and alerting solution that integrates AWS Budgets, CloudWatch, and AWS Chatbot to deliver real-time notifications to Slack channels.

[![AWS CDK](https://img.shields.io/badge/AWS%20CDK-v2-orange)](https://aws.amazon.com/cdk/)
[![Python](https://img.shields.io/badge/Python-3.12-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

## Overview

This project helps teams stay on top of AWS spending by automatically sending cost and budget alerts to Slack channels. It's designed as a reusable template that can be deployed to any AWS account with minimal configuration, preventing runaway costs before they become a problem.

### Key Features

- **Dual Slack Channel Strategy**: Critical alerts vs. heartbeat monitoring
- **AWS Budget Integration**: Daily and monthly budget tracking with configurable thresholds
- **CloudWatch Dashboard**: Comprehensive cost visualization and forecasting
- **AWS Chatbot**: Interactive AWS CLI access directly from Slack
- **Reusable SNS Topics**: Easy integration with other AWS infrastructure stacks
- **Security First**: Read-only Chatbot permissions, no secrets in code
- **Template-Based**: Simple YAML configuration for easy deployment
- **Make Commands**: Simple `make deploy`, `make destroy`, `make validate` workflow

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      AWS Account                            │
│                                                             │
│  ┌──────────────┐    ┌─────────────┐    ┌──────────────┐  │
│  │ AWS Budgets  │───▶│  SNS Topics │───▶│ AWS Chatbot  │  │
│  │              │    │             │    │              │  │
│  │ • Daily      │    │ • Critical  │    │ • Critical   │  │
│  │ • Monthly    │    │ • Heartbeat │    │ • Heartbeat  │  │
│  └──────────────┘    └─────────────┘    └──────────────┘  │
│                             │                    │          │
│                             ▼                    ▼          │
│                      ┌─────────────┐    ┌──────────────┐  │
│                      │  CloudWatch │    │   Secrets    │  │
│                      │  Dashboard  │    │   Manager    │  │
│                      └─────────────┘    └──────────────┘  │
└─────────────────────────────────────────────────────────────┘
                                │
                                ▼
                     ┌─────────────────────┐
                     │  Slack Workspace    │
                     │                     │
                     │  • #critical-alerts │
                     │  • #aws-heartbeat   │
                     └─────────────────────┘
```

### Notification Routing

**Critical Channel** (Low Noise)
- Monthly budget exceeded (100%+)
- Severe infrastructure failures
- Requires immediate action

**Heartbeat Channel** (Monitoring)
- Daily spend reports
- Monthly budget warnings (80%)
- Minor alerts and system health

## Prerequisites

### Required
- **AWS Account** with administrator access for initial setup
- **Slack Workspace** with admin access to create channels
- **Docker Desktop** (for DevContainer development environment)
- **PyCharm Professional** (or VS Code with DevContainer support)
- **Python 3.12+**
- **Node.js 18+** (for AWS CDK)

### Recommended
- **Anthropic API Key** (for Claude Code development assistance)
- Basic understanding of AWS CDK and Python

## Quick Start

### 1. Clone and Setup

```bash
git clone https://github.com/your-username/aws-chatbot-slack-monitor.git
cd aws-chatbot-slack-monitor
```

### 2. Configure Slack Workspace

Follow the detailed [Slack Setup Guide](docs/slack-setup.md) to:
1. Create two Slack channels (`#critical-alerts` and `#aws-heartbeat`)
2. Configure AWS Chatbot workspace integration
3. Get your Slack Workspace ID and Channel IDs

### 3. Configure Project Settings

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your Slack configuration
vim .env
```

Required `.env` variables:
```bash
SLACK_WORKSPACE_ID=T01234ABCDE
SLACK_CRITICAL_CHANNEL_ID=C01234ABCDE
SLACK_HEARTBEAT_CHANNEL_ID=C56789FGHIJ
NOTIFICATION_EMAILS=team@example.com,admin@example.com
```

Edit `config/config.yaml` for budget settings:
```yaml
budgets:
  daily_limit: 10.00      # Daily budget in USD
  monthly_limit: 300.00   # Monthly budget in USD
  monthly_threshold_warning: 80  # Warning at 80%
  monthly_threshold_critical: 100  # Alert at 100%
  currency: USD

aws:
  region: us-east-1
  account_id: "123456789012"  # Your AWS account ID
```

### 4. Setup AWS Deployment Credentials

```bash
# Configure AWS IAM user with required permissions
bash scripts/aws-permissions-config.sh

# Follow the prompts to create deployment credentials
```

### 5. Install Dependencies

```bash
# Python dependencies
pip install -r requirements.txt

# AWS CDK (if not already installed)
npm install -g aws-cdk
```

### 6. Deploy to AWS

```bash
# Synthesize CloudFormation template (validate)
make synth

# Preview changes
make diff

# Deploy to AWS
make deploy

# Test notifications
make validate
```

## Configuration

### Budget Configuration (`config/config.yaml`)

```yaml
budgets:
  daily_limit: 10.00              # Daily spending limit
  monthly_limit: 300.00           # Monthly spending limit
  monthly_threshold_warning: 80   # Warning threshold (%)
  monthly_threshold_critical: 100 # Critical threshold (%)
  currency: USD

aws:
  region: us-east-1              # Primary AWS region
  account_id: "123456789012"     # Your AWS account ID

dashboard:
  enabled: true
  name: "CostMonitoring"
  top_services_count: 10         # Number of services to show
```

### Environment Variables (`.env`)

```bash
# Slack Configuration (required)
SLACK_WORKSPACE_ID=T01234ABCDE
SLACK_CRITICAL_CHANNEL_ID=C01234ABCDE
SLACK_HEARTBEAT_CHANNEL_ID=C56789FGHIJ

# Email Notifications (optional)
NOTIFICATION_EMAILS=team@example.com,admin@example.com

# AWS Credentials (for deployment)
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_DEFAULT_REGION=us-east-1
CDK_DEFAULT_ACCOUNT=123456789012
CDK_DEFAULT_REGION=us-east-1
```

## Usage

### Make Commands

```bash
make deploy      # Deploy all stacks to AWS
make destroy     # Tear down all stacks
make diff        # Show deployment changes
make synth       # Synthesize CloudFormation templates
make validate    # Test Slack notification channels
make update      # Update budgets after config changes
```

### Direct CDK Commands

```bash
cdk deploy                    # Deploy all stacks
cdk deploy BudgetStack        # Deploy specific stack
cdk diff                      # Show changes
cdk synth                     # Generate CloudFormation
cdk destroy                   # Remove all resources
```

### Updating Budgets

1. Edit `config/config.yaml` with new budget values
2. Run `make update` or `make deploy`
3. Budgets will be updated without recreating resources

### Testing Notifications

```bash
# Test both Slack channels
make validate

# Or manually publish test messages
aws sns publish \
  --topic-arn arn:aws:sns:us-east-1:123456789012:critical-alerts \
  --message "Test critical alert"
```

## Slack Interaction

Once deployed, you can interact with AWS from Slack:

### View Cost Information
```
@aws cloudwatch get-metric-statistics --namespace AWS/Billing
```

### Check Budget Status
```
@aws budgets describe-budgets --account-id 123456789012
```

### List Alarms
```
@aws cloudwatch describe-alarms --state-value ALARM
```

All commands are **read-only** for security.

## Integration with Other Stacks

This monitoring system creates reusable SNS topics that other infrastructure can use:

### Example: Integrate ECS Alerts

```python
from aws_cdk import aws_sns as sns
from aws_cdk import Stack

class MyECSStack(Stack):
    def __init__(self, scope, id, **kwargs):
        super().__init__(scope, id, **kwargs)

        # Reference the critical alerts topic
        critical_topic = sns.Topic.from_topic_arn(
            self, "CriticalTopic",
            topic_arn="arn:aws:sns:us-east-1:123456789012:critical-alerts"
        )

        # Send ECS service down alert to critical channel
        ecs_alarm.add_alarm_action(
            cloudwatch_actions.SnsAction(critical_topic)
        )
```

See [Integration Guide](docs/integration-guide.md) for more examples.

## Development

### DevContainer Setup

This project uses DevContainers for isolated, reproducible development:

1. **Open in PyCharm**: File → Open → Select project
2. **Reopen in Container**: PyCharm will prompt automatically
3. **Wait for build**: First time takes 5-10 minutes
4. **Start coding**: Full development environment ready

See [.devcontainer/README.md](.devcontainer/README.md) for details.

### Running Tests

```bash
# Run all tests
python -m pytest tests/

# Run with coverage
python -m pytest tests/ --cov=cdk --cov-report=html

# Validate CDK code
cdk synth > /dev/null
```

### Code Quality

```bash
# Format code
black cdk/ tests/

# Lint code
flake8 cdk/ tests/

# Type checking
mypy cdk/
```

## Troubleshooting

### Deployment Issues

**Problem**: `Error: Slack workspace not found`
- **Solution**: Configure Slack workspace manually in AWS Console first
- See [Slack Setup Guide](docs/slack-setup.md)

**Problem**: `AccessDenied` errors during deployment
- **Solution**: Check IAM permissions with `bash scripts/aws-permissions-config.sh`

**Problem**: No notifications received in Slack
- **Solution**: Verify channel IDs in `.env` match Slack channels
- Run `make validate` to test

### Budget Alert Issues

**Problem**: Dashboard shows no billing data
- **Solution**: Billing metrics only available in `us-east-1` region
- Change deployment region to `us-east-1`

**Problem**: Email notifications not working
- **Solution**: Check inbox for SNS subscription confirmation emails
- Click "Confirm Subscription" link

### Chatbot Permission Issues

**Problem**: Chatbot can't execute commands from Slack
- **Solution**: Check IAM role has proper read policies
- See IAM role in `chatbot_stack.py`

## Project Structure

```
.
├── cdk/                        # AWS CDK infrastructure code
│   ├── app.py                 # CDK app entry point
│   ├── stacks/                # CDK stack definitions
│   │   ├── chatbot_stack.py   # Slack channel configurations
│   │   ├── budget_stack.py    # AWS Budgets and alerts
│   │   ├── monitoring_stack.py # CloudWatch dashboards
│   │   └── sns_stack.py       # SNS topics
│   └── constructs/            # Reusable CDK constructs
├── config/                     # Configuration files
│   ├── config.yaml            # Budget and AWS settings
│   └── .env.example           # Environment template
├── docs/                       # Documentation
│   ├── project-plan.md        # Implementation plan
│   ├── slack-setup.md         # Slack setup guide
│   └── integration-guide.md   # Integration examples
├── scripts/                    # Utility scripts
│   ├── aws-permissions-config.sh  # AWS IAM setup
│   └── deploy-secrets.py      # Secrets deployment
├── tests/                      # Test files
├── Makefile                    # Common commands
└── README.md                   # This file
```

## Security Considerations

- **No Secrets in Code**: All secrets in `.env` or AWS Secrets Manager
- **Read-Only Chatbot**: Slack commands can only read, not modify resources
- **Least Privilege IAM**: Minimal permissions for deployment and runtime
- **Container Isolation**: Development in isolated DevContainer
- **No Credential Mounting**: Project-specific AWS credentials only

## Contributing

This is a template project designed to be forked and customized. To contribute improvements:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly with `make validate`
5. Submit a pull request

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built with [AWS CDK](https://aws.amazon.com/cdk/)
- DevContainer template from [pycharm-claude-devcontainer](https://github.com/danjamk/pycharm-claude-devcontainer)
- AWS Chatbot service by [Amazon Web Services](https://aws.amazon.com/chatbot/)

## Support

- **Issues**: [GitHub Issues](https://github.com/your-username/aws-chatbot-slack-monitor/issues)
- **Documentation**: See `docs/` directory
- **AWS Chatbot Docs**: https://docs.aws.amazon.com/chatbot/
- **AWS CDK Docs**: https://docs.aws.amazon.com/cdk/

---

**Stay on top of your AWS costs with real-time Slack notifications!** 💰📊
