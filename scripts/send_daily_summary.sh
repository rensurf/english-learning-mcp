#!/bin/bash

# Explicitly set environment variables
export PATH="/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin:$HOME/.cargo/bin:$PATH"
export HOME="/Users/rennakamura"

# Log file path
LOG_FILE="$HOME/line_notifier.log"

# Record start time in log
echo "========================================" >> "$LOG_FILE"
echo "Started: $(date)" >> "$LOG_FILE"

# Move to project directory
cd "$HOME/english-learning-mcp" || exit 1

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "Error: .env file not found" >> "$LOG_FILE"
    exit 1
fi

# Check uv path
which uv >> "$LOG_FILE" 2>&1

# Execute
uv run python src/line_notifier.py >> "$LOG_FILE" 2>&1

# Record end time
echo "Finished: $(date)" >> "$LOG_FILE"
echo "========================================" >> "$LOG_FILE"