#!/bin/bash

# Ludus Bot Startup Script for Render
# This script handles data persistence setup

echo "🤖 Starting Ludus Bot..."
echo "📁 Checking data directory..."

# If RENDER_DISK_PATH is set, use it. Otherwise use current directory.
DATA_DIR="${RENDER_DISK_PATH:-.}"
echo "📂 Data directory: $DATA_DIR"

# Create data directory if it doesn't exist
mkdir -p "$DATA_DIR"

# List of data files that should persist
DATA_FILES=(
    "economy.json"
    "inventory.json"
    "pets.json"
    "gambling_stats.json"
    "leaderboard_stats.json"
    "fishing_data.json"
    "wyr_questions.json"
    "stories.json"
    "quests_data.json"
    "achievements_data.json"
)

# Initialize data files if they don't exist
for file in "${DATA_FILES[@]}"; do
    filepath="$DATA_DIR/$file"
    if [ ! -f "$filepath" ]; then
        echo "📝 Creating $file..."
        echo "{}" > "$filepath"
    else
        echo "✅ $file exists ($(stat -f%z "$filepath" 2>/dev/null || stat -c%s "$filepath" 2>/dev/null) bytes)"
    fi
done

echo ""
echo "🚀 Starting bot..."
python bot.py
