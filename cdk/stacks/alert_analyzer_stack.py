"""
AI Alert Analyzer Stack

Deploys the Phase 1 AI-powered alert analysis system:
- Lambda function with LangGraph workflow
- SNS subscription for alert notifications
- IAM permissions for AWS tools (Cost Explorer, CloudWatch, EMR)
- Environment variables for configuration

This replaces AWS Chatbot with AI-powered analysis.
"""

import json
from aws_cdk import (
    Stack,
    Duration,
    aws_lambda as lambda_,
    aws_sns as sns,
    aws_sns_subscriptions as subscriptions,
    aws_iam as iam,
    aws_logs as logs,
)
from constructs import Construct


class AlertAnalyzerStack(Stack):
    """Stack for AI-powered alert analysis Lambda."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        config: dict,
        critical_topic: sns.Topic,
        heartbeat_topic: sns.Topic,
        **kwargs
    ) -> None:
        """
        Initialize the Alert Analyzer stack.

        Args:
            scope: CDK app scope
            construct_id: Stack identifier
            config: Configuration from config.yaml
            critical_topic: SNS topic for critical alerts
            heartbeat_topic: SNS topic for heartbeat alerts
            **kwargs: Additional stack arguments
        """
        super().__init__(scope, construct_id, **kwargs)

        self.config = config

        # Create Lambda function
        self.alert_analyzer = self._create_lambda_function()

        # Subscribe to SNS topics
        self._subscribe_to_topics(critical_topic, heartbeat_topic)

        # Grant IAM permissions
        self._grant_permissions()

    def _create_lambda_function(self) -> lambda_.Function:
        """Create the alert analyzer Lambda function."""

        # Create Lambda execution role
        role = iam.Role(
            self,
            'AlertAnalyzerRole',
            assumed_by=iam.ServicePrincipal('lambda.amazonaws.com'),
            description='Execution role for AI Alert Analyzer',
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    'service-role/AWSLambdaBasicExecutionRole'
                ),
            ],
        )

        # Prepare configuration as JSON string for Lambda environment
        config_json = json.dumps(self.config)

        # Create Lambda function
        alert_analyzer = lambda_.Function(
            self,
            'AlertAnalyzer',
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler='index.lambda_handler',
            code=lambda_.Code.from_asset('cdk/lambda/alert_analyzer'),
            timeout=Duration.seconds(90),  # AI analysis can take time
            memory_size=512,  # Increased for LangGraph + tools
            role=role,
            environment={
                'CONFIG_JSON': config_json,
                # LLM configuration (from environment or use defaults)
                'LLM_PROVIDER': 'bedrock',
                'LLM_MODEL_ID': 'anthropic.claude-3-5-sonnet-20250514-v2:0',
                'LLM_TEMPERATURE': '0.3',
                'LLM_MAX_TOKENS': '2000',
                # Note: SLACK_CRITICAL_WEBHOOK and SLACK_HEARTBEAT_WEBHOOK
                # will be added from Secrets Manager in production
            },
            description='AI-powered AWS alert analyzer (Phase 1)',
            log_retention=logs.RetentionDays.ONE_WEEK,
        )

        return alert_analyzer

    def _subscribe_to_topics(
        self,
        critical_topic: sns.Topic,
        heartbeat_topic: sns.Topic
    ) -> None:
        """Subscribe Lambda to SNS topics."""

        # Subscribe to critical alerts topic
        critical_topic.add_subscription(
            subscriptions.LambdaSubscription(self.alert_analyzer)
        )

        # Subscribe to heartbeat alerts topic
        heartbeat_topic.add_subscription(
            subscriptions.LambdaSubscription(self.alert_analyzer)
        )

    def _grant_permissions(self) -> None:
        """Grant IAM permissions for AWS tools."""

        role = self.alert_analyzer.role

        # Cost Explorer permissions
        role.add_to_policy(
            iam.PolicyStatement(
                sid='CostExplorerAccess',
                actions=[
                    'ce:GetCostAndUsage',
                    'ce:GetCostForecast',
                    'budgets:DescribeBudgets',
                    'budgets:ViewBudget',
                ],
                resources=['*'],  # Cost Explorer doesn't support resource-level permissions
            )
        )

        # CloudWatch permissions
        role.add_to_policy(
            iam.PolicyStatement(
                sid='CloudWatchAccess',
                actions=[
                    'cloudwatch:GetMetricStatistics',
                    'cloudwatch:ListMetrics',
                    'logs:FilterLogEvents',
                    'logs:StartQuery',
                    'logs:GetQueryResults',
                    'logs:DescribeLogGroups',
                ],
                resources=['*'],
            )
        )

        # Lambda read permissions (for analyzing other Lambda functions)
        role.add_to_policy(
            iam.PolicyStatement(
                sid='LambdaReadAccess',
                actions=[
                    'lambda:GetFunction',
                    'lambda:GetFunctionConfiguration',
                    'lambda:ListFunctions',
                ],
                resources=['*'],
            )
        )

        # EC2 read permissions
        role.add_to_policy(
            iam.PolicyStatement(
                sid='EC2ReadAccess',
                actions=[
                    'ec2:DescribeInstances',
                    'ec2:DescribeInstanceStatus',
                ],
                resources=['*'],
            )
        )

        # EMR read permissions
        role.add_to_policy(
            iam.PolicyStatement(
                sid='EMRReadAccess',
                actions=[
                    'elasticmapreduce:DescribeCluster',
                    'elasticmapreduce:ListClusters',
                    'elasticmapreduce:ListSteps',
                    'elasticmapreduce:DescribeStep',
                ],
                resources=['*'],
            )
        )

        # Resource Groups Tagging API permissions
        role.add_to_policy(
            iam.PolicyStatement(
                sid='TaggingReadAccess',
                actions=[
                    'tag:GetResources',
                    'tag:GetTagKeys',
                    'tag:GetTagValues',
                ],
                resources=['*'],
            )
        )

        # CloudTrail read permissions
        role.add_to_policy(
            iam.PolicyStatement(
                sid='CloudTrailReadAccess',
                actions=[
                    'cloudtrail:LookupEvents',
                ],
                resources=['*'],
            )
        )

        # AWS Bedrock permissions for LLM
        role.add_to_policy(
            iam.PolicyStatement(
                sid='BedrockAccess',
                actions=[
                    'bedrock:InvokeModel',
                ],
                resources=[
                    f'arn:aws:bedrock:{self.region}::foundation-model/*',
                ],
            )
        )

        # Secrets Manager permissions (for Slack webhooks in production)
        role.add_to_policy(
            iam.PolicyStatement(
                sid='SecretsManagerAccess',
                actions=[
                    'secretsmanager:GetSecretValue',
                ],
                resources=[
                    f'arn:aws:secretsmanager:{self.region}:{self.account}:secret:aws-alert-intel/*',
                ],
            )
        )

        # STS for getting account ID
        role.add_to_policy(
            iam.PolicyStatement(
                sid='STSAccess',
                actions=[
                    'sts:GetCallerIdentity',
                ],
                resources=['*'],
            )
        )
