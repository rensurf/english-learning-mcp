#!/bin/bash
set -e

echo "🚀 Deploying English Learning MCP to AWS Lambda..."

# Check if SAM CLI is installed
if ! command -v sam &> /dev/null; then
    echo "❌ SAM CLI is not installed. Please install it first:"
    echo "   https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html"
    exit 1
fi

# Check AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    echo "❌ AWS credentials not configured. Please run: aws configure"
    exit 1
fi

echo "✅ Prerequisites check passed"

# Build
echo "📦 Building Lambda function..."
sam build

# Deploy
echo "🚢 Deploying to AWS..."
sam deploy \
    --guided \
    --stack-name english-learning-mcp \
    --capabilities CAPABILITY_IAM

echo "✅ Deployment complete!"
echo ""
echo "📝 Next steps:"
echo "1. Get the Function URL from the outputs above"
echo "2. Go to Claude.ai → Settings → Connectors"
echo "3. Add Custom Connector with the Function URL"
echo "4. Start using your MCP on all devices!"