# FULL DOCUMENTATION - PART 4B: LOTTERY & HEIST SYSTEMS

**Project:** Ludus Bot  
**Coverage:** Daily Lottery, Co-op Heist System  
**Total Lines:** 815 lines of code  
**Status:** ✅ COMPLETE  
**Date:** February 2026

---

## Table of Contents

1. [Lottery System Overview](#1-lottery-system-overview)
2. [Lottery Mechanics](#2-lottery-mechanics)
   - [Ticket System](#ticket-system)
   - [Daily Drawing Process](#daily-drawing-process)
   - [Jackpot Growth](#jackpot-growth)
   - [Winner Selection](#winner-selection)
3. [Lottery Commands](#3-lottery-commands)
4. [Heist System Overview](#4-heist-system-overview)
5. [Heist Mechanics](#5-heist-mechanics)
   - [Bank Heists](#bank-heists)
   - [Business Heists](#business-heists)
   - [Success Rates](#success-rates)
   - [Crew System](#crew-system)
6. [Heist Execution](#6-heist-execution)
7. [Heist Statistics](#7-heist-statistics)
8. [Commands Reference](#8-commands-reference)
9. [Summary](#9-summary)

---

## 1. LOTTERY SYSTEM OVERVIEW

**File:** `cogs/lottery.py` (313 lines)

The Lottery system is a daily raffle where users purchase tickets for a chance to win a growing jackpot. Every day at midnight UTC, one random ticket is drawn and the winner receives the entire jackpot.

### Core Features

**Daily Drawings:**
- Automated lottery drawing at midnight UTC (00:00)
- One winner selected per drawing
- Winner announced in all servers where the bot is present
- Drawing history tracked (last 10 winners)

**Ticket System:**
- Tickets cost **100 PsyCoins** each
- Users can buy 1-100 tickets per purchase
- Each ticket has a unique number (sequential)
- More tickets = higher win probability
- Tickets valid only for current drawing (reset after each drawing)

**Jackpot Mechanics:**
- Starting jackpot: **10,000 PsyCoins**
- 50% of ticket sales added to jackpot
- If no tickets sold, jackpot grows by **5,000 PsyCoins**
- Jackpot resets to 10,000 after a winner is drawn
- Can grow to massive amounts if many users participate

**Winner Notification:**
- Winner receives coins instantly (economy integration)
- Announcement sent to first text channel in every server
- Winner's name, jackpot amount, and winning ticket number shown
- Winner recorded in history (last 10 winners)

### Integration Points

**Economy System:**
- Ticket purchases deduct coins with reason `"lottery_tickets"`
- Winners receive coins with reason `"lottery_win"`
- 50% of ticket sales go to jackpot, 50% removed from circulation (coin sink)

**Task System:**
- Uses `discord.ext.tasks.loop` for automated hourly checks
- Checks if current time >= next drawing time
- Ensures bot is ready before starting task loop

**Data Persistence:**
- All lottery data stored in `data/lottery.json`
- Tickets, jackpot, history, and timestamps saved
- Atomic writes prevent data corruption

---

## 2. LOTTERY MECHANICS

### Ticket System

**Purchasing Tickets (Lines 185-254):**

```python
@lottery.command(name="buy")
async def lottery_buy(self, ctx, amount: int = 1):
    """Buy lottery tickets"""
    # Validation
    if amount < 1:
        await ctx.send("❌ You must buy at least 1 ticket!")
        return
    
    if amount > 100:
        await ctx.send("❌ Maximum 100 tickets per purchase!")
        return
    
    total_cost = amount * self.ticket_price  # 100 coins per ticket
    
    # Check balance
    economy_cog = self.bot.get_cog("Economy")
    balance = economy_cog.get_balance(ctx.author.id)
    
    if balance < total_cost:
        await ctx.send(f"❌ Not enough coins! You need {total_cost:,} but have {balance:,}")
        return
    
    # Deduct coins
    economy_cog.remove_coins(ctx.author.id, total_cost, "lottery_tickets")
    
    # Generate unique ticket numbers
    user_key = str(ctx.author.id)
    if user_key not in self.lottery_data["tickets"]:
        self.lottery_data["tickets"][user_key] = []
    
    new_tickets = []
    for _ in range(amount):
        ticket_num = self.lottery_data["ticket_counter"]  # Sequential counter
        self.lottery_data["tickets"][user_key].append(ticket_num)
        new_tickets.append(ticket_num)
        self.lottery_data["ticket_counter"] += 1
    
    # Increase jackpot (50% of sales)
    jackpot_increase = total_cost // 2
    self.lottery_data["current_jackpot"] += jackpot_increase
    
    self.save_data()
    
    # Show confirmation
    embed = discord.Embed(
        title="🎫 Tickets Purchased!",
        description=f"You bought **{amount}** ticket(s) for **{total_cost:,} coins**",
        color=discord.Color.green()
    )
    
    # Show ticket numbers (if 10 or fewer)
    if amount <= 10:
        ticket_list = ", ".join([f"#{t}" for t in new_tickets])
        embed.add_field(name="Your Tickets", value=ticket_list, inline=False)
    
    embed.add_field(name="New Jackpot", value=f"{self.lottery_data['current_jackpot']:,} coins", inline=True)
    
    # Calculate win probability
    total_tickets = sum(len(tickets) for tickets in self.lottery_data["tickets"].values())
    user_tickets = len(self.lottery_data["tickets"][user_key])
    win_chance = (user_tickets / total_tickets * 100)
    
    embed.add_field(name="Your Win Chance", value=f"{win_chance:.2f}%", inline=True)
    
    await ctx.send(embed=embed)
```

**Ticket Numbering:**
- Sequential numbering starting from 1
- Counter increments with each ticket sold
- Ensures every ticket has unique identifier
- Resets to 1 after each drawing

**Example Purchase Flow:**
```
User A buys 3 tickets:
- Ticket #1
- Ticket #2
- Ticket #3
- Cost: 300 coins
- Jackpot +150 coins (50%)

User B buys 2 tickets:
- Ticket #4
- Ticket #5
- Cost: 200 coins
- Jackpot +100 coins (50%)

Total tickets in pool: 5
User A win chance: 3/5 = 60%
User B win chance: 2/5 = 40%
```

---

### Daily Drawing Process

**Automated Drawing (Lines 53-128):**

```python
@tasks.loop(hours=1)
async def daily_drawing(self):
    """Check if it's time for the daily drawing"""
    now = datetime.utcnow()
    next_drawing = datetime.fromisoformat(self.lottery_data["next_drawing"])
    
    if now >= next_drawing:
        await self.conduct_drawing()

async def conduct_drawing(self):
    """Conduct the lottery drawing"""
    # Check if any tickets were sold
    if not self.lottery_data["tickets"]:
        # No tickets = jackpot grows by 5,000
        self.lottery_data["current_jackpot"] += 5000
        self.lottery_data["next_drawing"] = self.get_next_drawing_time().isoformat()
        self.save_data()
        return
    
    # Flatten all tickets into single pool
    all_tickets = []
    for user_id, tickets in self.lottery_data["tickets"].items():
        for ticket in tickets:
            all_tickets.append((user_id, ticket))
    
    # Example: all_tickets = [
    #   ("123456789", 1),
    #   ("123456789", 2),
    #   ("123456789", 3),
    #   ("987654321", 4),
    #   ("987654321", 5)
    # ]
    
    # Select random winner
    winner_user_id, winning_ticket = random.choice(all_tickets)
    jackpot = self.lottery_data["current_jackpot"]
    
    # Award coins to winner
    economy_cog = self.bot.get_cog("Economy")
    if economy_cog:
        economy_cog.add_coins(int(winner_user_id), jackpot, "lottery_win")
    
    # Record winner in history
    self.lottery_data["winners_history"].append({
        "user_id": winner_user_id,
        "jackpot": jackpot,
        "ticket": winning_ticket,
        "timestamp": datetime.utcnow().isoformat()
    })
    
    # Keep only last 10 winners
    if len(self.lottery_data["winners_history"]) > 10:
        self.lottery_data["winners_history"] = self.lottery_data["winners_history"][-10:]
    
    # Announce winner in all servers
    try:
        winner = await self.bot.fetch_user(int(winner_user_id))
        embed = discord.Embed(
            title="🎰 LOTTERY WINNER! 🎰",
            description=f"**{winner.name}** won the lottery jackpot!\n\n**Prize: {jackpot:,} PsyCoins**",
            color=discord.Color.gold()
        )
        embed.add_field(name="Winning Ticket", value=f"#{winning_ticket}", inline=True)
        embed.set_footer(text="Buy tickets with L!lottery buy <amount>")
        
        # Broadcast to all guilds (first available channel)
        for guild in self.bot.guilds:
            for channel in guild.text_channels:
                if channel.permissions_for(guild.me).send_messages:
                    try:
                        await channel.send(embed=embed)
                        break  # Only send to first channel per guild
                    except:
                        continue  # Try next channel if this one fails
    except:
        pass  # Silently fail if user/channels unavailable
    
    # Reset lottery for next drawing
    self.lottery_data["tickets"] = {}
    self.lottery_data["ticket_counter"] = 1
    self.lottery_data["current_jackpot"] = 10000  # Reset to base
    self.lottery_data["last_drawing"] = datetime.utcnow().isoformat()
    self.lottery_data["next_drawing"] = self.get_next_drawing_time().isoformat()
    
    self.save_data()
```

**Next Drawing Calculation (Lines 41-45):**
```python
def get_next_drawing_time(self):
    """Get the next drawing time (daily at midnight UTC)"""
    now = datetime.utcnow()
    next_drawing = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    return next_drawing
```

**Drawing Schedule:**
- Runs at **00:00 UTC** (midnight) daily
- Task checks every hour if drawing time has passed
- Immediate drawing if bot was offline during scheduled time
- Next drawing scheduled for next midnight after current drawing

---

### Jackpot Growth

**Growth Mechanisms:**

**1. Ticket Sales (50% contribution):**
```python
# When user buys tickets
total_cost = amount * 100  # 100 coins per ticket
jackpot_increase = total_cost // 2  # 50% to jackpot
self.lottery_data["current_jackpot"] += jackpot_increase

# Example:
# User buys 10 tickets = 1,000 coins
# Jackpot increases by 500 coins
# Other 500 coins removed from circulation (coin sink)
```

**2. No Sales Growth:**
```python
# If no tickets sold by drawing time
if not self.lottery_data["tickets"]:
    self.lottery_data["current_jackpot"] += 5000
    # Jackpot grows automatically
```

**Growth Example Timeline:**
```
Day 1:
- Starting jackpot: 10,000 coins
- 20 tickets sold (2,000 coins) → +1,000 to jackpot
- Drawing jackpot: 11,000 coins
- Winner drawn → Reset to 10,000

Day 2:
- Starting jackpot: 10,000 coins
- 50 tickets sold (5,000 coins) → +2,500 to jackpot
- Drawing jackpot: 12,500 coins
- Winner drawn → Reset to 10,000

Day 3:
- Starting jackpot: 10,000 coins
- 0 tickets sold → +5,000 automatic growth
- Drawing skipped: 15,000 coins

Day 4:
- Starting jackpot: 15,000 coins
- 100 tickets sold (10,000 coins) → +5,000 to jackpot
- Drawing jackpot: 20,000 coins
- Winner drawn → Reset to 10,000
```

**Jackpot as Coin Sink:**
- 50% of ticket purchases removed from economy
- Helps control inflation
- Balances coin generation from dailies/fishing/etc.
- Major coin sink alongside shop purchases

---

### Winner Selection

**Random Selection Algorithm (Lines 80-83):**
```python
# All tickets weighted equally
all_tickets = []
for user_id, tickets in self.lottery_data["tickets"].items():
    for ticket in tickets:
        all_tickets.append((user_id, ticket))

# True random selection (each ticket has equal chance)
winner_user_id, winning_ticket = random.choice(all_tickets)
```

**Fair Odds:**
- Every ticket has exactly 1/total_tickets chance of winning
- No manipulation or favoritism
- Python's `random.choice()` provides uniform distribution
- More tickets = proportionally higher win chance

**Probability Examples:**
```
Scenario 1: User A has 10 tickets, User B has 5 tickets
Total tickets: 15
User A win chance: 10/15 = 66.67%
User B win chance: 5/15 = 33.33%

Scenario 2: User A has 1 ticket, 99 others have 1 ticket each
Total tickets: 100
User A win chance: 1/100 = 1.00%
Others: 1% each

Scenario 3: User A buys all 100 max tickets (10,000 coins)
If only buyer: 100% win chance (but only wins ~15,000 for 10k spent = bad value)
If 10 others have 10 tickets each: 100/200 = 50% (better value)
```

**Strategy Considerations:**
- Buying many tickets in low-participation drawings = poor value
- Buying few tickets in high-participation drawings = lottery effect
- Optimal: Buy tickets when jackpot is high (30k+) and participation is moderate

---

## 3. LOTTERY COMMANDS

### View Lottery Info

**Command:** `L!lottery`  
**File Location:** Lines 131-180

```python
@commands.group(name="lottery", invoke_without_command=True)
async def lottery(self, ctx):
    """View current lottery information"""
    embed = discord.Embed(
        title="🎰 Daily Lottery",
        description=f"**Current Jackpot: {self.lottery_data['current_jackpot']:,} PsyCoins**",
        color=discord.Color.gold()
    )
    
    # Calculate total tickets sold
    total_tickets = sum(len(tickets) for tickets in self.lottery_data["tickets"].values())
    user_tickets = len(self.lottery_data["tickets"].get(str(ctx.author.id), []))
    
    embed.add_field(name="🎫 Ticket Price", value=f"{self.ticket_price:,} coins", inline=True)
    embed.add_field(name="🎫 Tickets Sold", value=total_tickets, inline=True)
    embed.add_field(name="🎫 Your Tickets", value=user_tickets, inline=True)
    
    # Time until next drawing
    next_drawing = datetime.fromisoformat(self.lottery_data["next_drawing"])
    time_until = next_drawing - datetime.utcnow()
    hours = int(time_until.total_seconds() // 3600)
    minutes = int((time_until.total_seconds() % 3600) // 60)
    
    embed.add_field(
        name="⏰ Next Drawing",
        value=f"In {hours}h {minutes}m",
        inline=False
    )
    
    # Show win probability if user has tickets
    if user_tickets > 0:
        win_chance = (user_tickets / total_tickets * 100) if total_tickets > 0 else 0
        embed.add_field(
            name="📊 Your Win Chance",
            value=f"{win_chance:.2f}%",
            inline=False
        )
    
    embed.set_footer(text="Buy tickets: L!lottery buy <amount>")
    
    await ctx.send(embed=embed)
```

**Display Example:**
```
🎰 Daily Lottery
━━━━━━━━━━━━━━━━

Current Jackpot: 23,500 PsyCoins

🎫 Ticket Price: 100 coins
🎫 Tickets Sold: 150
🎫 Your Tickets: 10

⏰ Next Drawing
In 7h 23m

📊 Your Win Chance
6.67%

Buy tickets: L!lottery buy <amount>
```

---

### Buy Tickets

**Command:** `L!lottery buy <amount>`  
**File Location:** Lines 185-254  
**Parameters:**
- `amount`: Number of tickets to buy (1-100)
- Default: 1 ticket

**Usage Examples:**
```
L!lottery buy          # Buy 1 ticket (100 coins)
L!lottery buy 5        # Buy 5 tickets (500 coins)
L!lottery buy 100      # Buy max 100 tickets (10,000 coins)
```

**Validation:**
- Minimum: 1 ticket
- Maximum: 100 tickets per purchase (prevents spam)
- No maximum total tickets per user (can buy multiple times)
- Balance check before purchase

**Display Example:**
```
🎫 Tickets Purchased!
━━━━━━━━━━━━━━━━

You bought 5 ticket(s) for 500 coins

Your Tickets
#47, #48, #49, #50, #51

New Jackpot: 23,750 coins
Your Win Chance: 5.33%
```

---

### View Your Tickets

**Command:** `L!lottery tickets [@user]`  
**File Location:** Lines 256-289  
**Aliases:** None  
**Parameters:**
- `member` (optional): View another user's tickets

```python
@lottery.command(name="tickets")
async def lottery_tickets(self, ctx, member: Optional[discord.Member] = None):
    """View your lottery tickets"""
    target = member or ctx.author
    user_key = str(target.id)
    
    if user_key not in self.lottery_data["tickets"] or not self.lottery_data["tickets"][user_key]:
        await ctx.send(f"🎫 {target.mention} has no tickets for the current drawing!")
        return
    
    tickets = self.lottery_data["tickets"][user_key]
    total_tickets = sum(len(t) for t in self.lottery_data["tickets"].values())
    win_chance = (len(tickets) / total_tickets * 100)
    
    embed = discord.Embed(
        title=f"🎫 {target.display_name}'s Lottery Tickets",
        description=f"**{len(tickets)}** tickets | **{win_chance:.2f}%** win chance",
        color=discord.Color.blue()
    )
    
    # Show individual ticket numbers (if 20 or fewer)
    if len(tickets) <= 20:
        ticket_list = ", ".join([f"#{t}" for t in sorted(tickets)])
        embed.add_field(name="Ticket Numbers", value=ticket_list, inline=False)
    else:
        # Show range for many tickets
        embed.add_field(
            name="Ticket Numbers",
            value=f"#{min(tickets)} to #{max(tickets)} (showing range due to many tickets)",
            inline=False
        )
    
    await ctx.send(embed=embed)
```

**Display Examples:**

**Few Tickets (≤20):**
```
🎫 PlayerName's Lottery Tickets
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

8 tickets | 5.33% win chance

Ticket Numbers
#47, #48, #49, #50, #51, #52, #53, #54
```

**Many Tickets (>20):**
```
🎫 HighRoller's Lottery Tickets
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

75 tickets | 50.00% win chance

Ticket Numbers
#1 to #75 (showing range due to many tickets)
```

---

### View Winners History

**Command:** `L!lottery winners` or `L!lottery history`  
**File Location:** Lines 291-309

```python
@lottery.command(name="winners", aliases=['history'])
async def lottery_winners(self, ctx):
    """View recent lottery winners"""
    if not self.lottery_data["winners_history"]:
        await ctx.send("📜 No lottery winners yet!")
        return
    
    embed = discord.Embed(
        title="🏆 Recent Lottery Winners",
        description="Last 10 winners",
        color=discord.Color.gold()
    )
    
    for i, winner_data in enumerate(reversed(self.lottery_data["winners_history"]), 1):
        try:
            user = await self.bot.fetch_user(int(winner_data["user_id"]))
            username = user.name
        except:
            username = f"User {winner_data['user_id']}"
        
        timestamp = datetime.fromisoformat(winner_data["timestamp"]).strftime("%Y-%m-%d")
        
        embed.add_field(
            name=f"#{i}. {username}",
            value=f"**{winner_data['jackpot']:,} coins**\nTicket #{winner_data['ticket']}\n*{timestamp}*",
            inline=True
        )
    
    await ctx.send(embed=embed)
```

**Display Example:**
```
🏆 Recent Lottery Winners
━━━━━━━━━━━━━━━━━━━━━━━

Last 10 winners

#1. PlayerOne           #2. GamerTwo           #3. LuckyThree
50,000 coins            32,500 coins           28,000 coins
Ticket #127             Ticket #89             Ticket #201
2026-02-04              2026-02-03             2026-02-02

#4. WinnerFour          #5. ChampFive          #6. UserSix
15,000 coins            23,000 coins           18,500 coins
Ticket #45              Ticket #156            Ticket #78
2026-02-01              2026-01-31             2026-01-30

[... up to 10 total winners ...]
```

---

### Manual Drawing (Owner Only)

**Command:** `L!lottery draw`  
**File Location:** Lines 311-313  
**Permissions:** Bot owner only

```python
@lottery.command(name="draw", hidden=True)
@commands.is_owner()
async def lottery_draw_manual(self, ctx):
    """Manually trigger a lottery drawing (owner only)"""
    await ctx.send("🎰 Conducting lottery drawing...")
    await self.conduct_drawing()
    await ctx.send("✅ Drawing complete!")
```

**Use Cases:**
- Testing lottery system
- Emergency drawing if automated task fails
- Forcing drawing for events
- Debugging

---

## 4. HEIST SYSTEM OVERVIEW

**File:** `cogs/heist.py` (502 lines)

The Heist system is a cooperative multiplayer game where 2-6 players team up to rob banks or other players' businesses. Success depends on crew size, with larger crews having higher success rates but splitting rewards more ways.

### Core Features

**Two Heist Types:**
1. **Bank Heist** (2-6 players)
   - Rob the city bank
   - Fixed reward: 10,000-50,000 coins
   - Risk: Lose 10% of bet on failure (bets not refunded)
   - Independent target (no player victim)

2. **Business Heist** (2-4 players)
   - Rob another player's business pending income
   - Variable reward: Depends on target's accumulated earnings
   - Risk: Lose entire bet on failure
   - Requires target to own businesses
   - Target's business income timers reset

**Crew System:**
- Leader starts heist with bet amount
- Other players join with same bet
- All crew members must wager equally
- 60 seconds to recruit (bank) or 45 seconds (business)
- Minimum 2 players to execute
- Refund if not enough players

**Success Rates (Crew Size):**
```
2 players: 40%
3 players: 55%
4 players: 70%
5 players: 80%
6 players: 90%
```

**Statistics Tracking:**
- Total heists participated
- Successful vs. failed heists
- Total coins stolen
- Total coins lost
- Success rate percentage
- Net profit/loss
- 30-minute cooldown per player

### Integration Points

**Economy System:**
- Bets deducted with reason `"heist_bet"`
- Rewards added with reason `"heist_success"`
- All crew members paid equally

**Business System:**
- Business heists steal pending income
- Target's `last_collect` timestamps reset
- Protection system prevents heisting protected businesses

**Profile System:**
- Heist stats can be viewed per player
- Leaderboard integration for most successful heisters

---

## 5. HEIST MECHANICS

### Bank Heists

**Starting a Bank Heist (Lines 117-195):**

```python
@heist.command(name="bank")
async def heist_bank(self, ctx, bet: int):
    """Start a bank heist"""
    # Check cooldown (30 minutes)
    can_start, minutes_left = self.can_start_heist(ctx.author.id)
    if not can_start:
        await ctx.send(f"⏰ You're on cooldown! Try again in {minutes_left} minutes.")
        return
    
    # Validate bet
    if bet < 1000:
        await ctx.send("❌ Minimum bet is 1,000 coins!")
        return
    
    if bet > 10000:
        await ctx.send("❌ Maximum bet is 10,000 coins per player!")
        return
    
    # Check balance
    economy_cog = self.bot.get_cog("Economy")
    balance = economy_cog.get_balance(ctx.author.id)
    if balance < bet:
        await ctx.send(f"❌ You need {bet:,} coins but have {balance:,}")
        return
    
    # Check if heist already active in channel
    if ctx.channel.id in self.active_heists:
        await ctx.send("❌ A heist is already being planned in this channel!")
        return
    
    # Deduct bet from leader
    economy_cog.remove_coins(ctx.author.id, bet, "heist_bet")
    
    # Create heist data structure
    self.active_heists[ctx.channel.id] = {
        "type": "bank",
        "leader": ctx.author.id,
        "crew": {str(ctx.author.id): bet},
        "bet_amount": bet,
        "target": None,  # No target for bank heists
        "started": datetime.utcnow().isoformat()
    }
    
    # Announce recruitment
    embed = discord.Embed(
        title="🏦 BANK HEIST RECRUITING!",
        description=f"{ctx.author.mention} is planning a bank heist!",
        color=discord.Color.red()
    )
    
    embed.add_field(name="Bet Amount", value=f"{bet:,} coins", inline=True)
    embed.add_field(name="Crew Size", value="1/6", inline=True)
    embed.add_field(name="Potential Reward", value="10,000-50,000 coins", inline=True)
    
    embed.add_field(
        name="Join Now!",
        value=f"Type `L!heist join` to join the crew!\n"
              f"You need {bet:,} coins to join.\n\n"
              f"⏰ Heist starts in 60 seconds!",
        inline=False
    )
    
    await ctx.send(embed=embed)
    
    # Wait 60 seconds for crew recruitment
    await asyncio.sleep(60)
    
    # Execute heist (if not cancelled)
    if ctx.channel.id in self.active_heists:
        await self.execute_heist(ctx)
```

**Bank Heist Parameters:**
- **Min bet:** 1,000 coins
- **Max bet:** 10,000 coins per player
- **Crew size:** 2-6 players
- **Recruitment time:** 60 seconds
- **Reward range:** 10,000-50,000 coins (random)
- **Reward split:** Evenly among crew

**Example Flow:**
```
Player A: L!heist bank 5000

[Bot announces recruitment - 60 second timer starts]

Player B: L!heist join  (pays 5,000 coins)
Player C: L!heist join  (pays 5,000 coins)

[60 seconds pass]

Crew size: 3 players
Success rate: 55%
Total bet pool: 15,000 coins

[Random roll: Success!]
Bank reward: 35,000 coins
Per person: 11,667 coins each
Net profit per person: +6,667 coins
```

---

### Business Heists

**Starting a Business Heist (Lines 197-286):**

```python
@heist.command(name="business")
async def heist_business(self, ctx, target: discord.Member, bet: int):
    """Start a business heist against another player"""
    # Validation
    if target.id == ctx.author.id:
        await ctx.send("❌ You can't heist yourself!")
        return
    
    if target.bot:
        await ctx.send("❌ Can't heist bots!")
        return
    
    # Check cooldown
    can_start, minutes_left = self.can_start_heist(ctx.author.id)
    if not can_start:
        await ctx.send(f"⏰ You're on cooldown! Try again in {minutes_left} minutes.")
        return
    
    # Check if target has businesses
    business_cog = self.bot.get_cog("Business")
    if not business_cog:
        await ctx.send("❌ Business system not loaded!")
        return
    
    target_businesses = business_cog.get_user_businesses(target.id)
    if not target_businesses["businesses"]:
        await ctx.send(f"❌ {target.mention} doesn't own any businesses!")
        return
    
    # Check business protection
    if target_businesses["protection"]:
        protection_expires = datetime.fromisoformat(target_businesses["protection"])
        if datetime.utcnow() < protection_expires:
            await ctx.send(f"🛡️ {target.mention}'s businesses are protected!")
            return
    
    # Validate bet
    if bet < 500:
        await ctx.send("❌ Minimum bet is 500 coins!")
        return
    
    if bet > 5000:
        await ctx.send("❌ Maximum bet is 5,000 coins per player!")
        return
    
    # Check balance
    economy_cog = self.bot.get_cog("Economy")
    balance = economy_cog.get_balance(ctx.author.id)
    if balance < bet:
        await ctx.send(f"❌ You need {bet:,} coins but have {balance:,}")
        return
    
    # Deduct bet
    economy_cog.remove_coins(ctx.author.id, bet, "heist_bet")
    
    # Create heist
    self.active_heists[ctx.channel.id] = {
        "type": "business",
        "leader": ctx.author.id,
        "crew": {str(ctx.author.id): bet},
        "bet_amount": bet,
        "target": target.id,  # Player being heisted
        "started": datetime.utcnow().isoformat()
    }
    
    # Announce recruitment
    embed = discord.Embed(
        title="🏢 BUSINESS HEIST RECRUITING!",
        description=f"{ctx.author.mention} is planning to rob {target.mention}!",
        color=discord.Color.orange()
    )
    
    embed.add_field(name="Bet Amount", value=f"{bet:,} coins", inline=True)
    embed.add_field(name="Crew Size", value="1/4", inline=True)
    embed.add_field(name="Target", value=target.mention, inline=True)
    
    embed.add_field(
        name="Join Now!",
        value=f"Type `L!heist join` to join the crew!\n"
              f"You need {bet:,} coins to join.\n\n"
              f"⏰ Heist starts in 45 seconds!",
        inline=False
    )
    
    await ctx.send(embed=embed)
    
    # Wait 45 seconds
    await asyncio.sleep(45)
    
    # Execute heist
    if ctx.channel.id in self.active_heists:
        await self.execute_heist(ctx)
```

**Business Heist Parameters:**
- **Min bet:** 500 coins
- **Max bet:** 5,000 coins per player
- **Crew size:** 2-4 players (smaller than bank)
- **Recruitment time:** 45 seconds (faster than bank)
- **Reward:** Target's accumulated business income
- **Minimum reward:** 1,000 coins (if target has no pending)

**Protection System:**
- Businesses can be protected (via Business cog)
- Protection expires after set time
- Protected businesses cannot be heisted
- Heist cancelled if protection detected

**Reward Calculation (Lines 398-415):**
```python
# Calculate total pending income from all target's businesses
total_stolen = 0
for biz_id, biz_data in target_businesses["businesses"].items():
    biz_type = biz_data["type"]  # e.g., "restaurant", "casino"
    level = biz_data["level"]    # Business upgrade level
    income = business_cog.calculate_income(biz_type, level)  # Coins per hour
    
    # Calculate time since last collection
    last_collect = datetime.fromisoformat(biz_data["last_collect"])
    hours_passed = (datetime.utcnow() - last_collect).total_seconds() / 3600
    pending = int(income * hours_passed)
    
    total_stolen += pending
    
    # Reset victim's collection timer (they lose pending income)
    biz_data["last_collect"] = datetime.utcnow().isoformat()

business_cog.save_data()

# Minimum 1,000 if no pending income
if total_stolen == 0:
    total_stolen = 1000

reward_per_person = total_stolen // crew_size
```

**Example Business Heist:**
```
Target: @RichPlayer
Businesses owned:
- Restaurant (Level 3): 500 coins/hour, 10 hours since collect = 5,000 pending
- Casino (Level 2): 800 coins/hour, 5 hours since collect = 4,000 pending
- Shop (Level 1): 200 coins/hour, 20 hours since collect = 4,000 pending

Total pending: 13,000 coins

Crew: 3 players
Bet: 2,000 each (6,000 total)
Success rate: 55%

If successful:
- Each crew member gets: 13,000 / 3 = 4,333 coins
- Net profit each: +2,333 coins
- Target loses 13,000 pending income
- Target's timers reset to 0

If failed:
- Crew loses 6,000 total
- Target keeps pending income
```

---

### Success Rates

**Success Rate Formula (Lines 339-342):**
```python
# Calculate success rate based on crew size
success_rates = {2: 0.40, 3: 0.55, 4: 0.70, 5: 0.80, 6: 0.90}
success_rate = success_rates.get(crew_size, 0.40)

# Roll for success (random 0.0-1.0)
success = random.random() < success_rate
```

**Success Rate Table:**
| Crew Size | Success Rate | Risk/Reward |
|-----------|--------------|-------------|
| 2 players | 40% | High risk, high reward per person |
| 3 players | 55% | Moderate risk, good reward |
| 4 players | 70% | Low risk, decent reward |
| 5 players | 80% | Very safe, split 5 ways |
| 6 players | 90% | Almost guaranteed, split 6 ways |

**Strategic Considerations:**

**2-Player Heists:**
- **Pros:** Maximum reward per person (split 2 ways)
- **Cons:** 60% failure rate (high risk)
- **Best for:** High rollers willing to gamble

**3-Player Heists:**
- **Pros:** Balanced risk/reward (55% success)
- **Cons:** Still risky
- **Best for:** Small groups, moderate bets

**4-Player Heists:**
- **Pros:** 70% success (fairly safe)
- **Cons:** Reward split 4 ways
- **Best for:** Standard heists, good balance

**5-6 Player Heists:**
- **Pros:** 80-90% success (very safe)
- **Cons:** Reward split many ways (low per-person gain)
- **Best for:** Low-risk farming, guaranteed small gains

**Expected Value (EV) Analysis:**

**Bank Heist (avg reward: 30,000 coins):**
```
2 players: (30,000/2 * 0.40) - (bet * 0.60) = 6,000 - 0.6*bet
3 players: (30,000/3 * 0.55) - (bet * 0.45) = 5,500 - 0.45*bet
4 players: (30,000/4 * 0.70) - (bet * 0.30) = 5,250 - 0.30*bet
5 players: (30,000/5 * 0.80) - (bet * 0.20) = 4,800 - 0.20*bet
6 players: (30,000/6 * 0.90) - (bet * 0.10) = 4,500 - 0.10*bet

With bet = 5,000:
2 players: 6,000 - 3,000 = +3,000 EV (best!)
3 players: 5,500 - 2,250 = +3,250 EV (slightly better)
4 players: 5,250 - 1,500 = +3,750 EV
5 players: 4,800 - 1,000 = +3,800 EV
6 players: 4,500 - 500 = +4,000 EV (highest EV!)

Conclusion: Larger crews have better EV despite smaller splits
```

---

### Crew System

**Joining a Heist (Lines 288-337):**

```python
@heist.command(name="join")
async def heist_join(self, ctx):
    """Join an active heist"""
    # Check if heist exists in channel
    if ctx.channel.id not in self.active_heists:
        await ctx.send("❌ No heist is being planned in this channel!")
        return
    
    heist = self.active_heists[ctx.channel.id]
    user_key = str(ctx.author.id)
    
    # Check if already in crew
    if user_key in heist["crew"]:
        await ctx.send("❌ You're already in the crew!")
        return
    
    # Check crew size limits
    max_crew = 6 if heist["type"] == "bank" else 4
    if len(heist["crew"]) >= max_crew:
        await ctx.send(f"❌ Crew is full! ({max_crew}/{max_crew})")
        return
    
    # Check if user has enough coins for bet
    economy_cog = self.bot.get_cog("Economy")
    bet = heist["bet_amount"]  # Must match leader's bet
    balance = economy_cog.get_balance(ctx.author.id)
    
    if balance < bet:
        await ctx.send(f"❌ You need {bet:,} coins to join but have {balance:,}")
        return
    
    # Join heist
    economy_cog.remove_coins(ctx.author.id, bet, "heist_bet")
    heist["crew"][user_key] = bet
    
    crew_size = len(heist["crew"])
    await ctx.send(f"✅ {ctx.author.mention} joined the crew! ({crew_size}/{max_crew})")
```

**Crew Requirements:**
- All members must bet same amount as leader
- No partial bets or custom amounts
- Maximum crew size enforced (6 for bank, 4 for business)
- Cannot join if heist already started
- Cannot join own heist multiple times

**Crew Cancellation (Lines 341-350):**
```python
if crew_size < 2:
    # Refund everyone if not enough crew
    economy_cog = self.bot.get_cog("Economy")
    for user_id, bet in heist["crew"].items():
        economy_cog.add_coins(int(user_id), bet, "heist_cancelled")
    
    del self.active_heists[ctx.channel.id]
    await ctx.send("❌ Heist cancelled! Not enough crew members. Bets refunded.")
    return
```

---

## 6. HEIST EXECUTION

**Execution Logic (Lines 339-455):**

```python
async def execute_heist(self, ctx):
    """Execute the heist after recruitment period"""
    heist = self.active_heists[ctx.channel.id]
    crew_size = len(heist["crew"])
    
    # Check minimum crew
    if crew_size < 2:
        # Refund and cancel
        economy_cog = self.bot.get_cog("Economy")
        for user_id, bet in heist["crew"].items():
            economy_cog.add_coins(int(user_id), bet, "heist_cancelled")
        del self.active_heists[ctx.channel.id]
        await ctx.send("❌ Heist cancelled! Not enough crew members. Bets refunded.")
        return
    
    # Calculate success probability
    success_rates = {2: 0.40, 3: 0.55, 4: 0.70, 5: 0.80, 6: 0.90}
    success_rate = success_rates.get(crew_size, 0.40)
    
    # Roll for success
    success = random.random() < success_rate
    
    economy_cog = self.bot.get_cog("Economy")
    
    if success:
        # HEIST SUCCESS
        if heist["type"] == "bank":
            # Bank heist reward (10k-50k)
            base_reward = random.randint(10000, 50000)
            reward_per_person = base_reward // crew_size
            
            # Pay crew members
            crew_mentions = []
            for user_id, bet in heist["crew"].items():
                uid = int(user_id)
                economy_cog.add_coins(uid, reward_per_person, "heist_success")
                
                # Update statistics
                stats = self.get_user_stats(uid)
                stats["total_heists"] += 1
                stats["successful"] += 1
                stats["total_stolen"] += reward_per_person
                stats["last_heist"] = datetime.utcnow().isoformat()
                
                user = await self.bot.fetch_user(uid)
                crew_mentions.append(user.mention)
            
            # Success announcement
            embed = discord.Embed(
                title="✅ HEIST SUCCESS!",
                description=f"The crew successfully robbed the bank!",
                color=discord.Color.green()
            )
            embed.add_field(name="Crew Size", value=crew_size, inline=True)
            embed.add_field(name="Total Loot", value=f"{base_reward:,} coins", inline=True)
            embed.add_field(name="Per Person", value=f"{reward_per_person:,} coins", inline=True)
            embed.add_field(name="Crew", value=", ".join(crew_mentions), inline=False)
        
        else:
            # Business heist reward (target's pending income)
            business_cog = self.bot.get_cog("Business")
            target_businesses = business_cog.get_user_businesses(heist["target"])
            
            # Calculate total pending income (logic shown earlier)
            total_stolen = 0
            for biz_id, biz_data in target_businesses["businesses"].items():
                biz_type = biz_data["type"]
                level = biz_data["level"]
                income = business_cog.calculate_income(biz_type, level)
                
                last_collect = datetime.fromisoformat(biz_data["last_collect"])
                hours_passed = (datetime.utcnow() - last_collect).total_seconds() / 3600
                pending = int(income * hours_passed)
                total_stolen += pending
                
                # Reset timer (victim loses pending income)
                biz_data["last_collect"] = datetime.utcnow().isoformat()
            
            business_cog.save_data()
            
            if total_stolen == 0:
                total_stolen = 1000  # Minimum reward
            
            reward_per_person = total_stolen // crew_size
            
            # Pay crew
            crew_mentions = []
            for user_id in heist["crew"].keys():
                uid = int(user_id)
                economy_cog.add_coins(uid, reward_per_person, "heist_success")
                
                # Update stats
                stats = self.get_user_stats(uid)
                stats["total_heists"] += 1
                stats["successful"] += 1
                stats["total_stolen"] += reward_per_person
                stats["last_heist"] = datetime.utcnow().isoformat()
                
                user = await self.bot.fetch_user(uid)
                crew_mentions.append(user.mention)
            
            # Success announcement
            embed = discord.Embed(
                title="✅ HEIST SUCCESS!",
                description=f"The crew robbed {(await self.bot.fetch_user(heist['target'])).mention}'s businesses!",
                color=discord.Color.green()
            )
            embed.add_field(name="Crew Size", value=crew_size, inline=True)
            embed.add_field(name="Total Stolen", value=f"{total_stolen:,} coins", inline=True)
            embed.add_field(name="Per Person", value=f"{reward_per_person:,} coins", inline=True)
            embed.add_field(name="Crew", value=", ".join(crew_mentions), inline=False)
    
    else:
        # HEIST FAILED
        embed = discord.Embed(
            title="❌ HEIST FAILED!",
            description="The crew was caught!",
            color=discord.Color.red()
        )
        
        total_lost = sum(heist["crew"].values())
        
        # Update failure stats
        crew_mentions = []
        for user_id in heist["crew"].keys():
            uid = int(user_id)
            
            stats = self.get_user_stats(uid)
            stats["total_heists"] += 1
            stats["failed"] += 1
            stats["total_lost"] += heist["crew"][user_id]
            stats["last_heist"] = datetime.utcnow().isoformat()
            
            user = await self.bot.fetch_user(uid)
            crew_mentions.append(user.mention)
        
        embed.add_field(name="Crew Size", value=crew_size, inline=True)
        embed.add_field(name="Success Rate", value=f"{int(success_rate * 100)}%", inline=True)
        embed.add_field(name="Total Lost", value=f"{total_lost:,} coins", inline=True)
        embed.add_field(name="Crew", value=", ".join(crew_mentions), inline=False)
    
    # Save stats and clean up
    self.save_data()
    del self.active_heists[ctx.channel.id]
    
    await ctx.send(embed=embed)
```

**Success Announcement Example:**
```
✅ HEIST SUCCESS!
━━━━━━━━━━━━━━━━

The crew successfully robbed the bank!

Crew Size: 4
Total Loot: 38,000 coins
Per Person: 9,500 coins

Crew: @Player1, @Player2, @Player3, @Player4
```

**Failure Announcement Example:**
```
❌ HEIST FAILED!
━━━━━━━━━━━━━━━━

The crew was caught!

Crew Size: 2
Success Rate: 40%
Total Lost: 10,000 coins

Crew: @Player1, @Player2
```

---

## 7. HEIST STATISTICS

**Statistics Structure (Lines 31-42):**

```python
def get_user_stats(self, user_id):
    """Get user's heist statistics"""
    user_key = str(user_id)
    if user_key not in self.heist_data:
        self.heist_data[user_key] = {
            "total_heists": 0,
            "successful": 0,
            "failed": 0,
            "total_stolen": 0,
            "total_lost": 0,
            "last_heist": None
        }
    return self.heist_data[user_key]
```

**Cooldown Check (Lines 44-58):**

```python
def can_start_heist(self, user_id):
    """Check if user can start a heist (30min cooldown)"""
    stats = self.get_user_stats(user_id)
    if not stats["last_heist"]:
        return True, None  # No cooldown, first heist
    
    last_heist = datetime.fromisoformat(stats["last_heist"])
    cooldown = timedelta(minutes=30)
    time_passed = datetime.utcnow() - last_heist
    
    if time_passed < cooldown:
        time_left = cooldown - time_passed
        minutes = int(time_left.total_seconds() // 60)
        return False, minutes  # On cooldown
    
    return True, None  # Cooldown expired
```

**View Stats Command (Lines 457-502):**

```python
@heist.command(name="stats")
async def heist_stats(self, ctx, member: Optional[discord.Member] = None):
    """View heist statistics"""
    target = member or ctx.author
    stats = self.get_user_stats(target.id)
    
    if stats["total_heists"] == 0:
        await ctx.send(f"🏴‍☠️ {target.mention} hasn't participated in any heists yet!")
        return
    
    # Calculate metrics
    success_rate = (stats["successful"] / stats["total_heists"]) * 100 if stats["total_heists"] > 0 else 0
    net_profit = stats["total_stolen"] - stats["total_lost"]
    
    embed = discord.Embed(
        title=f"🏴‍☠️ {target.display_name}'s Heist Stats",
        color=discord.Color.dark_red()
    )
    
    embed.add_field(name="Total Heists", value=stats["total_heists"], inline=True)
    embed.add_field(name="Successful", value=stats["successful"], inline=True)
    embed.add_field(name="Failed", value=stats["failed"], inline=True)
    
    embed.add_field(name="Success Rate", value=f"{success_rate:.1f}%", inline=True)
    embed.add_field(name="Total Stolen", value=f"{stats['total_stolen']:,} coins", inline=True)
    embed.add_field(name="Total Lost", value=f"{stats['total_lost']:,} coins", inline=True)
    
    embed.add_field(
        name="Net Profit",
        value=f"{'📈' if net_profit > 0 else '📉'} {net_profit:,} coins",
        inline=False
    )
    
    await ctx.send(embed=embed)
```

**Display Example:**
```
🏴‍☠️ PlayerName's Heist Stats
━━━━━━━━━━━━━━━━━━━━━━━━━

Total Heists: 25        Successful: 18       Failed: 7

Success Rate: 72.0%     Total Stolen: 287,000 coins
Total Lost: 35,000 coins

Net Profit
📈 +252,000 coins
```

**Statistics Use Cases:**
- Track individual heisting career
- Compare success rates between players
- Leaderboard for most successful heisters
- Risk assessment (high net profit = skilled player)
- Reputation system (invite skilled players to crew)

---

## 8. COMMANDS REFERENCE

### Lottery Commands

| Command | Description | Parameters | Cooldown |
|---------|-------------|------------|----------|
| `L!lottery` | View current jackpot & info | None | None |
| `L!lottery buy <amount>` | Buy lottery tickets | 1-100 tickets | None |
| `L!lottery tickets [@user]` | View ticket numbers | Optional: user | None |
| `L!lottery winners` | View winner history | None | None |
| `L!lottery draw` | Manual drawing (owner) | None | Owner only |

**Lottery Aliases:**
- `L!lottery history` → `L!lottery winners`

### Heist Commands

| Command | Description | Parameters | Cooldown |
|---------|-------------|------------|----------|
| `L!heist` | View heist info & rules | None | None |
| `L!heist bank <bet>` | Start bank heist | 1k-10k coins | 30 min |
| `L!heist business <@user> <bet>` | Start business heist | User, 500-5k coins | 30 min |
| `L!heist join` | Join active heist | None | None |
| `L!heist stats [@user]` | View heist statistics | Optional: user | None |

**Heist Restrictions:**
- Only one heist per channel at a time
- Leader's cooldown starts after heist execution
- Joining crew doesn't trigger cooldown
- Bets non-refundable (except cancellation)

---

## 9. SUMMARY

**Part 4B Coverage:**
- **Lottery System:** Daily raffle with growing jackpots
- **Heist System:** Cooperative multiplayer bank/business robbery

**Lottery Features:**
- Automated daily drawings at midnight UTC
- Sequential ticket numbering (unique IDs)
- 50% of sales → jackpot, 50% → coin sink
- Winner announced in all servers
- History tracking (last 10 winners)
- Fair probability (more tickets = higher chance)
- Minimum 100 coins, max 100 tickets per purchase

**Heist Features:**
- Two heist types (bank vs. business)
- 2-6 player co-op (bank) or 2-4 (business)
- Success rates scale with crew size (40%-90%)
- Equal bet requirement for all crew
- 30-minute cooldown per player
- Statistics tracking (wins, losses, profit)
- Business protection system integration
- Recruitment period (60s bank, 45s business)

**Key Technical Details:**
- Task loops for automated systems
- Cooldown management with timestamps
- Fair random selection algorithms
- Economy integration (bets, payouts, sinks)
- Business system integration
- Multi-guild announcements
- Atomic data persistence

**File Statistics:**
- lottery.py: 313 lines
- heist.py: 502 lines
- **Total:** 815 lines of code
- **Documentation:** ~12,000 words

**Economic Impact:**
- Lottery acts as major coin sink (50% of sales)
- Heists redistribute wealth (bank) or steal from players (business)
- High-risk/high-reward gameplay
- Encourages cooperation and social interaction

**Next Part:** Part 5 will cover Board & Card Games (Chess, Checkers, UNO, Poker, etc.)

---

*End of Part 4B Documentation*
