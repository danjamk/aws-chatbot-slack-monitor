# System Architecture

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                          AWS ACCOUNT                                │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    ALERT SOURCES                             │  │
│  ├──────────────────────────────────────────────────────────────┤  │
│  │  • AWS Budgets (warnings, critical)                         │  │
│  │  • CloudWatch Alarms (errors, warnings, info)               │  │
│  │  • Custom Events (application errors, business logic)       │  │
│  │  • AWS Health Events                                        │  │
│  │  • Security Hub Findings                                    │  │
│  └────────────────────────┬─────────────────────────────────────┘  │
│                           │                                         │
│                           ▼                                         │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                SNS TOPICS (Routing Layer)                    │  │
│  ├──────────────────────────────────────────────────────────────┤  │
│  │  critical-alerts    │  heartbeat-alerts                      │  │
│  │  (analyze with AI)  │  (pass through or on-demand)           │  │
│  └─────────┬──────────────────────┬──────────────────────────────┘  │
│            │                      │                                 │
│            ▼                      ▼                                 │
│  ┌──────────────────┐   ┌──────────────────────────┐              │
│  │  EventBridge Rule│   │  EventBridge Rule        │              │
│  │  (Critical)      │   │  (Heartbeat - Phase 2)   │              │
│  └────────┬─────────┘   └───────────┬──────────────┘              │
│           │                         │                              │
│           ▼                         │                              │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │              PHASE 1: Alert Analyzer Lambda                  │  │
│  ├──────────────────────────────────────────────────────────────┤  │
│  │  • Receives critical alerts                                  │  │
│  │  • Runs LangGraph workflow                                   │  │
│  │  • Executes AWS tools (boto3)                                │  │
│  │  • Calls Claude via Bedrock                                  │  │
│  │  • Formats Slack message                                     │  │
│  │  • Posts to webhook                                          │  │
│  └─────────┬────────────────────────────────────────────────────┘  │
│            │                                                        │
│            ├─────► AWS Bedrock (Claude 3.5 Sonnet)                 │
│            │                                                        │
│            └─────► Slack Webhooks                                  │
│                      │                                              │
└──────────────────────┼──────────────────────────────────────────────┘
                       │
                       ▼
         ┌──────────────────────────┐
         │     SLACK WORKSPACE      │
         ├──────────────────────────┤
         │  #aws-critical-alerts    │  ← Phase 1: AI analyzed alerts
         │  #aws-heartbeat          │  ← Phase 2: Tag bot for help
         └──────────────────────────┘
```

---

## Phase 1 Architecture (One-Shot Analysis)

### Components

```
┌──────────────────────────────────────────────────────────────┐
│                   AlertAnalyzer Lambda                       │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │              LangGraph Workflow                        │ │
│  │                                                        │ │
│  │  1. Classify Alert Node                               │ │
│  │     ↓                                                  │ │
│  │  2. Gather Context Node ────► AWS Tools               │ │
│  │     ↓                                                  │ │
│  │  3. Analyze with LLM Node ──► Claude API              │ │
│  │     ↓                                                  │ │
│  │  4. Format Response Node                              │ │
│  │     ↓                                                  │ │
│  │  5. Post to Slack Node                                │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │                   AWS Tools                            │ │
│  │  ┌────────────┬──────────────┬─────────────────────┐  │ │
│  │  │ Cost Tools │ Compute Tools│ Logging Tools       │  │ │
│  │  └────────────┴──────────────┴─────────────────────┘  │ │
│  └────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

### Data Flow (Phase 1)

```
Budget Alert Triggered
       │
       ▼
SNS: critical-alerts
       │
       ▼
EventBridge Rule
       │
       ▼
Lambda: AlertAnalyzer
       │
       ├─► [Node 1] Classify Alert
       │   └─► Type: "budget_warning"
       │
       ├─► [Node 2] Gather Context
       │   ├─► get_cost_breakdown(last_7_days)
       │   ├─► get_service_costs(top=5)
       │   └─► get_budget_status()
       │   Result: {total: $305, top: [Lambda: $180, S3: $50, ...]}
       │
       ├─► [Node 3] Analyze with LLM
       │   Input: Alert + Context
       │   LLM: Claude 3.5 Sonnet
       │   Output: {
       │     root_cause: "Lambda costs spiked 300%",
       │     diagnostics: ["aws ce get-cost-and-usage ...", ...],
       │     recommendations: ["Check ImageProcessor function", ...]
       │   }
       │
       ├─► [Node 4] Format Response
       │   Creates Slack Block Kit JSON
       │
       └─► [Node 5] Post to Slack
           Webhook: critical-alerts channel

User sees formatted alert in Slack
```

---

## Phase 2 Architecture (Interactive)

### Additional Components

```
┌──────────────────────────────────────────────────────────────┐
│                 Slack Socket Mode Integration                │
│                                                              │
│  User in Slack: "@aws-assistant why did costs spike?"       │
│         │                                                    │
│         ▼                                                    │
│  Slack API (Socket Mode WebSocket)                          │
│         │                                                    │
│         ▼                                                    │
│  API Gateway (WebSocket or REST)                            │
│         │                                                    │
│         ▼                                                    │
│  ┌──────────────────────────────────────────────────┐       │
│  │        ChatHandler Lambda                        │       │
│  │                                                  │       │
│  │  1. Validate Slack event                        │       │
│  │  2. Load conversation from DynamoDB              │       │
│  │  3. Add user message to conversation             │       │
│  │  4. Run LangGraph multi-agent workflow          │       │
│  │  5. Save conversation to DynamoDB                │       │
│  │  6. Post response to Slack                       │       │
│  └──────────────────────────────────────────────────┘       │
│         │                                                    │
│         ├─► DynamoDB (Conversation State)                   │
│         ├─► S3 (Archived Conversations)                     │
│         └─► Bedrock (Claude)                                │
└──────────────────────────────────────────────────────────────┘
```

### Conversation Flow (Phase 2)

```
User: "@aws-assistant why did Lambda costs spike?"
  │
  ▼
Slack Event → API Gateway → ChatHandler Lambda
  │
  ├─► Load conversation from DynamoDB
  │   (check if existing conversation or new)
  │
  ├─► LangGraph Supervisor Agent
  │   │
  │   ├─► Classify question: "cost analysis"
  │   │
  │   ├─► Route to: CostAnalyst Agent
  │   │   │
  │   │   ├─► Execute: get_cost_breakdown()
  │   │   ├─► Execute: get_lambda_metrics()
  │   │   └─► Analyze: "ImageProcessor spiked 1000x"
  │   │
  │   └─► Format response
  │
  ├─► Save to DynamoDB:
  │   {
  │     conversation_id: "user123-2025-10-21",
  │     messages: [
  │       {role: "user", content: "why did Lambda costs spike?"},
  │       {role: "assistant", content: "ImageProcessor function..."}
  │     ],
  │     ttl: timestamp + 7 days
  │   }
  │
  └─► Post to Slack

User sees response + can continue conversation
```

---

## LangGraph Workflow Design

### Phase 1: Linear Workflow

```python
from langgraph.graph import StateGraph, END

# Define workflow
workflow = StateGraph()

# Add nodes
workflow.add_node("classify_alert", classify_alert_node)
workflow.add_node("gather_context", gather_context_node)
workflow.add_node("analyze", analyze_with_llm_node)
workflow.add_node("format_response", format_slack_message_node)

# Define edges (linear flow)
workflow.set_entry_point("classify_alert")
workflow.add_edge("classify_alert", "gather_context")
workflow.add_edge("gather_context", "analyze")
workflow.add_edge("analyze", "format_response")
workflow.add_edge("format_response", END)

# Compile
agent = workflow.compile()
```

**State Schema:**
```python
class AlertState(TypedDict):
    # Input
    alert_type: str              # "budget_warning", "cloudwatch_alarm", etc.
    alert_data: dict             # Raw SNS/EventBridge payload

    # Processing
    context: dict                # Gathered AWS data
    analysis: dict               # LLM analysis result

    # Output
    slack_message: dict          # Slack Block Kit JSON
```

### Phase 2: Multi-Agent Workflow

```python
from langgraph.prebuilt import create_react_agent

# Create specialist agents
cost_agent = create_react_agent(
    llm,
    tools=[get_cost_breakdown, get_budget_status, ...],
    name="CostAnalyst"
)

infrastructure_agent = create_react_agent(
    llm,
    tools=[get_ec2_instances, get_lambda_functions, ...],
    name="InfraExpert"
)

logs_agent = create_react_agent(
    llm,
    tools=[get_cloudwatch_logs, search_logs, ...],
    name="LogsAnalyst"
)

# Supervisor workflow
supervisor = StateGraph()
supervisor.add_node("supervisor", supervisor_node)
supervisor.add_node("cost_agent", cost_agent)
supervisor.add_node("infra_agent", infrastructure_agent)
supervisor.add_node("logs_agent", logs_agent)

# Conditional routing
def route_to_agent(state):
    question_type = classify_question(state["user_message"])
    if question_type == "cost":
        return "cost_agent"
    elif question_type == "infrastructure":
        return "infra_agent"
    elif question_type == "logs":
        return "logs_agent"
    else:
        return "supervisor"  # Supervisor handles general questions

supervisor.add_conditional_edges(
    "supervisor",
    route_to_agent,
    {
        "cost_agent": "cost_agent",
        "infra_agent": "infra_agent",
        "logs_agent": "logs_agent",
        "supervisor": "supervisor",
        END: END
    }
)
```

---

## Storage Architecture

### DynamoDB Schema (Phase 2)

**Table: Conversations**
```
Primary Key: conversation_id (String)
Sort Key: timestamp (Number)

Attributes:
{
  "conversation_id": "user_U123ABC_2025-10-21",
  "user_id": "U123ABC",
  "channel_id": "C456DEF",
  "messages": [
    {
      "role": "user",
      "content": "Why did costs spike?",
      "timestamp": 1729512000
    },
    {
      "role": "assistant",
      "content": "Lambda function ImageProcessor...",
      "timestamp": 1729512005,
      "tools_used": ["get_cost_breakdown", "get_lambda_metrics"]
    }
  ],
  "created_at": 1729512000,
  "updated_at": 1729512005,
  "ttl": 1730116800,  # 7 days from creation
  "status": "active"  # active, archived, completed
}
```

**DynamoDB Configuration:**
- Billing Mode: On-Demand (pay per request)
- TTL Enabled: Yes (auto-delete after 7 days)
- Stream Enabled: Yes (for archival to S3)

**Cost Estimate:**
- 50 conversations/month × 5 messages each = 250 reads + 250 writes
- On-Demand: $0.25 per million reads, $1.25 per million writes
- **Monthly cost: < $1**

### S3 Schema (Phase 2 - Archival)

**Bucket: aws-alert-intelligence-archives**

```
s3://aws-alert-intelligence-archives/
├── conversations/
│   ├── year=2025/
│   │   ├── month=10/
│   │   │   ├── day=21/
│   │   │   │   ├── user_U123ABC_2025-10-21-14-30-00.json
│   │   │   │   └── user_U456DEF_2025-10-21-15-45-00.json
│   │   │   └── ...
│   │   └── ...
│   └── ...
└── metadata/
    └── conversation_index.json
```

**Lifecycle Policy:**
- 0-30 days: S3 Standard
- 30-90 days: S3 Standard-IA
- 90+ days: Glacier Flexible Retrieval
- 365+ days: Delete

**Cost Estimate:**
- 50 conversations/month × 10KB each = 500KB/month
- S3 Standard: $0.023/GB = ~$0.01/month
- **Negligible cost**

---

## Security Architecture

### IAM Roles and Permissions

**AlertAnalyzer Lambda Role:**
```yaml
Permissions:
  - Cost Explorer: Read (ce:GetCostAndUsage, ce:GetCostForecast)
  - CloudWatch: Read (cloudwatch:GetMetricData, logs:StartQuery)
  - Lambda: Read (lambda:ListFunctions, lambda:GetFunction)
  - EC2: Read (ec2:DescribeInstances)
  - S3: Read (s3:ListBucket, s3:GetObject)
  - Bedrock: InvokeModel (bedrock:InvokeModel)
  - Secrets Manager: Read (secretsmanager:GetSecretValue)
  - Logs: Write (logs:CreateLogGroup, logs:PutLogEvents)
```

**ChatHandler Lambda Role (Phase 2):**
```yaml
Additional Permissions:
  - DynamoDB: Read/Write (dynamodb:GetItem, dynamodb:PutItem)
  - S3: Write (s3:PutObject for archival)
```

### Secrets Management

**Slack Webhooks (Phase 1):**
```
AWS Secrets Manager:
  - Secret Name: aws-alert-intel/prod/slack-critical
    Value: {"webhook_url": "https://hooks.slack.com/..."}

  - Secret Name: aws-alert-intel/prod/slack-heartbeat
    Value: {"webhook_url": "https://hooks.slack.com/..."}
```

**Slack Bot Token (Phase 2):**
```
AWS Secrets Manager:
  - Secret Name: aws-alert-intel/prod/slack-bot
    Value: {
      "bot_token": "xoxb-...",
      "app_token": "xapp-..."
    }
```

### Network Security

- **Lambda VPC**: Optional (only if accessing VPC resources)
- **API Gateway**: Public endpoint with AWS IAM auth
- **Secrets Manager**: VPC endpoint if Lambda in VPC
- **Bedrock**: VPC endpoint if Lambda in VPC

---

## Monitoring and Observability

### CloudWatch Metrics

**Custom Metrics:**
```python
# Alert analyzer metrics
cloudwatch.put_metric_data(
    Namespace='AWSAlertIntelligence',
    MetricData=[
        {
            'MetricName': 'AlertsAnalyzed',
            'Value': 1,
            'Unit': 'Count',
            'Dimensions': [
                {'Name': 'AlertType', 'Value': 'budget_warning'}
            ]
        },
        {
            'MetricName': 'AnalysisLatency',
            'Value': execution_time_ms,
            'Unit': 'Milliseconds'
        },
        {
            'MetricName': 'LLMTokensUsed',
            'Value': tokens,
            'Unit': 'Count'
        }
    ]
)
```

### CloudWatch Dashboards

**Alert Intelligence Dashboard:**
- Alerts analyzed (count over time)
- Analysis latency (p50, p95, p99)
- LLM costs (estimated from tokens)
- Tool execution counts
- Error rates
- Conversation counts (Phase 2)

### Logging Strategy

**Structured Logging:**
```python
import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def log_event(event_type, **kwargs):
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "event_type": event_type,
        **kwargs
    }
    logger.info(json.dumps(log_entry))

# Usage
log_event("alert_received", alert_type="budget_warning", account_id="123456789012")
log_event("tool_executed", tool_name="get_cost_breakdown", duration_ms=450)
log_event("llm_called", model="claude-3-5-sonnet", tokens_in=1500, tokens_out=800)
```

### Alerting on the Alert System

**Meta-Alerts:**
- Alert Analyzer failure rate > 10%
- Average latency > 30 seconds
- Daily LLM cost > $5
- DynamoDB throttling (Phase 2)

---

## Deployment Architecture

### CDK Stack Organization

```
cdk/
├── app.py                          # CDK app entry point
├── stacks/
│   ├── sns_stack.py                # SNS topics
│   ├── alert_analyzer_stack.py     # Phase 1: Alert analyzer Lambda
│   ├── chat_handler_stack.py       # Phase 2: Interactive bot
│   ├── storage_stack.py            # Phase 2: DynamoDB + S3
│   └── monitoring_stack.py         # CloudWatch dashboards
```

**Stack Dependencies:**
```
SnsStack
  │
  ├─► AlertAnalyzerStack (Phase 1)
  │     └─► References SNS topic ARNs
  │
  ├─► ChatHandlerStack (Phase 2)
  │     ├─► References SNS topics
  │     └─► Depends on StorageStack
  │
  └─► MonitoringStack
        └─► References Lambda function ARNs
```

### Environment Strategy

```yaml
Environments:
  dev:
    account_id: "111111111111"
    region: us-east-1
    llm_model: claude-3-haiku  # Cheaper for dev

  staging:
    account_id: "222222222222"
    region: us-east-1
    llm_model: claude-3-5-sonnet

  prod:
    account_id: "333333333333"
    region: us-east-1
    llm_model: claude-3-5-sonnet
```

---

## Scalability Considerations

### Lambda Concurrency

**Phase 1:**
- Expected alerts: 10-50/month
- Lambda concurrency: 1-2
- No reserved concurrency needed

**Phase 2:**
- Expected interactions: 50-200/month
- Lambda concurrency: 2-5
- Consider reserved concurrency if consistent usage

### DynamoDB Capacity

**On-Demand Mode:**
- Automatically scales
- No capacity planning needed
- Pay per request

**Projected Load:**
- 50 conversations/month × 10 messages = 500 writes
- Avg 2 reads per write (load + save) = 1,000 reads
- Well within free tier limits

### Bedrock Quota

**Default Quotas (per region):**
- Claude 3.5 Sonnet: 10,000 tokens/minute
- Our usage: ~50 calls/month × 3,000 tokens = 150K tokens/month
- Average: ~5 tokens/minute
- **No quota concerns**

---

## Disaster Recovery

### Backup Strategy

**DynamoDB:**
- Point-in-time recovery: Enabled
- On-demand backups: Monthly
- Cross-region replication: Not needed (recreatable data)

**S3:**
- Versioning: Enabled
- Cross-region replication: Optional
- Lifecycle policies: Archive to Glacier

**Lambda:**
- Code stored in S3 by CDK
- Infrastructure as Code (CDK) in git
- Easy to redeploy

### Recovery Scenarios

**Lambda Failure:**
- CloudWatch alarm triggers
- Manual redeploy: `cdk deploy AlertAnalyzerStack`
- RTO: < 15 minutes

**DynamoDB Failure:**
- Restore from point-in-time recovery
- RTO: < 1 hour
- Data loss: < 5 minutes

**Complete Region Failure:**
- Redeploy to different region
- Update Slack webhooks
- RTO: < 2 hours

---

## Cost Optimization Strategies

### 1. Selective LLM Usage

Only invoke LLM for:
- Budget warnings (>80%)
- Budget critical (>100%)
- CloudWatch ERROR alarms
- Custom error events

Skip LLM for:
- Daily budget reports
- CloudWatch INFO alarms
- Routine updates

**Savings:** ~70% reduction in LLM calls

### 2. Tool Result Caching

Cache AWS API results for short period:
```python
# Cache cost data for 5 minutes
@lru_cache(maxsize=128)
def get_cost_breakdown_cached(date_str):
    return get_cost_breakdown(date_str)
```

**Savings:** Reduced AWS API calls

### 3. DynamoDB TTL

Auto-delete old conversations after 7 days

**Savings:** ~$0.50/month

### 4. S3 Lifecycle Policies

Archive to Glacier after 30 days

**Savings:** ~$0.10/month

### 5. Lambda Memory Optimization

Test and tune Lambda memory:
- Start: 512MB
- Benchmark: 256MB, 512MB, 1024MB
- Choose optimal price/performance

**Potential savings:** 20-30%

---

## Future Enhancements

### Potential Additions

1. **Multi-Account Support**
   - AWS Organizations integration
   - Aggregate costs across accounts
   - Tag bot with account context

2. **Custom Alert Rules Engine**
   - Define thresholds in config
   - Create custom CloudWatch alarms
   - User-defined analysis triggers

3. **Runbook Generation**
   - Auto-generate remediation guides
   - Store in S3 or Confluence
   - Version control runbooks

4. **Ticketing Integration**
   - Auto-create Jira tickets for critical issues
   - Link Slack threads to tickets
   - Update ticket status from Slack

5. **Cost Forecasting**
   - ML-based cost predictions
   - Anomaly detection
   - Budget recommendations

6. **Security Analysis**
   - Security Hub findings
   - GuardDuty alerts
   - IAM policy analysis

---

**Status:** Design Phase
**Last Updated:** 2025-10-21
**Next:** Review and iterate on architecture
