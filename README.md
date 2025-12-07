# English Learning MCP

A serverless English learning assistant built on AWS and powered by the Model Context Protocol (MCP).  
It helps you automatically save phrases, track corrections, analyze repeated mistakes, and receive daily learning summaries via LINE — all during your natural English study flow with Claude.

## 🚀 Why I Built This
I study English every day using Claude/ChatGPT, but I kept asking the same questions across different chat threads. I had no way to track:
- useful phrases
- grammar corrections
- repeated mistakes
- learning progress

This project solves that problem by automatically logging everything I learn in Claude Desktop and storing it securely in my AWS account.

## 🌟 Features
- **Phrase Management**  
  Save phrases with translations and context, search across all threads, and get review recommendations.

- **Correction Tracking**  
  Log grammar corrections with feedback and analyze recurring error patterns.

- **Daily LINE Summary**  
  EventBridge triggers a daily Lambda that sends learning summaries, weak points, and review items to LINE.

- **MCP Integration**  
  Claude Desktop can call MCP tools directly, making the experience natural and effortless.

## 🏗️ Architecture
- AWS Lambda (MCP server)
- DynamoDB (phrases & corrections)
- EventBridge (scheduled notifications)
- Lambda (LINE notification)
- SSM Parameter Store
- CloudFormation/SAM (IaC)

## 🛠️ Tech Stack
- Python 3.12
- AWS Lambda / DynamoDB / EventBridge / SSM
- GitHub Actions (CI/CD)
- MCP Server for AWS Lambda (`@modelcontextprotocol/server-aws-lambda`)

## ▶️ Quick Setup
```bash
uv sync
sam build
sam deploy --guided
```

Then configure Claude Desktop with your Lambda URL.

## 📄 Full Documentation
See **[README-full.md](./README-full.md)** for:
- full project background  
- detailed AWS architecture  
- database schema  
- setup instructions  
- usage examples  
- cost estimation  
- development notes

---

**Author:** Ren Nakamura  
Building this project as part of my portfolio to demonstrate cloud architecture skills for software engineering roles in Australia.
