#!/usr/bin/env python3
"""
Deploy Secrets to AWS Secrets Manager

This script reads secrets from the .env file and deploys them to AWS Secrets Manager
for secure access by the CDK stacks.

Secrets deployed:
- Slack Workspace ID
- Slack Critical Channel ID
- Slack Heartbeat Channel ID

Usage:
    python scripts/deploy-secrets.py

Requirements:
    - .env file with required Slack configuration
    - AWS credentials configured (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
    - boto3 installed
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, Optional

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv


class Colors:
    """ANSI color codes for terminal output."""

    RED = "\033[0;31m"
    GREEN = "\033[0;32m"
    YELLOW = "\033[1;33m"
    BLUE = "\033[0;34m"
    NC = "\033[0m"  # No Color


def print_header(message: str) -> None:
    """Print a formatted header message."""
    print(f"\n{Colors.BLUE}{'=' * 70}{Colors.NC}")
    print(f"{Colors.BLUE}{message}{Colors.NC}")
    print(f"{Colors.BLUE}{'=' * 70}{Colors.NC}\n")


def print_success(message: str) -> None:
    """Print a success message."""
    print(f"{Colors.GREEN}✓{Colors.NC} {message}")


def print_error(message: str) -> None:
    """Print an error message."""
    print(f"{Colors.RED}✗{Colors.NC} {message}")


def print_warning(message: str) -> None:
    """Print a warning message."""
    print(f"{Colors.YELLOW}⚠{Colors.NC}  {message}")


def print_info(message: str) -> None:
    """Print an info message."""
    print(f"  {message}")


def load_environment() -> bool:
    """
    Load environment variables from .env file.

    Returns:
        True if .env file was loaded successfully, False otherwise
    """
    env_path = Path(__file__).parent.parent / ".env"

    if not env_path.exists():
        print_error(f".env file not found at {env_path}")
        print_info("Create one from the template:")
        print_info("  cp config/.env.example .env")
        print_info("  vim .env  # Fill in your values")
        return False

    load_dotenv(env_path)
    print_success(f"Loaded environment from {env_path}")
    return True


def validate_required_secrets() -> Optional[Dict[str, str]]:
    """
    Validate that all required secrets are present in environment.

    Returns:
        Dictionary of secrets if all are present, None otherwise
    """
    required_vars = [
        "SLACK_WORKSPACE_ID",
        "SLACK_CRITICAL_CHANNEL_ID",
        "SLACK_HEARTBEAT_CHANNEL_ID",
    ]

    secrets = {}
    missing = []

    for var in required_vars:
        value = os.environ.get(var, "").strip()
        if not value:
            missing.append(var)
        else:
            secrets[var] = value

    if missing:
        print_error("Missing required environment variables:")
        for var in missing:
            print_info(f"  - {var}")
        print_info("\nEdit your .env file and add these values")
        return None

    # Validate format of Slack IDs
    workspace_id = secrets["SLACK_WORKSPACE_ID"]
    critical_channel_id = secrets["SLACK_CRITICAL_CHANNEL_ID"]
    heartbeat_channel_id = secrets["SLACK_HEARTBEAT_CHANNEL_ID"]

    format_errors = []

    if not workspace_id.startswith("T"):
        format_errors.append(
            f"SLACK_WORKSPACE_ID should start with 'T' (got: {workspace_id})"
        )

    if not critical_channel_id.startswith("C"):
        format_errors.append(
            f"SLACK_CRITICAL_CHANNEL_ID should start with 'C' (got: {critical_channel_id})"
        )

    if not heartbeat_channel_id.startswith("C"):
        format_errors.append(
            f"SLACK_HEARTBEAT_CHANNEL_ID should start with 'C' (got: {heartbeat_channel_id})"
        )

    if format_errors:
        print_error("Invalid Slack ID formats:")
        for error in format_errors:
            print_info(f"  - {error}")
        print_info("\nSlack IDs should look like:")
        print_info("  - Workspace ID: T01234ABCDE")
        print_info("  - Channel ID: C01234ABCDE")
        return None

    print_success("All required secrets are present and valid")
    return secrets


def get_secret_name() -> str:
    """
    Get the secret name from config or use default.

    Returns:
        Secret name to use in AWS Secrets Manager
    """
    # Try to get project name from config
    config_path = Path(__file__).parent.parent / "config" / "config.yaml"

    if config_path.exists():
        import yaml

        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
            project_name = config.get("project", {}).get("name", "aws-chatbot-monitor")
            environment = config.get("project", {}).get("environment", "prod")
            return f"{project_name}/{environment}/slack-config"

    # Default secret name
    return "aws-chatbot-monitor/prod/slack-config"


def get_aws_client():
    """
    Get AWS Secrets Manager client.

    Returns:
        boto3 Secrets Manager client

    Raises:
        Exception if AWS credentials are not configured
    """
    try:
        # Verify AWS credentials are configured
        sts = boto3.client("sts")
        identity = sts.get_caller_identity()
        print_success(f"Authenticated to AWS as: {identity['Arn']}")
        print_info(f"Account: {identity['Account']}")

        # Get region from environment or use default
        region = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
        print_info(f"Region: {region}")

        return boto3.client("secretsmanager", region_name=region)

    except Exception as e:
        print_error("Failed to authenticate to AWS")
        print_info(str(e))
        print_info("\nMake sure AWS credentials are configured:")
        print_info("  - Check your .env file has AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY")
        print_info("  - Or run: aws configure")
        sys.exit(1)


def deploy_secret(
    client, secret_name: str, secrets: Dict[str, str], update: bool = False
) -> bool:
    """
    Deploy or update secret in AWS Secrets Manager.

    Args:
        client: boto3 Secrets Manager client
        secret_name: Name of the secret
        secrets: Dictionary of secret values
        update: Whether this is an update to existing secret

    Returns:
        True if successful, False otherwise
    """
    secret_value = json.dumps(
        {
            "workspace_id": secrets["SLACK_WORKSPACE_ID"],
            "critical_channel_id": secrets["SLACK_CRITICAL_CHANNEL_ID"],
            "heartbeat_channel_id": secrets["SLACK_HEARTBEAT_CHANNEL_ID"],
        },
        indent=2,
    )

    try:
        if update:
            # Update existing secret
            client.update_secret(SecretId=secret_name, SecretString=secret_value)
            print_success(f"Updated secret: {secret_name}")
        else:
            # Create new secret
            client.create_secret(
                Name=secret_name,
                Description="Slack configuration for AWS Chatbot Slack Monitor",
                SecretString=secret_value,
            )
            print_success(f"Created secret: {secret_name}")

        return True

    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        if error_code == "ResourceExistsException":
            # Secret already exists, try updating instead
            return deploy_secret(client, secret_name, secrets, update=True)
        else:
            print_error(f"Failed to deploy secret: {e}")
            return False


def verify_secret(client, secret_name: str) -> bool:
    """
    Verify that the secret was deployed correctly.

    Args:
        client: boto3 Secrets Manager client
        secret_name: Name of the secret to verify

    Returns:
        True if secret exists and is readable, False otherwise
    """
    try:
        response = client.get_secret_value(SecretId=secret_name)
        secret_data = json.loads(response["SecretString"])

        print_success("Secret verification:")
        print_info(f"  - Workspace ID: {secret_data['workspace_id']}")
        print_info(f"  - Critical Channel ID: {secret_data['critical_channel_id']}")
        print_info(f"  - Heartbeat Channel ID: {secret_data['heartbeat_channel_id']}")

        return True

    except ClientError as e:
        print_error(f"Failed to verify secret: {e}")
        return False


def main():
    """Main entry point for the script."""
    print_header("AWS Secrets Manager - Deploy Slack Configuration")

    # Step 1: Load environment
    if not load_environment():
        sys.exit(1)

    # Step 2: Validate secrets
    secrets = validate_required_secrets()
    if not secrets:
        sys.exit(1)

    # Step 3: Get secret name
    secret_name = get_secret_name()
    print_info(f"Secret name: {secret_name}")

    # Step 4: Get AWS client
    client = get_aws_client()

    # Step 5: Deploy secret
    print("")
    print_info("Deploying secrets to AWS Secrets Manager...")
    if not deploy_secret(client, secret_name, secrets):
        sys.exit(1)

    # Step 6: Verify deployment
    print("")
    if not verify_secret(client, secret_name):
        sys.exit(1)

    # Success!
    print("")
    print_header("✓ Secrets Deployed Successfully")
    print_info("Your Slack configuration is now stored securely in AWS Secrets Manager")
    print_info("The CDK Chatbot stack can now access these values during deployment")
    print("")
    print_info("Next steps:")
    print_info("  1. Deploy the CDK stacks: make deploy")
    print_info("  2. Configure Slack workspace in AWS Console (one-time)")
    print_info("  3. Test notifications: make validate")
    print("")


if __name__ == "__main__":
    main()
