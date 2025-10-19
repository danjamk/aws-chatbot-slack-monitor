#!/bin/bash
# validate-notifications.sh - Test SNS topic notifications to Slack

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo ""
echo "╔════════════════════════════════════════════════════════╗"
echo "║  AWS Chatbot Slack Monitor - Notification Validator   ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""

# Get the AWS region
AWS_REGION="${AWS_DEFAULT_REGION:-us-east-1}"

echo -e "${BLUE}Checking deployed stacks...${NC}"

# Get SNS topic ARNs from CloudFormation outputs
CRITICAL_TOPIC_ARN=$(aws cloudformation describe-stacks \
    --stack-name ChatbotMonitorSnsStack \
    --region "$AWS_REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`CriticalTopicArn`].OutputValue' \
    --output text 2>/dev/null)

HEARTBEAT_TOPIC_ARN=$(aws cloudformation describe-stacks \
    --stack-name ChatbotMonitorSnsStack \
    --region "$AWS_REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`HeartbeatTopicArn`].OutputValue' \
    --output text 2>/dev/null)

if [ -z "$CRITICAL_TOPIC_ARN" ] || [ -z "$HEARTBEAT_TOPIC_ARN" ]; then
    echo -e "${RED}✗${NC} Could not find SNS topics"
    echo "   Make sure the SNS stack is deployed: make deploy"
    exit 1
fi

echo -e "${GREEN}✓${NC} Found SNS topics:"
echo "   Critical: ${CRITICAL_TOPIC_ARN}"
echo "   Heartbeat: ${HEARTBEAT_TOPIC_ARN}"
echo ""

# Test heartbeat channel
echo -e "${BLUE}Testing heartbeat channel...${NC}"
HEARTBEAT_MESSAGE_ID=$(aws sns publish \
    --topic-arn "$HEARTBEAT_TOPIC_ARN" \
    --subject "Test: Heartbeat Channel" \
    --message "$(cat <<'EOF'
This is a test message for the heartbeat channel.

If you're seeing this in Slack, your AWS Chatbot integration is working correctly!

Channel: Heartbeat (monitoring, warnings, daily reports)
Noise Level: May be noisy
Action Required: None - this is just a test

Timestamp: $(date -u +"%Y-%m-%d %H:%M:%S UTC")
EOF
)" \
    --region "$AWS_REGION" \
    --query 'MessageId' \
    --output text)

echo -e "${GREEN}✓${NC} Published to heartbeat channel"
echo "   Message ID: ${HEARTBEAT_MESSAGE_ID}"
echo ""

# Wait a bit before sending the critical message
sleep 2

# Test critical channel
echo -e "${BLUE}Testing critical channel...${NC}"
CRITICAL_MESSAGE_ID=$(aws sns publish \
    --topic-arn "$CRITICAL_TOPIC_ARN" \
    --subject "Test: Critical Alert Channel" \
    --message "$(cat <<'EOF'
This is a test message for the critical alerts channel.

If you're seeing this in Slack, your critical alerts are working!

⚠️  IMPORTANT: This channel should be LOW NOISE
Only critical alerts that require immediate action should appear here.

Channel: Critical Alerts
Noise Level: Low (only critical issues)
Action Required: None - this is just a test

Timestamp: $(date -u +"%Y-%m-%d %H:%M:%S UTC")
EOF
)" \
    --region "$AWS_REGION" \
    --query 'MessageId' \
    --output text)

echo -e "${GREEN}✓${NC} Published to critical channel"
echo "   Message ID: ${CRITICAL_MESSAGE_ID}"
echo ""

echo "╔════════════════════════════════════════════════════════╗"
echo "║  ✓ Validation Complete                                ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""
echo -e "${GREEN}Both test messages have been published to SNS.${NC}"
echo ""
echo "Next steps:"
echo "  1. Check your Slack channels for the test messages"
echo "  2. If you don't see them, verify AWS Chatbot configuration:"
echo "     - Go to AWS Console → AWS Chatbot"
echo "     - Check Slack workspace is authorized"
echo "     - Check channel configurations are correct"
echo "  3. Review SNS subscriptions:"
echo "     aws sns list-subscriptions-by-topic --topic-arn $HEARTBEAT_TOPIC_ARN"
echo ""
