# Integration Guide - Using SNS Topics from Other Stacks

This guide shows how to integrate other AWS infrastructure with the AWS Chatbot Slack Monitor notification system.

## Overview

The AWS Chatbot Slack Monitor project creates two SNS topics that can be used by other CDK stacks:

- **Critical Alerts** (`critical-alerts`) - For severe issues requiring immediate action
- **Heartbeat Alerts** (`heartbeat-alerts`) - For monitoring, warnings, and informational messages

Both topics are exported from the SNS stack and can be imported by any other stack in the same AWS account.

## Quick Reference

### Topic ARNs (Exported)

```yaml
Export Names:
  - ChatbotMonitorSnsStack-CriticalTopicArn
  - ChatbotMonitorSnsStack-HeartbeatTopicArn
```

### Import in CDK (Python)

```python
from aws_cdk import aws_sns as sns
from aws_cdk import Fn

# Import critical alerts topic
critical_topic = sns.Topic.from_topic_arn(
    self,
    "CriticalAlertsTopic",
    Fn.import_value("ChatbotMonitorSnsStack-CriticalTopicArn")
)

# Import heartbeat alerts topic
heartbeat_topic = sns.Topic.from_topic_arn(
    self,
    "HeartbeatAlertsTopic",
    Fn.import_value("ChatbotMonitorSnsStack-HeartbeatTopicArn")
)
```

## Integration Examples

### 1. ECS Service Alerts

Alert when an ECS service is unhealthy or task count drops to zero.

```python
from aws_cdk import Stack
from aws_cdk import aws_ecs as ecs
from aws_cdk import aws_cloudwatch as cloudwatch
from aws_cdk import aws_cloudwatch_actions as cloudwatch_actions
from aws_cdk import aws_sns as sns
from aws_cdk import Fn
from constructs import Construct


class MyECSStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        # Import the critical alerts topic
        critical_topic = sns.Topic.from_topic_arn(
            self,
            "CriticalAlertsTopic",
            Fn.import_value("ChatbotMonitorSnsStack-CriticalTopicArn")
        )

        # Your ECS service
        service = ecs.FargateService(...)

        # Create alarm for running task count
        task_count_alarm = cloudwatch.Alarm(
            self,
            "ECSTaskCountAlarm",
            metric=service.metric_running_task_count(),
            threshold=1,
            evaluation_periods=2,
            comparison_operator=cloudwatch.ComparisonOperator.LESS_THAN_THRESHOLD,
            alarm_name="ECS-Service-NoRunningTasks",
            alarm_description="Alert when ECS service has no running tasks",
        )

        # Send alarm to critical Slack channel
        task_count_alarm.add_alarm_action(
            cloudwatch_actions.SnsAction(critical_topic)
        )
```

### 2. Lambda Function Errors

Alert on Lambda function errors or throttling.

```python
from aws_cdk import Stack
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_cloudwatch as cloudwatch
from aws_cdk import aws_cloudwatch_actions as cloudwatch_actions
from aws_cdk import aws_sns as sns
from aws_cdk import Fn
from constructs import Construct


class MyLambdaStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        # Import topics
        critical_topic = sns.Topic.from_topic_arn(
            self,
            "CriticalAlertsTopic",
            Fn.import_value("ChatbotMonitorSnsStack-CriticalTopicArn")
        )

        heartbeat_topic = sns.Topic.from_topic_arn(
            self,
            "HeartbeatAlertsTopic",
            Fn.import_value("ChatbotMonitorSnsStack-HeartbeatTopicArn")
        )

        # Your Lambda function
        my_function = lambda_.Function(...)

        # Critical: High error rate
        error_alarm = cloudwatch.Alarm(
            self,
            "LambdaErrorAlarm",
            metric=my_function.metric_errors(),
            threshold=10,
            evaluation_periods=2,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            alarm_name="Lambda-HighErrorRate",
        )
        error_alarm.add_alarm_action(cloudwatch_actions.SnsAction(critical_topic))

        # Warning: Throttling occurring
        throttle_alarm = cloudwatch.Alarm(
            self,
            "LambdaThrottleAlarm",
            metric=my_function.metric_throttles(),
            threshold=5,
            evaluation_periods=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            alarm_name="Lambda-Throttling",
        )
        throttle_alarm.add_alarm_action(cloudwatch_actions.SnsAction(heartbeat_topic))
```

### 3. RDS Database Alerts

Alert on database connection issues or high CPU.

```python
from aws_cdk import Stack, Duration
from aws_cdk import aws_rds as rds
from aws_cdk import aws_cloudwatch as cloudwatch
from aws_cdk import aws_cloudwatch_actions as cloudwatch_actions
from aws_cdk import aws_sns as sns
from aws_cdk import Fn
from constructs import Construct


class MyDatabaseStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        # Import topics
        critical_topic = sns.Topic.from_topic_arn(
            self,
            "CriticalAlertsTopic",
            Fn.import_value("ChatbotMonitorSnsStack-CriticalTopicArn")
        )

        # Your RDS database
        database = rds.DatabaseInstance(...)

        # Critical: Database connections maxed out
        connection_alarm = cloudwatch.Alarm(
            self,
            "RDSConnectionAlarm",
            metric=database.metric_database_connections(),
            threshold=90,  # Adjust based on instance size
            evaluation_periods=2,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            alarm_name="RDS-HighConnections",
        )
        connection_alarm.add_alarm_action(cloudwatch_actions.SnsAction(critical_topic))

        # Critical: High CPU utilization
        cpu_alarm = cloudwatch.Alarm(
            self,
            "RDSCPUAlarm",
            metric=database.metric_cpu_utilization(),
            threshold=85,
            evaluation_periods=3,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            alarm_name="RDS-HighCPU",
        )
        cpu_alarm.add_alarm_action(cloudwatch_actions.SnsAction(critical_topic))
```

### 4. S3 Bucket Events

Alert on specific S3 bucket events.

```python
from aws_cdk import Stack
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_s3_notifications as s3n
from aws_cdk import aws_sns as sns
from aws_cdk import Fn
from constructs import Construct


class MyS3Stack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        # Import heartbeat topic
        heartbeat_topic = sns.Topic.from_topic_arn(
            self,
            "HeartbeatAlertsTopic",
            Fn.import_value("ChatbotMonitorSnsStack-HeartbeatTopicArn")
        )

        # Your S3 bucket
        bucket = s3.Bucket(...)

        # Notify on object creation in specific prefix
        bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED,
            s3n.SnsDestination(heartbeat_topic),
            s3.NotificationKeyFilter(prefix="uploads/")
        )
```

### 5. Custom Application Metrics

Publish custom application metrics and alert on thresholds.

```python
from aws_cdk import Stack, Duration
from aws_cdk import aws_cloudwatch as cloudwatch
from aws_cdk import aws_cloudwatch_actions as cloudwatch_actions
from aws_cdk import aws_sns as sns
from aws_cdk import Fn
from constructs import Construct


class MyAppStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        # Import topics
        critical_topic = sns.Topic.from_topic_arn(
            self,
            "CriticalAlertsTopic",
            Fn.import_value("ChatbotMonitorSnsStack-CriticalTopicArn")
        )

        # Custom metric (your app publishes this via CloudWatch SDK)
        payment_failures = cloudwatch.Metric(
            namespace="MyApp",
            metric_name="PaymentFailures",
            statistic="Sum",
            period=Duration.minutes(5),
        )

        # Alert on payment processing failures
        payment_alarm = cloudwatch.Alarm(
            self,
            "PaymentFailuresAlarm",
            metric=payment_failures,
            threshold=5,
            evaluation_periods=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            alarm_name="App-PaymentFailures",
            alarm_description="Alert when payment processing fails",
        )
        payment_alarm.add_alarm_action(cloudwatch_actions.SnsAction(critical_topic))
```

### 6. Direct SNS Publishing (Non-CDK)

If you have existing infrastructure, you can publish directly to the topics.

**Using AWS CLI**:
```bash
# Get the topic ARN
CRITICAL_TOPIC_ARN=$(aws cloudformation describe-stacks \
  --stack-name ChatbotMonitorSnsStack \
  --query 'Stacks[0].Outputs[?OutputKey==`CriticalTopicArn`].OutputValue' \
  --output text)

# Publish a message
aws sns publish \
  --topic-arn "$CRITICAL_TOPIC_ARN" \
  --subject "Production Database Down" \
  --message "Database instance i-1234567890 is not responding"
```

**Using Python (boto3)**:
```python
import boto3

# Create SNS client
sns_client = boto3.client('sns')

# Get topic ARN from CloudFormation
cf_client = boto3.client('cloudformation')
response = cf_client.describe_stacks(StackName='ChatbotMonitorSnsStack')
outputs = response['Stacks'][0]['Outputs']
critical_topic_arn = next(
    o['OutputValue'] for o in outputs
    if o['OutputKey'] == 'CriticalTopicArn'
)

# Publish message
sns_client.publish(
    TopicArn=critical_topic_arn,
    Subject='Production Alert',
    Message='Critical issue detected in production environment'
)
```

**Using Node.js (AWS SDK)**:
```javascript
const { CloudFormationClient, DescribeStacksCommand } = require("@aws-sdk/client-cloudformation");
const { SNSClient, PublishCommand } = require("@aws-sdk/client-sns");

async function publishAlert() {
  // Get topic ARN
  const cfClient = new CloudFormationClient({});
  const stackData = await cfClient.send(
    new DescribeStacksCommand({ StackName: "ChatbotMonitorSnsStack" })
  );

  const outputs = stackData.Stacks[0].Outputs;
  const topicArn = outputs.find(o => o.OutputKey === "CriticalTopicArn").OutputValue;

  // Publish message
  const snsClient = new SNSClient({});
  await snsClient.send(
    new PublishCommand({
      TopicArn: topicArn,
      Subject: "Production Alert",
      Message: "Critical issue detected"
    })
  );
}
```

## Message Formatting Tips

### Good Slack Message Format

When publishing to SNS topics that go to Slack, format your messages for readability:

```python
message = """
🔴 CRITICAL: Production API Error

Service: payment-api
Environment: production
Error Rate: 15% (normal: <1%)
Duration: 5 minutes

Impact: Payment processing degraded

Actions Taken:
- Auto-scaling triggered
- Team notified

Runbook: https://wiki.example.com/runbooks/payment-api-errors
Dashboard: https://grafana.example.com/payment-api
"""

sns_client.publish(
    TopicArn=critical_topic_arn,
    Subject="🔴 Production API Error",
    Message=message
)
```

### Best Practices

1. **Use emojis** for visual scanning: 🔴 🟡 🟢 ⚠️ ✅ ❌
2. **Include context**: Service name, environment, time
3. **Provide links**: Runbooks, dashboards, logs
4. **Keep it concise**: Slack has message limits
5. **Use proper subjects**: Shows in notification previews

## Notification Routing Guidelines

### Critical Channel (`critical-alerts`)

**Use for**:
- Production system down
- Data loss or corruption
- Security incidents
- Payment processing failures
- Budget exceeded (100%+)

**Characteristics**:
- Low noise (< 5 messages/day ideal)
- Requires immediate human action
- Wakes people up (use sparingly!)

### Heartbeat Channel (`heartbeat-alerts`)

**Use for**:
- Daily status reports
- Budget warnings (80%)
- Performance degradation
- Deployment notifications
- Scaling events
- Non-critical errors

**Characteristics**:
- Medium noise (acceptable)
- Informational or warning
- Action may be required during business hours

## Troubleshooting

### Messages not appearing in Slack

1. **Check SNS subscriptions**:
   ```bash
   aws sns list-subscriptions-by-topic \
     --topic-arn arn:aws:sns:us-east-1:123456789012:critical-alerts
   ```

2. **Verify AWS Chatbot subscription**:
   - Should show `Protocol: chatbot` or similar
   - Status should be `Confirmed`

3. **Check CloudWatch Logs**:
   - AWS Chatbot logs delivery attempts
   - Look for errors in CloudWatch Logs

4. **Test directly**:
   ```bash
   make validate
   ```

### Stack dependency errors

If you get errors about stack dependencies:

```
Error: ChatbotMonitorSnsStack must be deployed first
```

**Solution**: Deploy stacks in order:
```bash
cdk deploy ChatbotMonitorSnsStack  # First
cdk deploy MyCustomStack           # Then your stack
```

Or use `cdk deploy --all` to deploy in dependency order.

## Advanced: Creating Helper Functions

Create a reusable construct for importing the topics:

```python
# my_constructs/chatbot_alerts.py
from aws_cdk import aws_sns as sns
from aws_cdk import Fn
from constructs import Construct


class ChatbotAlerts(Construct):
    """
    Helper construct to import AWS Chatbot Slack Monitor topics.

    Usage:
        alerts = ChatbotAlerts(self, "Alerts")
        my_alarm.add_alarm_action(cloudwatch_actions.SnsAction(alerts.critical))
    """

    def __init__(self, scope: Construct, construct_id: str):
        super().__init__(scope, construct_id)

        self.critical = sns.Topic.from_topic_arn(
            self,
            "CriticalTopic",
            Fn.import_value("ChatbotMonitorSnsStack-CriticalTopicArn")
        )

        self.heartbeat = sns.Topic.from_topic_arn(
            self,
            "HeartbeatTopic",
            Fn.import_value("ChatbotMonitorSnsStack-HeartbeatTopicArn")
        )
```

Then use it in your stacks:

```python
from my_constructs.chatbot_alerts import ChatbotAlerts

class MyStack(Stack):
    def __init__(self, scope, construct_id, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        # Import both topics easily
        alerts = ChatbotAlerts(self, "Alerts")

        # Use in alarms
        my_alarm.add_alarm_action(
            cloudwatch_actions.SnsAction(alerts.critical)
        )
```

## Resources

- [AWS SNS Documentation](https://docs.aws.amazon.com/sns/)
- [AWS CloudWatch Alarms](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/AlarmThatSendsEmail.html)
- [AWS Chatbot Documentation](https://docs.aws.amazon.com/chatbot/)
- [CDK SNS Module](https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_sns.html)
