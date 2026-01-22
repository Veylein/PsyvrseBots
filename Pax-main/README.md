# Discord Chi Bot 🐼

A Discord bot that tracks user "chi" (positive energy) based on their language usage in your server, plus a monthly quest system!

## Features

### Chi System
- **Automatic Chi Tracking**: Monitors messages for positive and negative words
  - Positive words: +1 chi (react with 🐼💖)
  - Negative words: -2 chi (react with 🐼😡)
  - 30-second cooldown prevents chi spam
  
- **Chi Commands** (use `P!` prefix):
  - `P!chi` - Check your current chi score
  - `P!leaderboard` - View top 10 users by chi score
  - `P!chi add @member amount` - (Chi Manager Only) Add chi to a user
  - `P!chi remove @member amount` - (Chi Manager Only) Remove chi from a user
  - `P!claim` - Claim a Mystery Panda Token when one appears
  - `P!tokens` - View your mystery token stats and mini quests

- **Daily Evaluation**: At 23:59 UTC each day
  - Assigns positive role to users with chi > 0
  - Assigns negative role to users with chi < 0
  - Posts daily summary to configured channel

- **Milestone Rewards**: Sends DM when users reach 2500 chi (Nitro reward)

- **Mystery Panda Tokens**: Random token drops in active channels
  - Tokens appear when there's recent chat activity (within 15 seconds)
  - 60-second claim window with `P!claim`
  - Random rewards: bonus chi (10-50), mini quests, nickname effects, or mega tokens (+200 chi)
  - Track stats with `P!tokens`

### Quest System
- **Monthly Themed Quests**: Automatically themed quests for Halloween (Oct), Thanksgiving (Nov), and Winter (Dec)
  - 10 quests per month with unique challenges
  - Quest completion tracked via ✅ reactions from authorized user
  - Automatic role assignment for completing all quests

- **Quest Commands** (use `Q!` prefix):
  - `Q!Month` - (Admin Only) Reset and display current month's quests
  - `Q!see` - View your completed quests
  - `Q!todo` - View quests you haven't completed yet (5-minute cooldown)
  - `Q!questleaderboard` - View quest completion leaderboard

## Setup

1. **Discord Bot Token**: The bot requires a Discord bot token stored in Secrets as `DISCORD_TOKEN`

2. **Bot Permissions**: Your bot needs these permissions:
   - Read Messages/View Channels
   - Send Messages
   - Add Reactions
   - Manage Roles
   - Read Message History

3. **Bot Intents**: Enable these in Discord Developer Portal:
   - Server Members Intent
   - Message Content Intent

4. **Configuration** (Optional): Set these environment variables to customize:
   - `POSITIVE_ROLE_ID` - Role assigned to positive chi users
   - `NEGATIVE_ROLE_ID` - Role assigned to negative chi users
   - `CHANNEL_ID` - Channel for daily summaries
   - `PSY_DM_ID` - User to DM for milestone notifications
   - `CHI_NITRO_MILESTONE` - Chi required for Nitro (default 2500)

## How It Works

### Chi System
1. Bot monitors all messages in your Discord server
2. Detects positive/negative words from pre-configured lists
3. Updates user chi scores in `chi_data.json`
4. Reacts to messages with panda emojis
5. Daily at 23:59 UTC, assigns roles and posts summary
6. Notifies admin when users reach milestones

### Quest System
1. Admin uses `Q!Month` to load current month's themed quests
2. Users complete quests and post proof in chat
3. Admin reacts with ✅ to the user's message containing quest proof
4. Bot automatically marks quest as complete and DMs the user
5. Users who complete all 10 quests receive the Quest Completer role
6. Use `Q!see`, `Q!todo`, and `Q!questleaderboard` to track progress

## Running the Bot

The bot will start automatically in this Repl. Make sure you've set your `DISCORD_TOKEN` in Secrets.
