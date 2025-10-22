# AWS Tools Library - Specifications

## Overview

The tools library provides LangChain-compatible AWS inspection functions that the LangGraph agent can invoke to gather context about alerts.

**Design Principles:**
- Each tool has a single, well-defined purpose
- Clear docstrings for LLM understanding
- Type-safe with proper return structures
- Error handling with fallback values
- Caching where appropriate

---

## Tool Categories

### Phase 1 Tools (Start Here)

1. **Cost Tools** (4 tools)
   - Cost Explorer queries
   - Budget status
   - Service-level costs

2. **Compute Tools** (3 tools)
   - Lambda metrics and errors
   - EC2 instance status

3. **Logging Tools** (2 tools)
   - CloudWatch Logs queries
   - Log pattern analysis

4. **Infrastructure Tools** (2 tools)
   - Resource tagging
   - Recent changes

**Total: 11 tools for Phase 1**

---

## Cost Tools

### 1. get_cost_breakdown

**Purpose:** Get daily AWS cost breakdown for a time period

**Function Signature:**
```python
@tool
def get_cost_breakdown(days: int = 7) -> dict:
    """
    Get AWS cost breakdown for the last N days.

    Args:
        days: Number of days to query (default: 7, max: 90)

    Returns:
        dict: {
            "total": float,  # Total cost for period
            "currency": str,  # USD, EUR, etc.
            "daily": [
                {"date": "2025-10-21", "cost": 12.45},
                {"date": "2025-10-20", "cost": 10.23}
            ],
            "average_per_day": float,
            "trend": "increasing|decreasing|stable"
        }
    """
```

**Implementation:**
```python
import boto3
from datetime import datetime, timedelta
from langchain.tools import tool

@tool
def get_cost_breakdown(days: int = 7) -> dict:
    """Get AWS cost breakdown for the last N days."""
    ce_client = boto3.client('ce')

    # Validate input
    days = min(max(1, days), 90)  # Clamp between 1-90

    # Calculate date range
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)

    try:
        response = ce_client.get_cost_and_usage(
            TimePeriod={
                'Start': str(start_date),
                'End': str(end_date)
            },
            Granularity='DAILY',
            Metrics=['UnblendedCost']
        )

        # Parse results
        daily_costs = []
        total = 0.0

        for result in response['ResultsByTime']:
            cost = float(result['Total']['UnblendedCost']['Amount'])
            daily_costs.append({
                'date': result['TimePeriod']['Start'],
                'cost': round(cost, 2)
            })
            total += cost

        # Calculate average
        avg = total / len(daily_costs) if daily_costs else 0

        # Determine trend (simple: compare first half to second half)
        if len(daily_costs) >= 4:
            mid = len(daily_costs) // 2
            first_half_avg = sum(d['cost'] for d in daily_costs[:mid]) / mid
            second_half_avg = sum(d['cost'] for d in daily_costs[mid:]) / (len(daily_costs) - mid)

            if second_half_avg > first_half_avg * 1.1:
                trend = "increasing"
            elif second_half_avg < first_half_avg * 0.9:
                trend = "decreasing"
            else:
                trend = "stable"
        else:
            trend = "insufficient_data"

        return {
            "total": round(total, 2),
            "currency": "USD",
            "daily": daily_costs,
            "average_per_day": round(avg, 2),
            "trend": trend,
            "period_days": days
        }

    except Exception as e:
        return {
            "error": str(e),
            "total": 0.0,
            "currency": "USD",
            "daily": [],
            "average_per_day": 0.0,
            "trend": "error"
        }
```

---

### 2. get_service_costs

**Purpose:** Get top AWS services by cost

**Function Signature:**
```python
@tool
def get_service_costs(days: int = 7, top: int = 5) -> dict:
    """
    Get top AWS services by cost for a time period.

    Args:
        days: Number of days to query (default: 7)
        top: Number of top services to return (default: 5)

    Returns:
        dict: {
            "services": [
                {"name": "Amazon Lambda", "cost": 125.45, "percentage": 45.2},
                {"name": "Amazon S3", "cost": 78.30, "percentage": 28.1}
            ],
            "total": 277.75,
            "period_days": 7
        }
    """
```

**Implementation:**
```python
@tool
def get_service_costs(days: int = 7, top: int = 5) -> dict:
    """Get top AWS services by cost."""
    ce_client = boto3.client('ce')

    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)

    try:
        response = ce_client.get_cost_and_usage(
            TimePeriod={
                'Start': str(start_date),
                'End': str(end_date)
            },
            Granularity='MONTHLY',
            Metrics=['UnblendedCost'],
            GroupBy=[
                {
                    'Type': 'DIMENSION',
                    'Key': 'SERVICE'
                }
            ]
        )

        # Parse and sort by cost
        services = []
        total_cost = 0.0

        for result in response['ResultsByTime']:
            for group in result['Groups']:
                service_name = group['Keys'][0]
                cost = float(group['Metrics']['UnblendedCost']['Amount'])

                if cost > 0.01:  # Filter out negligible costs
                    services.append({
                        'name': service_name,
                        'cost': cost
                    })
                    total_cost += cost

        # Sort by cost descending
        services.sort(key=lambda x: x['cost'], reverse=True)

        # Take top N and add percentages
        top_services = []
        for service in services[:top]:
            percentage = (service['cost'] / total_cost * 100) if total_cost > 0 else 0
            top_services.append({
                'name': service['name'],
                'cost': round(service['cost'], 2),
                'percentage': round(percentage, 1)
            })

        return {
            'services': top_services,
            'total': round(total_cost, 2),
            'period_days': days,
            'num_services': len(services)
        }

    except Exception as e:
        return {
            'error': str(e),
            'services': [],
            'total': 0.0,
            'period_days': days
        }
```

---

### 3. get_budget_status

**Purpose:** Get current budget utilization

**Function Signature:**
```python
@tool
def get_budget_status() -> dict:
    """
    Get status of all AWS Budgets.

    Returns:
        dict: {
            "budgets": [
                {
                    "name": "MonthlyBudget",
                    "limit": 300.00,
                    "actual": 255.40,
                    "forecasted": 290.00,
                    "percentage": 85.1,
                    "status": "warning|ok|critical"
                }
            ]
        }
    """
```

**Implementation:**
```python
@tool
def get_budget_status() -> dict:
    """Get status of all AWS Budgets."""
    budgets_client = boto3.client('budgets')
    account_id = boto3.client('sts').get_caller_identity()['Account']

    try:
        response = budgets_client.describe_budgets(AccountId=account_id)

        budget_statuses = []

        for budget in response['Budgets']:
            name = budget['BudgetName']
            limit = float(budget['BudgetLimit']['Amount'])

            # Get actual spend
            actual_spend = budget.get('CalculatedSpend', {}).get('ActualSpend', {})
            actual = float(actual_spend.get('Amount', 0))

            # Get forecasted spend
            forecasted_spend = budget.get('CalculatedSpend', {}).get('ForecastedSpend', {})
            forecasted = float(forecasted_spend.get('Amount', 0)) if forecasted_spend else None

            # Calculate percentage
            percentage = (actual / limit * 100) if limit > 0 else 0

            # Determine status
            if percentage >= 100:
                status = "critical"
            elif percentage >= 80:
                status = "warning"
            else:
                status = "ok"

            budget_statuses.append({
                'name': name,
                'limit': round(limit, 2),
                'actual': round(actual, 2),
                'forecasted': round(forecasted, 2) if forecasted else None,
                'percentage': round(percentage, 1),
                'status': status,
                'time_unit': budget['TimeUnit']
            })

        return {'budgets': budget_statuses}

    except Exception as e:
        return {
            'error': str(e),
            'budgets': []
        }
```

---

### 4. get_cost_forecast

**Purpose:** Get cost forecast for end of month

**Function Signature:**
```python
@tool
def get_cost_forecast() -> dict:
    """
    Get AWS cost forecast for the rest of the month.

    Returns:
        dict: {
            "month_to_date": 255.40,
            "forecasted_month_end": 298.50,
            "confidence_interval": {
                "lower": 285.00,
                "upper": 312.00
            },
            "days_remaining": 9
        }
    """
```

---

## Compute Tools

### 5. get_lambda_metrics

**Purpose:** Get Lambda function metrics

**Function Signature:**
```python
@tool
def get_lambda_metrics(function_name: str, hours: int = 24) -> dict:
    """
    Get CloudWatch metrics for a Lambda function.

    Args:
        function_name: Name of the Lambda function
        hours: Number of hours to query (default: 24)

    Returns:
        dict: {
            "invocations": 12450,
            "errors": 1023,
            "error_rate": 8.2,
            "duration_avg_ms": 1250.5,
            "throttles": 5,
            "concurrent_executions_max": 3,
            "period_hours": 24
        }
    """
```

**Implementation:**
```python
@tool
def get_lambda_metrics(function_name: str, hours: int = 24) -> dict:
    """Get CloudWatch metrics for a Lambda function."""
    cw_client = boto3.client('cloudwatch')

    end_time = datetime.now()
    start_time = end_time - timedelta(hours=hours)

    metrics_to_query = [
        'Invocations',
        'Errors',
        'Duration',
        'Throttles',
        'ConcurrentExecutions'
    ]

    try:
        results = {}

        for metric_name in metrics_to_query:
            response = cw_client.get_metric_statistics(
                Namespace='AWS/Lambda',
                MetricName=metric_name,
                Dimensions=[
                    {'Name': 'FunctionName', 'Value': function_name}
                ],
                StartTime=start_time,
                EndTime=end_time,
                Period=3600,  # 1 hour periods
                Statistics=['Sum', 'Average', 'Maximum']
            )

            if response['Datapoints']:
                if metric_name in ['Invocations', 'Errors', 'Throttles']:
                    results[metric_name.lower()] = sum(d['Sum'] for d in response['Datapoints'])
                elif metric_name == 'Duration':
                    results['duration_avg_ms'] = sum(d['Average'] for d in response['Datapoints']) / len(response['Datapoints'])
                elif metric_name == 'ConcurrentExecutions':
                    results['concurrent_executions_max'] = max(d['Maximum'] for d in response['Datapoints'])
            else:
                results[metric_name.lower()] = 0

        # Calculate error rate
        invocations = results.get('invocations', 0)
        errors = results.get('errors', 0)
        error_rate = (errors / invocations * 100) if invocations > 0 else 0

        return {
            'function_name': function_name,
            'invocations': int(results.get('invocations', 0)),
            'errors': int(results.get('errors', 0)),
            'error_rate': round(error_rate, 2),
            'duration_avg_ms': round(results.get('duration_avg_ms', 0), 2),
            'throttles': int(results.get('throttles', 0)),
            'concurrent_executions_max': int(results.get('concurrent_executions_max', 0)),
            'period_hours': hours
        }

    except Exception as e:
        return {
            'error': str(e),
            'function_name': function_name,
            'invocations': 0,
            'errors': 0,
            'error_rate': 0,
            'period_hours': hours
        }
```

---

### 6. get_lambda_errors

**Purpose:** Get recent Lambda error logs

**Function Signature:**
```python
@tool
def get_lambda_errors(function_name: str, limit: int = 20) -> dict:
    """
    Get recent error logs from a Lambda function.

    Args:
        function_name: Name of the Lambda function
        limit: Maximum number of errors to return (default: 20)

    Returns:
        dict: {
            "errors": [
                {
                    "timestamp": "2025-10-21T14:30:45Z",
                    "message": "S3 timeout error",
                    "request_id": "abc-123"
                }
            ],
            "error_patterns": {
                "S3 timeout": 15,
                "DynamoDB throttle": 5
            }
        }
    """
```

---

### 7. get_ec2_instances

**Purpose:** Get running EC2 instances

**Function Signature:**
```python
@tool
def get_ec2_instances() -> dict:
    """
    Get all running EC2 instances.

    Returns:
        dict: {
            "instances": [
                {
                    "id": "i-1234567890abcdef0",
                    "type": "t3.medium",
                    "state": "running",
                    "launch_time": "2025-10-15T10:30:00Z",
                    "name": "WebServer-1"
                }
            ],
            "total_count": 5,
            "by_type": {"t3.medium": 3, "t3.large": 2}
        }
    """
```

---

## Logging Tools

### 8. get_cloudwatch_logs

**Purpose:** Query CloudWatch Logs

**Function Signature:**
```python
@tool
def get_cloudwatch_logs(
    log_group: str,
    hours: int = 1,
    filter_pattern: str = "",
    limit: int = 100
) -> dict:
    """
    Query CloudWatch Logs for a log group.

    Args:
        log_group: Log group name (e.g., "/aws/lambda/MyFunction")
        hours: Hours to look back (default: 1)
        filter_pattern: CloudWatch filter pattern (default: "" = all)
        limit: Max number of log entries (default: 100)

    Returns:
        dict: {
            "logs": [
                {
                    "timestamp": "2025-10-21T14:30:45Z",
                    "message": "ERROR: Connection timeout"
                }
            ],
            "total_count": 156,
            "returned_count": 100
        }
    """
```

**Implementation:**
```python
@tool
def get_cloudwatch_logs(
    log_group: str,
    hours: int = 1,
    filter_pattern: str = "",
    limit: int = 100
) -> dict:
    """Query CloudWatch Logs."""
    logs_client = boto3.client('logs')

    end_time = int(datetime.now().timestamp() * 1000)
    start_time = int((datetime.now() - timedelta(hours=hours)).timestamp() * 1000)

    try:
        # Start query
        query_string = f"fields @timestamp, @message | filter @message like /{filter_pattern}/ | limit {limit}"

        response = logs_client.start_query(
            logGroupName=log_group,
            startTime=start_time,
            endTime=end_time,
            queryString=query_string
        )

        query_id = response['queryId']

        # Wait for query to complete (max 30 seconds)
        import time
        for _ in range(30):
            result = logs_client.get_query_results(queryId=query_id)
            if result['status'] == 'Complete':
                break
            time.sleep(1)

        # Parse results
        log_entries = []
        for result_row in result.get('results', []):
            entry = {}
            for field in result_row:
                if field['field'] == '@timestamp':
                    entry['timestamp'] = field['value']
                elif field['field'] == '@message':
                    entry['message'] = field['value']
            if entry:
                log_entries.append(entry)

        return {
            'logs': log_entries,
            'total_count': len(log_entries),
            'returned_count': len(log_entries),
            'log_group': log_group,
            'period_hours': hours
        }

    except Exception as e:
        return {
            'error': str(e),
            'logs': [],
            'total_count': 0,
            'returned_count': 0
        }
```

---

### 9. search_logs

**Purpose:** Search logs with Insights query

**Function Signature:**
```python
@tool
def search_logs(
    log_groups: list[str],
    query: str,
    hours: int = 24
) -> dict:
    """
    Run CloudWatch Logs Insights query across multiple log groups.

    Args:
        log_groups: List of log group names
        query: CloudWatch Logs Insights query
        hours: Hours to look back

    Returns:
        dict: Query results
    """
```

---

## Infrastructure Tools

### 10. get_resource_tags

**Purpose:** Get resource tags for tracking

**Function Signature:**
```python
@tool
def get_resource_tags(limit: int = 20) -> dict:
    """
    Get recently modified resources and their tags.

    Args:
        limit: Max number of resources to return

    Returns:
        dict: {
            "resources": [
                {
                    "arn": "arn:aws:lambda:...",
                    "type": "lambda",
                    "tags": {"Environment": "prod", "Team": "backend"}
                }
            ]
        }
    """
```

---

### 11. get_recent_changes

**Purpose:** Get recent AWS resource changes

**Function Signature:**
```python
@tool
def get_recent_changes(hours: int = 24) -> dict:
    """
    Get recent CloudFormation stack updates and deployments.

    Args:
        hours: Hours to look back

    Returns:
        dict: {
            "changes": [
                {
                    "timestamp": "2025-10-21T10:30:00Z",
                    "type": "CloudFormation",
                    "stack_name": "BackendStack",
                    "status": "UPDATE_COMPLETE",
                    "resources_changed": 5
                }
            ]
        }
    """
```

---

## Tool Organization

### File Structure

```
lambda/alert_analyzer/tools/
├── __init__.py
├── cost_tools.py          # Tools 1-4
├── compute_tools.py       # Tools 5-7
├── logging_tools.py       # Tools 8-9
└── infrastructure_tools.py # Tools 10-11
```

### Tool Registration

```python
# lambda/alert_analyzer/tools/__init__.py

from .cost_tools import (
    get_cost_breakdown,
    get_service_costs,
    get_budget_status,
    get_cost_forecast
)
from .compute_tools import (
    get_lambda_metrics,
    get_lambda_errors,
    get_ec2_instances
)
from .logging_tools import (
    get_cloudwatch_logs,
    search_logs
)
from .infrastructure_tools import (
    get_resource_tags,
    get_recent_changes
)

# All tools list for LangGraph
ALL_TOOLS = [
    # Cost
    get_cost_breakdown,
    get_service_costs,
    get_budget_status,
    get_cost_forecast,
    # Compute
    get_lambda_metrics,
    get_lambda_errors,
    get_ec2_instances,
    # Logging
    get_cloudwatch_logs,
    search_logs,
    # Infrastructure
    get_resource_tags,
    get_recent_changes
]
```

---

## Testing Tools

### Unit Test Example

```python
# tests/test_cost_tools.py

import pytest
from moto import mock_ce  # AWS mocking library
from tools.cost_tools import get_cost_breakdown

@mock_ce
def test_get_cost_breakdown():
    """Test cost breakdown tool with mocked AWS."""
    # Setup mock data
    # ... mock Cost Explorer response ...

    result = get_cost_breakdown(days=7)

    assert 'total' in result
    assert 'daily' in result
    assert len(result['daily']) <= 7
    assert result['trend'] in ['increasing', 'decreasing', 'stable', 'insufficient_data']
```

### Integration Test

```python
# scripts/test-tools-live.py

"""Test tools against real AWS account (use carefully!)."""

from tools import get_cost_breakdown, get_lambda_metrics

# Test cost breakdown
print("Testing get_cost_breakdown...")
result = get_cost_breakdown(days=7)
print(f"Total cost (7 days): ${result['total']}")

# Test Lambda metrics
print("\nTesting get_lambda_metrics...")
result = get_lambda_metrics("MyFunction", hours=24)
print(f"Invocations: {result['invocations']}")
```

---

## Tool Development Guide

### Adding a New Tool

**Step 1: Define the function**
```python
# tools/new_category_tools.py

from langchain.tools import tool
import boto3

@tool
def my_new_tool(param: str) -> dict:
    """
    Clear description of what this tool does.

    Args:
        param: Description of parameter

    Returns:
        dict: Description of return structure
    """
    try:
        # Implementation
        result = do_something(param)
        return {'data': result}
    except Exception as e:
        return {'error': str(e)}
```

**Step 2: Register in __init__.py**
```python
from .new_category_tools import my_new_tool

ALL_TOOLS.append(my_new_tool)
```

**Step 3: Write tests**
```python
def test_my_new_tool():
    result = my_new_tool("test")
    assert 'data' in result or 'error' in result
```

**Step 4: Update documentation** (this file!)

---

## Best Practices

### 1. Error Handling
Always return a dict, even on error:
```python
try:
    # Normal flow
    return {'data': result}
except Exception as e:
    return {'error': str(e), 'data': None}
```

### 2. Type Safety
Use type hints:
```python
def get_cost_breakdown(days: int = 7) -> dict:
    ...
```

### 3. Clear Docstrings
LLM reads these to understand when to use the tool:
```python
"""
Get AWS cost breakdown for the last N days.

Use this tool when you need to analyze spending trends over time.
"""
```

### 4. Reasonable Defaults
```python
def get_cloudwatch_logs(hours: int = 1, limit: int = 100):
    # 1 hour default is safe, 100 logs is reasonable
```

### 5. Caching (Optional)
For expensive queries:
```python
from functools import lru_cache

@lru_cache(maxsize=32)
@tool
def expensive_query(param: str) -> dict:
    ...
```

---

## Future Tools (Phase 2+)

### Code Analysis Tools
- `get_lambda_source_code()` - Download Lambda code
- `read_git_repo()` - Clone and analyze repository
- `search_codebase()` - Grep through code

### Security Tools
- `get_security_findings()` - Security Hub findings
- `get_iam_issues()` - IAM Access Analyzer
- `get_guardduty_alerts()` - GuardDuty findings

### Advanced Cost Tools
- `get_cost_anomalies()` - AWS Cost Anomaly Detection
- `get_savings_plan_utilization()` - Savings Plans usage
- `get_reserved_instance_utilization()` - RI usage

---

**Status:** Specifications Complete
**Total Phase 1 Tools:** 11
**Ready for:** Implementation
