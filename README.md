# English Learning MCP

A serverless English learning system that automatically captures phrases and corrections from my daily Claude conversations.

## What it does

Every time I learn something new in English through Claude, this system:
- Saves useful phrases with Japanese translations
- Tracks grammar corrections and error patterns
- Sends daily learning summaries to my LINE
- Helps me review what I need to work on

No manual logging. Just study naturally and everything gets saved.

## Why I made this

I was using Claude/ChatGPT to study English every day, but kept asking the same questions in different threads. I had no persistent memory of:
- Phrases I'd learned
- Mistakes I'd already made
- What I should review

This solves that by storing everything in DynamoDB and making it searchable across all my conversations.

## How it works

**Architecture:**
- MCP server running on AWS Lambda
- DynamoDB for storage (phrases + corrections)
- EventBridge scheduling daily summaries
- LINE notifications via Messaging API

**The flow:**
1. I chat with Claude Desktop about English
2. Claude calls MCP tools to save phrases/corrections
3. Data goes to DynamoDB via Lambda
4. EventBridge triggers daily summary at 8 AM JST
5. Summary arrives on LINE

## Setup
```bash
# Install dependencies
uv sync

# Deploy to AWS
sam build
sam deploy --guided

# Add Lambda URL to Claude Desktop config
```

See [README-full.md](./README-full.md) for detailed setup, schema, and usage examples.

## Tech

Python 3.12, AWS Lambda, DynamoDB, EventBridge, SSM Parameter Store, SAM/CloudFormation, GitHub Actions

## Cost

~$1-2/month with AWS Free Tier (mostly DynamoDB + Lambda invocations)

---