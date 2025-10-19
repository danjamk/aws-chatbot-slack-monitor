"""
Budget Stack - AWS Budget Monitoring for AWS Chatbot Slack Monitor

This stack creates AWS Budgets with notification thresholds:
- Daily budget: 100% threshold → heartbeat channel
- Monthly budget: 80% threshold → heartbeat channel (warning)
- Monthly budget: 100% threshold → critical channel (alert)

All budget values are configured via config.yaml for easy updates.
"""

import os
from typing import List, Optional

from aws_cdk import Stack, CfnOutput
from aws_cdk import aws_budgets as budgets
from aws_cdk import aws_sns as sns
from constructs import Construct


class BudgetStack(Stack):
    """Stack for creating AWS Budgets and cost alerts."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        config: dict,
        critical_topic: sns.Topic,
        heartbeat_topic: sns.Topic,
        **kwargs,
    ) -> None:
        """
        Initialize the Budget Stack.

        Args:
            scope: CDK app scope
            construct_id: Unique identifier for this stack
            config: Configuration dictionary from config.yaml
            critical_topic: SNS topic for critical alerts
            heartbeat_topic: SNS topic for heartbeat/monitoring alerts
            **kwargs: Additional stack properties (env, etc.)
        """
        super().__init__(scope, construct_id, **kwargs)

        self.config = config
        self.critical_topic = critical_topic
        self.heartbeat_topic = heartbeat_topic

        # Get budget configuration
        self.budget_config = config["budgets"]
        self.aws_account = config["aws"]["account_id"]

        # Get email addresses from environment (optional)
        self.notification_emails = self._get_notification_emails()

        # Create budgets
        self._create_daily_budget()
        self._create_monthly_budgets()

    def _get_notification_emails(self) -> List[str]:
        """
        Get notification email addresses from environment.

        Returns:
            List of email addresses, or empty list if none configured
        """
        if not self.config["notifications"].get("email_enabled", False):
            return []

        email_list = os.environ.get("NOTIFICATION_EMAILS", "")
        if not email_list:
            return []

        return [email.strip() for email in email_list.split(",") if email.strip()]

    def _create_subscribers(
        self, include_sns_topic: Optional[sns.Topic] = None
    ) -> List[budgets.CfnBudget.SubscriberProperty]:
        """
        Create budget notification subscribers.

        Args:
            include_sns_topic: Optional SNS topic to include as subscriber

        Returns:
            List of subscriber properties for budget notifications
        """
        subscribers = []

        # Add email subscribers if configured
        for email in self.notification_emails:
            subscribers.append(
                budgets.CfnBudget.SubscriberProperty(
                    subscription_type="EMAIL", address=email
                )
            )

        # Add SNS topic subscriber if provided
        if include_sns_topic:
            subscribers.append(
                budgets.CfnBudget.SubscriberProperty(
                    subscription_type="SNS", address=include_sns_topic.topic_arn
                )
            )

        return subscribers

    def _create_daily_budget(self) -> None:
        """Create daily budget with 100% threshold notification."""
        daily_limit = float(self.budget_config["daily_limit"])
        currency = self.budget_config["currency"]

        # Create subscribers for daily budget (heartbeat channel)
        subscribers = self._create_subscribers(include_sns_topic=self.heartbeat_topic)

        if not subscribers:
            # If no subscribers, we still need at least the SNS topic
            subscribers = self._create_subscribers(include_sns_topic=self.heartbeat_topic)

        daily_budget = budgets.CfnBudget(
            self,
            "DailyBudget",
            budget=budgets.CfnBudget.BudgetDataProperty(
                budget_name=f"{self.config['project']['name']}-daily-budget",
                budget_type="COST",
                time_unit=self.budget_config["time_unit_daily"],
                budget_limit=budgets.CfnBudget.SpendProperty(
                    amount=daily_limit, unit=currency
                ),
            ),
            notifications_with_subscribers=[
                budgets.CfnBudget.NotificationWithSubscribersProperty(
                    notification=budgets.CfnBudget.NotificationProperty(
                        comparison_operator="GREATER_THAN",
                        notification_type="ACTUAL",
                        threshold=100,  # Alert at 100% of daily budget
                        threshold_type="PERCENTAGE",
                    ),
                    subscribers=subscribers,
                )
            ],
        )

        CfnOutput(
            self,
            "DailyBudgetName",
            value=daily_budget.budget.budget_name,
            description="Name of the daily budget",
        )

    def _create_monthly_budgets(self) -> None:
        """Create monthly budget with 80% warning and 100% alert thresholds."""
        monthly_limit = float(self.budget_config["monthly_limit"])
        currency = self.budget_config["currency"]
        warning_threshold = int(self.budget_config["monthly_threshold_warning"])
        critical_threshold = int(self.budget_config["monthly_threshold_critical"])

        # Create notification configurations
        notifications_with_subscribers = []

        # 80% Warning → Heartbeat Channel
        heartbeat_subscribers = self._create_subscribers(
            include_sns_topic=self.heartbeat_topic
        )
        if heartbeat_subscribers:
            notifications_with_subscribers.append(
                budgets.CfnBudget.NotificationWithSubscribersProperty(
                    notification=budgets.CfnBudget.NotificationProperty(
                        comparison_operator="GREATER_THAN",
                        notification_type="ACTUAL",
                        threshold=warning_threshold,
                        threshold_type="PERCENTAGE",
                    ),
                    subscribers=heartbeat_subscribers,
                )
            )

        # 100% Alert → Critical Channel
        critical_subscribers = self._create_subscribers(
            include_sns_topic=self.critical_topic
        )
        if critical_subscribers:
            notifications_with_subscribers.append(
                budgets.CfnBudget.NotificationWithSubscribersProperty(
                    notification=budgets.CfnBudget.NotificationProperty(
                        comparison_operator="GREATER_THAN",
                        notification_type="ACTUAL",
                        threshold=critical_threshold,
                        threshold_type="PERCENTAGE",
                    ),
                    subscribers=critical_subscribers,
                )
            )

        # Create the monthly budget
        monthly_budget = budgets.CfnBudget(
            self,
            "MonthlyBudget",
            budget=budgets.CfnBudget.BudgetDataProperty(
                budget_name=f"{self.config['project']['name']}-monthly-budget",
                budget_type="COST",
                time_unit=self.budget_config["time_unit_monthly"],
                budget_limit=budgets.CfnBudget.SpendProperty(
                    amount=monthly_limit, unit=currency
                ),
            ),
            notifications_with_subscribers=notifications_with_subscribers,
        )

        CfnOutput(
            self,
            "MonthlyBudgetName",
            value=monthly_budget.budget.budget_name,
            description="Name of the monthly budget",
        )

        CfnOutput(
            self,
            "MonthlyBudgetLimit",
            value=str(monthly_limit),
            description="Monthly budget limit amount",
        )

        CfnOutput(
            self,
            "MonthlyBudgetWarningThreshold",
            value=f"{warning_threshold}%",
            description="Monthly budget warning threshold percentage",
        )

        CfnOutput(
            self,
            "MonthlyBudgetCriticalThreshold",
            value=f"{critical_threshold}%",
            description="Monthly budget critical threshold percentage",
        )
