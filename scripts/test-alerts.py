#!/usr/bin/env python3
"""
Test script for sending test alerts to the AI Alert Analyzer.

Usage:
    python scripts/test-alerts.py budget-warning
    python scripts/test-alerts.py emr-failure
    python scripts/test-alerts.py daily-report
    python scripts/test-alerts.py all

This script sends test alert payloads to the SNS topics to verify
the AI alert analyzer is working correctly.
"""

import argparse
import boto3
import json
import sys
from pathlib import Path


def load_fixture(fixture_name: str) -> dict:
    """Load test fixture JSON file."""
    fixture_path = Path(__file__).parent.parent / "tests" / "fixtures" / f"{fixture_name}.json"

    if not fixture_path.exists():
        print(f"Error: Fixture not found: {fixture_path}")
        sys.exit(1)

    with open(fixture_path, "r") as f:
        return json.load(f)


def get_topic_arn(topic_name: str) -> str:
    """Get SNS topic ARN by name."""
    sns = boto3.client("sns")

    try:
        # List topics and find matching name
        response = sns.list_topics()

        for topic in response["Topics"]:
            if topic_name in topic["TopicArn"]:
                return topic["TopicArn"]

        print(f"Error: Topic not found: {topic_name}")
        print("Available topics:")
        for topic in response["Topics"]:
            print(f"  - {topic['TopicArn']}")
        sys.exit(1)

    except Exception as e:
        print(f"Error getting topic ARN: {e}")
        sys.exit(1)


def send_test_alert(alert_type: str, fixture_data: dict):
    """Send test alert to appropriate SNS topic."""

    # Determine which topic to use
    if "critical" in alert_type or "failure" in alert_type:
        topic_name = "critical-alerts"
    else:
        topic_name = "heartbeat-alerts"

    topic_arn = get_topic_arn(topic_name)

    sns = boto3.client("sns")

    # Extract message from fixture (different formats for SNS vs EventBridge)
    if "Records" in fixture_data:
        # SNS format
        message = fixture_data["Records"][0]["Sns"]["Message"]
        subject = fixture_data["Records"][0]["Sns"].get("Subject", f"Test {alert_type}")
    else:
        # EventBridge format
        message = json.dumps(fixture_data)
        subject = f"Test {alert_type}"

    try:
        print(f"\nSending test alert: {alert_type}")
        print(f"Topic: {topic_name} ({topic_arn})")
        print(f"Subject: {subject}")

        response = sns.publish(
            TopicArn=topic_arn,
            Message=message,
            Subject=subject,
        )

        print(f"✅ Successfully sent test alert!")
        print(f"Message ID: {response['MessageId']}")
        print(f"\nCheck your Slack channel for the AI-analyzed alert.")

    except Exception as e:
        print(f"❌ Error sending test alert: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Send test alerts to AI Alert Analyzer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/test-alerts.py budget-warning    # Test budget warning alert
  python scripts/test-alerts.py emr-failure       # Test EMR cluster failure
  python scripts/test-alerts.py daily-report      # Test daily cost report
  python scripts/test-alerts.py all               # Send all test alerts

Available Alert Types:
  budget-warning     - Monthly budget exceeded 80% (should trigger AI analysis)
  emr-failure        - EMR cluster terminated with errors (should trigger AI analysis)
  daily-report       - Daily cost report (should NOT trigger AI analysis, passthrough)
        """
    )

    parser.add_argument(
        "alert_type",
        choices=["budget-warning", "emr-failure", "daily-report", "all"],
        help="Type of test alert to send"
    )

    args = parser.parse_args()

    # Map alert types to fixture names
    alert_fixtures = {
        "budget-warning": "budget_warning",
        "emr-failure": "emr_failure",
        "daily-report": "daily_cost_report",
    }

    if args.alert_type == "all":
        print("Sending all test alerts...")
        for alert_type, fixture_name in alert_fixtures.items():
            fixture_data = load_fixture(fixture_name)
            send_test_alert(alert_type, fixture_data)
            print()  # Blank line between alerts
    else:
        fixture_name = alert_fixtures[args.alert_type]
        fixture_data = load_fixture(fixture_name)
        send_test_alert(args.alert_type, fixture_data)


if __name__ == "__main__":
    main()
