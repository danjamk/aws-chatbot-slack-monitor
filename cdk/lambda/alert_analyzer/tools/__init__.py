"""
AWS Tools for Alert Analysis

This module provides tools for gathering AWS context during alert analysis.
Tools are organized by category:
- cost_tools: Cost Explorer, Budget analysis
- compute_tools: Lambda, EC2, EMR metrics
- logging_tools: CloudWatch Logs queries
- infrastructure_tools: Resource tags, recent changes

All tools are collected in ALL_TOOLS list for LangGraph integration.
"""

from typing import List
from langchain.tools import BaseTool

# Import tools from each category
from tools.cost_tools import (
    get_cost_breakdown,
    get_service_costs,
    get_budget_status,
    get_cost_forecast,
)

from tools.compute_tools import (
    get_lambda_metrics,
    get_lambda_errors,
    get_ec2_instances,
    get_emr_cluster_status,
)

from tools.logging_tools import (
    get_cloudwatch_logs,
    search_logs,
)

from tools.infrastructure_tools import (
    get_resource_tags,
    get_recent_changes,
)

# Collect all tools for LangGraph
ALL_TOOLS: List[BaseTool] = [
    # Cost tools (4)
    get_cost_breakdown,
    get_service_costs,
    get_budget_status,
    get_cost_forecast,
    # Compute tools (4)
    get_lambda_metrics,
    get_lambda_errors,
    get_ec2_instances,
    get_emr_cluster_status,
    # Logging tools (2)
    get_cloudwatch_logs,
    search_logs,
    # Infrastructure tools (2)
    get_resource_tags,
    get_recent_changes,
]

__all__ = [
    'ALL_TOOLS',
    'get_cost_breakdown',
    'get_service_costs',
    'get_budget_status',
    'get_cost_forecast',
    'get_lambda_metrics',
    'get_lambda_errors',
    'get_ec2_instances',
    'get_emr_cluster_status',
    'get_cloudwatch_logs',
    'search_logs',
    'get_resource_tags',
    'get_recent_changes',
]
