# AWS Chatbot Slack Monitor Project

## Project Overview
This project provides AWS cost monitoring and alerting through Slack using AWS CDK (Python). It integrates AWS Budgets, CloudWatch, and AWS Chatbot to deliver real-time cost notifications to Slack channels, helping teams stay on top of AWS spending and avoid runaway costs.

The project is built as a reusable template that can be deployed to any AWS account with minimal configuration. Development happens in a PyCharm DevContainer with Claude Code integration for complete isolation and reproducibility.

## Development Environment Details

### Container Configuration
- **Base Image**: Python 3.12-slim
- **Container User**: developer (non-root for security)
- **IDE Backend**: PyCharm (running in container)
- **AI Assistant**: Claude Code (running in container)
- **Package Management**: pip with requirements.txt

### Directory Structure
```
/workspace/                      # Main project directory (mounted from host)
├── .devcontainer/              # DevContainer configuration files
│   ├── devcontainer.json       # Container settings
│   ├── Dockerfile              # Container image definition
│   ├── setup.sh               # Post-create setup script
│   ├── start.sh               # Post-start script
│   └── README.md              # DevContainer documentation
├── cdk/                        # AWS CDK infrastructure code
│   ├── app.py                 # CDK app entry point
│   ├── cdk.json               # CDK configuration
│   ├── stacks/                # CDK stack definitions
│   │   ├── __init__.py
│   │   ├── chatbot_stack.py   # Slack channel configurations
│   │   ├── budget_stack.py    # AWS Budgets and alerts
│   │   ├── monitoring_stack.py # CloudWatch dashboards
│   │   └── sns_stack.py       # SNS topics for notifications
│   └── custom_constructs/     # Reusable custom CDK constructs
│       ├── __init__.py
│       └── budget_alert.py    # Budget alert construct
├── config/                     # Configuration files
│   ├── config.yaml            # Safe config (in git)
│   └── .env.example           # Example environment variables
├── scripts/                    # Utility scripts
│   ├── aws-permissions-config.sh  # AWS IAM setup script
│   └── deploy-secrets.py      # Deploy .env to Secrets Manager
├── docs/                       # Documentation
│   ├── project-plan.md        # Detailed implementation plan
│   ├── slack-setup.md         # Slack workspace setup guide
│   └── integration-guide.md   # Guide for other stacks
├── tests/                      # Test files
│   ├── __init__.py
│   └── test_stacks.py         # CDK stack tests
├── Makefile                    # Common commands (deploy, destroy, validate)
├── requirements.txt            # Python dependencies
├── CLAUDE.md                   # This file (AI context)
└── README.md                   # Project documentation
```

### Persistent Storage
- **Claude Config**: `/home/developer/.claude` (persisted via Docker volume)
- **Bash History**: `/commandhistory/.bash_history` (persisted via Docker volume)
- **Pip Cache**: `/home/developer/.cache/pip` (persisted via Docker volume)

## Development Workflow

### Daily Startup
1. Open PyCharm
2. Open project (PyCharm detects devcontainer.json)
3. Choose "Reopen in Container" when prompted
4. Wait for container to build/start (first time takes longer)
5. PyCharm connects to container backend automatically

### Claude Code Usage
1. Open PyCharm's integrated terminal (connected to container)
2. Run `claude` to start Claude Code
3. Claude Code has full context of container environment
4. Use natural language to request code changes, debugging, etc.

### Common Commands (in container terminal)
```bash
# CDK Operations (use Makefile for convenience)
make deploy                     # Deploy the stack to AWS
make destroy                    # Tear down the stack
make validate                   # Test Slack notification channels
make diff                       # Show changes to be deployed
make synth                      # Synthesize CloudFormation template

# Direct CDK Commands
cdk deploy                      # Deploy all stacks
cdk deploy BudgetStack          # Deploy specific stack
cdk diff                        # Show deployment diff
cdk synth                       # Synthesize CloudFormation
cdk destroy                     # Destroy all stacks

# Configuration
cp config/.env.example .env     # Create environment file
vim config/config.yaml          # Edit budget configuration
python scripts/deploy-secrets.py # Deploy secrets to AWS

# Testing
python -m pytest tests/         # Run all tests
python -m pytest tests/ -v     # Run tests with verbose output
cdk synth > /dev/null           # Validate CDK code compiles

# Code Quality
black cdk/ tests/               # Format code
flake8 cdk/ tests/              # Check code style
mypy cdk/                       # Type checking

# AWS Setup
bash scripts/aws-permissions-config.sh  # Configure AWS deployment user

# Development
pip install -r requirements.txt # Install all dependencies
claude                          # Start Claude Code
```

## Environment Variables

### System Environment Variables (set in devcontainer)
- `PYTHONPATH=/workspace/cdk` - Python module search path for CDK code
- `CLAUDE_CONFIG_DIR=/home/developer/.claude` - Claude configuration
- `DEVCONTAINER=true` - Indicates we're in a development container
- `ANTHROPIC_API_KEY` - Your Claude API key (set on host, passed to container)

### AWS Credentials (configured via aws-permissions-config.sh)
- `AWS_ACCESS_KEY_ID` - AWS deployment user access key
- `AWS_SECRET_ACCESS_KEY` - AWS deployment user secret key
- `AWS_DEFAULT_REGION` - Default AWS region (e.g., us-east-1)
- `CDK_DEFAULT_ACCOUNT` - AWS account ID for CDK deployment
- `CDK_DEFAULT_REGION` - AWS region for CDK deployment

### Project Configuration (.env file - not committed)
- `SLACK_WORKSPACE_ID` - Slack workspace ID for AWS Chatbot
- `SLACK_CRITICAL_CHANNEL_ID` - Slack channel ID for critical alerts
- `SLACK_HEARTBEAT_CHANNEL_ID` - Slack channel ID for heartbeat/monitoring
- `NOTIFICATION_EMAILS` - Comma-separated email addresses for budget alerts (optional)

## Security Features
- **Container Isolation**: Claude Code cannot access host filesystem outside project
- **Non-root User**: All operations run as 'developer' user for security
- **API Key Isolation**: API keys are managed separately from project code
- **Network Isolation**: Container has limited network access

## PyCharm Integration
- **Backend in Container**: PyCharm server runs inside container for full context
- **Frontend on Host**: PyCharm UI runs on host, connects to container backend
- **Seamless Experience**: Debugging, running, testing all work normally
- **Plugin Support**: PyCharm plugins can be installed in container environment

## Project Architecture

### Core Components

**1. AWS Budgets**
- Daily budget with 100% threshold → heartbeat channel
- Monthly budget with 80% warning → heartbeat channel
- Monthly budget with 100% alert → critical channel
- Configurable budget amounts via config.yaml

**2. SNS Topics**
- `critical-alerts` - For budget overruns and severe issues
- `heartbeat-alerts` - For daily reports, warnings, and monitoring
- Both topics can be referenced by other AWS stacks

**3. AWS Chatbot Integration**
- Two Slack channel configurations (critical + heartbeat)
- Read-only IAM permissions for Slack commands
- Interactive AWS CLI access from Slack (@aws commands)

**4. CloudWatch Dashboard**
- Daily spend trends
- Monthly spend vs budget comparison
- Top services by cost
- Forecast to month-end
- (Note: Billing metrics only available in us-east-1)

**5. Configuration Management**
- `config/config.yaml` - Safe configuration (in git): budget amounts, thresholds, settings
- `.env` - Secrets (gitignored): Slack IDs, AWS credentials, emails
- AWS Secrets Manager - Deployed secrets for stack runtime access

### Notification Routing Strategy

**Critical Channel (Low Noise)**
- Monthly budget exceeded (100%+)
- Severe infrastructure failures (when integrated)
- Any message here requires immediate action

**Heartbeat Channel (May Be Noisy)**
- Daily spend reports
- Monthly budget warnings (80% threshold)
- Minor alerts and informational messages
- System health indicators

## Notes for Claude Code

### When Working with This Project:
- **File Paths**: Use paths relative to `/workspace` (e.g., `cdk/app.py`, not `./cdk/app.py`)
- **Python Imports**: The `cdk/` directory is in PYTHONPATH for clean imports
- **CDK Best Practices**: Use constructs for reusable components, stacks for logical groupings
- **Testing**: Run `cdk synth` to validate syntax, `pytest` for unit tests
- **Code Style**: Format with `black`, check with `flake8`, type-check with `mypy`
- **Git Operations**: Use READ-ONLY access - create commit messages in GIT-COMMIT-MSG.md

### AWS-Specific Considerations:
- **Region Flexibility**: Stack should work in any region, but billing metrics need us-east-1
- **IAM Permissions**: Chatbot should use read-only permissions for security
- **Secrets Handling**: Never commit Slack IDs or credentials - use .env + Secrets Manager
- **Budget vs Metrics**: AWS Budgets (alerts) != CloudWatch Billing Metrics (dashboard)
- **SNS Topic Design**: Create well-named topics that other stacks can easily reference

### Best Practices:
- **Security First**: Least-privilege IAM, no secrets in code, read-only Chatbot
- **Make it Reusable**: Template-based config, clear documentation, modular constructs
- **Test Before Deploy**: `cdk synth`, `cdk diff`, then `cdk deploy`
- **Configuration Over Code**: Use config.yaml for values that change between deployments

### Available Tools:
- **Python 3.12** with full standard library
- **AWS CDK v2** for infrastructure as code
- **pytest** for testing
- **black** for code formatting
- **flake8** for linting
- **mypy** for type checking
- **AWS CLI** for manual AWS operations
- **git** for version control (read-only in container)
- **All standard Unix tools**

### Git Workflow (Read-Only Access):
When user requests commits:
1. Create detailed commit message
2. Write to `GIT-COMMIT-MSG.md`
3. Provide git command: `git commit -F GIT-COMMIT-MSG.md`

When user requests pull requests:
1. Create detailed PR description
2. Write to `GIT-PULLREQUEST-MSG.md`
3. Provide gh command: `gh pr create --title "..." --body-file GIT-PULLREQUEST-MSG.md`

## Troubleshooting

### Container Issues
- **Container won't start**: Check Docker is running, rebuild with PyCharm
- **Permission errors**: Ensure files are owned by developer user
- **AWS CLI not found**: Run setup script or restart container

### PyCharm Issues
- **Can't connect**: Restart PyCharm and try reconnecting to container
- **Slow performance**: Increase Docker memory allocation
- **Missing features**: Check that all required plugins are installed

### AWS CDK Issues
- **CDK command not found**: Ensure CDK is installed: `npm install -g aws-cdk`
- **Deployment fails**: Check AWS credentials with `aws sts get-caller-identity`
- **Permission denied**: Verify IAM user has required permissions (see scripts/aws-permissions-config.sh)
- **Stack already exists**: Use `cdk diff` to see changes before deploying
- **Cannot find module errors**: Ensure `pip install -r requirements.txt` has been run

### AWS Chatbot Issues
- **Slack workspace not found**: Must configure Slack workspace manually first (see docs/slack-setup.md)
- **Channel configuration fails**: Verify Slack Channel IDs in .env are correct
- **No notifications received**: Check SNS topic subscriptions and Slack channel settings
- **Permission errors**: Review IAM role attached to Chatbot configuration

### Budget Alert Issues
- **No budget alerts**: Verify email subscriptions are confirmed (check inbox)
- **Wrong notifications sent**: Review notification routing in budget_stack.py
- **Dashboard shows no data**: Billing metrics require us-east-1 region

## Getting Help
- **Claude Code Help**: Run `claude --help` in container terminal
- **AWS CDK Documentation**: https://docs.aws.amazon.com/cdk/
- **AWS Chatbot Documentation**: https://docs.aws.amazon.com/chatbot/
- **Project Documentation**: See docs/ directory for detailed guides
- **Container Logs**: Check PyCharm's Services panel for container logs
