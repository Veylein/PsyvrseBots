# 🔧 P!log Command - Developer Portal Guide

## Overview
The `P!log` command is a comprehensive admin tool that gives you a real-time view into your bot's internal operations, errors, and system status.

---

## Command Usage
```
P!log
```
**Permissions Required:** Administrator

---

## What You'll See

### 📊 System Status Section
- **Bot Status**: Shows if the bot is RUNNING or STARTING
- **Uptime**: How long the bot has been running since last restart
- **Error Count**: Number of errors detected in the past hour

### 📊 System Statistics
Real-time counts of:
- **Guilds**: Number of Discord servers the bot is in
- **Registered Users**: Total users in the chi_data system
- **Teams**: Active teams created
- **Gardens**: Total gardens planted

### 🎮 Active Events Monitor
Live tracking of all running events:
- Chi Party
- Mini Chi/Food Events
- Rift Battle
- Artifact Hunts
- Spiritual Journey (garden boost)

Shows "None" if no events are active.

### 💾 Memory Usage
- **Error Logs**: Shows current log count out of max (100)
- **Artifact State**: Whether an artifact is currently spawned

### ⚠️ Recent Errors Section
Shows the **last 5 errors** from the past hour with:
- **Timestamp**: How long ago the error occurred (e.g., "5s ago", "12m ago")
- **Error Message**: What went wrong (truncated to 80 characters)
- **Command**: Which command triggered the error (e.g., `P!duel`)
- **User**: Who executed the command
- **Message Link**: Direct clickable link to jump to the message where the error occurred
- **Error Code**: Technical error type (e.g., `MissingRequiredArgument`, `CommandNotFound`)

---

## Automatic Error Logging

The bot now **automatically logs every command error** including:
- Command not found errors (silent, doesn't spam users)
- Missing arguments
- Permission errors
- Any unexpected exceptions

Each error is stored with:
- Exact timestamp
- Full error message
- Command name
- User who triggered it
- **Direct Discord message link** for debugging
- Error code/type

---

## Example Output

```
🔧 Pax Dev Portal - System Logs

System Status: ✅ RUNNING
Uptime: 3245s
Errors (Past Hour): 3

📊 System Statistics
Guilds: 2
Registered Users: 53
Teams: 10
Gardens: 27

🎮 Active Events
• Chi Party
• Rift Battle

💾 Memory Usage
Error Logs: 12/100
Artifact State: Idle

⚠️ Recent Errors

1. 5m ago
└ `Command "P!garden harvest" raised an exception: Garden not found`
└ Command: `P!garden`
└ User: TestUser#1234
└ [Jump to Message](https://discord.com/channels/xxx/yyy/zzz)
└ Code: `GardenNotFoundError`

2. 12m ago
└ `Missing required argument: amount`
└ Command: `P!chiadd`
└ User: Admin#5678
└ [Jump to Message](https://discord.com/channels/xxx/yyy/zzz)
└ Code: `MissingRequiredArgument`
```

---

## Use Cases

### 1. **Debugging User Issues**
When a user reports a problem, use `P!log` to:
- See if an error was logged
- Click the message link to jump directly to where it happened
- View the exact error message and error code

### 2. **System Health Checks**
Quickly verify:
- Bot is running correctly
- No recent errors
- All events are functioning
- Memory usage is normal

### 3. **Event Monitoring**
Check which events are currently active without having to manually verify each channel.

### 4. **Performance Tracking**
Monitor uptime and ensure the bot hasn't crashed or restarted unexpectedly.

---

## Color Coding

- **Blue Embed**: No errors detected (healthy system)
- **Orange Embed**: Errors found in the past hour (needs attention)

---

## Technical Details

- Error logs are stored in memory (max 100 entries)
- Only shows errors from the **past 60 minutes**
- Errors are automatically logged via global `on_command_error` handler
- Message links work for all channels the bot has access to
- Error logs persist until bot restarts (not stored in database)

---

## Commands Updated in Help System

The `P!help admin` command now includes:
```
🔧 System Monitoring
P!log - View bot errors, system status, and dev portal
└ Shows errors from past hour with message links
```

---

## Integration with Other Admin Tools

Pairs well with:
- `P!message` - View server message statistics
- `P!event end` - Force-stop problematic events
- `P!artifact give` - Gift compensation for error-affected users

---

**Last Updated:** November 10, 2025
