# Cross-Server Implementation Guide

## 🎯 Current Status

### ✅ Phase 1: Database Layer (COMPLETED)
- Database service fully isolated with guild_id parameter
- PSY sentinel system (guild_id=0) for cross-server admin
- Composite UNIQUE constraints for multi-server data
- Performance indexes on (guild_id, user_id) and (guild_id, team_id)
- Bot starts cleanly, loads/syncs data without errors

### ⏳ Phase 2: In-Memory Data Structures (TODO)
Transform flat dictionaries to guild-nested dictionaries

### ⏳ Phase 3: Command Layer Updates (TODO)
Update ~200 commands to pass ctx.guild.id to all operations

---

## 📊 Phase 2: In-Memory Data Structure Refactor

### Current Architecture (Single-Server)
```python
chi_data = {
    "user_id_1": {"chi": 1000, "rebirths": 5, ...},
    "user_id_2": {"chi": 2000, "rebirths": 3, ...}
}

teams_data = {
    "teams": {
        "team_id_1": {"name": "Team Alpha", "members": [...], ...},
        "team_id_2": {"name": "Team Beta", "members": [...], ...}
    },
    "user_teams": {"user_id_1": "team_id_1", ...},
    "pending_invites": {...}
}

gardens_data = {
    "gardens": {
        "user_id_1": {"tier": "legendary", "plants": [...], ...},
        "user_id_2": {"tier": "rare", "plants": [...], ...}
    },
    "garden_event": {"active": False, "end_time": None}
}
```

### Target Architecture (Multi-Server)
```python
chi_data = {
    "guild_id_1": {
        "user_id_1": {"chi": 1000, "rebirths": 5, ...},
        "user_id_2": {"chi": 2000, "rebirths": 3, ...}
    },
    "guild_id_2": {
        "user_id_3": {"chi": 500, "rebirths": 1, ...}
    }
}

teams_data = {
    "teams": {
        "guild_id_1": {
            "team_id_1": {"name": "Team Alpha", "members": [...], ...},
            "team_id_2": {"name": "Team Beta", "members": [...], ...}
        },
        "guild_id_2": {
            "team_id_3": {"name": "Team Gamma", "members": [...], ...}
        }
    },
    "user_teams": {
        "guild_id_1": {"user_id_1": "team_id_1", ...},
        "guild_id_2": {"user_id_3": "team_id_3", ...}
    },
    "pending_invites": {
        "guild_id_1": {...},
        "guild_id_2": {...}
    }
}

gardens_data = {
    "gardens": {
        "guild_id_1": {
            "user_id_1": {"tier": "legendary", "plants": [...], ...},
            "user_id_2": {"tier": "rare", "plants": [...], ...}
        },
        "guild_id_2": {
            "user_id_3": {"tier": "common", "plants": [...], ...}
        }
    },
    "garden_event": {
        "guild_id_1": {"active": False, "end_time": None},
        "guild_id_2": {"active": True, "end_time": "2025-11-15"}
    }
}
```

### Required Changes

#### 1. Helper Functions (New)
Create guild-aware accessor functions to abstract the nesting:

```python
def get_user_data(guild_id: int, user_id: int):
    """Get user data for a specific guild"""
    guild_str = str(guild_id)
    user_str = str(user_id)
    
    if guild_str not in chi_data:
        chi_data[guild_str] = {}
    
    if user_str not in chi_data[guild_str]:
        chi_data[guild_str][user_str] = DEFAULT_USER_DATA.copy()
    
    return chi_data[guild_str][user_str]

def get_team_data(guild_id: int, team_id: int):
    """Get team data for a specific guild"""
    guild_str = str(guild_id)
    team_str = str(team_id)
    
    if guild_str not in teams_data["teams"]:
        teams_data["teams"][guild_str] = {}
    
    return teams_data["teams"][guild_str].get(team_str)

def get_garden_data(guild_id: int, user_id: int):
    """Get garden data for a specific guild"""
    guild_str = str(guild_id)
    user_str = str(user_id)
    
    if guild_str not in gardens_data["gardens"]:
        gardens_data["gardens"][guild_str] = {}
    
    return gardens_data["gardens"][guild_str].get(user_str)

def get_all_users_in_guild(guild_id: int):
    """Get all users in a specific guild"""
    guild_str = str(guild_id)
    return chi_data.get(guild_str, {})

def get_all_teams_in_guild(guild_id: int):
    """Get all teams in a specific guild"""
    guild_str = str(guild_id)
    return teams_data["teams"].get(guild_str, {})

def get_all_gardens_in_guild(guild_id: int):
    """Get all gardens in a specific guild"""
    guild_str = str(guild_id)
    return gardens_data["gardens"].get(guild_str, {})
```

#### 2. Data Loading Refactor
Update `load_data_from_database()` to load ALL guilds:

```python
async def load_data_from_database():
    """Load all data from PostgreSQL database on startup for ALL guilds"""
    global chi_data, teams_data, gardens_data
    
    # Initialize nested structure
    chi_data = {}
    teams_data = {"teams": {}, "user_teams": {}, "pending_invites": {}}
    gardens_data = {"gardens": {}, "garden_event": {}}
    
    # Load data for EACH guild bot is in
    for guild in bot.guilds:
        guild_id = guild.id
        guild_str = str(guild_id)
        
        # Load users for this guild
        all_users = await db.get_all_users(guild_id=guild_id)
        if all_users:
            chi_data[guild_str] = {}
            for user_id, user_dict in all_users.items():
                sanitized_data = sanitize_datetime_fields(user_dict)
                chi_data[guild_str][str(user_id)] = sanitized_data
        
        # Load teams for this guild
        all_teams = await db.get_all_teams(guild_id=guild_id)
        if all_teams:
            teams_data["teams"][guild_str] = {}
            for team_id, team_dict in all_teams.items():
                sanitized_data = sanitize_datetime_fields(team_dict)
                teams_data["teams"][guild_str][str(team_id)] = sanitized_data
        
        # Load gardens for this guild
        all_gardens = await db.get_all_gardens(guild_id=guild_id)
        if all_gardens:
            gardens_data["gardens"][guild_str] = {}
            for user_id, garden_dict in all_gardens.items():
                sanitized_data = sanitize_datetime_fields(garden_dict)
                gardens_data["gardens"][guild_str][str(user_id)] = sanitized_data
        
        print(f"✅ Loaded data for guild {guild.name} (ID: {guild_id})")
```

#### 3. Sync Functions Refactor
Update sync functions to accept guild_id parameter:

```python
async def sync_user_to_db(user_id: int, guild_id: int):
    """Sync user data from chi_data to database"""
    if not db.pool:
        return
    
    try:
        guild_str = str(guild_id)
        user_str = str(user_id)
        
        if guild_str not in chi_data or user_str not in chi_data[guild_str]:
            return
        
        user_data = chi_data[guild_str][user_str]
        await db.create_or_update_user(
            user_id=user_id,
            guild_id=guild_id,
            chi=user_data.get("chi", 0),
            rebirths=user_data.get("rebirths", 0),
            milestones_claimed=user_data.get("milestones_claimed", []),
            mini_quests=user_data.get("mini_quests", []),
            active_pet=user_data.get("active_pet")
        )
    except Exception as e:
        print(f"⚠️ Failed to sync user {user_id} (guild {guild_id}) to database: {e}")
```

#### 4. Background Sync Task Refactor
Update to sync ALL guilds:

```python
@tasks.loop(minutes=1)
async def database_sync_task():
    """Periodically sync all critical data to database for ALL guilds"""
    if not db.pool:
        return
    
    try:
        # Sync ALL guilds
        for guild in bot.guilds:
            guild_id = guild.id
            guild_str = str(guild_id)
            
            # Sync all users in this guild
            if guild_str in chi_data:
                for user_id_str in list(chi_data[guild_str].keys()):
                    try:
                        await sync_user_to_db(int(user_id_str), guild_id)
                    except Exception:
                        pass
            
            # Sync all gardens in this guild
            if guild_str in gardens_data.get("gardens", {}):
                for user_id_str in list(gardens_data["gardens"][guild_str].keys()):
                    try:
                        await sync_garden_to_db(int(user_id_str), guild_id)
                    except Exception:
                        pass
                        
    except Exception as e:
        print(f"⚠️ Database sync failed: {e}")
```

---

## 🔧 Phase 3: Command Layer Updates

### Pattern 1: User Data Commands (Most Common)
**Current Pattern:**
```python
@bot.command(name="profile")
async def profile(ctx, member: discord.Member = None):
    member = member or ctx.author
    user_id = str(member.id)
    
    if user_id not in chi_data:
        chi_data[user_id] = DEFAULT_USER_DATA.copy()
    
    user = chi_data[user_id]
    # ... rest of command
```

**New Pattern:**
```python
@bot.command(name="profile")
async def profile(ctx, member: discord.Member = None):
    member = member or ctx.author
    guild_id = ctx.guild.id
    user_id = member.id
    
    user = get_user_data(guild_id, user_id)  # Helper function
    # ... rest of command
```

### Pattern 2: Team Commands
**Current Pattern:**
```python
@bot.command(name="team")
async def team_info(ctx):
    user_id = str(ctx.author.id)
    user_teams = teams_data.get("user_teams", {})
    
    if user_id not in user_teams:
        await ctx.send("You're not in a team!")
        return
    
    team_id = user_teams[user_id]
    team = teams_data["teams"][team_id]
    # ... rest of command
```

**New Pattern:**
```python
@bot.command(name="team")
async def team_info(ctx):
    guild_id = ctx.guild.id
    user_id = ctx.author.id
    guild_str = str(guild_id)
    user_str = str(user_id)
    
    user_teams = teams_data.get("user_teams", {}).get(guild_str, {})
    
    if user_str not in user_teams:
        await ctx.send("You're not in a team!")
        return
    
    team_id = user_teams[user_str]
    team = teams_data["teams"][guild_str][team_id]
    # ... rest of command
```

### Pattern 3: Garden Commands
**Current Pattern:**
```python
@bot.command(name="garden")
async def garden_status(ctx):
    user_id = str(ctx.author.id)
    gardens = gardens_data.get("gardens", {})
    
    if user_id not in gardens:
        await ctx.send("You don't have a garden!")
        return
    
    garden = gardens[user_id]
    # ... rest of command
```

**New Pattern:**
```python
@bot.command(name="garden")
async def garden_status(ctx):
    guild_id = ctx.guild.id
    user_id = ctx.author.id
    
    garden = get_garden_data(guild_id, user_id)  # Helper function
    
    if not garden:
        await ctx.send("You don't have a garden!")
        return
    
    # ... rest of command
```

### Pattern 4: Leaderboard Commands
**Current Pattern:**
```python
@bot.command(name="leaderboard")
async def leaderboard(ctx):
    sorted_users = sorted(
        chi_data.items(),
        key=lambda x: x[1].get("chi", 0),
        reverse=True
    )[:10]
    # ... display leaderboard
```

**New Pattern:**
```python
@bot.command(name="leaderboard")
async def leaderboard(ctx):
    guild_id = ctx.guild.id
    guild_users = get_all_users_in_guild(guild_id)  # Helper function
    
    sorted_users = sorted(
        guild_users.items(),
        key=lambda x: x[1].get("chi", 0),
        reverse=True
    )[:10]
    # ... display leaderboard (now guild-specific!)
```

---

## 📋 Implementation Checklist

### Phase 2: Data Structure Refactor
- [ ] Create helper functions (get_user_data, get_team_data, get_garden_data, etc.)
- [ ] Refactor load_data_from_database() to load all guilds
- [ ] Refactor sync_user_to_db() to accept guild_id parameter
- [ ] Refactor sync_garden_to_db() to accept guild_id parameter
- [ ] Refactor sync_team_to_db() to accept guild_id parameter
- [ ] Update database_sync_task() to sync all guilds
- [ ] Update schedule_db_sync() to pass guild_id
- [ ] Test data loading with multiple guilds
- [ ] Test background sync with multiple guilds

### Phase 3: Command Layer Updates (~200 commands)
Commands are grouped by category for systematic updates:

#### Chi & Economy Commands (20 commands)
- [ ] P!profile - User profile display
- [ ] P!leaderboard - Chi leaderboard
- [ ] P!give - Transfer chi between users
- [ ] P!daily - Daily chi rewards
- [ ] P!milestone - Milestone rewards
- [ ] P!rebirth - Manual rebirth
- [ ] P!cshop - Chi shop
- [ ] P!rshop - Rebirth shop
- [ ] P!buy - Purchase items
- [ ] P!inventory - View inventory
- [ ] P!use - Use items
- [ ] P!chest - Permanent chest storage
- [ ] P!sell - Sell seeds
- [ ] P!stats - User statistics
- [ ] (Plus 6 more economy-related commands)

#### Team Commands (15 commands)
- [ ] P!team - Team info
- [ ] P!createteam - Create team
- [ ] P!jointeam - Join team
- [ ] P!leaveteam - Leave team
- [ ] P!teamkick - Kick member
- [ ] P!teambase - View base
- [ ] P!teamupgrade - Upgrade base
- [ ] P!teamdecorate - Decorate base
- [ ] P!teamchi - Donate chi
- [ ] P!ally - Form alliance
- [ ] P!enemy - Declare enemy
- [ ] (Plus 4 more team commands)

#### Garden Commands (12 commands)
- [ ] P!garden - Garden status
- [ ] P!creategarden - Create garden
- [ ] P!plant - Plant seeds
- [ ] P!harvest - Harvest plants
- [ ] P!water - Water plants
- [ ] P!fertilize - Fertilize plants
- [ ] P!upgrade - Upgrade garden tier
- [ ] P!dgarden - Dongtian winter garden
- [ ] (Plus 4 more garden commands)

#### Combat Commands (25 commands)
- [ ] P!duel - Start duel
- [ ] P!attack - Attack in duel
- [ ] P!defend - Defend in duel
- [ ] P!boss - Boss battle
- [ ] P!train - NPC training
- [ ] P!rift - Rift event battle
- [ ] P!dboss - Dongtian boss battle
- [ ] (Plus 18 more combat commands)

#### Pet Commands (8 commands)
- [ ] P!pet store - View pets
- [ ] P!pet buy - Purchase pet
- [ ] P!pet info - Pet stats
- [ ] P!pet list - Owned pets
- [ ] P!pet switch - Change active pet
- [ ] P!pet feed - Feed pet
- [ ] P!pet shop - Pet food shop
- [ ] (Plus 1 more pet command)

#### Quest Commands (5 commands)
- [ ] P!quests - View quests
- [ ] P!quest - Quest progress
- [ ] P!dquest - Dongtian quests
- [ ] (Plus 2 more quest commands)

#### Artifact Commands (4 commands)
- [ ] P!artifacts - View artifacts
- [ ] P!claim - Claim artifact
- [ ] P!trade - Trade artifacts
- [ ] P!gift - Gift artifacts

#### Potion/Crafting Commands (6 commands)
- [ ] P!brew - Brew potions
- [ ] P!potions - View potions
- [ ] P!ingredients - View ingredients
- [ ] (Plus 3 more crafting commands)

#### Town/Exploration Commands (8 commands)
- [ ] P!town - View current town
- [ ] P!shop - Town shop
- [ ] P!mine - Mining
- [ ] P!dtown - Dongtian towns
- [ ] P!dshop - Dongtian shops
- [ ] P!dbuy - Dongtian purchases
- [ ] (Plus 2 more exploration commands)

#### Admin Commands (15 commands)
- [ ] P!reset - Reset user data
- [ ] P!totalreset - Reset all data
- [ ] P!event - Trigger events
- [ ] P!gift - Gift items to users
- [ ] P!message - Server stats
- [ ] P!log - Developer logs
- [ ] (Plus 9 more admin commands)

#### Utility Commands (12 commands)
- [ ] P!help - Help menu
- [ ] P!translate - Translation
- [ ] P!ping - Bot latency
- [ ] P!uptime - Bot uptime
- [ ] P!donate - Donation info
- [ ] (Plus 7 more utility commands)

#### Message/Event Handlers (10 handlers)
- [ ] on_message - Chi gain from messages
- [ ] on_member_join - Welcome message
- [ ] on_member_remove - Goodbye message
- [ ] on_guild_join - New guild setup
- [ ] on_guild_remove - Guild cleanup
- [ ] (Plus 5 more event handlers)

#### Background Tasks (5 tasks)
- [ ] daily_chi_evaluation - Daily role assignment
- [ ] monthly_quest_reset - Monthly quest refresh
- [ ] database_sync_task - Database sync (ALREADY UPDATED)
- [ ] artifact_spawn_task - Artifact spawning
- [ ] (Plus 1 more background task)

---

## 🧪 Testing Strategy

### Test Cases for Multi-Server Support
1. **Isolation Test**: Join bot to 2+ test servers, verify chi/data is completely separate
2. **PSY Admin Test**: Verify PSY user can use admin commands across all servers
3. **Data Persistence Test**: Restart bot, verify all guilds load data correctly
4. **Leaderboard Test**: Verify leaderboards show only users from current server
5. **Team Test**: Verify teams are server-specific, no cross-server teams
6. **Garden Test**: Verify gardens are isolated per server
7. **Combat Test**: Verify duels/battles don't leak between servers
8. **Event Test**: Trigger events in multiple servers, verify isolation

### Migration Testing
1. **Backup Test**: Verify existing single-server data migrates correctly
2. **Rollback Test**: Ensure rollback capability if migration fails
3. **Performance Test**: Verify bot performance with 5+ guilds

---

## 🎯 Estimated Effort

- **Phase 2 (Data Structures)**: ~4-6 hours
  - Helper functions: 1 hour
  - Data loading refactor: 1 hour
  - Sync functions refactor: 1 hour
  - Background tasks refactor: 1 hour
  - Testing: 2 hours

- **Phase 3 (Commands)**: ~20-30 hours
  - ~200 commands × 5-10 minutes each
  - Systematic category-by-category approach
  - Includes testing each command after update

- **Testing & Bug Fixes**: ~4-6 hours
  - Multi-server integration testing
  - Edge case handling
  - Performance optimization

**Total Estimated Time: 30-40 hours**

---

## 🚀 Deployment Strategy

### Option 1: Big Bang Migration (Risky)
- Complete all phases at once
- Single large PR/update
- Higher risk of bugs
- Faster if successful

### Option 2: Incremental Migration (Recommended)
1. Deploy Phase 2 (data structures) with backward compatibility
2. Test thoroughly with single server
3. Gradually update commands category by category
4. Enable multi-server support after 80%+ commands updated
5. Complete remaining commands
6. Remove backward compatibility code

### Option 3: Feature Flag Approach (Safest)
- Add `MULTI_SERVER_MODE = False` config flag
- Implement both architectures with conditional logic
- Test multi-server mode on test servers
- Flip flag when ready for production
- Remove old code after stable period

---

## 📝 Notes

### Why This Refactor is Necessary
The current architecture uses flat dictionaries that mix data from all Discord servers together. For true multi-server support, each server must have **completely isolated** user data, teams, gardens, and events. This refactor implements proper isolation at both the **database layer** (already done) and **in-memory layer** (Phase 2+3).

### PSY Admin Access
The PSY sentinel system (guild_id=0) ensures user ID 1382187068373074001 maintains admin access across ALL servers without needing to manually grant permissions on each server.

### Backward Compatibility
If you want to maintain single-server optimization, you can add a config flag and keep both architectures. For most use cases, the multi-server architecture has negligible performance impact.
