# PsySource Moderation Bot

A simple Discord moderation bot built with discord.py.

## Features
- Ban and kick commands
- Logging of moderation actions
- Configurable log and welcome channels
- Welcome messages for new members

## Setup
1. Install dependencies:
   ```sh
   pip install -r requirements.txt
   ```
2. Create a `.env` file in the PsySource directory with your bot token:
   ```env
   DISCORD_TOKEN=your_token_here
   ```
3. Run the bot:
   ```sh
   python bot.py
   ```

## Commands
- `/ban <user> [reason]` — Ban a user
- `/kick <user> [reason]` — Kick a user
- `/setlog <#channel>` — Set the log channel
- `/setwelcome <#channel>` — Set the welcome channel

## Notes
- Requires `Manage Messages`, `Ban Members`, and `Kick Members` permissions.
- Logging and welcome features require channel configuration.
