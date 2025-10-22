# AWS Alert Intelligence System - Overview

## Vision Statement

**A LangGraph-powered AWS monitoring system that provides AI-driven diagnostics for critical alerts and supports interactive investigation via Slack, deployable as a reusable CDK template.**

---

## Project Goals

### Primary Objectives

1. **Intelligent Alert Analysis**
   - Automatically analyze critical AWS alerts (budget overruns, CloudWatch alarms, errors)
   - Provide actionable diagnostics and remediation suggestions
   - Reduce time-to-resolution for AWS issues

2. **Cost Optimization**
   - Replace expensive solutions (Amazon Q Developer: $19/user/month)
   - Target cost: ~$1-2/month (Phase 1), ~$5-8/month (Phase 2)
   - Only invoke LLM for critical alerts, skip routine reports

3. **Extensibility Beyond Cost Monitoring**
   - Support any AWS alert type (not just billing)
   - Handle CloudWatch alarms, custom error events, infrastructure issues
   - Modular tool architecture for easy expansion

4. **Deployability as Template**
   - Clean, well-documented CDK code
   - Easy deployment to any AWS account
   - Configuration-driven (minimal code changes needed)
   - Suitable for open source release

5. **Progressive Enhancement**
   - Phase 1: One-shot AI analysis of critical alerts
   - Phase 2: Interactive Slack bot for investigation
   - Phase 3+: Multi-agent collaboration, human-in-the-loop workflows

---

## Key Differentiators

### vs. AWS Chatbot
- ❌ **AWS Chatbot**: Filters message types, reformats output, no AI, limited functionality
- ✅ **This System**: Full control, AI-powered analysis, beautiful formatting, extensible

### vs. Amazon Q Developer
- ❌ **Amazon Q**: $19/user/month, proprietary, limited to Q's capabilities
- ✅ **This System**: ~$5-8/month, open source, customizable agents and tools

### vs. Existing GitHub Solutions
- ❌ **Existing**: Cost monitoring OR AI chatbots, not both
- ✅ **This System**: Combines cost monitoring + AI analysis + interactive investigation

---

## Design Principles

### 1. **Cost-Conscious by Default**
- Only analyze alerts that matter (warnings, errors, critical events)
- Skip LLM for routine reports (daily budget summaries, info-level alerts)
- Use serverless architecture (pay only for what you use)
- Optimize conversation storage (DynamoDB TTL, S3 archival)

### 2. **Separation of Concerns**
- **Critical Channel**: High-priority alerts with AI analysis
- **Heartbeat Channel**: Routine reports, can tag bot for investigation
- Clear routing rules for what gets analyzed vs. what gets passed through

### 3. **Modular & Extensible**
- Tools organized by category (cost, compute, storage, logging, infrastructure)
- Easy to add new tools without changing agent code
- LangGraph workflow automatically discovers available tools

### 4. **Human-in-the-Loop**
- AI suggests, humans decide
- No automated remediation without approval
- Interactive investigation in Phase 2

### 5. **Production-Ready**
- Comprehensive error handling
- Logging and observability
- Cost tracking and alerts
- Security best practices (IAM least privilege, secrets management)

---

## Use Cases

### Phase 1: Automated Alert Analysis

**Scenario 1: Budget Alert**
```
Trigger: Monthly budget exceeds 80%

Traditional Flow:
1. Generic SNS email: "Budget exceeded"
2. User manually checks Cost Explorer
3. User runs various CLI commands
4. User analyzes data
5. User determines root cause
Time: 30-60 minutes

With AI Intelligence:
1. Alert triggers LangGraph agent
2. Agent gathers cost context (top services, trends, anomalies)
3. Claude analyzes and generates diagnostics
4. Formatted Slack message with:
   - Root cause analysis
   - Specific diagnostic commands
   - Remediation suggestions
Time: < 2 minutes, automated
```

**Scenario 2: Lambda Error Spike**
```
Trigger: CloudWatch alarm - Lambda error rate > 50%

Traditional Flow:
1. Alert received
2. User checks CloudWatch metrics
3. User searches logs
4. User correlates errors
5. User investigates upstream dependencies
Time: 15-30 minutes

With AI Intelligence:
1. Alert triggers agent
2. Agent gathers Lambda metrics, logs, related resources
3. Claude identifies pattern (retry loop, dependency failure, etc.)
4. Slack message with:
   - Error pattern analysis
   - Related resources affected
   - Suggested fixes
Time: < 2 minutes, automated
```

### Phase 2: Interactive Investigation

**Scenario 3: Cost Spike Investigation**
```
User in Slack: @aws-assistant why did costs spike 3x this week?

Agent:
1. Classifies question (cost analysis)
2. Routes to CostAnalyst agent
3. Executes relevant tools:
   - get_cost_breakdown(last_week)
   - get_service_costs(lambda)
   - get_lambda_metrics(top_functions)
4. Identifies spike: ImageProcessor function
5. Responds with analysis

User: Show me the logs

Agent:
1. Routes to LogsAnalyst agent
2. Executes: get_cloudwatch_logs(ImageProcessor, hours=24)
3. Identifies retry loop
4. Responds with findings + suggested fix

User: Create a runbook for this

Agent:
1. Generates runbook document
2. Saves to S3 or creates Confluence page
3. Returns link

Total time: 2-3 minutes vs. 1-2 hours manual investigation
```

---

## Success Metrics

### Phase 1 (Automated Analysis)
- ✅ Alert-to-diagnosis time: < 2 minutes (vs. 30-60 min manual)
- ✅ Monthly cost: < $2 (vs. $19 for Amazon Q)
- ✅ Accuracy: 90%+ relevant diagnostic suggestions
- ✅ Deployment time: < 30 minutes for new accounts

### Phase 2 (Interactive)
- ✅ Question-to-answer time: < 30 seconds
- ✅ Multi-turn conversation success: 80%+ satisfactory resolutions
- ✅ Monthly cost: < $10 (vs. $19 for Amazon Q)
- ✅ User satisfaction: "Helpful" rating on 80%+ interactions

---

## Phased Rollout

### Phase 1: Intelligent Critical Alerts (Weeks 1-2)
**Scope:**
- LangGraph agent for one-shot alert analysis
- Core tools: cost, Lambda, logs, EC2
- Slack webhook integration
- Critical alerts only (skip daily reports)

**Deliverables:**
- Working CDK stack
- 5-6 AWS tools
- Alert analyzer Lambda with LangGraph
- Documentation for deployment

**Target Users:**
- Single AWS account owner
- Teams wanting automated cost alerts

---

### Phase 2: Interactive Investigation (Weeks 3-4)
**Scope:**
- Slack Socket Mode bot
- Conversation state management (DynamoDB)
- Multi-turn interactions
- Tag bot in heartbeat channel

**Deliverables:**
- Chat handler Lambda
- DynamoDB conversation store
- Extended tool library (10+ tools)
- Interactive documentation

**Target Users:**
- Teams needing deep AWS investigation
- DevOps/FinOps teams

---

### Phase 3: Advanced Features (Future)
**Potential additions:**
- Multi-agent collaboration (supervisor + specialist agents)
- Human-in-the-loop approvals for remediation
- Automated runbook generation
- Integration with ticketing systems (Jira, ServiceNow)
- Custom alert rules engine
- Cost forecasting and optimization recommendations
- Security findings analysis
- Compliance violation alerts

---

## Non-Goals (Out of Scope)

### What This System Will NOT Do

1. **Automated Remediation Without Approval**
   - No auto-scaling, no auto-shutdowns, no auto-deletions
   - AI suggests, humans approve and execute
   - Safety first

2. **Replace AWS Console/CLI**
   - This is a diagnostic assistant, not a replacement for AWS tools
   - Deep investigation still requires Console/CLI access
   - Complements, doesn't replace

3. **General-Purpose Chatbot**
   - Focused on AWS operations and cost management
   - Not a knowledge base chatbot
   - Not a coding assistant (use Claude Code for that)

4. **Real-Time Monitoring Dashboard**
   - Not building Grafana/Datadog replacement
   - Focuses on alerts and investigation, not visualization
   - Use CloudWatch dashboards for real-time metrics

5. **Multi-Cloud Support (Initially)**
   - Phase 1-2: AWS only
   - Future: Could extend to GCP, Azure
   - Focus on doing AWS well first

---

## Technology Stack

### Core Technologies
- **Infrastructure**: AWS CDK (Python)
- **Compute**: AWS Lambda (Python 3.12)
- **AI Framework**: LangChain + LangGraph
- **LLM**: Claude 3.5 Sonnet (via AWS Bedrock)
- **Messaging**: Slack (webhooks for Phase 1, Socket Mode for Phase 2)
- **Storage**: DynamoDB (conversations), S3 (archives)
- **Orchestration**: EventBridge, SNS

### Why These Choices?

**LangChain + LangGraph:**
- Industry standard for AI agents
- Excellent tool integration
- Built-in memory and state management
- Active community and documentation

**AWS Bedrock (vs. Anthropic Direct API):**
- No additional vendor account needed
- Integrated with AWS IAM
- Same pricing as direct API
- Easier for AWS-focused deployments
- Option to switch to direct API if needed

**Slack:**
- Popular team communication platform
- Good webhook and bot APIs
- Block Kit for rich formatting
- Familiar to most teams

**Serverless Architecture:**
- Pay only for what you use
- Auto-scaling
- Low maintenance
- Cost-effective for sporadic alerts

---

## Documentation Structure

```
phase2-docs/
├── OVERVIEW.md           # This file - vision, goals, principles
├── ARCHITECTURE.md       # System design, component diagrams
├── PHASE1.md            # Phase 1 detailed design (one-shot analysis)
├── PHASE2.md            # Phase 2 detailed design (interactive)
├── TOOLS.md             # Tool specifications and development guide
├── AGENTS.md            # LangGraph workflow designs
├── DEPLOYMENT.md        # Setup and configuration guide
├── COST_ANALYSIS.md     # Detailed cost breakdown
└── PROJECT_STRUCTURE.md # File/folder organization
```

---

## Next Steps

1. **Review and Iterate** on this design
2. **Refine** based on feedback
3. **Finalize** architecture decisions
4. **Build** Phase 1 incrementally
5. **Test** with real alerts
6. **Document** learnings
7. **Deploy** to production
8. **Iterate** to Phase 2

---

## Questions for Discussion

1. **Alert Routing**: Is the critical/heartbeat channel split the right approach?
2. **LLM Provider**: Bedrock vs. Direct Anthropic API?
3. **Tool Scope**: Which AWS services should we prioritize for tools?
4. **Conversation Storage**: DynamoDB + S3 vs. alternatives?
5. **Deployment**: CDK vs. Terraform vs. SAM?
6. **Open Source**: MIT license? Apache 2.0?
7. **Testing**: How to test LangGraph agents effectively?

---

**Status:** Design Phase
**Last Updated:** 2025-10-21
**Next Review:** After initial feedback
