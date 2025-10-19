"""
Monitoring Stack - CloudWatch Dashboard for Cost Monitoring

This stack creates a CloudWatch dashboard with widgets for:
- Daily spend trends (last 30 days)
- Monthly spend vs budget comparison
- Top services by cost
- Forecast to month-end

IMPORTANT: CloudWatch billing metrics are only available in us-east-1 region.
If deploying to another region, the dashboard will be created but billing
widgets will not show data until you switch to us-east-1.
"""

from aws_cdk import Stack, CfnOutput, Duration
from aws_cdk import aws_cloudwatch as cloudwatch
from constructs import Construct


class MonitoringStack(Stack):
    """Stack for creating CloudWatch dashboard with cost monitoring widgets."""

    def __init__(
        self, scope: Construct, construct_id: str, config: dict, **kwargs
    ) -> None:
        """
        Initialize the Monitoring Stack.

        Args:
            scope: CDK app scope
            construct_id: Unique identifier for this stack
            config: Configuration dictionary from config.yaml
            **kwargs: Additional stack properties (env, etc.)
        """
        super().__init__(scope, construct_id, **kwargs)

        self.config = config
        self.dashboard_config = config["dashboard"]

        # Check if dashboard is enabled
        if not self.dashboard_config.get("enabled", True):
            return

        # Create the CloudWatch dashboard
        self._create_cost_dashboard()

    def _create_cost_dashboard(self) -> None:
        """Create CloudWatch dashboard with cost monitoring widgets."""
        project_name = self.config["project"]["name"]
        environment = self.config["project"]["environment"]
        dashboard_name = f"{project_name}-{environment}-{self.dashboard_config['name']}"

        # Create dashboard
        dashboard = cloudwatch.Dashboard(
            self,
            "CostMonitoringDashboard",
            dashboard_name=dashboard_name,
        )

        # Get budget values for reference lines
        monthly_budget = float(self.config["budgets"]["monthly_limit"])
        daily_budget = float(self.config["budgets"]["daily_limit"])
        currency = self.config["budgets"]["currency"]

        # Add header widget
        dashboard.add_widgets(
            cloudwatch.TextWidget(
                markdown=f"""# {project_name} - Cost Monitoring Dashboard

**Environment**: {environment}
**Monthly Budget**: ${monthly_budget:,.2f} {currency}
**Daily Budget**: ${daily_budget:,.2f} {currency}

---

⚠️ **Important**: Billing metrics are only available in **us-east-1** region.
If you don't see data, verify your region in the top-right corner.

Dashboard auto-refreshes every {self.dashboard_config.get('auto_refresh_seconds', 300)} seconds.
""",
                width=24,
                height=6,
            )
        )

        # Row 1: Current Month Spend + This Month's Trend
        dashboard.add_widgets(
            self._create_current_spend_widget(monthly_budget, currency),
            self._create_monthly_trend_widget(monthly_budget, currency),
        )

        # Row 2: Daily Spend Trend
        dashboard.add_widgets(
            self._create_daily_trend_widget(daily_budget, currency),
        )

        # Row 3: Top Services by Cost
        dashboard.add_widgets(
            self._create_top_services_widget(currency),
        )

        # Row 4: Forecast and Budget Status
        dashboard.add_widgets(
            self._create_forecast_widget(monthly_budget, currency),
            self._create_budget_status_widget(monthly_budget, currency),
        )

        # Output dashboard URL
        region = self.region
        CfnOutput(
            self,
            "DashboardURL",
            value=f"https://console.aws.amazon.com/cloudwatch/home?region={region}#dashboards:name={dashboard_name}",
            description="URL to the CloudWatch cost monitoring dashboard",
        )

        CfnOutput(
            self,
            "DashboardName",
            value=dashboard_name,
            description="Name of the CloudWatch dashboard",
        )

    def _create_current_spend_widget(
        self, monthly_budget: float, currency: str
    ) -> cloudwatch.GraphWidget:
        """
        Create widget showing current month spend.

        Args:
            monthly_budget: Monthly budget amount
            currency: Currency code (e.g., USD)

        Returns:
            GraphWidget showing current month estimated charges
        """
        return cloudwatch.SingleValueWidget(
            title="Current Month Spend",
            width=8,
            height=6,
            metrics=[
                cloudwatch.Metric(
                    namespace="AWS/Billing",
                    metric_name="EstimatedCharges",
                    dimensions_map={"Currency": currency},
                    statistic="Maximum",
                    period=Duration.hours(6),
                )
            ],
            set_period_to_time_range=True,
        )

    def _create_monthly_trend_widget(
        self, monthly_budget: float, currency: str
    ) -> cloudwatch.GraphWidget:
        """
        Create widget showing monthly spend trend.

        Args:
            monthly_budget: Monthly budget amount
            currency: Currency code

        Returns:
            GraphWidget showing monthly trend with budget line
        """
        # Create metric for estimated charges
        spend_metric = cloudwatch.Metric(
            namespace="AWS/Billing",
            metric_name="EstimatedCharges",
            dimensions_map={"Currency": currency},
            statistic="Maximum",
            period=Duration.hours(6),
        )

        return cloudwatch.GraphWidget(
            title="This Month's Spend Trend",
            width=16,
            height=6,
            left=[spend_metric],
            left_y_axis=cloudwatch.YAxisProps(
                label=f"Cost ({currency})",
                show_units=False,
            ),
            left_annotations=[
                cloudwatch.HorizontalAnnotation(
                    value=monthly_budget,
                    label=f"Monthly Budget: ${monthly_budget:,.2f}",
                    color=cloudwatch.Color.RED,
                ),
                cloudwatch.HorizontalAnnotation(
                    value=monthly_budget * 0.8,
                    label=f"80% Warning: ${monthly_budget * 0.8:,.2f}",
                    color=cloudwatch.Color.ORANGE,
                ),
            ],
            period=Duration.hours(6),
            statistic="Maximum",
        )

    def _create_daily_trend_widget(
        self, daily_budget: float, currency: str
    ) -> cloudwatch.GraphWidget:
        """
        Create widget showing daily spend trend for last 30 days.

        Args:
            daily_budget: Daily budget amount
            currency: Currency code

        Returns:
            GraphWidget showing 30-day daily spend trend
        """
        spend_metric = cloudwatch.Metric(
            namespace="AWS/Billing",
            metric_name="EstimatedCharges",
            dimensions_map={"Currency": currency},
            statistic="Maximum",
            period=Duration.days(1),
        )

        return cloudwatch.GraphWidget(
            title="Daily Spend Trend (Last 30 Days)",
            width=24,
            height=6,
            left=[spend_metric],
            left_y_axis=cloudwatch.YAxisProps(
                label=f"Daily Cost ({currency})",
                show_units=False,
            ),
            left_annotations=[
                cloudwatch.HorizontalAnnotation(
                    value=daily_budget,
                    label=f"Daily Budget: ${daily_budget:,.2f}",
                    color=cloudwatch.Color.RED,
                )
            ],
            period=Duration.days(1),
            statistic="Maximum",
            start="-P30D",  # Last 30 days
        )

    def _create_top_services_widget(self, currency: str) -> cloudwatch.GraphWidget:
        """
        Create widget showing top services by cost.

        Note: This is a placeholder. In practice, you would query Cost Explorer API
        or use CloudWatch Metrics to show per-service costs.

        Args:
            currency: Currency code

        Returns:
            TextWidget with instructions for viewing service costs
        """
        # Note: CloudWatch doesn't natively provide per-service billing metrics
        # Users need to use AWS Cost Explorer or AWS Budgets for this
        return cloudwatch.TextWidget(
            markdown=f"""## Top Services by Cost

**To view service-level costs:**

1. Go to [AWS Cost Explorer](https://console.aws.amazon.com/cost-management/home#/cost-explorer)
2. Select "Service" as the dimension
3. View current month spend by service

**Common High-Cost Services to Monitor:**
- EC2 (compute instances)
- S3 (storage)
- RDS (databases)
- Lambda (serverless functions)
- CloudWatch (logging & metrics)
- Data Transfer (cross-region, internet)

**Tip**: Enable Cost Allocation Tags to track costs by project, environment, or team.
""",
            width=24,
            height=8,
        )

    def _create_forecast_widget(
        self, monthly_budget: float, currency: str
    ) -> cloudwatch.GraphWidget:
        """
        Create widget showing spend forecast.

        Note: This is simplified. Real forecasting requires AWS Cost Explorer API.

        Args:
            monthly_budget: Monthly budget amount
            currency: Currency code

        Returns:
            GraphWidget with forecast annotation
        """
        spend_metric = cloudwatch.Metric(
            namespace="AWS/Billing",
            metric_name="EstimatedCharges",
            dimensions_map={"Currency": currency},
            statistic="Maximum",
            period=Duration.hours(12),
        )

        return cloudwatch.GraphWidget(
            title="Spend Forecast to Month-End",
            width=12,
            height=6,
            left=[spend_metric],
            left_y_axis=cloudwatch.YAxisProps(
                label=f"Cost ({currency})",
                show_units=False,
            ),
            left_annotations=[
                cloudwatch.HorizontalAnnotation(
                    value=monthly_budget,
                    label=f"Budget: ${monthly_budget:,.2f}",
                    color=cloudwatch.Color.RED,
                )
            ],
            period=Duration.hours(12),
            statistic="Maximum",
        )

    def _create_budget_status_widget(
        self, monthly_budget: float, currency: str
    ) -> cloudwatch.GraphWidget:
        """
        Create widget showing budget status.

        Args:
            monthly_budget: Monthly budget amount
            currency: Currency code

        Returns:
            TextWidget with budget status information
        """
        warning_threshold = int(
            self.config["budgets"]["monthly_threshold_warning"]
        )
        critical_threshold = int(
            self.config["budgets"]["monthly_threshold_critical"]
        )

        return cloudwatch.TextWidget(
            markdown=f"""## Budget Status

**Monthly Budget**: ${monthly_budget:,.2f} {currency}

**Alert Thresholds**:
- 🟡 **Warning** at {warning_threshold}% (${monthly_budget * warning_threshold / 100:,.2f}) → Heartbeat Channel
- 🔴 **Critical** at {critical_threshold}% (${monthly_budget * critical_threshold / 100:,.2f}) → Critical Channel

**Budget Alerts**:
- Daily budget alerts sent to heartbeat channel
- Monthly warnings (80%) sent to heartbeat channel
- Monthly alerts (100%) sent to critical channel

**To view detailed budget information**:
- [AWS Budgets Console](https://console.aws.amazon.com/billing/home#/budgets)
- Use `@aws budgets describe-budgets` in Slack

**To adjust budgets**:
1. Edit `config/config.yaml`
2. Run `make update` or `make deploy`
""",
            width=12,
            height=6,
        )
