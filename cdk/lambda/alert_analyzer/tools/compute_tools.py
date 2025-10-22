"""
Compute resource monitoring tools for Lambda, EC2, and EMR.

Tools:
- get_lambda_metrics: Get Lambda function invocation and error metrics
- get_lambda_errors: Get recent Lambda error logs
- get_ec2_instances: Get EC2 instances and their status
- get_emr_cluster_status: Get EMR cluster details and failure reason
"""

import boto3
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from langchain.tools import tool


@tool
def get_lambda_metrics(function_name: str, hours: int = 24) -> Dict[str, Any]:
    """
    Get Lambda function metrics for the last N hours.

    Args:
        function_name: Lambda function name
        hours: Hours of metrics to retrieve (default: 24, max: 168)

    Returns:
        dict: {
            "function_name": str,
            "invocations": int,
            "errors": int,
            "error_rate": float,
            "throttles": int,
            "avg_duration_ms": float,
            "max_duration_ms": float
        }

    Example:
        >>> get_lambda_metrics("my-function", hours=24)
        {
            "function_name": "my-function",
            "invocations": 1523,
            "errors": 12,
            "error_rate": 0.79,
            "throttles": 0,
            "avg_duration_ms": 245.3,
            "max_duration_ms": 2508.1
        }
    """
    cw_client = boto3.client('cloudwatch')

    hours = min(max(1, hours), 168)  # Max 7 days

    end_time = datetime.utcnow()
    start_time = end_time - timedelta(hours=hours)

    try:
        # Define metrics to query
        metrics_to_query = [
            ('Invocations', 'Sum'),
            ('Errors', 'Sum'),
            ('Throttles', 'Sum'),
            ('Duration', 'Average'),
            ('Duration', 'Maximum'),
        ]

        results = {}

        for metric_name, stat in metrics_to_query:
            response = cw_client.get_metric_statistics(
                Namespace='AWS/Lambda',
                MetricName=metric_name,
                Dimensions=[{
                    'Name': 'FunctionName',
                    'Value': function_name
                }],
                StartTime=start_time,
                EndTime=end_time,
                Period=3600,  # 1 hour periods
                Statistics=[stat]
            )

            # Sum or average the datapoints
            if response['Datapoints']:
                if stat == 'Sum':
                    value = sum(dp[stat] for dp in response['Datapoints'])
                elif stat == 'Average':
                    value = sum(dp[stat] for dp in response['Datapoints']) / len(response['Datapoints'])
                elif stat == 'Maximum':
                    value = max(dp[stat] for dp in response['Datapoints'])
                else:
                    value = 0

                key = f'{metric_name.lower()}_{stat.lower()}'
                results[key] = round(value, 2)
            else:
                key = f'{metric_name.lower()}_{stat.lower()}'
                results[key] = 0

        # Calculate error rate
        invocations = results.get('invocations_sum', 0)
        errors = results.get('errors_sum', 0)
        error_rate = (errors / invocations * 100) if invocations > 0 else 0

        return {
            'function_name': function_name,
            'invocations': int(results.get('invocations_sum', 0)),
            'errors': int(results.get('errors_sum', 0)),
            'error_rate': round(error_rate, 2),
            'throttles': int(results.get('throttles_sum', 0)),
            'avg_duration_ms': results.get('duration_average', 0),
            'max_duration_ms': results.get('duration_maximum', 0),
            'period': f'Last {hours} hours'
        }

    except Exception as e:
        return {
            'error': str(e),
            'function_name': function_name
        }


@tool
def get_lambda_errors(function_name: str, limit: int = 20) -> Dict[str, Any]:
    """
    Get recent Lambda function error logs.

    Args:
        function_name: Lambda function name
        limit: Maximum number of error messages to return (default: 20, max: 100)

    Returns:
        dict: {
            "function_name": str,
            "errors": [{timestamp, message, request_id}, ...],
            "error_count": int
        }

    Example:
        >>> get_lambda_errors("my-function", limit=10)
        {
            "function_name": "my-function",
            "errors": [
                {
                    "timestamp": "2025-10-22T10:30:45Z",
                    "message": "KeyError: 'user_id'",
                    "request_id": "abc-123-def"
                }
            ],
            "error_count": 1
        }
    """
    logs_client = boto3.client('logs')

    limit = min(max(1, limit), 100)
    log_group = f'/aws/lambda/{function_name}'

    try:
        # Query for ERROR level logs
        start_time = int((datetime.utcnow() - timedelta(hours=24)).timestamp() * 1000)
        end_time = int(datetime.utcnow().timestamp() * 1000)

        query = f"""
        fields @timestamp, @message, @requestId
        | filter @message like /ERROR/ or @message like /Exception/ or @message like /Error/
        | sort @timestamp desc
        | limit {limit}
        """

        # Start query
        query_response = logs_client.start_query(
            logGroupName=log_group,
            startTime=start_time,
            endTime=end_time,
            queryString=query
        )

        query_id = query_response['queryId']

        # Wait for query to complete (with timeout)
        import time
        max_wait = 10  # seconds
        waited = 0

        while waited < max_wait:
            result = logs_client.get_query_results(queryId=query_id)
            status = result['status']

            if status == 'Complete':
                break

            time.sleep(0.5)
            waited += 0.5

        if result['status'] != 'Complete':
            return {
                'error': 'Query timeout',
                'function_name': function_name
            }

        # Parse results
        errors = []
        for row in result['results']:
            error_entry = {}
            for field in row:
                if field['field'] == '@timestamp':
                    error_entry['timestamp'] = field['value']
                elif field['field'] == '@message':
                    error_entry['message'] = field['value'][:500]  # Truncate long messages
                elif field['field'] == '@requestId':
                    error_entry['request_id'] = field['value']

            if error_entry:
                errors.append(error_entry)

        return {
            'function_name': function_name,
            'errors': errors,
            'error_count': len(errors),
            'log_group': log_group
        }

    except logs_client.exceptions.ResourceNotFoundException:
        return {
            'error': f'Log group not found: {log_group}',
            'function_name': function_name,
            'errors': [],
            'error_count': 0
        }
    except Exception as e:
        return {
            'error': str(e),
            'function_name': function_name,
            'errors': [],
            'error_count': 0
        }


@tool
def get_ec2_instances() -> Dict[str, Any]:
    """
    Get EC2 instances and their current status.

    Returns:
        dict: {
            "instances": [{id, type, state, name, launch_time}, ...],
            "total_count": int,
            "running_count": int
        }

    Example:
        >>> get_ec2_instances()
        {
            "instances": [
                {
                    "id": "i-0abc123def456",
                    "type": "t3.medium",
                    "state": "running",
                    "name": "web-server-1",
                    "launch_time": "2025-10-20T08:00:00Z"
                }
            ],
            "total_count": 3,
            "running_count": 2
        }
    """
    ec2_client = boto3.client('ec2')

    try:
        response = ec2_client.describe_instances()

        instances = []
        running_count = 0

        for reservation in response['Reservations']:
            for instance in reservation['Instances']:
                # Extract instance name from tags
                name = 'N/A'
                tags = instance.get('Tags', [])
                for tag in tags:
                    if tag['Key'] == 'Name':
                        name = tag['Value']
                        break

                state = instance['State']['Name']
                if state == 'running':
                    running_count += 1

                instances.append({
                    'id': instance['InstanceId'],
                    'type': instance['InstanceType'],
                    'state': state,
                    'name': name,
                    'launch_time': instance.get('LaunchTime', 'Unknown').isoformat() if hasattr(instance.get('LaunchTime'), 'isoformat') else str(instance.get('LaunchTime', 'Unknown'))
                })

        return {
            'instances': instances,
            'total_count': len(instances),
            'running_count': running_count
        }

    except Exception as e:
        return {
            'error': str(e),
            'instances': [],
            'total_count': 0,
            'running_count': 0
        }


@tool
def get_emr_cluster_status(cluster_id: str) -> Dict[str, Any]:
    """
    Get EMR cluster details and failure information.

    Args:
        cluster_id: EMR cluster ID (e.g., j-XXXXXXXXXXXXX)

    Returns:
        dict: {
            "cluster_id": str,
            "name": str,
            "status": str,
            "state_change_reason": str,
            "failure_details": dict,
            "applications": [str],
            "created_at": str,
            "terminated_at": str
        }

    Example:
        >>> get_emr_cluster_status("j-ABC123DEF456")
        {
            "cluster_id": "j-ABC123DEF456",
            "name": "Data Processing Pipeline",
            "status": "TERMINATED_WITH_ERRORS",
            "state_change_reason": "Step failure",
            "failure_details": {
                "code": "STEP_FAILURE",
                "message": "Step s-123 failed with exit code 1"
            },
            "applications": ["Spark", "Hadoop"],
            "failed_steps": [...]
        }
    """
    emr_client = boto3.client('emr')

    try:
        # Get cluster details
        response = emr_client.describe_cluster(ClusterId=cluster_id)
        cluster = response['Cluster']

        status = cluster['Status']['State']
        state_change_reason = cluster['Status'].get('StateChangeReason', {})

        result = {
            'cluster_id': cluster_id,
            'name': cluster.get('Name', 'Unnamed'),
            'status': status,
            'state_change_reason': state_change_reason.get('Message', 'Unknown'),
            'state_change_code': state_change_reason.get('Code', 'Unknown'),
            'applications': [app['Name'] for app in cluster.get('Applications', [])],
            'created_at': cluster['Status']['Timeline'].get('CreationDateTime', 'Unknown').isoformat() if hasattr(cluster['Status']['Timeline'].get('CreationDateTime'), 'isoformat') else str(cluster['Status']['Timeline'].get('CreationDateTime', 'Unknown')),
        }

        # Add termination time if terminated
        if 'EndDateTime' in cluster['Status']['Timeline']:
            result['terminated_at'] = cluster['Status']['Timeline']['EndDateTime'].isoformat()

        # If cluster failed, get failed steps
        if 'TERMINATED_WITH_ERRORS' in status or 'FAILED' in status:
            steps_response = emr_client.list_steps(
                ClusterId=cluster_id,
                StepStates=['FAILED', 'CANCELLED']
            )

            failed_steps = []
            for step in steps_response['Steps']:
                step_detail = emr_client.describe_step(
                    ClusterId=cluster_id,
                    StepId=step['Id']
                )

                step_info = step_detail['Step']
                failed_steps.append({
                    'step_id': step_info['Id'],
                    'name': step_info['Name'],
                    'state': step_info['Status']['State'],
                    'failure_reason': step_info['Status'].get('StateChangeReason', {}).get('Message', 'Unknown')
                })

            result['failed_steps'] = failed_steps
            result['failure_details'] = {
                'code': state_change_reason.get('Code', 'Unknown'),
                'message': state_change_reason.get('Message', 'Unknown'),
                'failed_step_count': len(failed_steps)
            }

        return result

    except Exception as e:
        return {
            'error': str(e),
            'cluster_id': cluster_id
        }
