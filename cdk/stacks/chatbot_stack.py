"""
Chatbot Stack - AWS Chatbot Slack Integration

This stack creates AWS Chatbot configurations for Slack channels:
- Critical alerts channel (low noise, immediate action)
- Heartbeat alerts channel (monitoring, warnings, daily reports)

The stack reads Slack configuration from AWS Secrets Manager and
subscribes the Chatbot to the SNS topics created by the SNS stack.

Prerequisites:
- Slack workspace must be authorized in AWS Console (one-time manual step)
- Secrets deployed to AWS Secrets Manager via deploy-secrets.py
"""

from typing import List

from aws_cdk import Stack, CfnOutput, SecretValue
from aws_cdk import aws_chatbot as chatbot
from aws_cdk import aws_iam as iam
from aws_cdk import aws_secretsmanager as secretsmanager
from aws_cdk import aws_sns as sns
from constructs import Construct


class ChatbotStack(Stack):
    """Stack for creating AWS Chatbot Slack channel configurations."""

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
        Initialize the Chatbot Stack.

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

        # Get Slack configuration from Secrets Manager
        self.slack_config = self._get_slack_config()

        # Create IAM role for Chatbot (read-only)
        self.chatbot_role = self._create_chatbot_role()

        # Create Slack channel configurations
        self._create_critical_channel_config()
        self._create_heartbeat_channel_config()

    def _get_slack_config(self) -> secretsmanager.ISecret:
        """
        Get Slack configuration from AWS Secrets Manager.

        Returns:
            Secret containing Slack workspace and channel IDs
        """
        # Get secret name from config
        project_name = self.config["project"]["name"]
        environment = self.config["project"]["environment"]
        secret_name = f"{project_name}/{environment}/slack-config"

        # Reference existing secret (created by deploy-secrets.py)
        # Note: This uses from_secret_name_v2 which doesn't validate
        # that the secret exists during synthesis
        slack_secret = secretsmanager.Secret.from_secret_name_v2(
            self,
            "SlackConfig",
            secret_name=secret_name,
        )

        return slack_secret

    def _create_chatbot_role(self) -> iam.Role:
        """
        Create IAM role for AWS Chatbot with read-only permissions.

        Returns:
            IAM role for Chatbot to use when executing commands from Slack
        """
        # Create role that AWS Chatbot can assume
        role = iam.Role(
            self,
            "ChatbotRole",
            assumed_by=iam.ServicePrincipal("chatbot.amazonaws.com"),
            description="Read-only role for AWS Chatbot Slack integration",
        )

        # Add read-only permissions
        # Note: We use ReadOnlyAccess instead of AdministratorAccess (security best practice)
        role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("ReadOnlyAccess")
        )

        # Add CloudWatch read permissions (for viewing logs, metrics, alarms)
        role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name(
                "CloudWatchReadOnlyAccess"
            )
        )

        # Output the role ARN
        CfnOutput(
            self,
            "ChatbotRoleArn",
            value=role.role_arn,
            description="ARN of the IAM role used by AWS Chatbot",
        )

        return role

    def _create_critical_channel_config(self) -> None:
        """Create AWS Chatbot configuration for the critical alerts Slack channel."""
        project_name = self.config["project"]["name"]
        environment = self.config["project"]["environment"]

        # Note: We need to parse the secret to get individual values
        # Since we can't parse secrets during synthesis, we'll use a custom resource
        # or Lambda function in a real deployment. For now, we'll document this.

        # For CDK synthesis to work, we create the configuration with placeholders
        # that will be resolved at deploy time
        critical_config = chatbot.CfnSlackChannelConfiguration(
            self,
            "CriticalChannelConfig",
            configuration_name=f"{project_name}-{environment}-critical",
            iam_role_arn=self.chatbot_role.role_arn,
            # Slack workspace ID - must be set manually or via custom resource
            # This will fail during actual deployment until workspace is authorized
            slack_workspace_id=self.slack_config.secret_value_from_json(
                "workspace_id"
            ).unsafe_unwrap(),
            slack_channel_id=self.slack_config.secret_value_from_json(
                "critical_channel_id"
            ).unsafe_unwrap(),
            # Subscribe to critical alerts topic
            sns_topic_arns=[self.critical_topic.topic_arn],
            # Logging configuration
            logging_level=self.config["chatbot"]["logging_level"],
            # User role required (enforce that users assume a role)
            user_role_required=self.config["chatbot"]["user_role_required"],
        )

        CfnOutput(
            self,
            "CriticalChannelConfigName",
            value=critical_config.configuration_name,
            description="Name of the critical alerts Slack channel configuration",
        )

    def _create_heartbeat_channel_config(self) -> None:
        """Create AWS Chatbot configuration for the heartbeat alerts Slack channel."""
        project_name = self.config["project"]["name"]
        environment = self.config["project"]["environment"]

        heartbeat_config = chatbot.CfnSlackChannelConfiguration(
            self,
            "HeartbeatChannelConfig",
            configuration_name=f"{project_name}-{environment}-heartbeat",
            iam_role_arn=self.chatbot_role.role_arn,
            # Slack workspace ID
            slack_workspace_id=self.slack_config.secret_value_from_json(
                "workspace_id"
            ).unsafe_unwrap(),
            slack_channel_id=self.slack_config.secret_value_from_json(
                "heartbeat_channel_id"
            ).unsafe_unwrap(),
            # Subscribe to heartbeat alerts topic
            sns_topic_arns=[self.heartbeat_topic.topic_arn],
            # Logging configuration
            logging_level=self.config["chatbot"]["logging_level"],
            # User role required
            user_role_required=self.config["chatbot"]["user_role_required"],
        )

        CfnOutput(
            self,
            "HeartbeatChannelConfigName",
            value=heartbeat_config.configuration_name,
            description="Name of the heartbeat alerts Slack channel configuration",
        )

    def get_chatbot_role(self) -> iam.Role:
        """
        Get the Chatbot IAM role.

        Returns:
            The IAM role used by AWS Chatbot
        """
        return self.chatbot_role
