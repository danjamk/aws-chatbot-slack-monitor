"""
Chatbot Stack - AWS Chatbot Slack Integration

This stack creates AWS Chatbot configurations for Slack channels:
- Critical alerts channel (low noise, immediate action)
- Heartbeat alerts channel (monitoring, warnings, daily reports)

The stack reads Slack configuration from config.yaml and subscribes
the Chatbot to the SNS topics created by the SNS stack.

Prerequisites:
- Slack workspace must be authorized in AWS Console (one-time manual step)
- Slack IDs configured in config.yaml
"""

from aws_cdk import Stack, CfnOutput
from aws_cdk import aws_chatbot as chatbot
from aws_cdk import aws_iam as iam
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

        # Validate Slack configuration is present
        if "slack" not in config:
            raise ValueError(
                "Slack configuration missing from config.yaml. "
                "Add slack.workspace_id, slack.critical_channel_id, "
                "and slack.heartbeat_channel_id"
            )

        # Create IAM role for Chatbot (read-only)
        self.chatbot_role = self._create_chatbot_role()

        # Create Slack channel configurations
        self._create_critical_channel_config()
        self._create_heartbeat_channel_config()

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

        # Create Slack channel configuration
        # Slack IDs from config.yaml (not sensitive, just identifiers)
        critical_config = chatbot.CfnSlackChannelConfiguration(
            self,
            "CriticalChannelConfig",
            configuration_name=f"{project_name}-{environment}-critical",
            iam_role_arn=self.chatbot_role.role_arn,
            # Slack workspace and channel IDs from config.yaml
            slack_workspace_id=self.config["slack"]["workspace_id"],
            slack_channel_id=self.config["slack"]["critical_channel_id"],
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
            # Slack workspace and channel IDs from config.yaml
            slack_workspace_id=self.config["slack"]["workspace_id"],
            slack_channel_id=self.config["slack"]["heartbeat_channel_id"],
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
