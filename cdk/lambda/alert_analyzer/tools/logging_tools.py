"""
CloudWatch Logs query tools.

Tools:
- get_cloudwatch_logs: Get recent log entries from a log group
- search_logs: Search across multiple log groups with a query
"""

import boto3
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from langchain.tools import tool


@tool
def get_cloudwatch_logs(
    log_group: str,
    hours: int = 1,
    filter_pattern: Optional[str] = None,
    limit: int = 50
) -> Dict[str, Any]:
    """
    Get recent log entries from a CloudWatch log group.

    Args:
        log_group: Log group name (e.g., /aws/lambda/my-function)
        hours: Hours of logs to retrieve (default: 1, max: 72)
        filter_pattern: Optional filter pattern (e.g., "ERROR" or "[level=ERROR]")
        limit: Maximum number of log entries (default: 50, max: 100)

    Returns:
        dict: {
            "log_group": str,
            "entries": [{timestamp, message}, ...],
            "entry_count": int,
            "truncated": bool
        }

    Example:
        >>> get_cloudwatch_logs("/aws/lambda/my-function", hours=1, filter_pattern="ERROR")
        {
            "log_group": "/aws/lambda/my-function",
            "entries": [
                {
                    "timestamp": "2025-10-22T10:30:45Z",
                    "message": "ERROR: Failed to process request"
                }
            ],
            "entry_count": 1,
            "truncated": false
        }
    """
    logs_client = boto3.client('logs')

    hours = min(max(1, hours), 72)
    limit = min(max(1, limit), 100)

    start_time = int((datetime.utcnow() - timedelta(hours=hours)).timestamp() * 1000)
    end_time = int(datetime.utcnow().timestamp() * 1000)

    try:
        # Build filter arguments
        filter_args = {
            'logGroupName': log_group,
            'startTime': start_time,
            'endTime': end_time,
            'limit': limit
        }

        if filter_pattern:
            filter_args['filterPattern'] = filter_pattern

        # Get log events
        response = logs_client.filter_log_events(**filter_args)

        entries = []
        for event in response['events']:
            entries.append({
                'timestamp': datetime.fromtimestamp(event['timestamp'] / 1000).isoformat() + 'Z',
                'message': event['message'][:1000]  # Truncate long messages
            })

        return {
            'log_group': log_group,
            'entries': entries,
            'entry_count': len(entries),
            'truncated': len(entries) >= limit,
            'period': f'Last {hours} hour(s)'
        }

    except logs_client.exceptions.ResourceNotFoundException:
        return {
            'error': f'Log group not found: {log_group}',
            'log_group': log_group,
            'entries': [],
            'entry_count': 0,
            'truncated': False
        }
    except Exception as e:
        return {
            'error': str(e),
            'log_group': log_group,
            'entries': [],
            'entry_count': 0,
            'truncated': False
        }


@tool
def search_logs(
    log_groups: List[str],
    query: str,
    hours: int = 24
) -> Dict[str, Any]:
    """
    Search across multiple log groups using CloudWatch Insights query.

    Args:
        log_groups: List of log group names to search
        query: CloudWatch Insights query (SQL-like syntax)
        hours: Hours to search back (default: 24, max: 168)

    Returns:
        dict: {
            "results": [{field: value, ...}, ...],
            "result_count": int,
            "log_groups": [str],
            "query": str
        }

    Example:
        >>> search_logs(
        ...     log_groups=["/aws/lambda/function1", "/aws/lambda/function2"],
        ...     query="fields @timestamp, @message | filter @message like /ERROR/ | limit 20",
        ...     hours=24
        ... )
        {
            "results": [
                {"@timestamp": "2025-10-22 10:30:45", "@message": "ERROR: ..."}
            ],
            "result_count": 1,
            "log_groups": ["/aws/lambda/function1", "/aws/lambda/function2"],
            "query": "..."
        }
    """
    logs_client = boto3.client('logs')

    hours = min(max(1, hours), 168)  # Max 7 days

    start_time = int((datetime.utcnow() - timedelta(hours=hours)).timestamp())
    end_time = int(datetime.utcnow().timestamp())

    try:
        # Start query
        response = logs_client.start_query(
            logGroupNames=log_groups,
            startTime=start_time,
            endTime=end_time,
            queryString=query
        )

        query_id = response['queryId']

        # Wait for query to complete (with timeout)
        max_wait = 15  # seconds
        waited = 0

        while waited < max_wait:
            result = logs_client.get_query_results(queryId=query_id)
            status = result['status']

            if status == 'Complete':
                break
            elif status in ['Failed', 'Cancelled', 'Timeout']:
                return {
                    'error': f'Query {status.lower()}',
                    'results': [],
                    'result_count': 0
                }

            time.sleep(0.5)
            waited += 0.5

        if result['status'] != 'Complete':
            return {
                'error': 'Query timeout',
                'results': [],
                'result_count': 0
            }

        # Parse results
        results = []
        for row in result['results']:
            entry = {}
            for field in row:
                entry[field['field']] = field['value']

            if entry:
                results.append(entry)

        return {
            'results': results,
            'result_count': len(results),
            'log_groups': log_groups,
            'query': query,
            'period': f'Last {hours} hour(s)'
        }

    except Exception as e:
        return {
            'error': str(e),
            'results': [],
            'result_count': 0
        }
