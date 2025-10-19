"""
SNS Stack - Notification Topics for AWS Chatbot Slack Monitor

This stack creates the SNS topics used for routing notifications:
- critical-alerts: For budget overruns and severe issues (low noise)
- heartbeat-alerts: For daily reports, warnings, and monitoring (may be noisy)

Both topics can be referenced by other stacks for publishing notifications.
"""

import os
from typing import Optional

from aws_cdk import Stack, CfnOutput, RemovalPolicy
from aws_cdk import aws_sns as sns
from aws_cdk import aws_sns_subscriptions as subscriptions
from constructs import Construct


class SnsStack(Stack):
    """Stack for creating SNS notification topics."""

    def __init__(
        self, scope: Construct, construct_id: str, config: dict, **kwargs
    ) -> None:
        """
        Initialize the SNS Stack.

        Args:
            scope: CDK app scope
            construct_id: Unique identifier for this stack
            config: Configuration dictionary from config.yaml
            **kwargs: Additional stack properties (env, etc.)
        """
        super().__init__(scope, construct_id, **kwargs)

        self.config = config
        self.critical_topic: sns.Topic
        self.heartbeat_topic: sns.Topic

        # Create SNS topics
        self._create_topics()

        # Add email subscriptions if configured
        self._add_email_subscriptions()

        # Export topic ARNs for cross-stack references
        self._export_topic_arns()

    def _create_topics(self) -> None:
        """Create the critical and heartbeat SNS topics."""
        project_name = self.config["project"]["name"]
        environment = self.config["project"]["environment"]

        # Critical alerts topic (low noise, immediate action required)
        critical_topic_name = self.config["notifications"]["critical_topic_name"]
        self.critical_topic = sns.Topic(
            self,
            "CriticalAlertsTopic",
            display_name=f"{project_name} Critical Alerts ({environment})",
            topic_name=f"{project_name}-{environment}-{critical_topic_name}",
            # Enable encryption for security
            # master_key=kms.Key(...) # Uncomment for KMS encryption if needed
        )

        # Add tags
        self.critical_topic.node.default_child.add_property_override(
            "Tags",
            [
                {"Key": "Name", "Value": f"{project_name} Critical Alerts"},
                {"Key": "AlertType", "Value": "critical"},
                {"Key": "Noise", "Value": "low"},
            ],
        )

        # Heartbeat alerts topic (monitoring, may be noisy)
        heartbeat_topic_name = self.config["notifications"]["heartbeat_topic_name"]
        self.heartbeat_topic = sns.Topic(
            self,
            "HeartbeatAlertsTopic",
            display_name=f"{project_name} Heartbeat Alerts ({environment})",
            topic_name=f"{project_name}-{environment}-{heartbeat_topic_name}",
            # Enable encryption for security
            # master_key=kms.Key(...) # Uncomment for KMS encryption if needed
        )

        # Add tags
        self.heartbeat_topic.node.default_child.add_property_override(
            "Tags",
            [
                {"Key": "Name", "Value": f"{project_name} Heartbeat Alerts"},
                {"Key": "AlertType", "Value": "heartbeat"},
                {"Key": "Noise", "Value": "medium"},
            ],
        )

    def _add_email_subscriptions(self) -> None:
        """Add email subscriptions to SNS topics if configured."""
        # Check if email notifications are enabled
        if not self.config["notifications"].get("email_enabled", False):
            return

        # Get email addresses from environment variable
        email_list = os.environ.get("NOTIFICATION_EMAILS", "")
        if not email_list:
            # Email enabled but no addresses configured - that's OK
            return

        # Parse comma-separated email list
        emails = [email.strip() for email in email_list.split(",") if email.strip()]

        if not emails:
            return

        # Subscribe emails to both topics
        for email in emails:
            # Add to critical topic
            self.critical_topic.add_subscription(
                subscriptions.EmailSubscription(
                    email,
                    # JSON format provides more detail than plain text
                    json=False,
                )
            )

            # Add to heartbeat topic
            self.heartbeat_topic.add_subscription(
                subscriptions.EmailSubscription(
                    email,
                    json=False,
                )
            )

    def _export_topic_arns(self) -> None:
        """Export topic ARNs for use by other stacks."""
        # Export critical topic ARN
        CfnOutput(
            self,
            "CriticalTopicArn",
            value=self.critical_topic.topic_arn,
            description="ARN of the critical alerts SNS topic",
            export_name=f"{self.stack_name}-CriticalTopicArn",
        )

        # Export critical topic name
        CfnOutput(
            self,
            "CriticalTopicName",
            value=self.critical_topic.topic_name,
            description="Name of the critical alerts SNS topic",
            export_name=f"{self.stack_name}-CriticalTopicName",
        )

        # Export heartbeat topic ARN
        CfnOutput(
            self,
            "HeartbeatTopicArn",
            value=self.heartbeat_topic.topic_arn,
            description="ARN of the heartbeat alerts SNS topic",
            export_name=f"{self.stack_name}-HeartbeatTopicArn",
        )

        # Export heartbeat topic name
        CfnOutput(
            self,
            "HeartbeatTopicName",
            value=self.heartbeat_topic.topic_name,
            description="Name of the heartbeat alerts SNS topic",
            export_name=f"{self.stack_name}-HeartbeatTopicName",
        )

    def get_critical_topic(self) -> sns.Topic:
        """
        Get the critical alerts topic.

        Returns:
            The critical alerts SNS topic
        """
        return self.critical_topic

    def get_heartbeat_topic(self) -> sns.Topic:
        """
        Get the heartbeat alerts topic.

        Returns:
            The heartbeat alerts SNS topic
        """
        return self.heartbeat_topic
