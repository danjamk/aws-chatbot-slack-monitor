#!/usr/bin/env python3
"""
AWS Alert Intelligence System - CDK Application Entry Point

This is the main entry point for the AWS CDK application.
It loads configuration, sets up the CDK app, and instantiates all stacks.

Phase 1: AI-powered alert analysis
Phase 2: Interactive Slack bot (future)
"""

import os
from pathlib import Path

import yaml
from aws_cdk import App, Environment, Tags
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)

# Load configuration from config.yaml
config_path = Path(__file__).parent.parent / "config" / "config.yaml"
with open(config_path, "r") as f:
    config = yaml.safe_load(f)

# Create CDK app
app = App()

# Get AWS environment from config and environment variables
aws_env = Environment(
    account=os.environ.get("CDK_DEFAULT_ACCOUNT", config["aws"]["account_id"]),
    region=os.environ.get("CDK_DEFAULT_REGION", config["aws"]["region"]),
)

# Import stacks
from stacks.sns_stack import SnsStack
from stacks.budget_stack import BudgetStack
from stacks.chatbot_stack import ChatbotStack
from stacks.monitoring_stack import MonitoringStack
from stacks.daily_cost_stack import DailyCostStack
from stacks.alert_analyzer_stack import AlertAnalyzerStack  # Phase 1: AI analyzer

# Instantiate SNS Stack (foundation for all notifications)
sns_stack = SnsStack(
    app,
    f"{config['aws']['stack_prefix']}SnsStack",
    config=config,
    env=aws_env,
)

# Instantiate Budget Stack (cost monitoring and alerts)
budget_stack = BudgetStack(
    app,
    f"{config['aws']['stack_prefix']}BudgetStack",
    config=config,
    critical_topic=sns_stack.get_critical_topic(),
    heartbeat_topic=sns_stack.get_heartbeat_topic(),
    env=aws_env,
)

# Instantiate Chatbot Stack (Slack integration)
chatbot_stack = ChatbotStack(
    app,
    f"{config['aws']['stack_prefix']}ChatbotStack",
    config=config,
    critical_topic=sns_stack.get_critical_topic(),
    heartbeat_topic=sns_stack.get_heartbeat_topic(),
    env=aws_env,
)

# Instantiate Alert Analyzer Stack (Phase 1: AI-powered analysis)
if config.get("ai_analysis", {}).get("enabled", False):
    alert_analyzer_stack = AlertAnalyzerStack(
        app,
        f"{config['aws']['stack_prefix']}AlertAnalyzerStack",
        config=config,
        critical_topic=sns_stack.get_critical_topic(),
        heartbeat_topic=sns_stack.get_heartbeat_topic(),
        env=aws_env,
    )

# Instantiate Monitoring Stack (CloudWatch dashboard)
monitoring_stack = MonitoringStack(
    app,
    f"{config['aws']['stack_prefix']}MonitoringStack",
    config=config,
    env=aws_env,
)

# Instantiate Daily Cost Report Stack (optional, based on config)
if config.get("daily_report", {}).get("enabled", False):
    daily_cost_stack = DailyCostStack(
        app,
        f"{config['aws']['stack_prefix']}DailyCostStack",
        config=config,
        heartbeat_topic=sns_stack.get_heartbeat_topic(),
        env=aws_env,
    )

# Apply tags to all stacks
if "tags" in config:
    for key, value in config["tags"].items():
        Tags.of(app).add(key, value)

# Synthesize the CDK app
app.synth()
