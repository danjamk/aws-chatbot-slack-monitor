"""
AWS Alert Intelligence System - Lambda Handler

Phase 1: One-shot AI analysis of AWS alerts
- Triggered by SNS notifications
- Uses LangGraph workflow for alert analysis
- Posts results to Slack with AI insights

Entry point: lambda_handler(event, context)
"""

import json
import os
import sys
import yaml
from typing import Dict, Any

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

from agents import AlertAnalyzerWorkflow


def load_config() -> Dict[str, Any]:
    """
    Load configuration from environment variables.

    Configuration is passed to Lambda via CDK as environment variables.
    This includes both config.yaml values and .env secrets.
    """
    config = {}

    # Load structured config if provided (CDK passes as JSON string)
    config_json = os.getenv('CONFIG_JSON', '{}')
    try:
        config = json.loads(config_json)
    except json.JSONDecodeError:
        print('Warning: Could not parse CONFIG_JSON, using minimal config')
        config = {}

    # Ensure required sections exist
    if 'ai_analysis' not in config:
        config['ai_analysis'] = {
            'enabled': True,
            'rules': {},
            'blacklist': [],
            'whitelist': []
        }

    return config


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for AI alert analysis.

    Args:
        event: SNS event containing alert data
        context: Lambda context object

    Returns:
        dict: Response with status and result info
    """
    print(f'Received event: {json.dumps(event)}')

    try:
        # Load configuration
        config = load_config()

        # Initialize workflow
        workflow = AlertAnalyzerWorkflow(config)

        # Run workflow on the event
        result = workflow.run(event)

        # Check for errors
        if result.get('error'):
            print(f"Error in workflow: {result['error']}")
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'error': result['error'],
                    'message': 'Failed to process alert'
                })
            }

        # Success
        print(f"Successfully processed alert: {result.get('alert_type')}")
        print(f"Posted to channel: {result.get('slack_channel')}")

        return {
            'statusCode': 200,
            'body': json.dumps({
                'alert_type': result.get('alert_type'),
                'channel': result.get('slack_channel'),
                'message': 'Alert processed successfully'
            })
        }

    except Exception as e:
        print(f'Unhandled exception: {str(e)}')
        import traceback
        traceback.print_exc()

        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'message': 'Internal error processing alert'
            })
        }
