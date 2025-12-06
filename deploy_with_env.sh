#!/bin/bash
set -e

cd /Users/rennakamura/english-learning-mcp

echo "📝 Updating samconfig.toml with LINE parameters..."

# Generate compact private key using Python
COMPACT_KEY=$(python3 << 'PYTHON_SCRIPT'
import json

# Read .env file
with open('.env', 'r') as f:
    content = f.read()

# Extract LINE_PRIVATE_KEY
start = content.find("LINE_PRIVATE_KEY='") + len("LINE_PRIVATE_KEY='")
end = content.find("'", start + 1)
private_key = content[start:end]

# Compact JSON
compact = json.dumps(json.loads(private_key), separators=(',', ':'))
print(compact)
PYTHON_SCRIPT
)

# Update samconfig.toml
cat > samconfig.toml << EOF
version = 0.1

[default]
[default.deploy]
[default.deploy.parameters]
stack_name = "english-learning-mcp"
resolve_s3 = true
s3_prefix = "english-learning-mcp"
region = "ap-northeast-1"
confirm_changeset = true
capabilities = "CAPABILITY_IAM"
parameter_overrides = "DefaultUserId=\"default_user\" LineChannelId=\"2008609725\" LineKid=\"40c087d0-1c08-4c81-b3a6-0b241c65c42a\" LinePrivateKey='${COMPACT_KEY}' LineUserId=\"Ud7cf40701ff0473ada89545c8f88deb7\""
image_repositories = []
EOF

echo "✅ samconfig.toml updated"
echo "🚀 Deploying..."

sam deploy

echo "✅ Deployment complete!"