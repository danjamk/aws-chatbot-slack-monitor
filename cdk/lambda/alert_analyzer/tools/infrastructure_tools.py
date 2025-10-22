"""
Infrastructure monitoring tools for resource tags and recent changes.

Tools:
- get_resource_tags: Get recently modified resources and their tags
- get_recent_changes: Get recent CloudTrail events (infrastructure changes)
"""

import boto3
from datetime import datetime, timedelta
from typing import Dict, Any, List
from langchain.tools import tool


@tool
def get_resource_tags(limit: int = 20) -> Dict[str, Any]:
    """
    Get recently modified resources and their tags.

    Args:
        limit: Maximum number of resources to return (default: 20, max: 50)

    Returns:
        dict: {
            "resources": [{arn, type, tags}, ...],
            "resource_count": int
        }

    Example:
        >>> get_resource_tags(limit=10)
        {
            "resources": [
                {
                    "arn": "arn:aws:lambda:us-east-1:123456789012:function:my-func",
                    "type": "lambda:function",
                    "tags": {"Environment": "prod", "Team": "data"}
                }
            ],
            "resource_count": 1
        }
    """
    tagging_client = boto3.client('resourcegroupstaggingapi')

    limit = min(max(1, limit), 50)

    try:
        response = tagging_client.get_resources(
            ResourcesPerPage=limit
        )

        resources = []
        for resource in response['ResourceTagMappingList']:
            tags = {tag['Key']: tag['Value'] for tag in resource.get('Tags', [])}

            # Extract resource type from ARN
            arn = resource['ResourceARN']
            arn_parts = arn.split(':')
            resource_type = f"{arn_parts[2]}:{arn_parts[5].split('/')[0]}" if len(arn_parts) > 5 else 'unknown'

            resources.append({
                'arn': arn,
                'type': resource_type,
                'tags': tags
            })

        return {
            'resources': resources,
            'resource_count': len(resources)
        }

    except Exception as e:
        return {
            'error': str(e),
            'resources': [],
            'resource_count': 0
        }


@tool
def get_recent_changes(hours: int = 24) -> Dict[str, Any]:
    """
    Get recent infrastructure changes from CloudTrail.

    Queries CloudTrail for recent write operations (Create, Update, Delete).
    Useful for correlating alerts with recent infrastructure changes.

    Args:
        hours: Hours to look back (default: 24, max: 168)

    Returns:
        dict: {
            "events": [{time, user, event_name, resource, source_ip}, ...],
            "event_count": int,
            "period": str
        }

    Example:
        >>> get_recent_changes(hours=24)
        {
            "events": [
                {
                    "time": "2025-10-22T10:30:45Z",
                    "user": "alice@example.com",
                    "event_name": "RunInstances",
                    "resource": "i-0abc123",
                    "source_ip": "203.0.113.1"
                }
            ],
            "event_count": 1,
            "period": "Last 24 hours"
        }
    """
    cloudtrail_client = boto3.client('cloudtrail')

    hours = min(max(1, hours), 168)  # Max 7 days

    start_time = datetime.utcnow() - timedelta(hours=hours)
    end_time = datetime.utcnow()

    try:
        # Query CloudTrail for write events
        response = cloudtrail_client.lookup_events(
            StartTime=start_time,
            EndTime=end_time,
            LookupAttributes=[
                {
                    'AttributeKey': 'ReadOnly',
                    'AttributeValue': 'false'  # Only write operations
                }
            ],
            MaxResults=50  # CloudTrail limit
        )

        events = []
        for event in response['Events']:
            # Extract key information
            event_time = event.get('EventTime', '').isoformat() if hasattr(event.get('EventTime'), 'isoformat') else str(event.get('EventTime', ''))
            event_name = event.get('EventName', 'Unknown')
            username = event.get('Username', 'Unknown')

            # Try to extract resource information
            resources = event.get('Resources', [])
            resource_info = resources[0].get('ResourceName', 'N/A') if resources else 'N/A'

            # Get source IP
            import json
            cloud_trail_event = json.loads(event.get('CloudTrailEvent', '{}'))
            source_ip = cloud_trail_event.get('sourceIPAddress', 'Unknown')

            events.append({
                'time': event_time,
                'user': username,
                'event_name': event_name,
                'resource': resource_info,
                'source_ip': source_ip
            })

        return {
            'events': events,
            'event_count': len(events),
            'period': f'Last {hours} hours'
        }

    except Exception as e:
        return {
            'error': str(e),
            'events': [],
            'event_count': 0
        }
