# AWS Chatbot Slack Monitor

> **Real-time AWS cost monitoring and budget alerts delivered directly to Slack channels**

[![AWS CDK](https://img.shields.io/badge/AWS%20CDK-v2-orange?logo=amazon-aws)](https://aws.amazon.com/cdk/)
[![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Infrastructure](https://img.shields.io/badge/IaC-AWS%20CDK-blueviolet)](https://aws.amazon.com/cdk/)

Prevent runaway AWS costs with automated budget alerts and daily cost reports sent to Slack. This production-ready template uses AWS CDK to deploy a complete cost monitoring solution with CloudWatch dashboards, budget thresholds, and daily expense summaries.

---

## 🎯 Why Use This?

- **💰 Prevent Cost Overruns** - Get alerted before bills spiral out of control
- **📊 Daily Cost Reports** - Automated morning summaries with yesterday's spend and top services
- **🔔 Smart Notifications** - Critical alerts vs. monitoring updates in separate Slack channels
- **📈 Visual Dashboards** - CloudWatch dashboard with trends, forecasts, and budget comparisons
- **⚡ Quick Setup** - Deploy in 30 minutes with `make deploy`
- **🔒 Secure** - Read-only Chatbot permissions, secrets management, least-privilege IAM

---

## 🚀 Quick Start

### Prerequisites

- AWS account with admin access
- Slack workspace (admin access to create channels)
- Docker Desktop (for DevContainer development)
- Python 3.12+
- Node.js 18+ (for AWS CDK)

### 5-Minute Setup

```bash
# 1. Clone the repository
git clone https://github.com/your-username/aws-chatbot-slack-monitor.git
cd aws-chatbot-slack-monitor

# 2. Open in DevContainer (PyCharm or VS Code)
# PyCharm: File → Open → Select folder → "Reopen in Container"
# VS Code: Reopen in Container when prompted

# 3. Configure your settings
vim config/config.yaml
# Edit: AWS account ID, budgets, Slack IDs (see Setup Guide)

# 4. Deploy to AWS
make deploy
# Follow prompts - takes ~10 minutes

# 5. Test notifications
make validate
# Check your Slack channels for the test alarm!
```

**Full setup guide**: [SETUP.md](docs/SETUP.md)

---

## 📸 Screenshots

### Daily Cost Report in Slack
<img src="docs/screenshots/daily-cost-report.png" width="500" alt="Daily cost report showing yesterday's spend, MTD total, and top services">

*Automated daily summaries with budget status and top spending services*

### Budget Alert Example
<img src="docs/screenshots/budget-alert.png" width="500" alt="Budget alert notification in Slack">

*Real-time alerts when you hit 80% or 100% of monthly budget*

### CloudWatch Dashboard
<img src="docs/screenshots/cloudwatch-dashboard.png" width="700" alt="CloudWatch cost monitoring dashboard">

*Visual cost trends with budget threshold annotations*

---

## 🏗️ Architecture

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
│  ┌──────────────┐          ▼                    ▼          │
│  │   Lambda     │    ┌─────────────┐    ┌──────────────┐  │
│  │ Daily Report │    │  CloudWatch │    │ Amazon Q Dev │  │
│  │  (8 AM UTC)  │    │  Dashboard  │    │  (Chatbot)   │  │
│  └──────────────┘    └─────────────┘    └──────────────┘  │
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

### Notification Flow

**Critical Channel** (Low Noise)
- Monthly budget exceeded (100%+)
- Infrastructure failures (when integrated)
- **Goal**: < 5 messages/day, immediate action required

**Heartbeat Channel** (Monitoring)
- Daily cost reports (8 AM UTC)
- Monthly budget warnings (80%)
- Minor alerts and system health
- **Goal**: Daily visibility, action during business hours

---

## ✨ Features

### 1. Budget Monitoring
- **Daily Budget**: Alert when daily spend exceeds threshold → heartbeat channel
- **Monthly Budget**: Two-tier alerts (80% warning, 100% critical)
- **Customizable**: Configure amounts and thresholds in `config.yaml`

### 2. Daily Cost Reports (NEW!)
- Automated Lambda function runs daily at 8 AM UTC
- Yesterday's cost with budget comparison
- Month-to-date total with percentage
- Top 5 services by cost
- Status emojis (🟢 under budget, 🟡 warning, 🔴 over)

### 3. CloudWatch Dashboard
- Current month spend
- Daily and monthly trend graphs
- Budget threshold annotations
- Forecast to month-end
- **Note**: Billing metrics only in `us-east-1`

### 4. AWS Chatbot Integration
- Interactive AWS CLI commands from Slack (`@aws budgets describe-budgets`)
- Read-only permissions (security best practice)
- Formatted notifications with emojis and structure

### 5. Reusable SNS Topics
- Export topic ARNs for other stacks to use
- Integrate ECS, Lambda, RDS, S3 alerts
- See [Integration Guide](docs/integration-guide.md)

---

## 📂 Project Structure

```
aws-chatbot-slack-monitor/
├── cdk/                        # AWS CDK infrastructure code
│   ├── app.py                 # CDK app entry point
│   ├── cdk.json               # CDK configuration
│   └── stacks/                # Stack definitions
│       ├── sns_stack.py       # SNS topics for notifications
│       ├── budget_stack.py    # Budget monitoring and alerts
│       ├── chatbot_stack.py   # Slack channel integrations
│       ├── monitoring_stack.py # CloudWatch dashboard
│       └── daily_cost_stack.py # Daily cost reporting Lambda
├── config/                     # Configuration files
│   └── config.yaml            # Budgets, Slack IDs, settings
├── scripts/                    # Utility scripts
│   ├── aws-permissions-config.sh  # IAM setup for deployment
│   ├── deploy-secrets.py      # Deploy secrets to AWS
│   └── test-slack-with-alarm.sh   # Test Slack notifications
├── docs/                       # Documentation
│   ├── SETUP.md               # Detailed setup guide
│   ├── TROUBLESHOOTING.md     # Common issues and solutions
│   ├── deployment-checklist.md # Step-by-step deployment
│   ├── integration-guide.md   # Integrate with other stacks
│   └── slack-setup.md         # Slack workspace configuration
├── .devcontainer/             # DevContainer configuration
├── Makefile                    # Common commands
├── requirements.txt            # Python dependencies
└── README.md                   # This file
```

---

## ⚙️ Configuration

### Budget Settings (`config/config.yaml`)

```yaml
budgets:
  daily_limit: 10.00      # Daily budget in USD
  monthly_limit: 300.00   # Monthly budget in USD
  monthly_threshold_warning: 80   # Warning at 80%
  monthly_threshold_critical: 100 # Alert at 100%
  currency: USD

daily_report:
  enabled: true
  schedule_hour_utc: 8    # 8 AM UTC = 3 AM EST
```

### Slack Configuration

```yaml
slack:
  workspace_id: T09MR3DRVG8           # Your workspace ID
  critical_channel_id: C09N63G6F3J    # Critical alerts channel
  heartbeat_channel_id: C09MBQUPMK4   # Daily reports channel
```

**Get Slack IDs**: See [Slack Setup Guide](docs/slack-setup.md)

---

## 🛠️ Development Environment

### Option 1: DevContainer (Recommended)

This project uses DevContainers for consistent development across all platforms.

**PyCharm Professional**:
1. Open project
2. PyCharm detects `.devcontainer/devcontainer.json`
3. Click "Reopen in Container"
4. Wait for container build (~5 mins first time)

**VS Code**:
1. Install "Dev Containers" extension
2. Open project
3. Click "Reopen in Container" when prompted

**Benefits**:
- ✅ Isolated environment (won't affect your host)
- ✅ All dependencies pre-installed
- ✅ Reproducible across team members
- ✅ Python 3.12, AWS CDK, AWS CLI ready

### Option 2: Local Development

If you prefer not to use DevContainers:

```bash
# Install dependencies
pip install -r requirements.txt
npm install -g aws-cdk

# Configure AWS credentials
aws configure

# Proceed with deployment
make deploy
```

---

## 📋 Common Commands

```bash
# Deployment
make deploy              # Deploy all stacks to AWS
make destroy             # Tear down all infrastructure
make update              # Quick update (config changes only)
make diff                # Show pending changes

# Testing
make validate            # Test Slack notifications (creates temp alarm)
make synth               # Validate CDK code compiles

# Setup
bash scripts/aws-permissions-config.sh  # Setup AWS IAM user

# Monitoring
cdk list                 # List all stacks
aws budgets list-budgets --account-id YOUR_ACCOUNT_ID
```

---

## 🔐 Security

- **Least-Privilege IAM**: Chatbot has read-only access only
- **No Hardcoded Secrets**: Slack IDs in config (not sensitive), AWS keys in `.env` (gitignored)
- **Secrets Manager Ready**: Optional email notifications use AWS Secrets Manager
- **Isolated Deployment**: Project-specific IAM user with minimal permissions
- **DevContainer Isolation**: Development environment isolated from host

---

## 📊 Cost Estimate

**AWS Resources Monthly Cost** (approximate):
- AWS Budgets: $0.02/budget × 2 = **$0.04**
- Lambda (daily reports): ~30 invocations/month = **$0.00** (free tier)
- SNS: Negligible (few notifications) = **$0.00**
- CloudWatch Dashboard: 3 dashboards = **$9.00**
- **Total**: **~$9.04/month**

**Cost Savings**: Preventing a single runaway instance pays for this 100x over!

---

## 🤝 Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

---

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- Built with [AWS CDK](https://aws.amazon.com/cdk/)
- Developed with [Claude Code](https://claude.com/claude-code) AI assistance
- Inspired by the need to prevent surprise AWS bills!

---

## 📚 Additional Resources

- [Detailed Setup Guide](docs/SETUP.md)
- [Troubleshooting Guide](docs/TROUBLESHOOTING.md)
- [Integration Examples](docs/integration-guide.md)
- [Slack Setup](docs/slack-setup.md)
- [Deployment Checklist](docs/deployment-checklist.md)

---

## 🐛 Issues & Support

Found a bug? Have a question?

- **Issues**: [GitHub Issues](https://github.com/your-username/aws-chatbot-slack-monitor/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-username/aws-chatbot-slack-monitor/discussions)

---

## ⭐ Star This Project

If this project saved you from a surprise AWS bill, please star it! ⭐

---

**Made with ❤️ using AWS CDK and Claude Code**
