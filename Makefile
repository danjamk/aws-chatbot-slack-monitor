.PHONY: help install synth diff deploy deploy-secrets update destroy validate test format lint clean bootstrap

# Default target - show help
help:
	@echo "AWS Chatbot Slack Monitor - Make Commands"
	@echo ""
	@echo "Setup & Installation:"
	@echo "  make install         Install Python dependencies"
	@echo "  make bootstrap       Bootstrap AWS CDK (first-time setup)"
	@echo "  make deploy-secrets  Deploy secrets from .env to AWS Secrets Manager"
	@echo ""
	@echo "Deployment:"
	@echo "  make synth           Synthesize CloudFormation templates"
	@echo "  make diff            Show changes to be deployed"
	@echo "  make deploy          Deploy all stacks to AWS"
	@echo "  make update          Quick update of config-driven resources (budgets)"
	@echo "  make destroy         Destroy all stacks (CAUTION!)"
	@echo ""
	@echo "Testing:"
	@echo "  make validate        Test Slack notification channels"
	@echo "  make test            Run unit tests"
	@echo "  make test-cov        Run tests with coverage report"
	@echo ""
	@echo "Code Quality:"
	@echo "  make format          Format code with black"
	@echo "  make lint            Lint code with flake8"
	@echo "  make typecheck       Type check with mypy"
	@echo "  make check           Run all checks (format + lint + typecheck + test)"
	@echo ""
	@echo "Utilities:"
	@echo "  make clean           Remove generated files and caches"
	@echo "  make logs            Show recent CloudWatch logs (if applicable)"
	@echo ""

# Install Python dependencies
install:
	@echo "Installing Python dependencies..."
	pip install -r requirements.txt
	@echo "✅ Dependencies installed"

# Bootstrap AWS CDK (first-time only)
bootstrap:
	@echo "Bootstrapping AWS CDK..."
	@echo "Make sure AWS_DEFAULT_REGION and CDK_DEFAULT_ACCOUNT are set in .env"
	cdk bootstrap
	@echo "✅ CDK bootstrap complete"

# Deploy secrets to AWS Secrets Manager
deploy-secrets:
	@echo "Deploying secrets to AWS Secrets Manager..."
	@if [ ! -f .env ]; then \
		echo "❌ Error: .env file not found"; \
		echo "Copy config/.env.example to .env and fill in your values"; \
		exit 1; \
	fi
	python scripts/deploy-secrets.py
	@echo "✅ Secrets deployed"

# Synthesize CloudFormation templates
synth:
	@echo "Synthesizing CDK stacks..."
	cdk synth
	@echo "✅ Synthesis complete"

# Show deployment diff
diff:
	@echo "Showing deployment diff..."
	cdk diff

# Deploy all stacks
deploy: deploy-secrets
	@echo "Deploying all stacks to AWS..."
	@echo "⚠️  This will create real AWS resources that may incur costs"
	@read -p "Continue? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		cdk deploy --all --require-approval never; \
		echo "✅ Deployment complete"; \
	else \
		echo "❌ Deployment cancelled"; \
	fi

# Quick update of config-driven resources (faster than full deploy)
update:
	@echo "Updating config-driven resources..."
	cdk deploy ChatbotMonitorBudgetStack --require-approval never
	@echo "✅ Update complete"

# Destroy all stacks
destroy:
	@echo "⚠️  CAUTION: This will destroy all AWS resources created by this project"
	@echo "This includes:"
	@echo "  - SNS topics and subscriptions"
	@echo "  - AWS Budgets"
	@echo "  - AWS Chatbot configurations"
	@echo "  - CloudWatch dashboards"
	@echo "  - Secrets in Secrets Manager"
	@read -p "Are you ABSOLUTELY sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		cdk destroy --all --force; \
		echo "✅ Stacks destroyed"; \
	else \
		echo "❌ Destroy cancelled"; \
	fi

# Test Slack notification channels
validate:
	@echo "Testing Slack notification channels..."
	@bash scripts/validate-notifications.sh

# Run unit tests
test:
	@echo "Running unit tests..."
	python -m pytest tests/ -v

# Run tests with coverage
test-cov:
	@echo "Running tests with coverage..."
	python -m pytest tests/ --cov=cdk --cov-report=html --cov-report=term
	@echo "✅ Coverage report generated in htmlcov/"

# Format code
format:
	@echo "Formatting code with black..."
	black cdk/ tests/ scripts/*.py
	@echo "✅ Code formatted"

# Lint code
lint:
	@echo "Linting code with flake8..."
	flake8 cdk/ tests/ scripts/*.py --max-line-length=100 --extend-ignore=E203,W503
	@echo "✅ Linting complete"

# Type check code
typecheck:
	@echo "Type checking with mypy..."
	mypy cdk/ --ignore-missing-imports
	@echo "✅ Type checking complete"

# Run all code quality checks
check: format lint typecheck test
	@echo "✅ All checks passed"

# Clean generated files and caches
clean:
	@echo "Cleaning generated files..."
	rm -rf cdk.out/
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf .mypy_cache/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	@echo "✅ Cleanup complete"

# Show CloudWatch logs (if applicable)
logs:
	@echo "⚠️  Log viewing not yet implemented"
	@echo "View logs in AWS Console:"
	@echo "  https://console.aws.amazon.com/cloudwatch/home#logsV2:log-groups"
