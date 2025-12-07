# English Learning MCP

A serverless English learning assistant built on AWS, using the Model Context Protocol (MCP) to help track phrases, corrections, and learning progress with automated LINE notifications.

---

# Why I Built This

As a software engineer preparing to work abroad — especially in Australia — I study English daily using Claude or ChatGPT.  
I often ask questions like:

- "Is this expression natural?"
- "How do you say this in English?"

### The Problem
I realized I was asking the **same questions repeatedly** across different chat threads. When I wanted to review something I learned, searching past conversations was frustrating.

I also liked the grammar corrections Claude gave me, but:
- I couldn't track them
- I couldn't see patterns in my mistakes
- I forgot what I learned after a few days

Anki was too manual and interrupted my learning flow.

### What I Needed
- 📝 **Automatic logging** of phrases & corrections  
- 🔍 **Cross-thread search**  
- 📊 **Pattern analysis** of repeated mistakes  
- 📈 **Progress tracking**  
- 🎯 **Smart review** of phrases that need attention  

### Why MCP + Serverless?
- Works seamlessly with **Claude Desktop**
- Data is stored securely in **my own AWS account**
- Zero maintenance (serverless)
- Scales automatically and costs < **$1/month**
- Great real-world practice for AWS backend engineering

This solves a real daily problem while demonstrating cloud architecture skills needed for my future work in Australia.

---

# Overview

This project implements a cloud-native MCP server that provides tools for English language learning:

- Save and search English phrases with Japanese translations  
- Track grammar corrections and analyze error patterns  
- Get personalized review recommendations  
- Receive daily summaries via LINE  

---

# Architecture

```
┌─────────────┐
│   Claude    │
│   Desktop   │
└──────┬──────┘
       │ MCP Protocol
       ▼
┌───────────────────────────────┐
│  Lambda Function (MCP Server) │
│  - save_phrase                │
│  - search_phrases             │
│  - list_phrases               │
│  - get_review_priority        │
│  - save_correction            │
│  - analyze_weaknesses         │
└──────────┬────────────────────┘
           │
           ▼
    ┌──────────────┐
    │  DynamoDB    │
    │  - phrases   │
    │  - corrections │
    └──────────────┘

┌──────────────────┐
│  EventBridge     │
│  (Daily @ 23:00) │
└────────┬─────────┘
         │
         ▼
┌─────────────────────────┐
│  Lambda (LINE Notifier) │
└────────┬────────────────┘
         │
         ▼
    ┌────────┐
    │  LINE  │
    └────────┘
```

---

# Features

## 1. Phrase Management
- **save_phrase**: Store phrases with translations and context  
- **list_phrases**: Paginated viewing  
- **search_phrases**: Full-text search on English/Japanese/context  
- **get_review_priority**: Recommends phrases based on usage patterns  

## 2. Correction Tracking
- **save_correction**: Save grammar corrections  
- **analyze_weaknesses**: Identify repeated mistake patterns  

## 3. Automated Notifications (LINE)
- Daily summary at 23:00 JST  
- Includes:
  - weak points  
  - review items  
  - recent corrections  

---

# Tech Stack

**AWS Services**
- Lambda  
- DynamoDB  
- EventBridge  
- SSM Parameter Store  
- CloudFormation / SAM  

**Libraries**
- `awslabs.mcp-lambda-handler`  
- `boto3`  
- `pyjwt`, `cryptography`  
- `requests`  

---

# Setup

## 1. Install dependencies
```bash
uv sync
```

## 2. Deploy to AWS
```bash
sam build
sam deploy --guided
```

## 3. Optional: Configure LINE credentials
Stored in SSM Parameter Store.

## 4. Configure Claude Desktop
Add this to your Claude Desktop config:

```json
{
  "mcpServers": {
    "english-learning": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-aws-lambda",
        "<YOUR_LAMBDA_FUNCTION_URL>"
      ]
    }
  }
}
```

---

# Usage Examples

### Save a phrase
```
Save this phrase: "break the ice" = "場の雰囲気を和らげる",
context: "Used at the beginning of meetings"
```

### Search phrases
```
Search for phrases about "meeting"
```

### Save a correction
```
Save this correction:
Original: "I will go to there tomorrow"
Corrected: "I will go there tomorrow"
Error: grammar
Feedback: "'there' doesn't take 'to'"
```

---

# Database Schema

## Phrases Table
- english  
- japanese  
- context  
- created_at  
- reviewed_at  
- query_count  
- last_queried_at  

## Corrections Table
- original_text  
- corrected_text  
- feedback  
- error_pattern  
- created_at  
- reviewed_at  

---

# Cost Estimation
- DynamoDB: < **$1/month**  
- Lambda: free tier  
- EventBridge: free  

---

# Future Improvements
- [ ] Spaced repetition (SRS)  
- [ ] Multi-user support  
- [ ] CSV / Anki export  

---

# Author

**Ren Nakamura**  
Building this project as part of my portfolio to demonstrate cloud architecture skills for software engineering roles in Australia.

MIT License
