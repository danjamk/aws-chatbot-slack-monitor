# AWS Chatbot Slack Monitor - Project Implementation Plan

**Project Status**: 🚧 In Progress
**Last Updated**: 2025-10-18
**Version**: 1.0.0

## Executive Summary

This document outlines the detailed implementation plan for the AWS Chatbot Slack Monitor project - a comprehensive cost monitoring and alerting system that integrates AWS Budgets, CloudWatch, and AWS Chatbot to deliver real-time notifications to Slack channels.

### Project Goals

1. **Prevent Runaway Costs**: Automated alerts when AWS spending exceeds thresholds
2. **Team Visibility**: Real-time cost information in Slack where teams collaborate
3. **Reusable Template**: Easy to deploy across multiple AWS accounts and projects
4. **Extensible Architecture**: SNS topics that other infrastructure can leverage
5. **Security First**: Read-only Chatbot, no secrets in code, least-privilege IAM

## Architecture Overview

### Components

```
┌─────────────────────────────────────────────────────────────────────┐
│                           AWS CDK Stacks                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌──────────────────┐   ┌──────────────────┐   ┌─────────────────┐ │
│  │  SNS Stack       │   │  Budget Stack    │   │  Chatbot Stack  │ │
│  │                  │   │                  │   │                 │ │
│  │  • critical-     │◀──│  • Daily Budget  │──▶│  • Critical Ch. │ │
│  │    alerts        │   │  • Monthly Budget│   │  • Heartbeat Ch.│ │
│  │  • heartbeat-    │   │  • SNS Alarms    │   │  • IAM Roles    │ │
│  │    alerts        │   │                  │   │  • Read-Only    │ │
│  └──────────────────┘   └──────────────────┘   └─────────────────┘ │
│                                                                       │
│  ┌──────────────────┐   ┌──────────────────┐                        │
│  │ Monitoring Stack │   │  Secrets Stack   │                        │
│  │                  │   │                  │                        │
│  │  • CW Dashboard  │   │  • Slack IDs     │                        │
│  │  • Cost Metrics  │   │  • Config Values │                        │
│  │  • Forecasting   │   │                  │                        │
│  └──────────────────┘   └──────────────────┘                        │
└─────────────────────────────────────────────────────────────────────┘
```

### Technology Stack

- **Infrastructure as Code**: AWS CDK v2 (Python)
- **AWS Services**:
  - AWS Budgets (cost tracking)
  - AWS Chatbot (Slack integration)
  - Amazon SNS (notifications)
  - Amazon CloudWatch (metrics & dashboards)
  - AWS Secrets Manager (secure configuration)
- **Development**:
  - Python 3.12
  - PyCharm DevContainer
  - pytest (testing)
  - Make (build automation)

## Implementation Phases

### Phase 1: Project Setup and Foundation ✅

**Status**: In Progress
**Estimated**: 2-3 hours
**Actual**: TBD

#### Tasks

- [x] Research AWS CDK + Chatbot integration best practices
- [x] Review requirements and ask clarifying questions
- [x] Update CLAUDE.md for project context
- [x] Move DevContainer README to .devcontainer/
- [x] Create new project README.md
- [x] Create this project plan document
- [ ] Update scripts/aws-permissions-config.sh
- [ ] Setup project directory structure
- [ ] Create config/config.yaml template
- [ ] Create config/.env.example
- [ ] Update requirements.txt with CDK dependencies
- [ ] Create Makefile with common commands
- [ ] Initialize CDK project structure

#### Deliverables

- ✅ Updated documentation (CLAUDE.md, README.md)
- ✅ Project plan (this document)
- ⏳ Project structure and scaffolding
- ⏳ Configuration templates
- ⏳ Build automation (Makefile)

---

### Phase 2: SNS Topics and Foundation Stack 📋

**Status**: Not Started
**Estimated**: 2-3 hours

#### Tasks

- [ ] Create `cdk/app.py` - CDK application entry point
- [ ] Create `cdk/stacks/sns_stack.py`
  - [ ] Define `critical-alerts` SNS topic
  - [ ] Define `heartbeat-alerts` SNS topic
  - [ ] Add email subscriptions from config
  - [ ] Export topic ARNs for cross-stack references
  - [ ] Add topic policies for cross-account access (future)
- [ ] Create base CDK configuration (`cdk.json`)
- [ ] Write unit tests for SNS stack
- [ ] Validate with `cdk synth`

#### Technical Decisions

**SNS Topic Naming Convention**:
- Format: `{project}-{environment}-{purpose}`
- Example: `chatbot-prod-critical-alerts`
- Allows multiple deployments in same account

**Email Subscriptions**:
- Read from `.env` file: `NOTIFICATION_EMAILS`
- Comma-separated list
- Require confirmation (standard SNS behavior)

#### Deliverables

- SNS topics deployed and accessible
- Email subscriptions configured
- Topic ARNs exported for other stacks
- Unit tests passing

---

### Phase 3: AWS Budget Stack 📋

**Status**: Not Started
**Estimated**: 3-4 hours

#### Tasks

- [ ] Create `cdk/stacks/budget_stack.py`
  - [ ] Implement daily budget with 100% threshold
  - [ ] Implement monthly budget with 80% threshold
  - [ ] Implement monthly budget with 100% threshold
  - [ ] Configure SNS notifications to appropriate topics
  - [ ] Load budget values from config.yaml
- [ ] Create `cdk/constructs/budget_alert.py` (reusable construct)
  - [ ] Parameterized budget construct
  - [ ] SNS topic integration
  - [ ] Threshold configuration
- [ ] Write unit tests for budget stack
- [ ] Test budget updates (change config, redeploy)
- [ ] Validate with `cdk synth`

#### Technical Decisions

**Budget Notification Routing**:
- Daily 100% → heartbeat-alerts
- Monthly 80% → heartbeat-alerts
- Monthly 100% → critical-alerts

**Budget Configuration**:
```yaml
budgets:
  daily_limit: 10.00
  monthly_limit: 300.00
  monthly_threshold_warning: 80
  monthly_threshold_critical: 100
  currency: USD
```

**Update Strategy**:
- Budgets support in-place updates
- No resource replacement needed
- Quick updates via `make update`

#### Deliverables

- Daily and monthly budgets configured
- SNS notifications routing to correct channels
- Reusable budget construct
- Configuration-driven budget values
- Unit tests passing

---

### Phase 4: AWS Chatbot Stack 📋

**Status**: Not Started
**Estimated**: 3-4 hours

#### Tasks

- [ ] **PREREQUISITE**: Document manual Slack workspace setup
  - [ ] Create `docs/slack-setup.md`
  - [ ] Step-by-step Slack channel creation
  - [ ] AWS Chatbot workspace authorization
  - [ ] How to get Workspace ID and Channel IDs
- [ ] Create `cdk/stacks/chatbot_stack.py`
  - [ ] Load Slack IDs from AWS Secrets Manager
  - [ ] Create critical channel configuration
  - [ ] Create heartbeat channel configuration
  - [ ] Configure read-only IAM role
  - [ ] Subscribe to SNS topics
- [ ] Create script `scripts/deploy-secrets.py`
  - [ ] Read .env file
  - [ ] Deploy secrets to AWS Secrets Manager
  - [ ] Handle secret updates
- [ ] Write unit tests for Chatbot stack
- [ ] Document IAM permissions required
- [ ] Validate with `cdk synth`

#### Technical Decisions

**Secrets Management**:
- Secrets stored in AWS Secrets Manager
- Deployed before CDK stack
- Secret name: `{project}/slack-config`
- Structure:
  ```json
  {
    "workspace_id": "T01234ABCDE",
    "critical_channel_id": "C01234ABCDE",
    "heartbeat_channel_id": "C56789FGHIJ"
  }
  ```

**IAM Permissions** (Read-Only):
```python
managed_policies = [
    "ReadOnlyAccess",
    "CloudWatchReadOnlyAccess"
]

# No write permissions
# No console access
# Scoped to specific resources
```

**Guardrail Policies**:
- Use AWS managed `ReadOnlyAccess` instead of `AdministratorAccess`
- Additional restrictions on sensitive services
- No IAM modifications
- No billing modifications

#### Deliverables

- Slack setup documentation
- Secrets deployment script
- Chatbot configurations for both channels
- Read-only IAM role
- SNS topic subscriptions
- Unit tests passing

---

### Phase 5: CloudWatch Monitoring Stack 📋

**Status**: Not Started
**Estimated**: 3-4 hours

#### Tasks

- [ ] Create `cdk/stacks/monitoring_stack.py`
  - [ ] Create CloudWatch Dashboard
  - [ ] Add daily spend trend widget
  - [ ] Add monthly spend vs budget widget
  - [ ] Add top services by cost widget
  - [ ] Add forecast widget
  - [ ] Configure auto-refresh
- [ ] Research CloudWatch Billing Metrics API
- [ ] Implement metric queries for cost data
- [ ] Handle region constraints (us-east-1 only for billing)
- [ ] Write unit tests for monitoring stack
- [ ] Test dashboard rendering
- [ ] Validate with `cdk synth`

#### Technical Decisions

**Dashboard Name**:
- `{project}-{environment}-cost-monitoring`
- Example: `chatbot-prod-cost-monitoring`

**Widgets**:
1. **Daily Spend Trend**
   - Line graph, last 30 days
   - EstimatedCharges metric
   - Daily granularity

2. **Monthly Spend vs Budget**
   - Number + gauge
   - Current month spend
   - Budget limit overlay
   - Percentage indicator

3. **Top Services by Cost**
   - Bar chart
   - Top 10 services
   - Current month
   - Sorted by cost descending

4. **Forecast to Month-End**
   - Line graph
   - Historical spend + forecast
   - Budget threshold line

**Region Handling**:
- Billing metrics ONLY in us-east-1
- Dashboard can be in any region
- Cross-region metric queries
- Fallback message if not us-east-1

#### Deliverables

- CloudWatch dashboard deployed
- All widgets configured and rendering
- Cross-region support
- Unit tests passing

---

### Phase 6: Configuration and Secrets Management 📋

**Status**: Not Started
**Estimated**: 2 hours

#### Tasks

- [ ] Finalize `config/config.yaml` schema
  - [ ] Budget configuration
  - [ ] AWS settings
  - [ ] Dashboard configuration
  - [ ] Notification settings
- [ ] Create `config/.env.example` with all variables
- [ ] Implement config validation
  - [ ] YAML schema validation
  - [ ] Required field checks
  - [ ] Type validation
- [ ] Create `scripts/deploy-secrets.py`
  - [ ] Read .env file safely
  - [ ] Validate required secrets
  - [ ] Deploy to AWS Secrets Manager
  - [ ] Update existing secrets
  - [ ] Handle errors gracefully
- [ ] Document configuration options
- [ ] Add .env to .gitignore (if not already)

#### Configuration Schema

**config/config.yaml**:
```yaml
project:
  name: aws-chatbot-monitor
  environment: prod

budgets:
  daily_limit: 10.00
  monthly_limit: 300.00
  monthly_threshold_warning: 80
  monthly_threshold_critical: 100
  currency: USD

aws:
  region: us-east-1
  account_id: "123456789012"

dashboard:
  enabled: true
  name: CostMonitoring
  top_services_count: 10
  auto_refresh_seconds: 300

notifications:
  email_enabled: true
  slack_enabled: true
```

**.env**:
```bash
# Slack Configuration
SLACK_WORKSPACE_ID=T01234ABCDE
SLACK_CRITICAL_CHANNEL_ID=C01234ABCDE
SLACK_HEARTBEAT_CHANNEL_ID=C56789FGHIJ

# AWS Credentials
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_DEFAULT_REGION=us-east-1
CDK_DEFAULT_ACCOUNT=123456789012
CDK_DEFAULT_REGION=us-east-1

# Email Notifications
NOTIFICATION_EMAILS=team@example.com,admin@example.com
```

#### Deliverables

- Configuration schema finalized
- Environment template created
- Secret deployment automation
- Configuration validation
- Documentation updated

---

### Phase 7: Build Automation (Makefile) 📋

**Status**: Not Started
**Estimated**: 2 hours

#### Tasks

- [ ] Create Makefile with targets:
  - [ ] `make install` - Install dependencies
  - [ ] `make synth` - Synthesize CloudFormation
  - [ ] `make diff` - Show deployment diff
  - [ ] `make deploy` - Deploy all stacks
  - [ ] `make deploy-secrets` - Deploy secrets first
  - [ ] `make update` - Update config-driven resources
  - [ ] `make destroy` - Tear down stacks
  - [ ] `make validate` - Test notifications
  - [ ] `make test` - Run unit tests
  - [ ] `make format` - Format code
  - [ ] `make lint` - Lint code
- [ ] Add help target with descriptions
- [ ] Add dependency checks
- [ ] Add error handling
- [ ] Document all commands

#### Make Targets Details

**make validate**:
```bash
# Test both SNS topics
aws sns publish \
  --topic-arn $(CRITICAL_TOPIC_ARN) \
  --subject "Test Alert" \
  --message "This is a test of the critical alerts channel"

aws sns publish \
  --topic-arn $(HEARTBEAT_TOPIC_ARN) \
  --subject "Test Heartbeat" \
  --message "This is a test of the heartbeat channel"
```

**make deploy**:
```bash
# Deploy in dependency order
cdk deploy SnsStack --require-approval never
cdk deploy BudgetStack --require-approval never
cdk deploy ChatbotStack --require-approval never
cdk deploy MonitoringStack --require-approval never
```

**make update**:
```bash
# Only update config-driven resources (faster)
cdk deploy BudgetStack --require-approval never
```

#### Deliverables

- Comprehensive Makefile
- All common operations automated
- Help documentation
- Error handling

---

### Phase 8: AWS IAM Setup Script 📋

**Status**: Not Started
**Estimated**: 2-3 hours

#### Tasks

- [ ] Update `scripts/aws-permissions-config.sh`
  - [ ] Define CDK deployment permissions
  - [ ] Define runtime permissions (Chatbot)
  - [ ] Create IAM user
  - [ ] Attach policies
  - [ ] Generate access keys
  - [ ] Output credentials for .env
- [ ] Document required permissions
- [ ] Create minimal permission policy
- [ ] Test with fresh AWS account
- [ ] Handle error cases

#### Required Permissions

**CDK Deployment User**:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "cloudformation:*",
        "s3:*",
        "sns:*",
        "budgets:*",
        "chatbot:*",
        "cloudwatch:*",
        "iam:*",
        "secretsmanager:*",
        "sts:GetCallerIdentity"
      ],
      "Resource": "*"
    }
  ]
}
```

**Chatbot Runtime Role** (created by CDK):
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "cloudwatch:Describe*",
        "cloudwatch:Get*",
        "cloudwatch:List*",
        "logs:Describe*",
        "logs:Get*",
        "logs:List*",
        "logs:FilterLogEvents",
        "sns:Get*",
        "sns:List*"
      ],
      "Resource": "*"
    }
  ]
}
```

#### Deliverables

- IAM setup script updated
- Minimal permissions documented
- Deployment user created
- Access keys generated
- .env template updated

---

### Phase 9: Testing and Validation 📋

**Status**: Not Started
**Estimated**: 3-4 hours

#### Tasks

- [ ] Write comprehensive unit tests
  - [ ] SNS stack tests
  - [ ] Budget stack tests
  - [ ] Chatbot stack tests
  - [ ] Monitoring stack tests
  - [ ] Configuration validation tests
- [ ] Write integration tests
  - [ ] Full stack deployment test
  - [ ] Notification flow test
  - [ ] Slack message formatting test
  - [ ] Budget threshold test
- [ ] Test notification routing
  - [ ] Daily budget → heartbeat
  - [ ] Monthly 80% → heartbeat
  - [ ] Monthly 100% → critical
- [ ] Test Slack interactive commands
  - [ ] @aws cloudwatch describe-alarms
  - [ ] @aws budgets describe-budgets
  - [ ] Read-only verification
- [ ] Test configuration updates
  - [ ] Change budget values
  - [ ] Redeploy
  - [ ] Verify updates
- [ ] Test dashboard
  - [ ] Verify all widgets render
  - [ ] Check metric queries
  - [ ] Test in us-east-1 and other regions
- [ ] Document test scenarios

#### Test Scenarios

1. **Fresh Deployment**
   - New AWS account
   - No existing resources
   - Complete setup from scratch

2. **Budget Threshold Crossing**
   - Artificially trigger budget alerts
   - Verify correct channel routing
   - Check message formatting

3. **Configuration Updates**
   - Change budget in config.yaml
   - Run make update
   - Verify budget updated without recreation

4. **Slack Commands**
   - Test read-only commands work
   - Verify write commands fail
   - Check error messages

5. **Multi-Region**
   - Deploy to non-us-east-1 region
   - Verify everything works except billing dashboard
   - Check graceful degradation

#### Deliverables

- Comprehensive test suite
- All tests passing
- Integration tests automated
- Test documentation
- Test scenarios validated

---

### Phase 10: Documentation 📋

**Status**: Not Started
**Estimated**: 3-4 hours

#### Tasks

- [ ] Create `docs/slack-setup.md`
  - [ ] Creating Slack channels
  - [ ] AWS Chatbot workspace setup
  - [ ] Finding Workspace and Channel IDs
  - [ ] Troubleshooting Slack issues
- [ ] Create `docs/integration-guide.md`
  - [ ] How to reference SNS topics
  - [ ] Example integrations (ECS, Lambda, etc.)
  - [ ] Message formatting guidelines
  - [ ] Best practices
- [ ] Create `docs/architecture.md`
  - [ ] Detailed architecture diagrams
  - [ ] Component interactions
  - [ ] Data flows
  - [ ] Security model
- [ ] Update main README.md
  - [ ] Quick start guide
  - [ ] Configuration reference
  - [ ] Troubleshooting
  - [ ] FAQ
- [ ] Create CONTRIBUTING.md
  - [ ] Development setup
  - [ ] Code style
  - [ ] Pull request process
  - [ ] Testing requirements
- [ ] Create LICENSE file (MIT)
- [ ] Add code comments and docstrings
  - [ ] All public functions
  - [ ] All CDK constructs
  - [ ] All stacks
  - [ ] Complex logic

#### Documentation Standards

- **Format**: Markdown
- **Style**: Clear, concise, example-driven
- **Diagrams**: ASCII art or Mermaid
- **Code Examples**: Complete and runnable
- **Assumptions**: State all prerequisites
- **Troubleshooting**: Common issues + solutions

#### Deliverables

- Complete documentation suite
- All guides written and reviewed
- Code fully commented
- Examples tested and working
- README comprehensive

---

### Phase 11: Deployment and Validation 📋

**Status**: Not Started
**Estimated**: 2-3 hours

#### Tasks

- [ ] Test deployment to fresh AWS account
- [ ] Validate all stacks deploy successfully
- [ ] Test notification flow end-to-end
- [ ] Verify Slack messages appear correctly
- [ ] Test interactive Slack commands
- [ ] Validate CloudWatch dashboard
- [ ] Test configuration updates
- [ ] Verify secrets management
- [ ] Test make commands
- [ ] Performance testing (deployment time)
- [ ] Clean up test resources

#### Validation Checklist

- [ ] All CDK stacks deploy without errors
- [ ] SNS topics created and subscribed
- [ ] Budget alerts configured correctly
- [ ] Slack channels receive notifications
- [ ] Critical/heartbeat routing works
- [ ] CloudWatch dashboard visible
- [ ] Dashboard widgets render correctly
- [ ] Slack commands work (read-only)
- [ ] Configuration updates work
- [ ] Secrets deployed successfully
- [ ] Email notifications work (if configured)
- [ ] All make commands execute
- [ ] Tests pass
- [ ] Documentation accurate

#### Deliverables

- Fully deployed and validated system
- All tests passing
- Documentation verified
- Known issues documented
- Ready for public release

---

## Risk Assessment

### Technical Risks

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| AWS Chatbot Slack integration requires manual setup | Medium | High | Clear documentation, screenshots |
| Billing metrics only in us-east-1 | Low | High | Graceful degradation, clear warnings |
| SNS email confirmation required | Low | High | Document in setup guide |
| CDK deployment permissions too broad | Medium | Medium | Minimal IAM policy, document restrictions |
| Budget threshold notifications delayed | Low | Medium | Document AWS Budgets behavior, set expectations |
| Cost of running the monitoring stack | Low | Low | Stack is very low cost (~$5-10/month) |

### Project Risks

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Slack workspace changes breaking integration | Medium | Low | Version lock Slack IDs, update docs |
| AWS Budgets API changes | Medium | Low | Use stable CDK constructs, monitor deprecations |
| DevContainer setup complexity | Low | Medium | Detailed setup guide, common issues documented |
| Configuration complexity for users | Medium | Medium | Sensible defaults, validation, examples |

## Success Criteria

### Functional Requirements

- [ ] Daily budget alerts sent to heartbeat channel
- [ ] Monthly 80% warnings sent to heartbeat channel
- [ ] Monthly 100% alerts sent to critical channel
- [ ] CloudWatch dashboard shows cost data
- [ ] Slack commands work (read-only)
- [ ] Configuration updates work without redeployment
- [ ] Email notifications work (if configured)

### Non-Functional Requirements

- [ ] Deployment completes in < 10 minutes
- [ ] Configuration updates in < 2 minutes
- [ ] Notifications arrive within 15 minutes of threshold
- [ ] Dashboard loads in < 5 seconds
- [ ] Cost of stack < $10/month
- [ ] Documentation complete and accurate
- [ ] Code coverage > 80%
- [ ] No secrets in code repository

### User Experience

- [ ] Setup guide clear and complete
- [ ] Configuration intuitive
- [ ] Error messages helpful
- [ ] Slack messages well-formatted
- [ ] Dashboard visually appealing
- [ ] Make commands obvious and simple

## Timeline

**Estimated Total**: 25-30 hours

- Phase 1 (Setup): 2-3 hours ✅ In Progress
- Phase 2 (SNS): 2-3 hours
- Phase 3 (Budgets): 3-4 hours
- Phase 4 (Chatbot): 3-4 hours
- Phase 5 (Monitoring): 3-4 hours
- Phase 6 (Config): 2 hours
- Phase 7 (Makefile): 2 hours
- Phase 8 (IAM): 2-3 hours
- Phase 9 (Testing): 3-4 hours
- Phase 10 (Docs): 3-4 hours
- Phase 11 (Validation): 2-3 hours

**Target Completion**: TBD

## Next Steps

**Immediate**:
1. Complete Phase 1 setup tasks
2. Initialize CDK project structure
3. Create configuration templates
4. Setup Makefile

**Short-term** (Next session):
1. Begin Phase 2 (SNS Stack)
2. Implement configuration loading
3. Write first unit tests

**Long-term**:
1. Complete all phases sequentially
2. Full integration testing
3. Public release

## Status Updates

### 2025-10-18 - Project Kickoff

- ✅ Research completed on AWS CDK + Chatbot integration
- ✅ Requirements clarified with user
- ✅ Documentation structure created (CLAUDE.md, README.md)
- ✅ Project plan created (this document)
- ⏳ Next: Complete Phase 1 setup tasks

---

## Appendix

### Key AWS Resources

- **AWS Budgets**: https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-managing-costs.html
- **AWS Chatbot**: https://docs.aws.amazon.com/chatbot/latest/adminguide/what-is.html
- **AWS CDK Python**: https://docs.aws.amazon.com/cdk/api/v2/python/
- **SNS**: https://docs.aws.amazon.com/sns/latest/dg/welcome.html
- **CloudWatch Billing**: https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/monitor_estimated_charges_with_cloudwatch.html

### Reference Projects

- https://github.com/lvthillo/cdk-slack-chatbot
- https://dev.to/talkncloud/aws-chatbot-and-aws-budget-with-slack-cdk-cf-39c1
- https://github.com/aws-samples/amazon-cloudwatch-alarms-repeated-notification-cdk

---

*This is a living document and will be updated as the project progresses.*
