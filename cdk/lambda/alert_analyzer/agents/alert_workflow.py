"""
LangGraph workflow for AI-powered alert analysis.

Phase 1: One-shot analysis with 5 nodes:
1. classify_alert - Determine alert type and extract metadata
2. gather_context - Use AWS tools to gather relevant information
3. analyze_with_llm - Send context to Claude for analysis
4. format_response - Create Slack message with blocks
5. post_to_slack - Send message to appropriate Slack channel
"""

import json
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, TypedDict

import boto3
import requests
from langchain_aws import ChatBedrock
from langgraph.graph import StateGraph, END

# Import tools (will be implemented next)
from tools import ALL_TOOLS


class AlertState(TypedDict):
    """State object passed between workflow nodes."""
    # Input
    raw_event: Dict[str, Any]
    alert_type: Optional[str]
    alert_metadata: Optional[Dict[str, Any]]

    # Processing
    context: Optional[Dict[str, Any]]
    analysis_result: Optional[Dict[str, Any]]

    # Output
    slack_message: Optional[Dict[str, Any]]
    slack_channel: Optional[str]  # critical or heartbeat
    error: Optional[str]


class AlertAnalyzerWorkflow:
    """LangGraph workflow for analyzing AWS alerts with AI."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the workflow.

        Args:
            config: Configuration dict from config.yaml and .env
        """
        self.config = config
        self.llm = self._initialize_llm()
        self.graph = self._build_graph()

    def _initialize_llm(self) -> ChatBedrock:
        """Initialize the LLM client (AWS Bedrock)."""
        model_id = os.getenv('LLM_MODEL_ID', 'anthropic.claude-3-5-sonnet-20250514-v2:0')
        temperature = float(os.getenv('LLM_TEMPERATURE', '0.3'))
        max_tokens = int(os.getenv('LLM_MAX_TOKENS', '2000'))

        return ChatBedrock(
            model_id=model_id,
            model_kwargs={
                'temperature': temperature,
                'max_tokens': max_tokens,
            },
            region_name=os.getenv('AWS_DEFAULT_REGION', 'us-east-1'),
        )

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow."""
        workflow = StateGraph(AlertState)

        # Add nodes
        workflow.add_node("classify_alert", self.classify_alert)
        workflow.add_node("gather_context", self.gather_context)
        workflow.add_node("analyze_with_llm", self.analyze_with_llm)
        workflow.add_node("format_response", self.format_response)
        workflow.add_node("post_to_slack", self.post_to_slack)

        # Define edges
        workflow.set_entry_point("classify_alert")
        workflow.add_edge("classify_alert", "gather_context")
        workflow.add_edge("gather_context", "analyze_with_llm")
        workflow.add_edge("analyze_with_llm", "format_response")
        workflow.add_edge("format_response", "post_to_slack")
        workflow.add_edge("post_to_slack", END)

        return workflow.compile()

    def classify_alert(self, state: AlertState) -> AlertState:
        """
        Node 1: Classify the alert and extract metadata.

        Determines:
        - Alert type (budget_warning, budget_critical, cloudwatch_alarm, emr_failure, etc.)
        - Whether this alert should receive AI analysis
        - Which Slack channel to use (critical or heartbeat)
        - Alert metadata for context gathering
        """
        raw_event = state['raw_event']

        # Extract SNS message if present
        message = raw_event
        if 'Records' in raw_event and len(raw_event['Records']) > 0:
            sns_record = raw_event['Records'][0]
            if 'Sns' in sns_record:
                message_body = sns_record['Sns'].get('Message', '{}')
                try:
                    message = json.loads(message_body)
                except json.JSONDecodeError:
                    message = {'RawMessage': message_body}

        # Classify based on message content
        alert_type, metadata, channel = self._classify_message(message)

        # Check if this alert should be analyzed
        should_analyze = self._should_analyze(alert_type, message)

        if not should_analyze:
            # Skip AI analysis, create simple passthrough message
            state['alert_type'] = 'passthrough'
            state['alert_metadata'] = metadata
            state['slack_channel'] = channel
            state['context'] = None
            state['analysis_result'] = None
            return state

        state['alert_type'] = alert_type
        state['alert_metadata'] = metadata
        state['slack_channel'] = channel

        return state

    def _classify_message(self, message: Dict[str, Any]) -> tuple[str, Dict[str, Any], str]:
        """
        Classify the message type and extract metadata.

        Returns:
            (alert_type, metadata, slack_channel)
        """
        # Budget alerts
        if 'AlarmName' in message and 'Budget' in message.get('AlarmName', ''):
            alarm_name = message['AlarmName']
            if 'Monthly' in alarm_name:
                if message.get('NewStateValue') == 'ALARM':
                    threshold = self._extract_threshold(alarm_name)
                    if threshold >= 100:
                        return ('budget_critical', {'threshold': threshold}, 'critical')
                    elif threshold >= 80:
                        return ('budget_warning', {'threshold': threshold}, 'heartbeat')
            elif 'Daily' in alarm_name:
                return ('daily_budget_exceeded', {}, 'heartbeat')

        # Daily cost report
        if 'AlarmName' in message and 'DailyCostReport' in message.get('AlarmName', ''):
            return ('daily_cost_report', {}, 'heartbeat')

        # CloudWatch alarms
        if 'AlarmName' in message and 'NewStateValue' in message:
            alarm_name = message['AlarmName']
            state = message['NewStateValue']
            reason = message.get('NewStateReason', '')

            # Determine severity
            if 'ERROR' in alarm_name.upper() or 'CRITICAL' in alarm_name.upper():
                return ('cloudwatch_alarm_error', {
                    'alarm_name': alarm_name,
                    'state': state,
                    'reason': reason
                }, 'critical')
            else:
                return ('cloudwatch_alarm_warning', {
                    'alarm_name': alarm_name,
                    'state': state,
                    'reason': reason
                }, 'heartbeat')

        # EMR events
        if 'detail-type' in message:
            detail_type = message['detail-type']
            if 'EMR' in detail_type:
                detail = message.get('detail', {})
                state = detail.get('state', '')
                cluster_id = detail.get('clusterId', '')

                if 'TERMINATED_WITH_ERRORS' in state:
                    return ('emr_cluster_failure', {
                        'cluster_id': cluster_id,
                        'state': state
                    }, 'critical')
                elif 'FAILED' in state:
                    return ('emr_step_failure', {
                        'cluster_id': cluster_id,
                        'state': state
                    }, 'critical')

        # Default: unknown custom event
        return ('custom_event', {}, 'heartbeat')

    def _extract_threshold(self, alarm_name: str) -> int:
        """Extract threshold percentage from alarm name."""
        match = re.search(r'(\d+)%', alarm_name)
        if match:
            return int(match.group(1))
        return 0

    def _should_analyze(self, alert_type: str, message: Dict[str, Any]) -> bool:
        """
        Determine if this alert should receive AI analysis.

        Checks:
        1. AI analysis enabled globally
        2. Alert type matches analysis rules
        3. Not in blacklist
        4. Or in whitelist (overrides blacklist)
        """
        ai_config = self.config.get('ai_analysis', {})

        # Check if AI analysis is enabled
        if not ai_config.get('enabled', True):
            return False

        # Check whitelist first (overrides everything)
        whitelist = ai_config.get('whitelist', [])
        message_str = json.dumps(message)
        for pattern in whitelist:
            if pattern in message_str:
                return True

        # Check blacklist
        blacklist = ai_config.get('blacklist', [])
        for pattern in blacklist:
            if pattern in message_str:
                return False

        # Check analysis rules
        rules = ai_config.get('rules', {})
        rule_key = f'analyze_{alert_type}'

        return rules.get(rule_key, False)

    def gather_context(self, state: AlertState) -> AlertState:
        """
        Node 2: Gather contextual information using AWS tools.

        Based on alert type, calls relevant AWS tools to gather:
        - Cost data (for budget alerts)
        - Lambda metrics (for compute alerts)
        - CloudWatch logs (for errors)
        - EMR cluster status (for EMR failures)
        - Recent infrastructure changes
        """
        if state['alert_type'] == 'passthrough':
            # No context gathering needed
            return state

        alert_type = state['alert_type']
        metadata = state['alert_metadata']
        context = {}

        try:
            # Budget alerts - gather cost data
            if 'budget' in alert_type or 'cost' in alert_type:
                from tools.cost_tools import get_cost_breakdown, get_service_costs, get_budget_status

                context['cost_breakdown'] = get_cost_breakdown(days=7)
                context['top_services'] = get_service_costs(days=7, top=5)
                context['budget_status'] = get_budget_status()

            # CloudWatch alarms - get logs
            if 'cloudwatch_alarm' in alert_type:
                alarm_name = metadata.get('alarm_name', '')
                # Try to extract log group from alarm name or description
                # This is a simplified version - production would need more logic
                from tools.logging_tools import get_cloudwatch_logs

                # Example: if alarm is for Lambda errors, get Lambda logs
                if 'lambda' in alarm_name.lower():
                    function_name = self._extract_function_name(alarm_name)
                    if function_name:
                        log_group = f'/aws/lambda/{function_name}'
                        context['logs'] = get_cloudwatch_logs(
                            log_group=log_group,
                            hours=1,
                            limit=20
                        )

            # EMR failures - get cluster details
            if 'emr' in alert_type:
                from tools.compute_tools import get_emr_cluster_status

                cluster_id = metadata.get('cluster_id')
                if cluster_id:
                    context['emr_status'] = get_emr_cluster_status(cluster_id)

            # Always gather recent changes for infrastructure context
            from tools.infrastructure_tools import get_recent_changes
            context['recent_changes'] = get_recent_changes(hours=24)

            state['context'] = context

        except Exception as e:
            print(f"Error gathering context: {e}")
            state['context'] = {'error': str(e)}

        return state

    def _extract_function_name(self, alarm_name: str) -> Optional[str]:
        """Extract Lambda function name from alarm name."""
        # Simple extraction - production would be more robust
        match = re.search(r'([a-zA-Z0-9_-]+)[-_]?(errors|duration|throttles)', alarm_name.lower())
        if match:
            return match.group(1)
        return None

    def analyze_with_llm(self, state: AlertState) -> AlertState:
        """
        Node 3: Analyze alert with LLM (Claude).

        Sends alert + context to Claude for:
        - Root cause analysis
        - Diagnostic suggestions
        - Remediation recommendations
        - AWS CLI commands for investigation
        """
        if state['alert_type'] == 'passthrough':
            # No LLM analysis needed
            return state

        alert_type = state['alert_type']
        metadata = state['alert_metadata']
        context = state['context']

        # Build prompt for Claude
        prompt = self._build_analysis_prompt(alert_type, metadata, context)

        try:
            # Invoke LLM
            response = self.llm.invoke(prompt)

            # Parse response
            analysis = {
                'summary': response.content,
                'timestamp': datetime.utcnow().isoformat(),
                'model': os.getenv('LLM_MODEL_ID', 'claude-3-5-sonnet')
            }

            state['analysis_result'] = analysis

        except Exception as e:
            print(f"Error analyzing with LLM: {e}")
            state['analysis_result'] = {
                'error': str(e),
                'summary': 'Failed to analyze alert with AI.'
            }

        return state

    def _build_analysis_prompt(self, alert_type: str, metadata: Dict, context: Dict) -> str:
        """Build the prompt for Claude analysis."""
        prompt = f"""You are an AWS infrastructure expert analyzing an alert.

Alert Type: {alert_type}
Alert Metadata: {json.dumps(metadata, indent=2)}

Contextual Information:
{json.dumps(context, indent=2)}

Please provide:
1. **Root Cause Analysis**: What caused this alert?
2. **Impact Assessment**: What is the potential impact?
3. **Diagnostic Commands**: AWS CLI commands to investigate further
4. **Remediation Steps**: Concrete actions to resolve the issue
5. **Prevention**: How to prevent this in the future

Format your response in Markdown with clear sections.
Be concise but thorough. Focus on actionable insights."""

        return prompt

    def format_response(self, state: AlertState) -> AlertState:
        """
        Node 4: Format response as Slack message.

        Creates Slack Block Kit message with:
        - Alert summary (header)
        - AI analysis (if available)
        - Context data (collapsible)
        - Action buttons (optional)
        """
        alert_type = state['alert_type']
        metadata = state['alert_metadata']
        analysis = state.get('analysis_result')
        context = state.get('context')

        # Determine alert emoji and color
        emoji, color = self._get_alert_style(alert_type, state['slack_channel'])

        # Build Slack blocks
        blocks = []

        # Header
        blocks.append({
            'type': 'header',
            'text': {
                'type': 'plain_text',
                'text': f'{emoji} AWS Alert: {alert_type.replace("_", " ").title()}'
            }
        })

        # Alert details
        details_text = self._format_alert_details(alert_type, metadata)
        blocks.append({
            'type': 'section',
            'text': {
                'type': 'mrkdwn',
                'text': details_text
            }
        })

        # AI Analysis (if available)
        if analysis and 'summary' in analysis:
            blocks.append({'type': 'divider'})
            blocks.append({
                'type': 'section',
                'text': {
                    'type': 'mrkdwn',
                    'text': f'*🤖 AI Analysis:*\n{analysis["summary"][:2500]}'  # Slack limit
                }
            })

        # Context (collapsible)
        if context and alert_type != 'passthrough':
            context_summary = self._format_context_summary(context)
            blocks.append({'type': 'divider'})
            blocks.append({
                'type': 'section',
                'text': {
                    'type': 'mrkdwn',
                    'text': f'*📊 Context Data:*\n{context_summary}'
                }
            })

        # Footer
        blocks.append({
            'type': 'context',
            'elements': [{
                'type': 'mrkdwn',
                'text': f'🕐 {datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")} UTC | Powered by AWS Alert Intelligence'
            }]
        })

        state['slack_message'] = {
            'blocks': blocks,
            'text': f'{emoji} {alert_type.replace("_", " ").title()}'  # Fallback text
        }

        return state

    def _get_alert_style(self, alert_type: str, channel: str) -> tuple[str, str]:
        """Get emoji and color for alert type."""
        if channel == 'critical' or 'failure' in alert_type or 'critical' in alert_type:
            return ('🔴', 'danger')
        elif 'warning' in alert_type:
            return ('🟡', 'warning')
        else:
            return ('🔵', 'good')

    def _format_alert_details(self, alert_type: str, metadata: Dict) -> str:
        """Format alert details as markdown."""
        lines = [f'*Type:* `{alert_type}`']

        for key, value in metadata.items():
            lines.append(f'*{key.replace("_", " ").title()}:* `{value}`')

        return '\n'.join(lines)

    def _format_context_summary(self, context: Dict) -> str:
        """Format context data summary."""
        lines = []

        if 'cost_breakdown' in context:
            cost_data = context['cost_breakdown']
            lines.append(f'💰 Total Cost (7d): ${cost_data.get("total", 0):.2f}')

        if 'top_services' in context:
            services = context['top_services'].get('services', [])[:3]
            if services:
                lines.append(f'🔝 Top Services: {", ".join([s["service"] for s in services])}')

        if 'emr_status' in context:
            emr = context['emr_status']
            lines.append(f'📦 EMR Cluster: `{emr.get("cluster_id", "N/A")}`')
            lines.append(f'   Status: `{emr.get("status", "Unknown")}`')

        return '\n'.join(lines) if lines else 'No additional context available'

    def post_to_slack(self, state: AlertState) -> AlertState:
        """
        Node 5: Post message to Slack.

        Sends the formatted message to the appropriate Slack channel
        using the webhook URL from environment variables.
        """
        channel = state['slack_channel']
        message = state['slack_message']

        # Get webhook URL from environment
        webhook_env_var = f'SLACK_{channel.upper()}_WEBHOOK'
        webhook_url = os.getenv(webhook_env_var)

        if not webhook_url:
            print(f'Error: {webhook_env_var} not set in environment')
            state['error'] = f'Missing {webhook_env_var}'
            return state

        try:
            response = requests.post(
                webhook_url,
                json=message,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )

            if response.status_code != 200:
                print(f'Error posting to Slack: {response.status_code} - {response.text}')
                state['error'] = f'Slack API error: {response.status_code}'
            else:
                print(f'Successfully posted to {channel} channel')

        except Exception as e:
            print(f'Error posting to Slack: {e}')
            state['error'] = str(e)

        return state

    def run(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run the workflow on an incoming alert event.

        Args:
            event: Lambda event (SNS notification)

        Returns:
            Final state with results
        """
        initial_state: AlertState = {
            'raw_event': event,
            'alert_type': None,
            'alert_metadata': None,
            'context': None,
            'analysis_result': None,
            'slack_message': None,
            'slack_channel': None,
            'error': None
        }

        final_state = self.graph.invoke(initial_state)

        return final_state
