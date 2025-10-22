# Phase 1: Intelligent Critical Alerts - Implementation Guide

## Overview

Phase 1 focuses on **one-shot AI analysis** of critical AWS alerts. When a critical event occurs (budget warning, CloudWatch alarm, etc.), the system automatically:
1. Gathers relevant AWS context
2. Analyzes with Claude
3. Posts actionable diagnostics to Slack

**No conversation history, no interactivity** - just intelligent, automated alert enrichment.

---

## Scope

### What Phase 1 Includes ✅

- **Alert Routing**: SNS topics for critical vs. heartbeat alerts
- **Alert Analyzer Lambda**: LangGraph workflow for analysis
- **AWS Tools**: Cost, compute, logging, infrastructure inspection
- **LLM Integration**: Claude 3.5 Sonnet via Bedrock
- **Slack Output**: Formatted messages with diagnostics
- **CDK Infrastructure**: Deployable stack

### What Phase 1 Excludes ❌

- ❌ Interactive chat (Phase 2)
- ❌ Conversation history storage (Phase 2)
- ❌ Multi-turn interactions (Phase 2)
- ❌ Git/code analysis tools (Future)
- ❌ Human-in-the-loop approvals (Phase 3)

---

## Architecture Components

```
┌─────────────────────────────────────────────────────────────┐
│                    AWS ALERT SOURCES                        │
├─────────────────────────────────────────────────────────────┤
│  • AWS Budgets (>80% warning, >100% critical)              │
│  • CloudWatch Alarms (ERROR, WARN levels)                  │
│  • Custom Events (application errors)                      │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              SNS Topic: critical-alerts                     │
│  (Only alerts that should be analyzed by AI)                │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│          EventBridge Rule: Route to AlertAnalyzer           │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                AlertAnalyzer Lambda Function                │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐ │
│  │            LangGraph Workflow (5 nodes)               │ │
│  ├───────────────────────────────────────────────────────┤ │
│  │  1. classify_alert     → Identify alert type         │ │
│  │  2. gather_context     → Execute AWS tools           │ │
│  │  3. analyze_with_llm   → Call Claude via Bedrock     │ │
│  │  4. format_response    → Create Slack blocks         │ │
│  │  5. post_to_slack      → Send webhook                │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐ │
│  │                  AWS Tools Library                    │ │
│  ├───────────────────────────────────────────────────────┤ │
│  │  Cost Tools:                                          │ │
│  │    • get_cost_breakdown()                             │ │
│  │    • get_budget_status()                              │ │
│  │    • get_service_costs()                              │ │
│  │                                                       │ │
│  │  Compute Tools:                                       │ │
│  │    • get_lambda_metrics()                             │ │
│  │    • get_lambda_errors()                              │ │
│  │    • get_ec2_instances()                              │ │
│  │                                                       │ │
│  │  Logging Tools:                                       │ │
│  │    • get_cloudwatch_logs()                            │ │
│  │    • search_logs()                                    │ │
│  │                                                       │ │
│  │  Infrastructure Tools:                                │ │
│  │    • get_resource_tags()                              │ │
│  │    • get_recent_changes()                             │ │
│  └───────────────────────────────────────────────────────┘ │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ├─► AWS Bedrock (Claude 3.5 Sonnet)
                         │
                         └─► Slack Webhook (critical channel)
```

---

## Alert Routing Rules

### Critical Alerts (Analyzed by AI)

**Budget Alerts:**
- Monthly budget ≥ 80% → critical-alerts → AI analysis
- Monthly budget ≥ 100% → critical-alerts → AI analysis
- Daily budget exceeded → critical-alerts → AI analysis

**CloudWatch Alarms:**
- State: ALARM + Namespace: AWS/Lambda + ErrorCount → AI analysis
- State: ALARM + any ERROR-level alarm → AI analysis
- State: ALARM + custom error metrics → AI analysis

**Custom Events:**
- EventBridge pattern matches critical severity → AI analysis

### Heartbeat Alerts (Pass-Through, No AI)

**Routine Reports:**
- Daily cost summary → heartbeat-alerts → No AI (raw data)
- CloudWatch INFO alarms → heartbeat-alerts → No AI
- Health check success → heartbeat-alerts → No AI

**Configuration:**
```yaml
# config/config.yaml
analysis_rules:
  # Budget alerts
  analyze_budget_warning: true        # ≥80%
  analyze_budget_critical: true       # ≥100%
  analyze_daily_budget_report: false  # Skip AI

  # CloudWatch alarms
  analyze_alarm_state_alarm: true     # ERROR/WARN
  analyze_alarm_state_ok: false       # INFO
  analyze_alarm_state_insufficient_data: false

  # Custom events (by pattern matching)
  critical_event_patterns:
    - "$.detail.severity == 'CRITICAL'"
    - "$.detail.errorType == 'FATAL'"
```

---

## LangGraph Workflow Implementation

### State Schema

```python
from typing import TypedDict, Optional, List, Dict, Any

class AlertState(TypedDict):
    """State passed through the LangGraph workflow."""

    # Input (from SNS/EventBridge)
    raw_event: Dict[str, Any]           # Original event payload
    alert_type: Optional[str]           # Classified type
    alert_metadata: Optional[Dict]      # Parsed metadata

    # Processing
    context: Optional[Dict]             # AWS data gathered by tools
    analysis_result: Optional[Dict]     # LLM analysis output

    # Output
    slack_message: Optional[Dict]       # Slack Block Kit JSON
    error: Optional[str]                # Error message if failed
```

### Node 1: Classify Alert

**Purpose:** Determine what type of alert this is

```python
def classify_alert_node(state: AlertState) -> AlertState:
    """
    Parse the SNS/EventBridge message and classify alert type.

    Alert Types:
    - budget_warning: Monthly budget 80-99%
    - budget_critical: Monthly budget ≥100%
    - budget_daily: Daily budget exceeded
    - cloudwatch_alarm_lambda: Lambda-related alarm
    - cloudwatch_alarm_generic: Other CloudWatch alarm
    - custom_error: Custom application error event
    """
    raw_event = state["raw_event"]

    # Check if this is a budget alert
    if "detail-type" in raw_event and "AWS Budget" in raw_event["detail-type"]:
        detail = raw_event["detail"]
        threshold = detail.get("thresholdPercentage", 0)

        if threshold >= 100:
            alert_type = "budget_critical"
        elif threshold >= 80:
            alert_type = "budget_warning"
        else:
            alert_type = "budget_daily"

        metadata = {
            "budget_name": detail.get("budgetName"),
            "actual_spend": detail.get("actualSpend"),
            "forecasted_spend": detail.get("forecastedSpend"),
            "threshold": threshold
        }

    # Check if this is a CloudWatch alarm
    elif "AlarmName" in raw_event:
        alarm_data = raw_event
        namespace = alarm_data.get("Trigger", {}).get("Namespace", "")

        if "AWS/Lambda" in namespace:
            alert_type = "cloudwatch_alarm_lambda"
        else:
            alert_type = "cloudwatch_alarm_generic"

        metadata = {
            "alarm_name": alarm_data.get("AlarmName"),
            "alarm_description": alarm_data.get("AlarmDescription"),
            "metric_name": alarm_data.get("Trigger", {}).get("MetricName"),
            "namespace": namespace,
            "state_reason": alarm_data.get("NewStateReason")
        }

    # Custom events
    else:
        alert_type = "custom_error"
        metadata = {"raw": raw_event}

    state["alert_type"] = alert_type
    state["alert_metadata"] = metadata

    return state
```

### Node 2: Gather Context

**Purpose:** Execute relevant AWS tools based on alert type

```python
def gather_context_node(state: AlertState) -> AlertState:
    """
    Execute AWS tools to gather diagnostic context.

    Tool selection based on alert type:
    - Budget alerts → cost tools
    - Lambda alarms → compute + logging tools
    - Generic alarms → infrastructure tools
    """
    alert_type = state["alert_type"]
    metadata = state["alert_metadata"]
    context = {}

    try:
        if alert_type.startswith("budget_"):
            # Gather cost context
            context["cost_breakdown"] = get_cost_breakdown(days=7)
            context["service_costs"] = get_service_costs(top=5)
            context["budget_status"] = get_budget_status()
            context["cost_forecast"] = get_cost_forecast()

        elif alert_type == "cloudwatch_alarm_lambda":
            # Gather Lambda context
            # Extract function name from alarm description or metric
            function_name = extract_lambda_name(metadata)

            if function_name:
                context["lambda_metrics"] = get_lambda_metrics(function_name)
                context["lambda_errors"] = get_lambda_errors(function_name)
                context["recent_logs"] = get_cloudwatch_logs(
                    log_group=f"/aws/lambda/{function_name}",
                    hours=1,
                    filter_pattern="ERROR"
                )

        elif alert_type == "cloudwatch_alarm_generic":
            # Gather general infrastructure context
            metric_name = metadata.get("metric_name")
            namespace = metadata.get("namespace")

            if "EC2" in namespace:
                context["ec2_instances"] = get_ec2_instances()
            elif "RDS" in namespace:
                context["rds_instances"] = get_rds_instances()

            # Get recent CloudFormation changes
            context["recent_changes"] = get_recent_changes(hours=24)

        # Always useful: recent resource tags
        context["resource_tags"] = get_resource_tags(limit=10)

    except Exception as e:
        context["error"] = f"Failed to gather context: {str(e)}"

    state["context"] = context
    return state

def extract_lambda_name(metadata: dict) -> Optional[str]:
    """Extract Lambda function name from alarm metadata."""
    # Try alarm description first
    description = metadata.get("alarm_description", "")
    if "Function:" in description:
        return description.split("Function:")[1].split()[0]

    # Try metric dimensions
    dimensions = metadata.get("dimensions", {})
    if "FunctionName" in dimensions:
        return dimensions["FunctionName"]

    return None
```

### Node 3: Analyze with LLM

**Purpose:** Send context to Claude for analysis

```python
from langchain_aws import ChatBedrock

def analyze_with_llm_node(state: AlertState) -> AlertState:
    """
    Call Claude to analyze the alert and provide diagnostics.

    LLM receives:
    - Alert type and metadata
    - Gathered AWS context
    - System prompt with instructions

    LLM returns structured analysis:
    - Root cause hypothesis
    - Impact assessment
    - Diagnostic commands (AWS CLI)
    - Remediation suggestions
    - Common causes
    """
    alert_type = state["alert_type"]
    metadata = state["alert_metadata"]
    context = state["context"]

    # Initialize Claude via Bedrock
    llm = ChatBedrock(
        model_id="anthropic.claude-3-5-sonnet-20250514-v2:0",
        model_kwargs={
            "temperature": 0.3,
            "max_tokens": 2000
        }
    )

    # Build prompt
    prompt = build_analysis_prompt(alert_type, metadata, context)

    try:
        # Call LLM
        response = llm.invoke(prompt)

        # Parse structured response
        analysis = parse_llm_response(response.content)

        state["analysis_result"] = analysis

    except Exception as e:
        state["error"] = f"LLM analysis failed: {str(e)}"
        state["analysis_result"] = {
            "root_cause": "Unable to analyze (LLM error)",
            "diagnostics": [],
            "recommendations": ["Check CloudWatch console manually"]
        }

    return state

def build_analysis_prompt(alert_type: str, metadata: dict, context: dict) -> str:
    """Build the LLM prompt with alert context."""

    prompt = f"""You are an AWS expert analyzing a critical alert.

ALERT TYPE: {alert_type}

ALERT DETAILS:
{json.dumps(metadata, indent=2)}

AWS CONTEXT GATHERED:
{json.dumps(context, indent=2)}

Please analyze this alert and provide:

1. ROOT CAUSE ANALYSIS
   - What likely caused this alert?
   - What evidence supports this hypothesis?

2. IMPACT ASSESSMENT
   - How severe is this issue?
   - What systems/services are affected?
   - Estimated cost impact (if applicable)

3. DIAGNOSTIC COMMANDS
   - Provide 3-5 AWS CLI commands to investigate further
   - Include expected output for each command
   - Use actual resource names from the context

4. REMEDIATION STEPS
   - What should be done to fix this?
   - Prioritize quick wins vs. long-term fixes
   - Include specific commands or console actions

5. COMMON CAUSES
   - List 3-5 common reasons this alert might occur
   - Help the team learn from this incident

Format your response as JSON:
{{
  "root_cause": "...",
  "evidence": ["...", "..."],
  "impact": {{
    "severity": "HIGH|MEDIUM|LOW",
    "affected_services": ["...", "..."],
    "estimated_cost": "..."
  }},
  "diagnostics": [
    {{
      "command": "aws ce get-cost-and-usage ...",
      "purpose": "See daily cost breakdown",
      "expected_output": "Shows spike in Lambda costs"
    }}
  ],
  "remediation": [
    {{
      "action": "Add exponential backoff to Lambda function",
      "priority": "HIGH",
      "steps": ["...", "..."]
    }}
  ],
  "common_causes": ["...", "...", "..."],
  "next_steps": ["...", "..."]
}}
"""

    return prompt

def parse_llm_response(response_text: str) -> dict:
    """Parse LLM response into structured format."""
    try:
        # Try to parse as JSON
        return json.loads(response_text)
    except json.JSONDecodeError:
        # Fallback: extract text between ```json and ```
        import re
        json_match = re.search(r'```json\n(.*?)\n```', response_text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(1))
        else:
            # Return unstructured
            return {"raw_response": response_text}
```

### Node 4: Format Response

**Purpose:** Create Slack Block Kit message

```python
def format_slack_message_node(state: AlertState) -> AlertState:
    """
    Format the analysis into a Slack Block Kit message.

    Slack message includes:
    - Header with alert type and severity
    - Root cause section
    - Impact assessment
    - Diagnostic commands (collapsible)
    - Remediation steps
    - Common causes (educational)
    """
    alert_type = state["alert_type"]
    metadata = state["alert_metadata"]
    analysis = state["analysis_result"]

    # Determine emoji and color based on severity
    severity = analysis.get("impact", {}).get("severity", "MEDIUM")
    if severity == "HIGH":
        emoji = "🔴"
        color = "#FF0000"
    elif severity == "MEDIUM":
        emoji = "🟡"
        color = "#FFA500"
    else:
        emoji = "🟢"
        color = "#00FF00"

    # Build Slack blocks
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"{emoji} {alert_type.replace('_', ' ').title()}"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Root Cause:* {analysis.get('root_cause', 'Unknown')}"
            }
        },
        {"type": "divider"}
    ]

    # Impact section
    impact = analysis.get("impact", {})
    if impact:
        blocks.append({
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*Severity:* {impact.get('severity', 'Unknown')}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Cost Impact:* {impact.get('estimated_cost', 'Unknown')}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Affected:* {', '.join(impact.get('affected_services', []))}"
                }
            ]
        })

    # Diagnostic commands (collapsible)
    diagnostics = analysis.get("diagnostics", [])
    if diagnostics:
        diag_text = "\\n\\n".join([
            f"*{i+1}. {d.get('purpose', 'Investigate')}*\\n```{d.get('command', '')}```"
            for i, d in enumerate(diagnostics[:5])
        ])

        blocks.extend([
            {"type": "divider"},
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*🔍 Diagnostic Commands*\\n{diag_text}"
                }
            }
        ])

    # Remediation steps
    remediation = analysis.get("remediation", [])
    if remediation:
        remed_text = "\\n".join([
            f"{i+1}. {r.get('action', '')} _(Priority: {r.get('priority', 'MEDIUM')})_"
            for i, r in enumerate(remediation[:3])
        ])

        blocks.extend([
            {"type": "divider"},
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*🔧 Recommended Actions*\\n{remed_text}"
                }
            }
        ])

    # Common causes (educational)
    common_causes = analysis.get("common_causes", [])
    if common_causes:
        causes_text = "\\n".join([
            f"• {cause}"
            for cause in common_causes[:5]
        ])

        blocks.extend([
            {"type": "divider"},
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"💡 *Common Causes:*\\n{causes_text}"
                    }
                ]
            }
        ])

    # Footer
    blocks.append({
        "type": "context",
        "elements": [
            {
                "type": "mrkdwn",
                "text": f"🤖 AI-powered analysis • {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}"
            }
        ]
    })

    state["slack_message"] = {
        "blocks": blocks,
        "text": f"{emoji} {alert_type}: {analysis.get('root_cause', 'Alert triggered')}"  # Fallback text
    }

    return state
```

### Node 5: Post to Slack

**Purpose:** Send message to Slack webhook

```python
import requests

def post_to_slack_node(state: AlertState) -> AlertState:
    """
    Post the formatted message to Slack webhook.

    Retrieves webhook URL from Secrets Manager and posts message.
    """
    slack_message = state["slack_message"]

    try:
        # Get webhook URL from Secrets Manager
        webhook_url = get_slack_webhook_url("critical")

        # Post to Slack
        response = requests.post(
            webhook_url,
            json=slack_message,
            timeout=10
        )

        if response.status_code != 200:
            raise Exception(f"Slack API error: {response.status_code} {response.text}")

        print(f"✅ Posted to Slack successfully")

    except Exception as e:
        state["error"] = f"Failed to post to Slack: {str(e)}"
        print(f"❌ Slack posting failed: {e}")

    return state

def get_slack_webhook_url(channel: str) -> str:
    """Retrieve Slack webhook URL from Secrets Manager."""
    import boto3

    secrets_client = boto3.client('secretsmanager')
    secret_name = f"aws-alert-intel/prod/slack-{channel}"

    response = secrets_client.get_secret_value(SecretId=secret_name)
    secret = json.loads(response['SecretString'])

    return secret['webhook_url']
```

### Workflow Compilation

```python
from langgraph.graph import StateGraph, END

def create_alert_workflow():
    """Create and compile the LangGraph workflow."""

    workflow = StateGraph(AlertState)

    # Add nodes
    workflow.add_node("classify_alert", classify_alert_node)
    workflow.add_node("gather_context", gather_context_node)
    workflow.add_node("analyze_with_llm", analyze_with_llm_node)
    workflow.add_node("format_response", format_slack_message_node)
    workflow.add_node("post_to_slack", post_to_slack_node)

    # Define flow (linear)
    workflow.set_entry_point("classify_alert")
    workflow.add_edge("classify_alert", "gather_context")
    workflow.add_edge("gather_context", "analyze_with_llm")
    workflow.add_edge("analyze_with_llm", "format_response")
    workflow.add_edge("format_response", "post_to_slack")
    workflow.add_edge("post_to_slack", END)

    return workflow.compile()
```

---

## Lambda Handler

```python
# lambda/alert_analyzer/index.py

import json
from agents.alert_workflow import create_alert_workflow

# Create workflow once (cold start)
workflow = create_alert_workflow()

def handler(event, context):
    """
    Lambda handler for alert analysis.

    Input: SNS/EventBridge event
    Output: Success/failure status
    """
    print(f"Received event: {json.dumps(event)}")

    # Extract SNS message if wrapped
    if "Records" in event and event["Records"][0].get("EventSource") == "aws:sns":
        message = json.loads(event["Records"][0]["Sns"]["Message"])
    else:
        message = event

    # Initialize state
    initial_state = {
        "raw_event": message,
        "alert_type": None,
        "alert_metadata": None,
        "context": None,
        "analysis_result": None,
        "slack_message": None,
        "error": None
    }

    try:
        # Run workflow
        final_state = workflow.invoke(initial_state)

        if final_state.get("error"):
            print(f"⚠️ Workflow completed with errors: {final_state['error']}")
            return {
                "statusCode": 500,
                "body": json.dumps({"error": final_state["error"]})
            }

        print(f"✅ Alert analyzed successfully: {final_state['alert_type']}")
        return {
            "statusCode": 200,
            "body": json.dumps({"alert_type": final_state["alert_type"]})
        }

    except Exception as e:
        print(f"❌ Workflow failed: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
```

---

## Testing Strategy

### Unit Tests

```python
# tests/test_workflow_nodes.py

import pytest
from agents.alert_workflow import (
    classify_alert_node,
    gather_context_node,
    analyze_with_llm_node
)

def test_classify_budget_warning():
    """Test classification of budget warning alert."""
    state = {
        "raw_event": {
            "detail-type": "AWS Budget Notification",
            "detail": {
                "budgetName": "MonthlyBudget",
                "thresholdPercentage": 85,
                "actualSpend": 255.00,
                "forecastedSpend": 300.00
            }
        }
    }

    result = classify_alert_node(state)

    assert result["alert_type"] == "budget_warning"
    assert result["alert_metadata"]["threshold"] == 85

def test_gather_context_for_budget():
    """Test context gathering for budget alerts."""
    state = {
        "alert_type": "budget_warning",
        "alert_metadata": {"budget_name": "MonthlyBudget"}
    }

    result = gather_context_node(state)

    assert "cost_breakdown" in result["context"]
    assert "service_costs" in result["context"]

# Add more tests...
```

### Integration Tests

```python
# tests/test_full_workflow.py

def test_full_workflow_budget_alert():
    """Test complete workflow with sample budget alert."""
    from agents.alert_workflow import create_alert_workflow

    workflow = create_alert_workflow()

    initial_state = {
        "raw_event": load_fixture("budget_warning_sample.json"),
        "alert_type": None,
        "alert_metadata": None,
        "context": None,
        "analysis_result": None,
        "slack_message": None,
        "error": None
    }

    # Run workflow (mocked Slack posting)
    with mock_slack_webhook():
        final_state = workflow.invoke(initial_state)

    # Assertions
    assert final_state["alert_type"] == "budget_warning"
    assert final_state["slack_message"] is not None
    assert final_state["error"] is None
    assert "root_cause" in final_state["analysis_result"]
```

### Local Testing

```bash
# scripts/test-analysis.py

import json
from lambda.alert_analyzer.index import handler

# Load sample event
with open('tests/fixtures/budget_alert.json') as f:
    event = json.load(f)

# Invoke handler locally
response = handler(event, {})

print(json.dumps(response, indent=2))
```

---

## Deployment

### CDK Stack

```python
# cdk/stacks/alert_analyzer_stack.py

from aws_cdk import Stack, Duration
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_iam as iam
from aws_cdk import aws_sns as sns
from aws_cdk import aws_lambda_event_sources as event_sources
from constructs import Construct

class AlertAnalyzerStack(Stack):
    """Stack for Phase 1 alert analyzer."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        config: dict,
        critical_topic: sns.Topic,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create Lambda execution role
        lambda_role = self._create_lambda_role()

        # Create Lambda function
        alert_analyzer = lambda_.Function(
            self,
            "AlertAnalyzer",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="index.handler",
            code=lambda_.Code.from_asset("lambda/alert_analyzer"),
            timeout=Duration.seconds(60),
            memory_size=512,
            role=lambda_role,
            environment={
                "AWS_ACCOUNT_ID": config["aws"]["account_id"],
                "LLM_MODEL_ID": config["llm"]["model_id"],
                "LLM_TEMPERATURE": str(config["llm"]["temperature"])
            }
        )

        # Subscribe to SNS topic
        alert_analyzer.add_event_source(
            event_sources.SnsEventSource(critical_topic)
        )

    def _create_lambda_role(self) -> iam.Role:
        """Create IAM role for Lambda with necessary permissions."""
        role = iam.Role(
            self,
            "AlertAnalyzerRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com")
        )

        # CloudWatch Logs
        role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name(
                "service-role/AWSLambdaBasicExecutionRole"
            )
        )

        # Cost Explorer
        role.add_to_policy(iam.PolicyStatement(
            actions=["ce:GetCostAndUsage", "ce:GetCostForecast"],
            resources=["*"]
        ))

        # CloudWatch Metrics & Logs
        role.add_to_policy(iam.PolicyStatement(
            actions=[
                "cloudwatch:GetMetricData",
                "logs:StartQuery",
                "logs:GetQueryResults"
            ],
            resources=["*"]
        ))

        # Lambda (read-only)
        role.add_to_policy(iam.PolicyStatement(
            actions=[
                "lambda:GetFunction",
                "lambda:ListFunctions",
                "lambda:GetFunctionConfiguration"
            ],
            resources=["*"]
        ))

        # EC2 (read-only)
        role.add_to_policy(iam.PolicyStatement(
            actions=["ec2:DescribeInstances"],
            resources=["*"]
        ))

        # Bedrock
        role.add_to_policy(iam.PolicyStatement(
            actions=["bedrock:InvokeModel"],
            resources=["*"]
        ))

        # Secrets Manager
        role.add_to_policy(iam.PolicyStatement(
            actions=["secretsmanager:GetSecretValue"],
            resources=["arn:aws:secretsmanager:*:*:secret:aws-alert-intel/*"]
        ))

        return role
```

---

## Expected Costs (Phase 1)

### Monthly Cost Breakdown

**Assumptions:**
- 10 critical alerts/month
- Average 30 seconds execution per alert
- 2,000 input tokens + 1,000 output tokens per analysis

| Component | Usage | Monthly Cost |
|-----------|-------|--------------|
| **Lambda Invocations** | 10 invocations | $0.00 (free tier) |
| **Lambda Duration** | 10 × 30s @ 512MB | $0.01 |
| **Claude 3.5 Sonnet (Bedrock)** | 10 × 3K tokens | $0.60 |
| **CloudWatch Logs** | ~10MB | $0.01 |
| **Secrets Manager** | 2 secrets | $0.80 |
| **SNS** | 10 messages | $0.00 |
| **EventBridge** | 10 events | $0.00 |
| **TOTAL PHASE 1** | | **$1.42/month** |

### Cost Scaling

**At 50 alerts/month:**
- Lambda: $0.03
- Claude: $3.00
- Other: $0.82
- **Total: $3.85/month**

**At 100 alerts/month:**
- Lambda: $0.06
- Claude: $6.00
- Other: $0.82
- **Total: $6.88/month**

**Still cheaper than Amazon Q Developer ($19/month)!**

---

## Success Metrics

### Phase 1 Goals

- ✅ Alert-to-Slack latency: < 60 seconds
- ✅ Analysis accuracy: 80%+ relevant suggestions
- ✅ Monthly cost: < $2 for typical usage
- ✅ Error rate: < 5%
- ✅ Time saved per alert: 20-30 minutes (vs manual investigation)

### Monitoring

**CloudWatch Metrics to Track:**
- AlertsProcessed (count)
- AnalysisLatency (milliseconds)
- LLMTokensUsed (count)
- ToolExecutions (count by tool name)
- ErrorRate (percentage)

**CloudWatch Alarms:**
- Alert: ErrorRate > 10% over 5 minutes
- Alert: AnalysisLatency > 60 seconds (p99)
- Alert: Daily cost > $1

---

**Status:** Design Complete
**Ready for:** Implementation
**Next:** Build tools library (TOOLS.md)
