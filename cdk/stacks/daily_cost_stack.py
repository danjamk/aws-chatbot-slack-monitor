"""
Daily Cost Report Stack - Scheduled Cost Summary to Slack

This stack creates:
- Lambda function that queries AWS Cost Explorer
- EventBridge rule to trigger Lambda daily
- Sends formatted cost summary to heartbeat channel via SNS
"""

from aws_cdk import Stack, Duration, CfnOutput
from aws_cdk import aws_cloudwatch as cloudwatch
from aws_cdk import aws_cloudwatch_actions as cw_actions
from aws_cdk import aws_events as events
from aws_cdk import aws_events_targets as targets
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_sns as sns
from constructs import Construct


class DailyCostStack(Stack):
    """Stack for daily cost reporting Lambda function."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        config: dict,
        heartbeat_topic: sns.Topic,
        **kwargs,
    ) -> None:
        """
        Initialize the Daily Cost Stack.

        Args:
            scope: CDK app scope
            construct_id: Unique identifier for this stack
            config: Configuration dictionary from config.yaml
            heartbeat_topic: SNS topic for daily reports
            **kwargs: Additional stack properties (env, etc.)
        """
        super().__init__(scope, construct_id, **kwargs)

        self.config = config
        self.heartbeat_topic = heartbeat_topic

        # Create Lambda function for daily cost reporting
        self.cost_function = self._create_cost_function()

        # Create CloudWatch alarm for daily cost reports
        self._create_cost_alarm()

        # Create EventBridge rule for daily schedule
        self._create_daily_schedule()

    def _create_cost_function(self) -> lambda_.Function:
        """
        Create Lambda function that queries Cost Explorer and sends report.

        Returns:
            Lambda function for daily cost reporting
        """
        # Create Lambda execution role with Cost Explorer permissions
        lambda_role = iam.Role(
            self,
            "DailyCostLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            description="Role for daily cost reporting Lambda",
        )

        # Add Cost Explorer read permissions
        lambda_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "ce:GetCostAndUsage",
                    "ce:GetCostForecast",
                ],
                resources=["*"],
            )
        )

        # Add CloudWatch permissions for metrics and alarms
        lambda_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "cloudwatch:PutMetricData",
                    "cloudwatch:SetAlarmState",
                ],
                resources=["*"],
            )
        )

        # Add CloudWatch Logs permissions
        lambda_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name(
                "service-role/AWSLambdaBasicExecutionRole"
            )
        )

        # Add SNS publish permissions
        self.heartbeat_topic.grant_publish(lambda_role)

        # Create Lambda function
        cost_function = lambda_.Function(
            self,
            "DailyCostFunction",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="index.handler",
            code=lambda_.Code.from_inline(self._get_lambda_code()),
            timeout=Duration.seconds(60),
            role=lambda_role,
            environment={
                "SNS_TOPIC_ARN": self.heartbeat_topic.topic_arn,
                "MONTHLY_BUDGET": str(self.config["budgets"]["monthly_limit"]),
                "DAILY_BUDGET": str(self.config["budgets"]["daily_limit"]),
                "CURRENCY": self.config["budgets"]["currency"],
            },
            description="Daily AWS cost report to Slack",
        )

        CfnOutput(
            self,
            "DailyCostFunctionArn",
            value=cost_function.function_arn,
            description="ARN of the daily cost reporting Lambda function",
        )

        return cost_function

    def _create_daily_schedule(self) -> None:
        """Create EventBridge rule to trigger Lambda daily."""
        # Get schedule from config, default to 8 AM UTC
        schedule_hour = self.config.get("daily_report", {}).get("schedule_hour_utc", 8)

        # Create EventBridge rule for daily schedule
        rule = events.Rule(
            self,
            "DailyCostReportRule",
            schedule=events.Schedule.cron(
                minute="0",
                hour=str(schedule_hour),
                month="*",
                week_day="*",
                year="*",
            ),
            description=f"Trigger daily cost report at {schedule_hour}:00 UTC",
        )

        # Add Lambda as target
        rule.add_target(targets.LambdaFunction(self.cost_function))

        CfnOutput(
            self,
            "DailyCostReportSchedule",
            value=f"{schedule_hour}:00 UTC daily",
            description="Schedule for daily cost reports",
        )

    def _create_cost_alarm(self) -> None:
        """
        Create CloudWatch alarm for daily cost reports.

        The Lambda function will manually trigger this alarm's state to send
        notifications to Slack via AWS Chatbot (which only displays certain
        message types like CloudWatch alarms).
        """
        # Create a custom metric for daily cost reports
        metric = cloudwatch.Metric(
            namespace="AWS/Billing",
            metric_name="DailyCostReport",
            statistic="Average",
            period=Duration.days(1),
        )

        # Create alarm that Lambda will manually trigger
        alarm = cloudwatch.Alarm(
            self,
            "DailyCostReportAlarm",
            alarm_name="DailyCostReportAlarm",
            alarm_description="Daily AWS cost report (triggered by Lambda)",
            metric=metric,
            threshold=0,  # Dummy threshold - Lambda sets state manually
            evaluation_periods=1,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
        )

        # Add SNS action so alarm notifications go to Slack
        alarm.add_alarm_action(cw_actions.SnsAction(self.heartbeat_topic))

        CfnOutput(
            self,
            "DailyCostAlarmName",
            value=alarm.alarm_name,
            description="CloudWatch alarm for daily cost reports",
        )

    def _get_lambda_code(self) -> str:
        """
        Get Lambda function code for daily cost reporting.

        Returns:
            Python code for Lambda function
        """
        return """
import json
import os
from datetime import datetime, timedelta
from decimal import Decimal

import boto3

ce_client = boto3.client('ce')
sns_client = boto3.client('sns')
cw_client = boto3.client('cloudwatch')

# CloudWatch alarm name for daily cost reports
ALARM_NAME = "DailyCostReportAlarm"

def handler(event, context):
    '''Lambda handler for daily cost reporting.'''

    # Get environment variables
    sns_topic_arn = os.environ['SNS_TOPIC_ARN']
    monthly_budget = float(os.environ['MONTHLY_BUDGET'])
    daily_budget = float(os.environ['DAILY_BUDGET'])
    currency = os.environ['CURRENCY']

    # Get yesterday's date
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)

    # Get month start date
    month_start = today.replace(day=1)

    try:
        # Get yesterday's cost
        yesterday_response = ce_client.get_cost_and_usage(
            TimePeriod={
                'Start': str(yesterday),
                'End': str(today)
            },
            Granularity='DAILY',
            Metrics=['UnblendedCost']
        )

        yesterday_cost = float(
            yesterday_response['ResultsByTime'][0]['Total']['UnblendedCost']['Amount']
        )

        # Get month-to-date cost
        mtd_response = ce_client.get_cost_and_usage(
            TimePeriod={
                'Start': str(month_start),
                'End': str(today)
            },
            Granularity='MONTHLY',
            Metrics=['UnblendedCost']
        )

        mtd_cost = float(
            mtd_response['ResultsByTime'][0]['Total']['UnblendedCost']['Amount']
        )

        # Get top 5 services for yesterday
        services_response = ce_client.get_cost_and_usage(
            TimePeriod={
                'Start': str(yesterday),
                'End': str(today)
            },
            Granularity='DAILY',
            Metrics=['UnblendedCost'],
            GroupBy=[
                {
                    'Type': 'DIMENSION',
                    'Key': 'SERVICE'
                }
            ]
        )

        # Parse service costs
        services = []
        for group in services_response['ResultsByTime'][0]['Groups']:
            service_name = group['Keys'][0]
            service_cost = float(group['Metrics']['UnblendedCost']['Amount'])
            if service_cost > 0.01:  # Only include services over $0.01
                services.append((service_name, service_cost))

        # Sort by cost descending and take top 5
        services.sort(key=lambda x: x[1], reverse=True)
        top_services = services[:5]

        # Calculate percentages
        daily_budget_pct = (yesterday_cost / daily_budget * 100) if daily_budget > 0 else 0
        monthly_budget_pct = (mtd_cost / monthly_budget * 100) if monthly_budget > 0 else 0

        # Determine status emoji
        if yesterday_cost > daily_budget:
            daily_emoji = "🔴"
        elif yesterday_cost > daily_budget * 0.8:
            daily_emoji = "🟡"
        else:
            daily_emoji = "🟢"

        if monthly_budget_pct >= 100:
            monthly_emoji = "🔴"
        elif monthly_budget_pct >= 80:
            monthly_emoji = "🟡"
        else:
            monthly_emoji = "🟢"

        # Format service breakdown
        service_lines = []
        for service, cost in top_services:
            # Shorten service names
            short_name = service.replace('Amazon ', '').replace('AWS ', '')
            service_lines.append(f"  • {short_name}: ${cost:.2f}")

        services_text = "\\n".join(service_lines) if service_lines else "  • No significant costs"

        # Build message - formatted for CloudWatch alarm
        message = f'''📊 Daily AWS Cost Report for {yesterday.strftime("%B %d, %Y")}

{daily_emoji} Yesterday: ${yesterday_cost:.2f} {currency} (Budget: ${daily_budget:.2f}, {daily_budget_pct:.1f}%)
{monthly_emoji} Month-to-Date: ${mtd_cost:.2f} {currency} (Budget: ${monthly_budget:.2f}, {monthly_budget_pct:.1f}%)

Top Services (Yesterday):
{services_text}

Status: 🟢 Under budget | 🟡 Approaching limit | 🔴 Over budget

View details: CloudWatch Dashboards | AWS Cost Explorer'''

        # Put custom metric for daily cost
        cw_client.put_metric_data(
            Namespace='AWS/Billing',
            MetricData=[
                {
                    'MetricName': 'DailyCostReport',
                    'Value': yesterday_cost,
                    'Unit': 'None',
                    'Timestamp': datetime.now()
                }
            ]
        )

        # Trigger CloudWatch alarm with custom state
        # This creates an alarm notification that AWS Chatbot will display
        try:
            cw_client.set_alarm_state(
                AlarmName=ALARM_NAME,
                StateValue='ALARM',
                StateReason=message,
                StateReasonData=json.dumps({
                    'version': '1.0',
                    'queryDate': str(datetime.now()),
                    'metricData': {
                        'yesterdayCost': yesterday_cost,
                        'mtdCost': mtd_cost,
                        'dailyBudget': daily_budget,
                        'monthlyBudget': monthly_budget
                    }
                })
            )
            print(f"Triggered CloudWatch alarm with daily cost report: ${yesterday_cost:.2f}")
        except cw_client.exceptions.ResourceNotFoundException:
            # Alarm doesn't exist yet - send via SNS as fallback
            print(f"Alarm {ALARM_NAME} not found, using SNS fallback")
            sns_client.publish(
                TopicArn=sns_topic_arn,
                Subject=f"📊 Daily AWS Cost: ${yesterday_cost:.2f}",
                Message=message
            )

        return {
            'statusCode': 200,
            'body': json.dumps({
                'yesterday_cost': yesterday_cost,
                'mtd_cost': mtd_cost
            })
        }

    except Exception as e:
        error_msg = f"Error generating daily cost report: {str(e)}"
        print(error_msg)
        raise
"""

    def get_cost_function(self) -> lambda_.Function:
        """
        Get the daily cost reporting Lambda function.

        Returns:
            Lambda function
        """
        return self.cost_function
