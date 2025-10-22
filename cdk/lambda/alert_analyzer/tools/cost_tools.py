"""
Cost analysis tools using AWS Cost Explorer.

Tools:
- get_cost_breakdown: Get daily cost breakdown for last N days
- get_service_costs: Get top services by cost
- get_budget_status: Get current budget utilization
- get_cost_forecast: Get forecasted cost for month

Cost Explorer API charges $0.01 per request.
"""

import boto3
from datetime import datetime, timedelta
from typing import Dict, Any
from langchain.tools import tool


@tool
def get_cost_breakdown(days: int = 7) -> Dict[str, Any]:
    """
    Get AWS cost breakdown for the last N days with trend analysis.

    Args:
        days: Number of days to query (default: 7, max: 90)

    Returns:
        dict: {
            "total": float,
            "currency": str,
            "daily": [{date, cost}, ...],
            "average_per_day": float,
            "trend": "increasing|decreasing|stable"
        }

    Example:
        >>> get_cost_breakdown(days=7)
        {
            "total": 45.67,
            "currency": "USD",
            "daily": [{"date": "2025-10-15", "cost": 6.52}, ...],
            "average_per_day": 6.52,
            "trend": "increasing"
        }
    """
    ce_client = boto3.client('ce')

    # Validate and clamp days
    days = min(max(1, days), 90)

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
        total_cost = 0.0

        for result in response['ResultsByTime']:
            date = result['TimePeriod']['Start']
            cost = float(result['Total']['UnblendedCost']['Amount'])
            daily_costs.append({'date': date, 'cost': round(cost, 2)})
            total_cost += cost

        # Calculate trend
        if len(daily_costs) >= 2:
            first_half = sum(d['cost'] for d in daily_costs[:len(daily_costs)//2])
            second_half = sum(d['cost'] for d in daily_costs[len(daily_costs)//2:])

            if second_half > first_half * 1.1:
                trend = 'increasing'
            elif second_half < first_half * 0.9:
                trend = 'decreasing'
            else:
                trend = 'stable'
        else:
            trend = 'unknown'

        return {
            'total': round(total_cost, 2),
            'currency': 'USD',
            'daily': daily_costs,
            'average_per_day': round(total_cost / len(daily_costs), 2) if daily_costs else 0,
            'trend': trend,
            'period': f'{start_date} to {end_date}'
        }

    except Exception as e:
        return {
            'error': str(e),
            'total': 0,
            'currency': 'USD'
        }


@tool
def get_service_costs(days: int = 7, top: int = 5) -> Dict[str, Any]:
    """
    Get top AWS services by cost for the last N days.

    Args:
        days: Number of days to query (default: 7, max: 90)
        top: Number of top services to return (default: 5, max: 20)

    Returns:
        dict: {
            "services": [{service, cost, percentage}, ...],
            "total": float,
            "currency": str
        }

    Example:
        >>> get_service_costs(days=7, top=5)
        {
            "services": [
                {"service": "Amazon EC2", "cost": 25.30, "percentage": 55.4},
                {"service": "AWS Lambda", "cost": 10.20, "percentage": 22.3},
                ...
            ],
            "total": 45.67,
            "currency": "USD"
        }
    """
    ce_client = boto3.client('ce')

    days = min(max(1, days), 90)
    top = min(max(1, top), 20)

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
            GroupBy=[{
                'Type': 'DIMENSION',
                'Key': 'SERVICE'
            }]
        )

        # Parse and sort services by cost
        services = []
        total_cost = 0.0

        if response['ResultsByTime']:
            result = response['ResultsByTime'][0]

            for group in result['Groups']:
                service_name = group['Keys'][0]
                cost = float(group['Metrics']['UnblendedCost']['Amount'])

                if cost > 0.01:  # Ignore negligible costs
                    services.append({
                        'service': service_name,
                        'cost': round(cost, 2)
                    })
                    total_cost += cost

        # Sort by cost descending
        services.sort(key=lambda x: x['cost'], reverse=True)

        # Calculate percentages and limit to top N
        for service in services[:top]:
            service['percentage'] = round((service['cost'] / total_cost * 100), 1) if total_cost > 0 else 0

        return {
            'services': services[:top],
            'total': round(total_cost, 2),
            'currency': 'USD',
            'period': f'{start_date} to {end_date}'
        }

    except Exception as e:
        return {
            'error': str(e),
            'services': [],
            'total': 0,
            'currency': 'USD'
        }


@tool
def get_budget_status() -> Dict[str, Any]:
    """
    Get current AWS budget utilization status.

    Returns:
        dict: {
            "budgets": [{name, limit, actual, forecasted, percentage, status}, ...],
            "currency": str
        }

    Example:
        >>> get_budget_status()
        {
            "budgets": [
                {
                    "name": "MonthlyBudget",
                    "limit": 300.0,
                    "actual": 245.50,
                    "forecasted": 285.00,
                    "percentage": 81.8,
                    "status": "warning"
                }
            ],
            "currency": "USD"
        }
    """
    budgets_client = boto3.client('budgets')

    try:
        # Get account ID
        sts_client = boto3.client('sts')
        account_id = sts_client.get_caller_identity()['Account']

        # Get all budgets
        response = budgets_client.describe_budgets(AccountId=account_id)

        budgets = []
        for budget in response['Budgets']:
            budget_name = budget['BudgetName']
            limit = float(budget['BudgetLimit']['Amount'])
            actual = float(budget.get('CalculatedSpend', {}).get('ActualSpend', {}).get('Amount', 0))
            forecasted = float(budget.get('CalculatedSpend', {}).get('ForecastedSpend', {}).get('Amount', 0))

            percentage = (actual / limit * 100) if limit > 0 else 0

            # Determine status
            if percentage >= 100:
                status = 'exceeded'
            elif percentage >= 80:
                status = 'warning'
            elif percentage >= 60:
                status = 'caution'
            else:
                status = 'ok'

            budgets.append({
                'name': budget_name,
                'limit': round(limit, 2),
                'actual': round(actual, 2),
                'forecasted': round(forecasted, 2),
                'percentage': round(percentage, 1),
                'status': status,
                'time_period': budget.get('TimePeriod', {})
            })

        return {
            'budgets': budgets,
            'currency': 'USD'
        }

    except Exception as e:
        return {
            'error': str(e),
            'budgets': [],
            'currency': 'USD'
        }


@tool
def get_cost_forecast() -> Dict[str, Any]:
    """
    Get forecasted AWS cost for the current month.

    Returns:
        dict: {
            "forecasted_total": float,
            "current_spend": float,
            "days_remaining": int,
            "daily_average": float,
            "currency": str
        }

    Example:
        >>> get_cost_forecast()
        {
            "forecasted_total": 285.50,
            "current_spend": 245.30,
            "days_remaining": 8,
            "daily_average": 8.17,
            "currency": "USD"
        }
    """
    ce_client = boto3.client('ce')

    try:
        # Get current month start and end
        now = datetime.now().date()
        month_start = now.replace(day=1)
        month_end = (month_start + timedelta(days=32)).replace(day=1)

        # Get forecast
        response = ce_client.get_cost_forecast(
            TimePeriod={
                'Start': str(now),
                'End': str(month_end)
            },
            Metric='UNBLENDED_COST',
            Granularity='MONTHLY'
        )

        forecasted = float(response['Total']['Amount'])

        # Get current month spend
        current_response = ce_client.get_cost_and_usage(
            TimePeriod={
                'Start': str(month_start),
                'End': str(now)
            },
            Granularity='MONTHLY',
            Metrics=['UnblendedCost']
        )

        current_spend = 0.0
        if current_response['ResultsByTime']:
            current_spend = float(current_response['ResultsByTime'][0]['Total']['UnblendedCost']['Amount'])

        # Calculate remaining days
        days_in_month = (month_end - month_start).days
        days_elapsed = (now - month_start).days
        days_remaining = days_in_month - days_elapsed

        daily_average = current_spend / days_elapsed if days_elapsed > 0 else 0

        return {
            'forecasted_total': round(forecasted, 2),
            'current_spend': round(current_spend, 2),
            'days_remaining': days_remaining,
            'daily_average': round(daily_average, 2),
            'currency': 'USD',
            'month': month_start.strftime('%Y-%m')
        }

    except Exception as e:
        return {
            'error': str(e),
            'forecasted_total': 0,
            'current_spend': 0,
            'currency': 'USD'
        }
