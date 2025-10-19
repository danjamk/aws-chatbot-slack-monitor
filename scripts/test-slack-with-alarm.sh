#!/bin/bash
# Test Slack notifications using CloudWatch Alarms (supported by AWS Chatbot)

set -e

echo "Creating test CloudWatch alarm to trigger Slack notification..."

# Get topic ARN
CRITICAL_TOPIC_ARN=$(aws cloudformation describe-stacks \
    --stack-name ChatbotMonitorSnsStack \
    --query 'Stacks[0].Outputs[?OutputKey==`CriticalTopicArn`].OutputValue' \
    --output text)

# Create a test alarm
aws cloudwatch put-metric-alarm \
    --alarm-name "ChatbotTest-DeleteMe" \
    --alarm-description "Test alarm for Slack notifications - SAFE TO DELETE" \
    --actions-enabled \
    --alarm-actions "$CRITICAL_TOPIC_ARN" \
    --metric-name CPUUtilization \
    --namespace AWS/EC2 \
    --statistic Average \
    --period 60 \
    --evaluation-periods 1 \
    --threshold 0.1 \
    --comparison-operator LessThanThreshold

echo "✅ Test alarm created: ChatbotTest-DeleteMe"
echo ""
echo "This alarm will trigger because CPUUtilization < 0.1% (always true)"
echo "Check your Slack channel in 1-2 minutes for the notification!"
echo ""
echo "To delete the test alarm:"
echo "  aws cloudwatch delete-alarms --alarm-names ChatbotTest-DeleteMe"
