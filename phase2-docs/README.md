# AWS Alert Intelligence System - Design Documentation

**Status:** 🟡 Design Phase - Iteration in Progress
**Version:** 0.1.0
**Last Updated:** 2025-10-21

---

## What Is This?

This folder contains comprehensive design documentation for **rebuilding the AWS monitoring system with AI-powered analysis**.

**The Problem:** AWS Chatbot is limiting our capabilities - it filters messages, reformats output, provides no AI analysis, and costs $19/month for basic natural language features.

**The Solution:** Build our own LangGraph-powered system that analyzes AWS alerts with Claude AI, provides actionable diagnostics, and supports interactive investigation via Slack - all for ~$3-10/month.

---

## Documentation Structure

### Start Here

**[OVERVIEW.md](OVERVIEW.md)** - Vision, goals, and project scope
- Why we're building this
- What problems it solves
- Success metrics
- Phased rollout plan

### System Design

**[ARCHITECTURE.md](ARCHITECTURE.md)** - High-level system architecture
- Component diagrams
- Phase 1 (one-shot analysis) design
- Phase 2 (interactive bot) design
- LangGraph workflow structure
- Security and IAM
- Monitoring strategy

**[STORAGE_COMPARISON.md](STORAGE_COMPARISON.md)** - Storage cost analysis
- DynamoDB vs. S3 vs. ElastiCache
- Cost breakdown per solution
- Performance comparison
- **Recommendation:** DynamoDB On-Demand

### Implementation Plans

**[PHASE1.md](PHASE1.md)** - Phase 1 detailed implementation
- One-shot AI analysis of critical alerts
- Alert routing rules
- LangGraph workflow (5 nodes)
- Lambda handler implementation
- Testing strategy
- Expected costs: **$1.42/month**

**[TOOLS.md](TOOLS.md)** - AWS tools library specifications
- 11 tools for Phase 1
- Cost, compute, logging, infrastructure tools
- Implementation examples
- Tool development guide
- Future tools (git integration, security)

### Operations

**[COST_ANALYSIS.md](COST_ANALYSIS.md)** - Detailed cost breakdown
- Component-by-component cost analysis
- Scaling projections (10, 50, 100 alerts/month)
- DynamoDB cost expectations
- Comparison to Amazon Q Developer
- Optimization strategies
- **Key Finding:** 60-85% cheaper than alternatives

**[DEPLOYMENT.md](DEPLOYMENT.md)** - Step-by-step deployment guide
- Prerequisites
- AWS and Slack setup
- Configuration
- Deployment commands
- Testing procedures
- Troubleshooting

---

## Quick Decision Summary

### Confirmed Decisions ✅

1. **Start with AWS tools only** (defer git integration)
2. **11 core tools for Phase 1:**
   - Cost: get_cost_breakdown, get_service_costs, get_budget_status, get_cost_forecast
   - Compute: get_lambda_metrics, get_lambda_errors, get_ec2_instances
   - Logging: get_cloudwatch_logs, search_logs
   - Infrastructure: get_resource_tags, get_recent_changes

3. **DynamoDB On-Demand for conversation storage** (Phase 2)
   - Cost: ~$0.01/month (negligible)
   - Fast, simple, serverless

4. **Cost-optimized architecture:**
   - Only analyze critical alerts (≥80% budget, ERROR alarms)
   - Skip daily reports (no LLM cost)
   - Expected: $1.42/month (Phase 1), $5-10/month (Phase 2)

### Open Questions ❓

- Which specific CloudWatch alarms to analyze?
- Should we keep AWS Chatbot during transition (hybrid approach)?
- Custom alert patterns to support?
- Detailed Slack message format preferences?

---

## Key Insights from Design

### 1. Cost is NOT a Concern

**Storage:** DynamoDB costs < $0.10/month even at 10x expected scale
**Biggest cost:** Claude API (~70% of total), still only $5-10/month
**Comparison:** 60-85% cheaper than Amazon Q Developer

**Decision:** Don't over-optimize storage. Use DynamoDB for simplicity.

### 2. LLM Analysis is the Real Value

**Without AI:**
- Generic alert: "Budget exceeded"
- User investigates manually: 30-60 minutes

**With AI:**
- Root cause analysis
- Specific diagnostic commands
- Remediation suggestions
- Investigation time: < 2 minutes

**Value:** 15-30x faster issue resolution

### 3. Code/Repo Integration is Game-Changing

**Original idea:** Basic AWS tools
**Your insight:** Analyze git repos and Lambda code

**Impact:**
- Correlate code changes with cost spikes
- Identify buggy commits automatically
- Provide specific code fixes

**Priority:** Phase 3 (after Phase 1/2 working)

### 4. Modular Tool Architecture Enables Growth

**Phase 1:** 11 AWS tools
**Phase 2:** Add conversation tools
**Phase 3:** Add git/code tools
**Phase 4:** Add security tools (Security Hub, GuardDuty)

**Each addition is independent** - no need to redesign core system

---

## What's Different from Current System?

| Feature | AWS Chatbot (Current) | AI Alert Intelligence (Proposed) |
|---------|----------------------|-----------------------------------|
| **Message Filtering** | Filters out plain SNS | Accepts all event types |
| **Formatting** | Rigid CloudWatch format | Custom, beautiful Slack blocks |
| **AI Analysis** | None | Claude-powered diagnostics |
| **Diagnostic Suggestions** | None | Auto-generated AWS CLI commands |
| **Interactive Queries** | Basic CLI only ($19/month extra) | Natural language (Phase 2) |
| **Cost** | $0 (basic) or $19/month (Q) | $3-10/month (all features) |
| **Customization** | Limited | Full control |
| **Root Cause Analysis** | None | Automated |
| **Code Integration** | No | Yes (future) |

---

## Project Timeline

### Phase 1: Intelligent Critical Alerts
**Duration:** 2-3 days
**Deliverables:**
- LangGraph alert analyzer
- 11 AWS tools
- Slack integration
- CDK deployment stack
- Documentation

**Success Criteria:**
- Alert-to-Slack < 60 seconds
- 80%+ relevant suggestions
- Cost < $2/month
- Error rate < 5%

### Phase 2: Interactive Investigation
**Duration:** 1 week (when ready)
**Deliverables:**
- Slack Socket Mode bot
- DynamoDB conversation storage
- Multi-turn interaction support
- Extended tool library

**Success Criteria:**
- Question-to-answer < 30 seconds
- 80%+ satisfactory resolutions
- Cost < $10/month

### Phase 3: Advanced Features
**Duration:** TBD
**Potential Features:**
- Git/code integration
- Multi-agent collaboration
- Human-in-the-loop workflows
- Security analysis tools
- Runbook generation

---

## How to Use This Documentation

### For Reviewers
1. Read **OVERVIEW.md** - understand the vision
2. Read **COST_ANALYSIS.md** - verify cost expectations
3. Review **ARCHITECTURE.md** - check system design
4. Provide feedback on open questions

### For Implementers
1. Read **OVERVIEW.md** and **ARCHITECTURE.md** - big picture
2. Study **PHASE1.md** - implementation details
3. Reference **TOOLS.md** - tool specifications
4. Follow **DEPLOYMENT.md** - step-by-step setup

### For Operators
1. **DEPLOYMENT.md** - how to deploy
2. **COST_ANALYSIS.md** - cost expectations
3. **OVERVIEW.md** - success metrics
4. **ARCHITECTURE.md** → Monitoring section

---

## Next Steps

### Immediate (This Week)
1. ✅ **Review design docs** (you are here!)
2. ⏳ **Provide feedback** - what needs refinement?
3. ⏳ **Decide:** Proceed with implementation or iterate more?

### After Design Approval
1. Create CDK stack structure
2. Implement LangGraph workflow
3. Build 5-6 core tools (start simple)
4. Deploy to dev environment
5. Test with real alerts
6. Iterate based on results

---

## Questions for Discussion

**Before we proceed with implementation:**

1. **Alert Routing:**
   - Is critical/heartbeat channel split correct?
   - What specific thresholds should trigger AI analysis?

2. **Tool Priority:**
   - Which 5-6 tools should we build first?
   - Any critical tools missing from the list?

3. **LLM Provider:**
   - AWS Bedrock (integrated) vs. Direct Anthropic API?
   - Claude 3.5 Sonnet vs. Haiku for simple queries?

4. **Migration Strategy:**
   - Keep AWS Chatbot during transition (hybrid)?
   - Or full replacement from day 1?

5. **Success Metrics:**
   - What defines "good enough" AI analysis?
   - How to measure time saved vs. manual investigation?

6. **Future Features:**
   - Priority order for Phase 2/3 features?
   - Git integration: must-have or nice-to-have?

---

## Design Principles (Reference)

### Cost-Conscious by Default
- Only analyze what matters
- Optimize for token usage
- Use serverless (pay per use)

### Separation of Concerns
- Critical vs. heartbeat channels
- Clear routing rules
- Modular tool architecture

### Modularity & Extensibility
- Easy to add new tools
- LangGraph auto-discovers tools
- Independent feature development

### Human-in-the-Loop
- AI suggests, humans decide
- No auto-remediation (Phase 1-2)
- Interactive approval flow (Phase 3)

### Production-Ready
- Comprehensive error handling
- Logging and observability
- Security best practices
- Cost tracking and alerts

---

## Document Status

| Document | Status | Last Updated | Needs Review |
|----------|--------|--------------|--------------|
| OVERVIEW.md | ✅ Complete | 2025-10-21 | ⏳ Yes |
| ARCHITECTURE.md | ✅ Complete | 2025-10-21 | ⏳ Yes |
| STORAGE_COMPARISON.md | ✅ Complete | 2025-10-21 | ⏳ Yes |
| PHASE1.md | ✅ Complete | 2025-10-21 | ⏳ Yes |
| TOOLS.md | ✅ Complete | 2025-10-21 | ⏳ Yes |
| COST_ANALYSIS.md | ✅ Complete | 2025-10-21 | ⏳ Yes |
| DEPLOYMENT.md | ✅ Complete | 2025-10-21 | ⏳ Yes |

---

## Feedback

**How to provide feedback:**

1. **Inline comments** - Edit docs with suggestions
2. **Questions file** - Create `QUESTIONS.md` with your questions
3. **Discussion** - Talk through concerns
4. **Iteration** - Request changes to specific sections

**What we need:**
- Technical accuracy review
- Cost estimate validation
- Architecture feasibility check
- Tool prioritization input
- Implementation approach confirmation

---

## Getting Started with Implementation

**Once design is approved:**

```bash
# 1. Update project structure
mkdir -p cdk/lambda/alert_analyzer/{agents,tools}
mkdir -p tests/fixtures

# 2. Install dependencies
pip install langchain langgraph langchain-aws boto3

# 3. Start with simple proof-of-concept
# - Build 2-3 core tools
# - Create basic LangGraph workflow
# - Test with mocked data

# 4. Iterate from there
```

---

## Related Documentation

**Existing Project Docs:**
- `/workspace/docs/SETUP.md` - Current system setup
- `/workspace/docs/TROUBLESHOOTING.md` - Current troubleshooting
- `/workspace/docs/deployment-checklist.md` - Current deployment

**External References:**
- [LangChain Docs](https://python.langchain.com/)
- [LangGraph Docs](https://langchain-ai.github.io/langgraph/)
- [AWS Bedrock Docs](https://docs.aws.amazon.com/bedrock/)
- [Claude API Docs](https://docs.anthropic.com/)

---

## Contact & Support

**Questions?**
- Review the docs first
- Check open questions section
- Discuss with team

**Found an issue in docs?**
- Note it in feedback
- Suggest improvements
- Help make docs better!

---

**Let's build something awesome!** 🚀

The current AWS Chatbot approach is limiting us. This new system will provide:
- 15-30x faster issue resolution
- 60-85% cost savings
- Full customization and control
- AI-powered diagnostics
- Extensible architecture for future growth

**Next:** Review, provide feedback, decide to proceed! ✅
