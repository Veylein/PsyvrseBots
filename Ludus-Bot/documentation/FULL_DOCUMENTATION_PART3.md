# 📦 PART 3: SIMULATION SYSTEMS - COMPLETE DOCUMENTATION

> **Coverage:** Fishing, Farming, Zoo Collection, Mining Adventure
> **Total Lines:** 7,499 lines (fishing.py: 3,472, mining.py: 3,254, farming.py: 773)
> **Completion Status:** ✅ 100% COMPLETE - All files read and documented
> **Last Updated:** 2024

---

## 📑 TABLE OF CONTENTS

1. [Fishing System (3,472 lines)](#1-fishing-system)
   - [Overview & Architecture](#fishing-overview)
   - [UI View Classes](#fishing-ui-classes)
   - [Game Data Structures](#fishing-data)
   - [Commands & Features](#fishing-commands)
   - [Tournament System](#fishing-tournaments)
   
2. [Farming System (773 lines)](#2-farming-system)
   - [Overview & Architecture](#farming-overview)
   - [Crop Management](#farming-crops)
   - [Farm Upgrades](#farming-upgrades)
   - [Commands & Features](#farming-commands)

3. [Zoo Collection System (800 lines)](#3-zoo-system)
   - [Overview & Architecture](#zoo-overview)
   - [Animal Encounters](#zoo-encounters)
   - [Collection Management](#zoo-collection)

4. [Mining Adventure System (3,254 lines)](#4-mining-system)
   - [Overview & Architecture](#mining-overview)
   - [World Generation](#mining-world)
   - [Gameplay Mechanics](#mining-gameplay)
   - [Multiplayer System](#mining-multiplayer)
   - [Developer Mode](#mining-dev)

---

# 1. FISHING SYSTEM

**File:** `cogs/fishing.py` (3,472 lines)  
**Class:** `Fishing(commands.Cog)`

## Fishing Overview

The fishing system is the **largest and most complex simulation game** in Ludus Bot, featuring:

- **Interactive minigames** with real-time button controls
- **9 fishing areas** with progression system
- **50+ fish species** across 6 rarity tiers
- **Kraken boss fight** with 8 attack patterns
- **Tournament system** with automatic and manual modes
- **Equipment progression** (rods, boats, bait)
- **Weather and time multipliers**
- **In-game encyclopedia** with 8 help pages
- **Crafting system** for special bait

---

## Fishing UI Classes

### 1. FishingMinigameView (Lines 110-440)

**Purpose:** Interactive button-based fishing minigame where players align their rod with a moving fish.

**Initialization:**
```python
def __init__(self, cog, user, fish_id, difficulty, rod_id):
    self.cog = cog
    self.user = user
    self.fish_id = fish_id
    self.difficulty = difficulty  # 1-5 stars
    self.rod_id = rod_id
    
    # Calculate rod bonuses
    self.rod_bonuses = {
        "basic_rod": 0.0,
        "sturdy_rod": 0.15,
        "carbon_rod": 0.25,
        "master_rod": 0.35,
        "legendary_rod": 0.45
    }
    
    # Minigame state
    self.rod_position = 5  # Center position (0-10 range)
    self.fish_position = 5
    self.catches = 0
    self.escapes = 0
    
    # Apply rod bonus to difficulty
    bonus = self.rod_bonuses.get(rod_id, 0)
    self.required_catches = max(3, int(difficulty * 3 * (1 - bonus)))
    self.max_escapes = max(2, int(difficulty * 2 * (1 + bonus)))
```

**Key Methods:**

1. **`start_auto_movement(interaction)`** - Starts fish auto-movement task
```python
async def start_auto_movement(self, interaction):
    """Move fish automatically every 2-4 seconds"""
    while not self.is_finished():
        await asyncio.sleep(random.uniform(2, 4))
        
        # Move fish randomly
        direction = random.choice([-1, 1])
        self.fish_position = max(0, min(10, self.fish_position + direction))
        
        # Update display
        await self.update_display(interaction)
```

2. **`check_alignment()`** - Validates rod/fish alignment
```python
def check_alignment(self):
    """Check if rod is EXACTLY aligned with fish"""
    return self.rod_position == self.fish_position
```

3. **`move_left_callback(interaction)`** - Move rod left
```python
async def move_left_callback(self, interaction: discord.Interaction):
    self.rod_position = max(0, self.rod_position - 1)
    await self.update_display(interaction)
```

4. **`reel_callback(interaction)`** - Attempt to catch fish
```python
async def reel_callback(self, interaction: discord.Interaction):
    if self.check_alignment():
        self.catches += 1
        
        # Check if won
        if self.catches >= self.required_catches:
            await self.handle_win(interaction)
        else:
            # Show progress
            await self.update_display(interaction)
    else:
        self.escapes += 1
        
        # Check if lost
        if self.escapes >= self.max_escapes:
            await self.handle_loss(interaction)
        else:
            # Show progress
            await self.update_display(interaction)
```

**Game Flow:**
1. Player starts minigame after fish bites
2. Fish moves automatically every 2-4 seconds
3. Player uses ⬅️ ➡️ to move rod (11 positions: 0-10)
4. Player presses 🎣 when aligned EXACTLY with fish
5. ✅ Perfect alignment → Catch progress (green indicator)
6. ❌ Misalignment → Escape progress (red indicator)
7. Win: Reach `required_catches` before `max_escapes`
8. Lose: Fish escapes after too many misses

**Rod Bonuses:**
- **Basic Rod:** 0% bonus (standard difficulty)
- **Sturdy Rod:** +15% bonus (15% fewer catches needed, 15% more escapes allowed)
- **Carbon Rod:** +25% bonus
- **Master Rod:** +35% bonus
- **Legendary Rod:** +45% bonus (makes hardest fish 45% easier)

**Example Calculations:**
- **Legendary Fish (5 stars) with Basic Rod:**
  - Required catches: 5 × 3 × (1 - 0.0) = 15 catches
  - Max escapes: 5 × 2 × (1 + 0.0) = 10 escapes
  
- **Legendary Fish (5 stars) with Legendary Rod:**
  - Required catches: 5 × 3 × (1 - 0.45) = 8 catches (47% easier!)
  - Max escapes: 5 × 2 × (1 + 0.45) = 15 escapes (50% more forgiving)

---

### 2. KrakenBossFight (Lines 443-850)

**Purpose:** Epic boss fight against the legendary Kraken, featuring turn-based combat with 8 unique attack patterns.

**Initialization:**
```python
class KrakenBossFight(discord.ui.View):
    def __init__(self, cog, user, rod_id):
        super().__init__(timeout=300)  # 5 minute timeout
        self.cog = cog
        self.user = user
        self.rod_id = rod_id
        
        # Combat stats
        self.player_hp = 100
        self.max_player_hp = 100
        self.kraken_hp = 1000
        self.max_kraken_hp = 1000
        
        self.turn = 0
        self.defending = False
        self.last_player_action = None
        
        # Kraken attack patterns (8 unique attacks)
        self.kraken_attacks = [
            {
                "name": "TIDAL WAVE",
                "emoji": "🌊",
                "damage_range": (40, 60),
                "description": "A massive wave crashes down!"
            },
            {
                "name": "WHIRLPOOL",
                "emoji": "🌀",
                "damage_range": (30, 50),
                "description": "You're pulled into a swirling vortex!"
            },
            {
                "name": "LIGHTNING STORM",
                "emoji": "⚡",
                "damage_range": (50, 70),
                "description": "Lightning strikes from above!"
            },
            {
                "name": "TENTACLE SLAM",
                "emoji": "🦑",
                "damage_range": (35, 55),
                "description": "A massive tentacle slams down!"
            },
            {
                "name": "INK CLOUD",
                "emoji": "☁️",
                "damage_range": (20, 40),
                "description": "You're blinded by thick ink!"
            },
            {
                "name": "CRUSHING GRIP",
                "emoji": "✊",
                "damage_range": (45, 65),
                "description": "You're caught in a crushing grip!"
            },
            {
                "name": "ABYSSAL ROAR",
                "emoji": "💀",
                "damage_range": (60, 80),
                "description": "A terrifying roar shakes your soul!"
            },
            {
                "name": "REGENERATION",
                "emoji": "💚",
                "damage_range": (-50, -30),  # Negative = healing
                "description": "The Kraken regenerates health!"
            }
        ]
```

**Combat Actions:**

1. **Heavy Strike** - High damage, high risk
```python
@discord.ui.button(emoji="⚔️", label="Heavy Strike", style=discord.ButtonStyle.danger)
async def heavy_strike(self, interaction: discord.Interaction, button: discord.ui.Button):
    if interaction.user != self.user:
        await interaction.response.send_message("❌ Not your fight!", ephemeral=True)
        return
    
    damage = random.randint(80, 120)
    self.kraken_hp -= damage
    self.last_player_action = f"⚔️ You dealt {damage} damage with Heavy Strike!"
    
    await self.process_turn(interaction)
```

2. **Quick Strike** - Moderate damage, safer
```python
@discord.ui.button(emoji="🎯", label="Quick Strike", style=discord.ButtonStyle.primary)
async def quick_strike(self, interaction: discord.Interaction, button: discord.ui.Button):
    damage = random.randint(40, 70)
    self.kraken_hp -= damage
    self.last_player_action = f"🎯 You dealt {damage} damage with Quick Strike!"
    
    await self.process_turn(interaction)
```

3. **Defend** - Reduce incoming damage by 50%
```python
@discord.ui.button(emoji="🛡️", label="Defend", style=discord.ButtonStyle.secondary)
async def defend(self, interaction: discord.Interaction, button: discord.ui.Button):
    self.defending = True
    self.last_player_action = "🛡️ You brace for impact!"
    
    await self.process_turn(interaction)
```

4. **Heal** - Restore 25-40 HP (vulnerable to attack)
```python
@discord.ui.button(emoji="❤️", label="Heal", style=discord.ButtonStyle.success)
async def heal(self, interaction: discord.Interaction, button: discord.ui.Button):
    heal_amount = random.randint(25, 40)
    self.player_hp = min(self.max_player_hp, self.player_hp + heal_amount)
    self.last_player_action = f"❤️ You restored {heal_amount} HP!"
    
    await self.process_turn(interaction)
```

**Kraken AI:**
```python
async def kraken_turn(self):
    """Execute Kraken's attack"""
    attack = random.choice(self.kraken_attacks)
    
    if "REGENERATION" in attack["name"]:
        # Kraken heals
        heal = random.randint(30, 50)
        self.kraken_hp = min(self.max_kraken_hp, self.kraken_hp + heal)
        return f"{attack['emoji']} **{attack['name']}** - {attack['description']}\n" \
               f"💚 The Kraken healed {heal} HP!"
    else:
        # Kraken attacks player
        damage = random.randint(*attack["damage_range"])
        
        # Apply defense reduction
        if self.defending:
            damage = int(damage * 0.5)
            self.defending = False
        
        self.player_hp -= damage
        return f"{attack['emoji']} **{attack['name']}** - {attack['description']}\n" \
               f"💔 You took {damage} damage!"
```

**Victory Rewards:**
```python
async def handle_victory(self, interaction):
    """Player defeats Kraken"""
    # Add Kraken to fish collection
    user_data = self.cog.get_user_data(self.user.id)
    if "kraken" not in user_data["fish_caught"]:
        user_data["fish_caught"]["kraken"] = {"count": 1, "biggest": 1500}
        user_data["total_catches"] += 1
    
    # Award 5,000-10,000 coins
    reward = random.randint(5000, 10000)
    economy_cog = self.cog.bot.get_cog("Economy")
    if economy_cog:
        economy_cog.add_coins(self.user.id, reward, "kraken_boss")
    
    # Award achievement
    if "kraken_slayer" not in user_data.get("achievements", []):
        user_data["achievements"].append("kraken_slayer")
    
    # Save data
    self.cog.save_fishing_data()
    
    # Display victory embed
    embed = discord.Embed(
        title="🏆 VICTORY!",
        description=f"**You have defeated THE KRAKEN!**\n\n"
                   f"🦑 **THE KRAKEN** added to your collection!\n"
                   f"💰 Earned **{reward} PsyCoins**!\n"
                   f"🏆 Achievement Unlocked: **Kraken Slayer**!\n\n"
                   f"*Legends will be told of your bravery...*",
        color=discord.Color.gold()
    )
    
    await interaction.edit_original_response(embed=embed, view=None)
```

---

### 3. EncyclopediaView (Lines 24-98, 885-1013)

**Purpose:** Paginated fish encyclopedia with rarity filtering.

**Features:**
- **50+ fish species** displayed in pages
- **Rarity filters:** All, Common, Uncommon, Rare, Epic, Legendary, Mythic, BOSS
- **Pagination buttons:** First, Previous, Next, Last
- **Detailed stats:** Name, rarity, value, weight range, catch chance

**Initialization:**
```python
class EncyclopediaView(discord.ui.View):
    def __init__(self, cog, fish_list, rarity_filter=None):
        super().__init__(timeout=180)
        self.cog = cog
        self.fish_list = fish_list  # List of (fish_id, fish_data) tuples
        self.current_page = 0
        self.fish_per_page = 6
        self.rarity_filter = rarity_filter
        
        # Rarity emoji mapping
        self.rarity_emojis = {
            "Common": "⚪",
            "Uncommon": "🟢",
            "Rare": "🔵",
            "Epic": "🟣",
            "Legendary": "🟠",
            "Mythic": "🔴",
            "BOSS": "💀"
        }
```

**Page Generation:**
```python
def get_embed(self):
    """Generate current page embed"""
    start = self.current_page * self.fish_per_page
    end = start + self.fish_per_page
    page_fish = self.fish_list[start:end]
    
    embed = discord.Embed(
        title="📖 Fish Encyclopedia",
        description=f"**Filter:** {self.rarity_filter or 'All Species'}\n"
                   f"**Page {self.current_page + 1}/{self.total_pages()}**\n"
                   f"**Total Species:** {len(self.fish_list)}\n",
        color=discord.Color.blue()
    )
    
    for fish_id, fish in page_fish:
        rarity_emoji = self.rarity_emojis.get(fish["rarity"], "⚪")
        weight_range = f"{fish['weight'][0]}-{fish['weight'][1]}kg"
        
        embed.add_field(
            name=f"{rarity_emoji} {fish['name']}",
            value=f"**Rarity:** {fish['rarity']}\n"
                  f"**Value:** {fish['value']} coins\n"
                  f"**Weight:** {weight_range}\n"
                  f"**Catch Rate:** {fish['chance']}%",
            inline=True
        )
    
    return embed
```

**Rarity Filter Dropdown:**
```python
@discord.ui.select(
    placeholder="Filter by rarity...",
    options=[
        discord.SelectOption(label="All Fish", value="all", emoji="🐟"),
        discord.SelectOption(label="Common", value="common", emoji="⚪"),
        discord.SelectOption(label="Uncommon", value="uncommon", emoji="🟢"),
        discord.SelectOption(label="Rare", value="rare", emoji="🔵"),
        discord.SelectOption(label="Epic", value="epic", emoji="🟣"),
        discord.SelectOption(label="Legendary", value="legendary", emoji="🟠"),
        discord.SelectOption(label="Mythic", value="mythic", emoji="🔴"),
        discord.SelectOption(label="BOSS", value="boss", emoji="💀")
    ]
)
async def rarity_select(self, interaction: discord.Interaction, select: discord.ui.Select):
    """Filter fish by rarity"""
    selected = select.values[0]
    
    if selected == "all":
        self.fish_list = self.cog.get_all_fish()
    else:
        all_fish = self.cog.get_all_fish()
        self.fish_list = [
            (fid, f) for fid, f in all_fish 
            if f["rarity"].lower() == selected.lower()
        ]
    
    self.current_page = 0
    await interaction.response.edit_message(embed=self.get_embed(), view=self)
```

---

### 4. ShopSelectView (Lines 1015-1200)

**Purpose:** 3-dropdown shop interface for purchasing rods, boats, and bait.

**Initialization:**
```python
class ShopSelectView(discord.ui.View):
    def __init__(self, cog, user_data):
        super().__init__(timeout=180)
        self.cog = cog
        self.user_data = user_data
        
        # Create 3 separate dropdowns
        self.add_item(self.create_rod_dropdown())
        self.add_item(self.create_boat_dropdown())
        self.add_item(self.create_bait_dropdown())
```

**Rod Shop Dropdown:**
```python
def create_rod_dropdown(self):
    """Create rod purchase dropdown"""
    options = []
    
    for rod_id, rod in self.cog.rods.items():
        # Check if already owned
        owned = rod_id == self.user_data["rod"]
        
        options.append(discord.SelectOption(
            label=rod["name"],
            value=rod_id,
            description=f"{rod['cost']} coins - {rod['description']}",
            emoji="✅" if owned else "🎣"
        ))
    
    select = discord.ui.Select(
        placeholder="Purchase a fishing rod...",
        options=options,
        row=0
    )
    select.callback = self.rod_callback
    return select

async def rod_callback(self, interaction: discord.Interaction):
    """Handle rod purchase"""
    rod_id = interaction.data['values'][0]
    rod = self.cog.rods[rod_id]
    
    # Check if already owned
    if rod_id == self.user_data["rod"]:
        await interaction.response.send_message(
            f"❌ You already have the {rod['name']}!",
            ephemeral=True
        )
        return
    
    # Check balance
    economy_cog = self.cog.bot.get_cog("Economy")
    balance = economy_cog.get_balance(interaction.user.id)
    
    if balance < rod["cost"]:
        await interaction.response.send_message(
            f"❌ Not enough coins! Need {rod['cost']}, have {balance}.",
            ephemeral=True
        )
        return
    
    # Purchase
    economy_cog.remove_coins(interaction.user.id, rod["cost"])
    self.user_data["rod"] = rod_id
    self.cog.save_fishing_data()
    
    # Confirmation
    embed = discord.Embed(
        title="✅ Purchase Successful!",
        description=f"You bought **{rod['name']}** for {rod['cost']} coins!\n\n"
                   f"**Catch Bonus:** +{rod['catch_bonus']}%\n"
                   f"**Rare Bonus:** +{rod['rare_bonus']}%",
        color=discord.Color.green()
    )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)
    
    # Refresh shop display after 3 seconds
    await asyncio.sleep(3)
    await self.refresh_shop(interaction)
```

**Rod Prices:**
- Basic Rod: **FREE** (starter)
- Carbon Fiber Rod: **1,000 coins**
- Professional Rod: **5,000 coins**
- Master Angler Rod: **15,000 coins**
- Poseidon's Trident (Legendary): **50,000 coins**

**Boat Prices:**
- On Foot: **FREE** (starter, pond/river only)
- Canoe: **2,000 coins** (unlocks Lake)
- Motorboat: **10,000 coins** (unlocks Ocean, Tropical)
- Luxury Yacht: **50,000 coins** (unlocks Arctic, Reef)
- Research Submarine: **250,000 coins** (unlocks Abyss, Mariana Trench)

**Bait Prices:**
- Worm: **10 coins** (3 uses, +5% catch, common fish)
- Cricket: **25 coins** (3 uses, +10% catch, +5% rare)
- Minnow: **50 coins** (2 uses, +20% catch, +10% rare)
- Squid: **100 coins** (2 uses, +35% catch, +20% rare)
- Golden Lure: **500 coins** (1 use, +75% catch, +50% rare, legendary bait)
- Kraken Bait: **Cannot buy** (craft from 8 Kraken Tentacles)

---

### 5. AreaSelectView (Lines 1200-1450)

**Purpose:** Area travel system with boat requirement validation and unlock costs.

**9 Fishing Areas:**

1. **🌿 Peaceful Pond** (FREE, On Foot)
   - Unlock: Free (starter area)
   - Fish: Common Fish, Minnow, Carp, Tadpole, Lily Pad
   - Description: "A calm pond perfect for beginners"

2. **🌊 Flowing River** (FREE, On Foot)
   - Unlock: Free (starter area)
   - Fish: Trout, Salmon, Bass, Catfish, River Stone
   - Description: "Fast-moving water with active fish"

3. **🏞️ Crystal Lake** (500 coins, Canoe required)
   - Fish: Pike, Walleye, Perch, Sturgeon, Water Lily
   - Description: "Deep freshwater with variety"

4. **🌊 Open Ocean** (2,500 coins, Motorboat required)
   - Fish: Tuna, Swordfish, Marlin, Mackerel, Seaweed
   - Description: "Vast saltwater adventure"

5. **🏝️ Tropical Paradise** (5,000 coins, Motorboat required)
   - Fish: Clownfish, Angelfish, Butterflyfish, Parrotfish, Coral
   - Description: "Exotic fish and warm waters"

6. **❄️ Arctic Waters** (10,000 coins, Yacht required)
   - Fish: Arctic Char, Halibut, Seal, Penguin, Ice Crystal
   - Description: "Frozen seas with rare creatures"

7. **🪸 Coral Reef** (15,000 coins, Yacht required)
   - Fish: Seahorse, Lionfish, Moray Eel, Octopus, Pearl
   - Description: "Colorful underwater paradise"

8. **🌑 Dark Abyss** (50,000 coins, Submarine required)
   - Fish: Anglerfish, Giant Squid, Gulper Eel, Vampire Squid, Black Pearl
   - Description: "The deepest, most mysterious waters"

9. **🕳️ Mariana Trench** (100,000 coins, Submarine required)
   - Fish: Ancient Coelacanth, Megalodon Tooth, Kraken Tentacle, Atlantis Relic, Cosmic Jellyfish
   - Description: "The ultimate fishing challenge"
   - Special: Only place to summon Kraken boss

**Area Selection Logic:**
```python
async def area_callback(self, interaction: discord.Interaction):
    """Handle area travel/unlock"""
    area_id = interaction.data['values'][0]
    area = self.cog.areas[area_id]
    
    # Check boat requirements FIRST
    required_boat = area.get("required_boat", "none")
    current_boat = self.user_data.get("boat", "none")
    current_boat_data = self.cog.boats.get(current_boat, {})
    allowed_areas = current_boat_data.get("areas", [])
    
    if area_id not in allowed_areas:
        req_boat_data = self.cog.boats.get(required_boat, {})
        await interaction.response.send_message(
            f"❌ **Boat Requirement Not Met!**\n\n"
            f"📍 **{area['name']}** requires **{req_boat_data['name']}**\n"
            f"🛶 You currently have: **{current_boat_data['name']}**\n\n"
            f"💰 **{req_boat_data['name']}** costs: {req_boat_data['cost']:,} coins\n"
            f"🏪 Purchase from `/fish shop`!",
            ephemeral=True
        )
        return
    
    # Check if area is unlocked
    unlocked = area_id in self.user_data["unlocked_areas"]
    
    if not unlocked:
        # Show unlock confirmation
        unlock_cost = area.get("unlock_cost", 0)
        
        if unlock_cost > 0:
            economy_cog = self.cog.bot.get_cog("Economy")
            balance = economy_cog.get_balance(interaction.user.id)
            
            if balance < unlock_cost:
                await interaction.response.send_message(
                    f"❌ Not enough coins to unlock {area['name']}!\n"
                    f"Need {unlock_cost:,}, have {balance:,}.",
                    ephemeral=True
                )
                return
            
            # Deduct and unlock
            economy_cog.remove_coins(interaction.user.id, unlock_cost)
            self.user_data["unlocked_areas"].append(area_id)
            self.cog.save_fishing_data()
            
            await interaction.response.send_message(
                f"🗺️ **Unlocked {area['name']}!**\n"
                f"Paid {unlock_cost:,} coins.",
                ephemeral=True
            )
    
    # Travel to area
    self.user_data["current_area"] = area_id
    self.cog.save_fishing_data()
    
    await interaction.response.send_message(
        f"📍 Traveled to **{area['name']}**!\n"
        f"{area['description']}\n\n"
        f"Ready to fish with `/fish cast`!",
        ephemeral=True
    )
```

---

### 6. DetailedInventoryView (Lines 1450-1800)

**Purpose:** Paginated fish collection with statistics and equipment display.

**Display Sections:**

1. **Overall Statistics**
```python
embed = discord.Embed(
    title=f"🎒 {user.display_name}'s Fishing Inventory",
    description=f"**Total Catches:** {user_data['total_catches']}\n"
               f"**Total Value:** {user_data['total_value']:,} coins\n"
               f"**Species Collected:** {len(user_data['fish_caught'])}/50",
    color=discord.Color.blue()
)
```

2. **Equipment Section**
```python
embed.add_field(
    name="🎣 Current Equipment",
    value=f"**Rod:** {self.cog.rods[user_data['rod']]['name']}\n"
          f"**Boat:** {self.cog.boats[user_data['boat']]['name']}\n"
          f"**Area:** {self.cog.areas[user_data['current_area']]['name']}",
    inline=False
)
```

3. **Bait Inventory**
```python
bait_text = ""
for bait_id, count in user_data.get("bait_inventory", {}).items():
    bait = self.cog.baits[bait_id]
    bait_text += f"{bait['name']}: **{count}x**\n"

embed.add_field(
    name="🪱 Bait Inventory",
    value=bait_text or "No bait",
    inline=False
)
```

4. **Fish Collection (Paginated, 8 per page)**
```python
start = self.current_page * 8
end = start + 8
page_fish = list(user_data["fish_caught"].items())[start:end]

fish_text = ""
for fish_id, data in page_fish:
    fish = self.cog.fish_types[fish_id]
    
    # Handle old data format
    if isinstance(data, int):
        count = data
        biggest = 0
    elif isinstance(data, dict):
        count = data.get("count", 1)
        biggest = data.get("biggest", 0)
    
    rarity_emoji = {
        "Common": "⚪",
        "Uncommon": "🟢",
        "Rare": "🔵",
        "Epic": "🟣",
        "Legendary": "🟠",
        "Mythic": "🔴",
        "BOSS": "💀"
    }[fish["rarity"]]
    
    fish_text += f"{rarity_emoji} **{fish['name']}** - {count}x caught (Biggest: {biggest}kg)\n"

embed.add_field(
    name=f"🐟 Fish Collection (Page {self.current_page + 1}/{total_pages})",
    value=fish_text,
    inline=False
)
```

**Navigation Buttons:**
- **⏮️ First Page** - Jump to page 1
- **◀️ Previous** - Go back one page
- **▶️ Next** - Advance one page
- **⏭️ Last Page** - Jump to final page
- **⚙️ Equipment** - Open equipment change menu

---

### 7. InventoryEquipView (Lines 1750-1850)

**Purpose:** Switch rods and boats from owned items.

**Equipment Selection:**
```python
class InventoryEquipView(discord.ui.View):
    def __init__(self, cog, user_data):
        super().__init__(timeout=120)
        self.cog = cog
        self.user_data = user_data
        
        # Rod dropdown (only owned rods)
        rod_options = []
        for rod_id, rod in self.cog.rods.items():
            if rod_id == user_data["rod"] or rod["cost"] == 0:
                rod_options.append(discord.SelectOption(
                    label=rod["name"],
                    value=rod_id,
                    description=f"Catch: +{rod['catch_bonus']}%",
                    emoji="✅" if rod_id == user_data["rod"] else "🎣"
                ))
        
        # Boat dropdown (only owned boats)
        boat_options = []
        for boat_id, boat in self.cog.boats.items():
            if boat_id == user_data["boat"] or boat["cost"] == 0:
                boat_options.append(discord.SelectOption(
                    label=boat["name"],
                    value=boat_id,
                    description=boat["description"],
                    emoji="✅" if boat_id == user_data["boat"] else "🛶"
                ))

async def rod_change_callback(self, interaction: discord.Interaction):
    """Switch active rod"""
    new_rod_id = interaction.data['values'][0]
    old_rod = self.cog.rods[self.user_data["rod"]]["name"]
    new_rod = self.cog.rods[new_rod_id]["name"]
    
    self.user_data["rod"] = new_rod_id
    self.cog.save_fishing_data()
    
    await interaction.response.send_message(
        f"🎣 Switched from **{old_rod}** to **{new_rod}**!",
        ephemeral=True
    )
```

---

### 8. FishingHelpView (Lines 1850-2100)

**Purpose:** 8-page in-game help system covering all fishing features.

**Page 1: Main Commands**
```python
page0 = discord.Embed(
    title="📖 Fishing Help - Commands",
    description="Welcome to the **Ultimate Fishing Simulator**!\n"
               "An interactive minigame with equipment, areas, and more!\n",
    color=discord.Color.blue()
)
page0.add_field(
    name="🎣 Main Commands",
    value="`/fish cast` - Cast your line (start minigame)\n"
         "`/fish inventory` - View your fish collection\n"
         "`/fish shop` - Purchase equipment & bait\n"
         "`/fish craft` - Craft special items (Kraken Bait)\n"
         "`/fish areas` - View locations & travel\n"
         "`/fish encyclopedia` - See all fish types\n"
         "`/fish stats` - View your statistics\n"
         "`/fishhelp` - This help menu",
    inline=False
)
```

**Page 2: Minigame Controls**
```python
page1.add_field(
    name="🎮 How to Play",
    value="1. **Cast** - Use `/fish cast` to start\n"
         "2. **Wait** - Fish will bite after 2-3 seconds\n"
         "3. **Minigame** - Interactive button controls:\n"
         "   • Use ⬅️ ➡️ to move your rod (11 positions)\n"
         "   • Align EXACTLY with the fish (must be 🟢)\n"
         "   • Press 🎣 to reel in when perfectly aligned\n"
         "   • Fish moves automatically - timing is key!\n"
         "4. **Success** - Reach required catches before max escapes\n"
         "5. **Rewards** - Earn coins, XP, and add to collection!",
    inline=False
)
```

**Page 3: Fishing Rods**
```python
page2.add_field(
    name="🎣 Fishing Rods",
    value="**Basic Rod** - FREE starter rod\n"
         "• Catch: +0%, Rare: +0%\n\n"
         "**Carbon Fiber Rod** - 1,000 coins\n"
         "• Catch: +10%, Rare: +5%\n\n"
         "**Professional Rod** - 5,000 coins\n"
         "• Catch: +25%, Rare: +15%\n\n"
         "**Master Angler Rod** - 15,000 coins\n"
         "• Catch: +50%, Rare: +30%\n\n"
         "**Poseidon's Trident** - 50,000 coins\n"
         "• Catch: +100%, Rare: +60% (LEGENDARY!)",
    inline=False
)
```

**Page 4: Rod Bonuses (Minigame Difficulty)**
```python
page3.add_field(
    name="📈 Rod Minigame Bonuses",
    value="Better rods make minigames EASIER!\n\n"
         "**Basic Rod:** 0% bonus (standard difficulty)\n"
         "**Sturdy Rod:** +15% bonus (15% easier)\n"
         "**Carbon Rod:** +25% bonus (25% easier)\n"
         "**Master Rod:** +35% bonus (35% easier)\n"
         "**Legendary Rod:** +45% bonus (45% easier)\n\n"
         "**Effects:**\n"
         "• Fewer catches needed to succeed\n"
         "• More escapes allowed before failure\n"
         "• Fish moves slightly slower\n\n"
         "*Example: Legendary fish with Basic Rod requires 15 catches.\n"
         "With Legendary Rod, only 8 catches needed!*",
    inline=False
)
```

**Page 5: Bait & Boats**
```python
page4.add_field(
    name="🪱 Bait Types",
    value="**Worm** - 10 coins (3 uses, +5% catch)\n"
         "**Cricket** - 25 coins (3 uses, +10% catch, +5% rare)\n"
         "**Minnow** - 50 coins (2 uses, +20% catch, +10% rare)\n"
         "**Squid** - 100 coins (2 uses, +35% catch, +20% rare)\n"
         "**Golden Lure** - 500 coins (1 use, +75% catch, +50% rare)\n"
         "**Kraken Bait** - CRAFT ONLY (summons Kraken boss)",
    inline=False
)

page4.add_field(
    name="🛶 Boats",
    value="**On Foot** - FREE (Pond, River)\n"
         "**Canoe** - 2,000 coins (+ Lake)\n"
         "**Motorboat** - 10,000 coins (+ Ocean, Tropical)\n"
         "**Yacht** - 50,000 coins (+ Arctic, Reef)\n"
         "**Submarine** - 250,000 coins (+ Abyss, Trench)",
    inline=False
)
```

**Page 6: Fishing Areas**
```python
page5.add_field(
    name="🗺️ All Fishing Areas",
    value="1. **🌿 Peaceful Pond** - FREE (Common fish)\n"
         "2. **🌊 Flowing River** - FREE (Uncommon fish)\n"
         "3. **🏞️ Crystal Lake** - 500 coins (Rare fish)\n"
         "4. **🌊 Open Ocean** - 2,500 coins (Epic fish)\n"
         "5. **🏝️ Tropical Paradise** - 5,000 coins (Exotic fish)\n"
         "6. **❄️ Arctic Waters** - 10,000 coins (Arctic creatures)\n"
         "7. **🪸 Coral Reef** - 15,000 coins (Reef species)\n"
         "8. **🌑 Dark Abyss** - 50,000 coins (Deep sea horrors)\n"
         "9. **🕳️ Mariana Trench** - 100,000 coins (Mythic fish)\n\n"
         "*Each area requires specific boat to access!*",
    inline=False
)
```

**Page 7: Tournaments & Advanced**
```python
page6.add_field(
    name="🏆 Tournament Types",
    value="**Biggest Fish** - Heaviest catch wins\n"
         "**Most Fish** - Highest quantity wins\n"
         "**Rarest Fish** - Highest rarity wins\n\n"
         "**Frequency:** 6-12 hour intervals\n"
         "**Spawn Chance:** 10% (VERY RARE!)\n"
         "**Prizes:** 1st: 1000, 2nd: 500, 3rd: 250 coins",
    inline=False
)

page6.add_field(
    name="🌤️ Weather & Time Effects",
    value="**Weather Multipliers:**\n"
         "• ☀️ Sunny: 1.0x (normal)\n"
         "• ☁️ Cloudy: 1.2x (more active)\n"
         "• 🌧️ Rainy: 1.5x (best conditions!)\n"
         "• ⛈️ Stormy: 0.5x (dangerous)\n"
         "• 🌫️ Foggy: 1.3x (mysterious)\n\n"
         "**Time Multipliers:**\n"
         "• 🌅 Dawn: 1.4x (5-7 AM)\n"
         "• 🌇 Dusk: 1.4x (6-8 PM)\n"
         "• 🌙 Night: 1.2x (9 PM-4 AM)\n"
         "• 🌞 Noon: 0.8x (12-2 PM)",
    inline=False
)
```

**Page 8: Kraken Boss**
```python
page7.add_field(
    name="🦑 The Kraken Boss",
    value="**How to Summon:**\n"
         "1. Catch 8x Kraken Tentacles (Mariana Trench)\n"
         "2. Craft Kraken Bait at `/fish craft`\n"
         "3. Travel to 🕳️ Mariana Trench\n"
         "4. Use `/fish cast` and select Kraken Bait\n\n"
         "**Boss Stats:**\n"
         "• 1000 HP (extremely durable)\n"
         "• 8 unique attack patterns\n"
         "• Devastating damage (20-80 per attack)\n"
         "• Can regenerate health\n"
         "• 5 minute time limit",
    inline=False
)

page7.add_field(
    name="⚔️ Combat System",
    value="**⚔️ Heavy Strike** - High damage, high risk (80-120 dmg)\n"
         "**🎯 Quick Strike** - Moderate damage, safer (40-70 dmg)\n"
         "**🛡️ Defend** - Reduce damage taken by 50%\n"
         "**❤️ Heal** - Restore 25-40 HP (vulnerable!)\n\n"
         "⚠️ The Kraken has 1000 HP and devastating attacks!",
    inline=False
)

page7.add_field(
    name="🏆 Rewards",
    value="**Victory:**\n"
         "• 🦑 THE KRAKEN added to collection\n"
         "• 💰 5,000-10,000 PsyCoins\n"
         "• 🏆 Achievement: Kraken Slayer\n"
         "• Eternal glory!\n\n"
         "*Only the strongest will prevail...*",
    inline=False
)
```

---

## Fishing Data

### Complete Fish Database (50 Species)

**File Location:** `cogs/fishing.py` Lines 2383-2460

#### Common Tier (5 species, Pond/River)
```python
"common_fish": {
    "name": "🐟 Common Fish",
    "rarity": "Common",
    "value": 10,
    "weight": [0.5, 2],
    "chance": 40
}

"minnow": {
    "name": "🐠 Minnow",
    "rarity": "Common",
    "value": 8,
    "weight": [0.1, 0.5],
    "chance": 35
}

"carp": {
    "name": "🐡 Carp",
    "rarity": "Common",
    "value": 15,
    "weight": [2, 8],
    "chance": 30
}

"tadpole": {
    "name": "🎣 Tadpole",
    "rarity": "Common",
    "value": 5,
    "weight": [0.05, 0.2],
    "chance": 25
}

"lily_pad": {
    "name": "🌸 Lily Pad",
    "rarity": "Common",
    "value": 3,
    "weight": [0.1, 0.3],
    "chance": 20
}
```

#### Uncommon Tier (5 species, River/Lake)
```python
"trout": {
    "name": "🐟 Trout",
    "rarity": "Uncommon",
    "value": 35,
    "weight": [1, 5],
    "chance": 25
}

"salmon": {
    "name": "🐟 Salmon",
    "rarity": "Uncommon",
    "value": 45,
    "weight": [3, 12],
    "chance": 20
}

"bass": {
    "name": "🐟 Bass",
    "rarity": "Uncommon",
    "value": 40,
    "weight": [2, 8],
    "chance": 22
}

"perch": {
    "name": "🐟 Perch",
    "rarity": "Uncommon",
    "value": 35,
    "weight": [0.5, 3],
    "chance": 20
}

"mackerel": {
    "name": "🐟 Mackerel",
    "rarity": "Uncommon",
    "value": 50,
    "weight": [1, 5],
    "chance": 18
}
```

#### Rare Tier (10 species, Lake/Ocean/Tropical/Arctic)
```python
"catfish": {
    "name": "🐟 Catfish",
    "rarity": "Rare",
    "value": 65,
    "weight": [5, 25],
    "chance": 12
}

"pike": {
    "name": "🐟 Pike",
    "rarity": "Rare",
    "value": 75,
    "weight": [3, 15],
    "chance": 15
}

"walleye": {
    "name": "🐟 Walleye",
    "rarity": "Rare",
    "value": 70,
    "weight": [2, 10],
    "chance": 14
}

"tuna": {
    "name": "🐟 Tuna",
    "rarity": "Rare",
    "value": 100,
    "weight": [10, 50],
    "chance": 12
}

"angelfish": {
    "name": "😇 Angelfish",
    "rarity": "Rare",
    "value": 90,
    "weight": [0.5, 2],
    "chance": 15
}

"butterflyfish": {
    "name": "🦋 Butterflyfish",
    "rarity": "Rare",
    "value": 85,
    "weight": [0.3, 1.5],
    "chance": 14
}

"parrotfish": {
    "name": "🦜 Parrotfish",
    "rarity": "Rare",
    "value": 95,
    "weight": [2, 10],
    "chance": 12
}

"arctic_char": {
    "name": "🐟 Arctic Char",
    "rarity": "Rare",
    "value": 110,
    "weight": [2, 8],
    "chance": 15
}

"halibut": {
    "name": "🐟 Halibut",
    "rarity": "Rare",
    "value": 120,
    "weight": [10, 80],
    "chance": 12
}

"seahorse": {
    "name": "🦑 Seahorse",
    "rarity": "Rare",
    "value": 130,
    "weight": [0.1, 0.5],
    "chance": 14
}
```

#### Epic Tier (10 species, Ocean/Tropical/Arctic/Reef)
```python
"sturgeon": {
    "name": "🐟 Sturgeon",
    "rarity": "Epic",
    "value": 200,
    "weight": [20, 100],
    "chance": 5
}

"swordfish": {
    "name": "🗡️ Swordfish",
    "rarity": "Epic",
    "value": 250,
    "weight": [50, 200],
    "chance": 6
}

"marlin": {
    "name": "🐟 Marlin",
    "rarity": "Epic",
    "value": 300,
    "weight": [100, 500],
    "chance": 5
}

"seal": {
    "name": "🦭 Seal",
    "rarity": "Epic",
    "value": 350,
    "weight": [50, 200],
    "chance": 5
}

"penguin": {
    "name": "🐧 Penguin",
    "rarity": "Epic",
    "value": 400,
    "weight": [20, 40],
    "chance": 4
}

"lionfish": {
    "name": "🦁 Lionfish",
    "rarity": "Epic",
    "value": 280,
    "weight": [0.5, 3],
    "chance": 7
}

"moray_eel": {
    "name": "🐍 Moray Eel",
    "rarity": "Epic",
    "value": 320,
    "weight": [5, 30],
    "chance": 6
}

"octopus": {
    "name": "🐙 Octopus",
    "rarity": "Epic",
    "value": 300,
    "weight": [3, 15],
    "chance": 8
}

"pearl": {
    "name": "📿 Pearl",
    "rarity": "Epic",
    "value": 500,
    "weight": [0.05, 0.2],
    "chance": 3
}

"ice_crystal": {
    "name": "💎 Ice Crystal",
    "rarity": "Epic",
    "value": 150,
    "weight": [0.1, 1],
    "chance": 10
}
```

#### Legendary Tier (5 species, Abyss)
```python
"anglerfish": {
    "name": "🎣 Anglerfish",
    "rarity": "Legendary",
    "value": 800,
    "weight": [5, 50],
    "chance": 8
}

"giant_squid": {
    "name": "🦑 Giant Squid",
    "rarity": "Legendary",
    "value": 1000,
    "weight": [100, 500],
    "chance": 5
}

"gulper_eel": {
    "name": "🐍 Gulper Eel",
    "rarity": "Legendary",
    "value": 900,
    "weight": [2, 15],
    "chance": 6
}

"vampire_squid": {
    "name": "🦇 Vampire Squid",
    "rarity": "Legendary",
    "value": 850,
    "weight": [1, 10],
    "chance": 7
}

"black_pearl": {
    "name": "⚫ Black Pearl",
    "rarity": "Legendary",
    "value": 2000,
    "weight": [0.1, 0.5],
    "chance": 2
}
```

#### Mythic Tier (5 species, Mariana Trench)
```python
"ancient_coelacanth": {
    "name": "🐠 Ancient Coelacanth",
    "rarity": "Mythic",
    "value": 5000,
    "weight": [50, 200],
    "chance": 5
}

"megalodon_tooth": {
    "name": "🦷 Megalodon Tooth",
    "rarity": "Mythic",
    "value": 8000,
    "weight": [10, 30],
    "chance": 3
}

"kraken_tentacle": {
    "name": "🦑 Kraken Tentacle",
    "rarity": "Mythic",
    "value": 10000,
    "weight": [100, 500],
    "chance": 2
}

"atlantis_relic": {
    "name": "🏺 Atlantis Relic",
    "rarity": "Mythic",
    "value": 15000,
    "weight": [5, 20],
    "chance": 1.5
}

"cosmic_jellyfish": {
    "name": "🌌 Cosmic Jellyfish",
    "rarity": "Mythic",
    "value": 25000,
    "weight": [0.5, 5],
    "chance": 0.5
}
```

#### BOSS Tier (1 species, Kraken Fight Only)
```python
"kraken": {
    "name": "🦑 THE KRAKEN",
    "rarity": "BOSS",
    "value": 50000,
    "weight": [1000, 2000],
    "chance": 0  # Cannot be caught normally
}
```

---

## Fishing Commands

### 1. `/fish` - Main Fishing Command

**Location:** Lines 2595-2650

**Choices:**
- `menu` - Show main fishing menu
- `cast` - Cast fishing line (start minigame)
- `inventory` - View fish collection
- `shop` - Purchase equipment & bait
- `craft` - Craft special items (Kraken Bait)
- `areas` - View and travel to fishing locations
- `encyclopedia` - Browse all fish species
- `stats` - View fishing statistics

**Implementation:**
```python
@app_commands.command(name="fish", description="🎣 Advanced Fishing Simulator")
@app_commands.describe(action="What would you like to do?")
@app_commands.choices(action=[
    app_commands.Choice(name="🏠 Main Menu", value="menu"),
    app_commands.Choice(name="🎣 Cast Line", value="cast"),
    app_commands.Choice(name="🎒 Inventory", value="inventory"),
    app_commands.Choice(name="🏪 Shop", value="shop"),
    app_commands.Choice(name="🔨 Craft", value="craft"),
    app_commands.Choice(name="🗺️ Areas", value="areas"),
    app_commands.Choice(name="📖 Encyclopedia", value="encyclopedia"),
    app_commands.Choice(name="📊 Stats", value="stats"),
])
async def fish_main(self, interaction: discord.Interaction, action: Optional[str] = "menu"):
    """Main fishing command dispatcher"""
    if action == "cast":
        # Check for bait selection
        user_data = self.get_user_data(interaction.user.id)
        bait_inventory = user_data.get("bait_inventory", {})
        has_bait = bool(bait_inventory) and any(count > 0 for count in bait_inventory.values())
        
        if has_bait:
            # Show bait selection menu
            view = BaitSelectView(self, user_data, interaction)
            await interaction.response.send_message(embed=bait_embed, view=view)
        else:
            # Cast directly without bait
            await self.cast_action(interaction, None)
    
    elif action == "inventory":
        await self.fish_inventory_action(interaction)
    
    elif action == "shop":
        await self.fish_shop_action(interaction)
    
    elif action == "craft":
        await self.fish_craft_action(interaction)
    
    elif action == "areas":
        await self.fish_areas_action(interaction)
    
    elif action == "encyclopedia":
        await self.fish_encyclopedia_action(interaction, None)
    
    elif action == "stats":
        await self.fish_stats_action(interaction)
    
    else:  # menu
        await self.fish_menu_action(interaction)
```

---

### 2. Cast Action (Fishing Gameplay)

**Location:** Lines 2723-2813

**Flow:**
1. Check for Kraken Bait special case
2. Get weather and time conditions
3. Calculate bonuses from rod, bait, pets
4. Select random fish from area based on weighted chances
5. Start fishing minigame
6. Update profile statistics

**Weather System:**
```python
self.weather_types = {
    "sunny": {"multiplier": 1.0, "emoji": "☀️", "description": "Perfect fishing weather!"},
    "cloudy": {"multiplier": 1.2, "emoji": "☁️", "description": "Fish are more active!"},
    "rainy": {"multiplier": 1.5, "emoji": "🌧️", "description": "Great fishing conditions!"},
    "stormy": {"multiplier": 0.5, "emoji": "⛈️", "description": "Dangerous conditions!"},
    "foggy": {"multiplier": 1.3, "emoji": "🌫️", "description": "Mysterious catches await!"},
}
```

**Time System:**
```python
self.time_periods = {
    "dawn": {"multiplier": 1.4, "emoji": "🌅", "hours": [5, 6, 7]},
    "morning": {"multiplier": 1.0, "emoji": "🌄", "hours": [8, 9, 10, 11]},
    "noon": {"multiplier": 0.8, "emoji": "🌞", "hours": [12, 13, 14]},
    "afternoon": {"multiplier": 1.0, "emoji": "🌤️", "hours": [15, 16, 17]},
    "dusk": {"multiplier": 1.4, "emoji": "🌇", "hours": [18, 19, 20]},
    "night": {"multiplier": 1.2, "emoji": "🌙", "hours": [21, 22, 23, 0, 1, 2, 3, 4]},
}
```

**Pet Multipliers:**
```python
# Integration with Pets cog for bonuses
pets_cog = self.bot.get_cog("Pets")
if pets_cog:
    pet_multiplier = pets_cog.get_fishing_multiplier(user_id)
    rarity_mult = pets_cog.get_rarity_multiplier(user_id, fish_rarity)
```

**Fish Selection Algorithm:**
```python
# Calculate catch chance
base_chance = 100
total_multiplier = weather_data["multiplier"] * time_data["multiplier"]
total_multiplier += (rod_bonus + bait_bonus) / 100

# Weight fish chances
fish_chances = []
for fish_id in available_fish:
    fish = self.fish_types[fish_id]
    adjusted_chance = fish["chance"] * total_multiplier * pet_multiplier * rarity_mult
    fish_chances.append((fish_id, adjusted_chance))

# Select fish using weighted random
total_weight = sum(chance for _, chance in fish_chances)
rand = random.uniform(0, total_weight)
current = 0
caught_fish_id = fish_chances[0][0]

for fish_id, chance in fish_chances:
    current += chance
    if rand <= current:
        caught_fish_id = fish_id
        break
```

---

### 3. `/fishhelp` - Help System

**Location:** Lines 2163-2165

**Implementation:**
```python
@app_commands.command(name="fishhelp", description="View all fishing commands and info (paginated)")
async def fishhelp_slash(self, interaction: discord.Interaction):
    view = FishingHelpView(self)
    await interaction.response.send_message(embed=view.get_current_embed(), view=view)
```

---

### 4. Craft System

**Location:** Lines 3033-3156

**Kraken Bait Recipe:**
- **Requires:** 8x Kraken Tentacle
- **Produces:** 1x Kraken Bait
- **Purpose:** Summon Kraken boss in Mariana Trench

**Crafting Logic:**
```python
async def fish_craft_action(self, interaction: discord.Interaction):
    """Craft special fishing items like Kraken Bait"""
    user_data = self.get_user_data(interaction.user.id)
    fish_caught = user_data.get("fish_caught", {})
    
    # Check for Kraken Tentacles
    kraken_tentacles = 0
    if "kraken_tentacle" in fish_caught and isinstance(fish_caught["kraken_tentacle"], dict):
        kraken_tentacles = fish_caught["kraken_tentacle"].get("count", 0)
    
    can_craft_kraken = kraken_tentacles >= 8
    
    if can_craft_kraken:
        # Consume tentacles
        fish_caught["kraken_tentacle"]["count"] -= 8
        if fish_caught["kraken_tentacle"]["count"] <= 0:
            del fish_caught["kraken_tentacle"]
        
        # Adjust total catches
        if user_data["total_catches"] >= 8:
            user_data["total_catches"] -= 8
        
        # Give kraken bait
        if "bait_inventory" not in user_data:
            user_data["bait_inventory"] = {}
        user_data["bait_inventory"]["kraken_bait"] = \
            user_data["bait_inventory"].get("kraken_bait", 0) + 1
        
        self.save_fishing_data()
```

---

## Fishing Tournaments

**Location:** Lines 3158-3417

### Tournament Types

1. **Biggest Fish** - Heaviest catch wins
2. **Most Fish** - Highest quantity wins
3. **Rarest Fish** - Best rarity wins

### Automatic Tournament System

**Background Task:**
```python
async def random_tournament_loop(self):
    """Background task to randomly start tournaments"""
    await self.bot.wait_until_ready()
    
    while not self.bot.is_closed():
        try:
            # Wait 6-12 hours between tournaments (RARE!)
            wait_time = random.randint(21600, 43200)  # 6-12 hours in seconds
            await asyncio.sleep(wait_time)
            
            # Get all guilds and pick random ones
            for guild in self.bot.guilds:
                # 10% chance per guild (very rare)
                if random.random() < 0.1:
                    guild_config = self.get_guild_config(guild.id)
                    
                    # Only start if channel is configured
                    if guild_config.get("tournament_channel"):
                        channel = self.bot.get_channel(guild_config["tournament_channel"])
                        if channel and channel.permissions_for(guild.me).send_messages:
                            asyncio.create_task(
                                self.start_random_tournament(guild.id, channel.id)
                            )
        
        except Exception as e:
            print(f"[FISHING] Error in random tournament loop: {e}")
            await asyncio.sleep(3600)  # Wait 1 hour on error
```

**Tournament Structure:**
```python
tournament_data = {
    'mode': mode_value,  # "biggest", "most", or "rarest"
    'mode_name': mode_name,  # Display name
    'host': None,  # Auto-generated (or user_id for manual)
    'participants': {},  # user_id: {count, biggest_weight, rarest_rarity, etc.}
    'end_time': end_time,  # datetime
    'duration': duration,  # minutes
    'channel_id': channel_id,  # Where to announce
    'auto_generated': True  # vs manual tournament
}
```

**Catch Recording:**
```python
def record_tournament_catch(self, guild_id: str, user_id: int, fish_id: str, weight: float):
    """Record a catch for tournament tracking"""
    tournament = self.active_tournaments[str(guild_id)]
    user_id_str = str(user_id)
    
    if user_id_str not in tournament['participants']:
        tournament['participants'][user_id_str] = {
            'count': 0,
            'biggest_weight': 0,
            'biggest_fish': None,
            'rarest_rarity': 'Common',
            'rarest_fish': None
        }
    
    player_data = tournament['participants'][user_id_str]
    fish_data = self.fish_types[fish_id]
    
    # Update count
    player_data['count'] += 1
    
    # Update biggest
    if weight > player_data['biggest_weight']:
        player_data['biggest_weight'] = weight
        player_data['biggest_fish'] = fish_data['name']
    
    # Update rarest
    rarity_order = {
        "Common": 0, "Uncommon": 1, "Rare": 2,
        "Epic": 3, "Legendary": 4, "Mythic": 5
    }
    if rarity_order.get(fish_data['rarity'], 0) > rarity_order.get(player_data['rarest_rarity'], 0):
        player_data['rarest_rarity'] = fish_data['rarity']
        player_data['rarest_fish'] = fish_data['name']
```

**Tournament End:**
```python
async def end_tournament(self, guild_id: str):
    """End tournament and announce winners"""
    tournament = self.active_tournaments[guild_id]
    participants = tournament['participants']
    mode = tournament['mode']
    
    # Sort participants
    if mode == "biggest":
        sorted_players = sorted(
            participants.items(),
            key=lambda x: x[1].get('biggest_weight', 0),
            reverse=True
        )
    elif mode == "most":
        sorted_players = sorted(
            participants.items(),
            key=lambda x: x[1].get('count', 0),
            reverse=True
        )
    elif mode == "rarest":
        rarity_values = {
            "Common": 1, "Uncommon": 2, "Rare": 3,
            "Epic": 4, "Legendary": 5, "Mythic": 6
        }
        sorted_players = sorted(
            participants.items(),
            key=lambda x: rarity_values.get(x[1].get('rarest_rarity', 'Common'), 0),
            reverse=True
        )
    
    # Award prizes
    prizes = [1000, 500, 250]  # 1st, 2nd, 3rd place
    economy_cog = self.bot.get_cog("Economy")
    
    for idx, (user_id, data) in enumerate(sorted_players[:3]):
        economy_cog.add_coins(int(user_id), prizes[idx], "fishing_tournament")
```

---

## Data Persistence

**File:** `data/fishing_data.json`

**User Data Structure:**
```json
{
    "user_id": {
        "rod": "basic_rod",
        "boat": "none",
        "current_area": "pond",
        "bait_inventory": {
            "worm": 5,
            "cricket": 2,
            "golden_lure": 1
        },
        "fish_caught": {
            "common_fish": {
                "count": 15,
                "biggest": 1.8
            },
            "tuna": {
                "count": 3,
                "biggest": 42.5
            },
            "kraken": {
                "count": 1,
                "biggest": 1500
            }
        },
        "total_catches": 150,
        "total_value": 25000,
        "unlocked_areas": ["pond", "river", "lake", "ocean"],
        "achievements": ["first_catch", "100_fish", "kraken_slayer"],
        "stats": {
            "biggest_catch": "Marlin - 450kg",
            "rarest_catch": "Kraken",
            "favorite_area": "ocean"
        }
    }
}
```

---

# 2. FARMING SYSTEM

**File:** `cogs/farming.py` (773 lines)  
**Class:** `FarmingManager` & `Farming(commands.Cog)`

## Farming Overview

The farming system provides a **crop growing simulation** with:

- **10 crop types** with different growth times and seasons
- **Plot-based farming** (4-20 plots, upgradeable)
- **Seasonal mechanics** (spring, summer, fall, winter, all-season)
- **Farm upgrades** (sprinkler, fertilizer, greenhouse)
- **Leveling system** (farming XP and levels)
- **Energy system** integration
- **Harvest bonuses** (10% chance for double yield)

---

## Farming Data

### Crop Definitions

**Location:** Lines 25-110

```python
self.crops = {
    "wheat": {
        "name": "Wheat",
        "emoji": "🌾",
        "grow_time": 30,  # minutes
        "seed_cost": 10,
        "sell_price": 25,
        "xp": 5,
        "season": "all",
        "energy_cost": 5
    },
    "corn": {
        "name": "Corn",
        "emoji": "🌽",
        "grow_time": 45,
        "seed_cost": 15,
        "sell_price": 40,
        "xp": 8,
        "season": "summer",
        "energy_cost": 7
    },
    "tomato": {
        "name": "Tomato",
        "emoji": "🍅",
        "grow_time": 60,
        "seed_cost": 20,
        "sell_price": 55,
        "xp": 10,
        "season": "spring",
        "energy_cost": 8
    },
    "carrot": {
        "name": "Carrot",
        "emoji": "🥕",
        "grow_time": 25,
        "seed_cost": 8,
        "sell_price": 20,
        "xp": 4,
        "season": "fall",
        "energy_cost": 4
    },
    "potato": {
        "name": "Potato",
        "emoji": "🥔",
        "grow_time": 40,
        "seed_cost": 12,
        "sell_price": 30,
        "xp": 6,
        "season": "all",
        "energy_cost": 6
    },
    "pumpkin": {
        "name": "Pumpkin",
        "emoji": "🎃",
        "grow_time": 120,
        "seed_cost": 50,
        "sell_price": 150,
        "xp": 25,
        "season": "fall",
        "energy_cost": 15
    },
    "strawberry": {
        "name": "Strawberry",
        "emoji": "🍓",
        "grow_time": 35,
        "seed_cost": 18,
        "sell_price": 45,
        "xp": 7,
        "season": "spring",
        "energy_cost": 7
    },
    "watermelon": {
        "name": "Watermelon",
        "emoji": "🍉",
        "grow_time": 90,
        "seed_cost": 35,
        "sell_price": 100,
        "xp": 18,
        "season": "summer",
        "energy_cost": 12
    },
    "lettuce": {
        "name": "Lettuce",
        "emoji": "🥬",
        "grow_time": 20,
        "seed_cost": 6,
        "sell_price": 15,
        "xp": 3,
        "season": "all",
        "energy_cost": 3
    },
    "eggplant": {
        "name": "Eggplant",
        "emoji": "🍆",
        "grow_time": 70,
        "seed_cost": 28,
        "sell_price": 75,
        "xp": 14,
        "season": "summer",
        "energy_cost": 10
    }
}
```

### Crop Categories

**All-Season Crops (can plant anytime):**
- Wheat (30min, 25 coins)
- Potato (40min, 30 coins)
- Lettuce (20min, 15 coins)

**Spring Crops:**
- Tomato (60min, 55 coins)
- Strawberry (35min, 45 coins)

**Summer Crops:**
- Corn (45min, 40 coins)
- Watermelon (90min, 100 coins)
- Eggplant (70min, 75 coins)

**Fall Crops:**
- Carrot (25min, 20 coins)
- Pumpkin (120min, 150 coins) - **Best profit!**

---

## Farm Management

### Farm Data Structure

**Location:** Lines 170-195

```python
def get_farm(self, user_id):
    """Get or create user's farm"""
    user_id = str(user_id)
    if user_id not in self.farms:
        self.farms[user_id] = {
            "plots": 4,  # Starting plots
            "max_plots": 20,  # Max upgradeable
            "farming_level": 1,
            "farming_xp": 0,
            "crops_planted": {},  # plot_id: {crop, planted_at, ready_at}
            "total_harvested": 0,
            "crops_harvested": {},  # crop_name: count
            "upgrades": {
                "sprinkler": False,  # Reduces grow time 20%
                "fertilizer": False,  # +50% sell price
                "greenhouse": False   # All-season crops
            }
        }
        self.save_farms()
    return self.farms[user_id]
```

---

## Farming Upgrades

**Location:** Lines 335-365

### 1. Additional Plot

**Cost:** 500 × (current_plots - 3) coins (gets more expensive)  
**Effect:** Add 1 more plot (max 20 total)

**Example Costs:**
- 5th plot: 500 × (4 - 3) = 500 coins
- 6th plot: 500 × (5 - 3) = 1,000 coins
- 10th plot: 500 × (9 - 3) = 3,000 coins
- 20th plot: 500 × (19 - 3) = 8,000 coins

### 2. Sprinkler System

**Cost:** 2,000 coins  
**Effect:** Reduces all crop grow times by 20%  
**Example:** Pumpkin (120min) → 96 minutes

### 3. Premium Fertilizer

**Cost:** 3,000 coins  
**Effect:** +50% crop sell price  
**Example:** Pumpkin (150 coins) → 225 coins

### 4. Greenhouse

**Cost:** 5,000 coins  
**Effect:** Grow all crops year-round (ignores season restrictions)  
**Benefit:** Plant summer crops in winter, etc.

---

## Farming Commands

### 1. `L!farm` - View Farm

**Location:** Lines 488-544

**Display:**
- Farming level and XP progress
- Current season
- Total crops harvested
- All plot statuses (empty, growing, ready)
- Installed upgrades
- Command help

**Example Output:**
```
🔥 UserName's Farm
Level 5 Farmer
Season: Summer ☀️
XP: 250/500
Total Harvested: 150 crops

━━━━━━━━━━━━━━━━━━━━━━━━

Plot 1: 🌾 Wheat - 15m remaining
Plot 2: ✨ 🍅 Tomato - READY!
Plot 3: 🟫 Empty
Plot 4: 🌽 Corn - 30m remaining

Upgrades:
💧 Sprinkler (-20% grow time)
💩 Fertilizer (+50% sell price)
```

### 2. `L!seeds` - View Available Seeds

**Location:** Lines 546-574

**Display:**
- Current season
- All 10 crops with:
  - ✅/❌ Can plant in current season
  - Seed count owned
  - Grow time
  - Seed cost
  - Sell price
  - Season requirement

**Example:**
```
✅ 🌾 Wheat
Seeds Owned: 5 | Grow Time: 30m
Seed Cost: 10 coins | Sell Price: 25 coins
Season: All

❌ 🍅 Tomato
Seeds Owned: 2 | Grow Time: 60m
Seed Cost: 20 coins | Sell Price: 55 coins
Season: Spring (Cannot plant in Summer!)
```

### 3. `L!plant <crop> <plot>` - Plant Crop

**Location:** Lines 576-617

**Validation:**
1. Check energy cost (profile system)
2. Check seed availability
3. Check season compatibility (unless greenhouse)
4. Check plot availability
5. Plant crop and consume seed

**Energy Costs:**
- Lettuce: 3 energy
- Carrot: 4 energy
- Wheat: 5 energy
- Potato: 6 energy
- Strawberry: 7 energy
- Corn: 7 energy
- Tomato: 8 energy
- Eggplant: 10 energy
- Watermelon: 12 energy
- Pumpkin: 15 energy

**Implementation:**
```python
async def plant_command(self, ctx, crop: str, plot: int = 0):
    """Plant a crop"""
    # Check profile for energy
    profiles = self.load_profile()
    user_id = str(ctx.author.id)
    
    if user_id in profiles:
        profile = profiles[user_id]
        crop_data = self.manager.crops.get(crop.lower())
        if crop_data:
            if profile['energy'] < crop_data['energy_cost']:
                await ctx.send(f"❌ Not enough energy! Need {crop_data['energy_cost']}, have {profile['energy']}.")
                return
            
            profile['energy'] -= crop_data['energy_cost']
            self.save_profile(profiles)
    
    success, message = self.manager.plant_crop(ctx.author.id, plot, crop.lower())
    
    if success:
        # Update profile stats
        profile_cog = self.bot.get_cog("Profile")
        if profile_cog and hasattr(profile_cog, "profile_manager"):
            profile_cog.profile_manager.record_game_played(ctx.author.id, "farming")
```

### 4. `L!harvest <plot>` - Harvest Crop

**Location:** Lines 619-675

**Harvest Logic:**
```python
def harvest_crop(self, user_id, plot_id):
    """Harvest a ready crop"""
    plant_data = farm["crops_planted"][str(plot_id)]
    ready_time = datetime.fromisoformat(plant_data["ready_at"])
    
    # Check if ready
    if datetime.utcnow() < ready_time:
        time_left = ready_time - datetime.utcnow()
        minutes = int(time_left.total_seconds() / 60)
        return False, f"Not ready yet! {minutes} minutes remaining.", None
    
    crop = self.crops[plant_data["crop_id"]]
    
    # Calculate value with upgrades
    value = crop["sell_price"]
    if farm["upgrades"]["fertilizer"]:
        value = int(value * 1.5)
    
    # Random bonus yield (10% chance for double)
    quantity = 2 if random.random() < 0.1 else 1
    total_value = value * quantity
    
    # Update stats
    farm["total_harvested"] += quantity
    farm["crops_harvested"][crop["name"]] = \
        farm["crops_harvested"].get(crop["name"], 0) + quantity
    
    farm["farming_xp"] += crop["xp"] * quantity
    
    # Check level up
    level_up = False
    xp_needed = farm["farming_level"] * 100
    if farm["farming_xp"] >= xp_needed:
        farm["farming_level"] += 1
        farm["farming_xp"] -= xp_needed
        level_up = True
    
    # Remove crop from plot
    del farm["crops_planted"][str(plot_id)]
    
    self.save_farms()
    
    return True, {
        "crop": crop,
        "quantity": quantity,
        "value": total_value,
        "xp": crop["xp"] * quantity,
        "level_up": level_up,
        "new_level": farm["farming_level"] if level_up else None
    }, total_value
```

**Rewards:**
- **Base:** 1x crop at sell price + XP
- **10% Chance:** 2x crop (double yield!)
- **Fertilizer Bonus:** +50% sell price
- **Level Up:** Every 100 XP (level × 100)

**TCG Integration:**
```python
# Chance to award TCG card for simulation category
if tcg_manager:
    try:
        awarded = tcg_manager.award_for_game_event(str(ctx.author.id), 'simulation')
        if awarded:
            names = [CARD_DATABASE.get(c, {}).get('name', c) for c in awarded]
            await ctx.send(f"You received TCG card(s): {', '.join(names)}")
    except Exception:
        pass
```

### 5. `L!farmupgrade` - View Upgrades

**Location:** Lines 677-722

**Display:**
- All available upgrades with costs
- Current status (owned/not owned)
- Effects description
- Purchase commands

### 6. `L!buyupgrade <type>` - Purchase Upgrade

**Location:** Lines 724-773

**Validation:**
1. Check upgrade availability
2. Check balance (Economy cog)
3. Deduct coins
4. Apply upgrade

**Example:**
```python
async def buyupgrade_command(self, ctx, upgrade_type: str):
    """Purchase a farm upgrade"""
    success, message, cost = self.manager.upgrade_farm(ctx.author.id, upgrade_type.lower())
    
    if not success:
        await ctx.send(f"❌ {message}")
        return
    
    # Deduct coins via Economy cog
    economy_cog = self.bot.get_cog("Economy")
    if economy_cog:
        balance = economy_cog.get_balance(ctx.author.id)
        if balance < cost:
            await ctx.send(f"❌ Not enough coins! Need {cost}, have {balance}.")
            return
        economy_cog.remove_coins(ctx.author.id, cost)
```

---

## Seasonal System

**Location:** Lines 197-210

```python
def get_current_season(self):
    """Get current season based on month"""
    month = datetime.utcnow().month
    if month in [3, 4, 5]:
        return "spring"
    elif month in [6, 7, 8]:
        return "summer"
    elif month in [9, 10, 11]:
        return "fall"
    else:
        return "winter"

def can_plant_crop(self, crop_id, season, has_greenhouse):
    """Check if crop can be planted in current season"""
    crop = self.crops.get(crop_id)
    if not crop:
        return False
    
    if crop["season"] == "all":
        return True
    
    if has_greenhouse:
        return True
    
    return crop["season"] == season
```

**Season Mapping:**
- **Spring:** March, April, May (Tomato, Strawberry)
- **Summer:** June, July, August (Corn, Watermelon, Eggplant)
- **Fall:** September, October, November (Carrot, Pumpkin)
- **Winter:** December, January, February (All-season crops only, unless greenhouse)

---

## Data Persistence

**Files:**
- `data/farms.json` - Farm structures and upgrades
- `data/seeds.json` - Seed inventory per user

**Farm Data Structure:**
```json
{
    "user_id": {
        "plots": 6,
        "max_plots": 20,
        "farming_level": 5,
        "farming_xp": 250,
        "crops_planted": {
            "0": {
                "crop_id": "wheat",
                "planted_at": "2024-01-15T10:30:00",
                "ready_at": "2024-01-15T11:00:00"
            },
            "1": {
                "crop_id": "pumpkin",
                "planted_at": "2024-01-15T09:00:00",
                "ready_at": "2024-01-15T11:00:00"
            }
        },
        "total_harvested": 150,
        "crops_harvested": {
            "Wheat": 50,
            "Pumpkin": 10,
            "Tomato": 30
        },
        "upgrades": {
            "sprinkler": true,
            "fertilizer": true,
            "greenhouse": false
        }
    }
}
```

**Seeds Data Structure:**
```json
{
    "user_id": {
        "wheat": 10,
        "corn": 5,
        "pumpkin": 2,
        "tomato": 8
    }
}
```

---


## PART 3 SUMMARY

### Total Coverage

**Lines Documented:** 4,245 lines  
**Files Covered:** 3 files
- fishing.py: 3,472 lines
- farming.py: 773 lines

### Key Systems

**Fishing (Most Complex):**
- 8 interactive UI view classes
- 50+ fish species across 6 rarity tiers
- 9 fishing areas with progression
- Kraken boss fight with 8 attack patterns
- Tournament system (auto + manual)
- Rod/boat/bait equipment
- Weather & time multipliers
- Crafting system
- 8-page help system

**Farming:**
- 10 crop types with seasonal mechanics
- Plot-based farming (4-20 plots)
- 4 farm upgrades
- Leveling system
- Energy system integration
- Random double yield bonus

**Zoo:**
- 60+ animals across 8 game sources
- 15% encounter chance
- 3 rarity tiers
- Collection tracking
- Filtering system
- Integration with all minigames

### Command Reference

**Fishing Commands:**
- `/fish menu` - Main menu
- `/fish cast` - Start fishing (minigame)
- `/fish inventory` - View collection
- `/fish shop` - Buy equipment
- `/fish craft` - Craft Kraken Bait
- `/fish areas` - Travel to locations
- `/fish encyclopedia` - Browse fish
- `/fish stats` - View statistics
- `/fishhelp` - 8-page help system

**Farming Commands:**
- `L!farm` - View farm status
- `L!seeds` - View available seeds
- `L!plant <crop> <plot>` - Plant seeds
- `L!harvest <plot>` - Harvest crops
- `L!farmupgrade` - View upgrades
- `L!buyupgrade <type>` - Purchase upgrade

**Zoo Commands:**
- `L!zoo [filter]` / `/zoo` - View collection
- `L!release <animal>` / `/zoo_release` - Release animal

**Mining Commands:**
- `/mine` - Start/Resume mining adventure
- `L!ownermine` - Developer mode (owner only)
- Arrow buttons - Movement & mining
- Shop dropdown - Buy upgrades
- Inventory dropdown - Place items & view inventory

---

# 4. MINING ADVENTURE SYSTEM

**File:** `cogs/mining.py` (3,254 lines)  
**Class:** `Mining(commands.Cog)`

## Mining Overview

The **Mining Adventure** system is a **2D procedurally generated Minecraft-style mining game** implemented entirely in Discord using interactive Components v2 UI. This is the most technically complex simulation system, featuring:

- **Procedural world generation** with seed-based determinism
- **Real-time image rendering** with PIL (32x32 block textures)
- **Singleplayer & multiplayer modes** (per-server toggle)
- **6 biomes** with depth-based progression (Surface → Abyss)
- **25+ block types** including ores, structures, and special blocks
- **Energy system** with regeneration (1 per 30 seconds)
- **Upgradeable equipment** (pickaxe, backpack, max energy)
- **Item placement** (ladders, torches, portals)
- **Structure generation** (mineshafts with chests)
- **Gravity physics** (fall damage, auto-descent)
- **Portal teleportation** (public/private)
- **12-hour map reset** system (configurable)
- **Developer mode** with debug tools (owner only)

**Key Technical Features:**
- 11x10 viewport rendered as PNG image (352x320 pixels)
- Async map rendering in executor to prevent blocking
- Darkness overlay with torch lighting (5-block radius)
- Multiplayer player tracking with real-time position updates
- JSON persistence for world state and player data
- Server config integration for shared world toggle

---

## Mining World Generation

### Biome System (Lines 18-23)

**6 Biomes with progressive difficulty:**

```python
BIOMES = {
    0: {"name": "Surface", "blocks": ["dirt", "stone", "coal"], "hardness": 1.0},
    10: {"name": "Underground", "blocks": ["stone", "coal", "iron"], "hardness": 1.2},
    25: {"name": "Deep Caves", "blocks": ["stone", "iron", "gold", "redstone"], "hardness": 1.5},
    50: {"name": "Mineral Depths", "blocks": ["deepslate", "gold", "diamond", "emerald"], "hardness": 2.0},
    75: {"name": "Ancient Depths", "blocks": ["deepslate", "diamond", "emerald", "netherite"], "hardness": 3.0},
    100: {"name": "Abyss", "blocks": ["bedrock", "netherite", "ancient_debris"], "hardness": 5.0}
}
```

**Biome Selection Logic:**
- Depth determines biome (Y-coordinate)
- Hardness affects energy cost: `energy_cost = hardness / (1 + pickaxe_level * 0.15)`
- Block distribution: 60% common, 25% uncommon, 10% rare, 5% very rare

### Block Value System (Lines 25-31)

```python
BLOCK_VALUES = {
    "dirt": 1, "stone": 2, "coal": 5, "iron": 15, "gold": 50,
    "redstone": 30, "diamond": 200, "emerald": 300, "deepslate": 10,
    "netherite": 1000, "ancient_debris": 500, "bedrock": 0, "grass": 1,
    "mineshaft_wood": 2, "mineshaft_support": 3, "mineshaft_rail": 5,
    "mineshaft_entrance": 0, "chest": 0  # Chests contain loot, not value
}
```

### Procedural Generation Algorithm (Lines 109-155)

**Seed-Based Deterministic Generation:**

```python
def generate_world(self, regenerate=False):
    """Generate procedural world"""
    # Generate shop at y=-1 (above surface)
    for x in range(-50, 50):
        if x == 4:  # Shop left
            self.map_data[(x, -1)] = "shop_left"
        elif x == 5:  # Shop right
            self.map_data[(x, -1)] = "shop_right"
        else:
            self.map_data[(x, -1)] = "air"
    
    # Generate surface (y=0) with grass
    for x in range(-50, 50):
        if (x, 0) not in self.map_data:
            self.map_data[(x, 0)] = "grass"
    
    # Generate underground layers (y=1 to 150)
    for y in range(1, 150):
        biome = self.get_biome(y)
        for x in range(-50, 50):
            # Skip if regenerating and block is air (preserve mined areas)
            if regenerate and (x, y) in self.map_data and self.map_data[(x, y)] == "air":
                continue
            
            # Stable procedural generation - deterministic seed
            seed_value = (x * 73856093) ^ (y * 19349663) ^ self.seed
            pos_rng = random.Random(seed_value)
            noise = pos_rng.random()
            blocks = biome["blocks"]
            
            # Weighted block distribution
            if noise < 0.6:
                block = blocks[0]  # 60% - Most common
            elif noise < 0.85:
                block = blocks[1] if len(blocks) > 1 else blocks[0]  # 25%
            elif noise < 0.95:
                block = blocks[2] if len(blocks) > 2 else blocks[1]  # 10%
            else:
                block = blocks[-1]  # 5% - Rarest
            
            self.map_data[(x, y)] = block
    
    # Generate structures (mineshafts)
    self.generate_structures()
```

**Key Features:**
- **100x150 world** (x: -50 to 50, y: -1 to 150)
- **Deterministic:** Same seed = same world every time
- **Per-position RNG:** Each coordinate has unique seed from formula
- **Regeneration-safe:** Preserves mined areas (air blocks) when map resets
- **Shop placement:** Always at (4, -1) and (5, -1) above surface

### Structure Generation - Mineshafts (Lines 157-226)

**Horizontal tunnel system with support beams, rails, torches, and loot chests:**

```python
def generate_structures(self):
    """Generate world structures like mineshafts"""
    # Generate 2-5 mineshafts at random positions
    num_mineshafts = self.rng.randint(2, 5)
    for i in range(num_mineshafts):
        # Random starting X position (avoid shop area)
        start_x = self.rng.choice([x for x in range(-45, 35) if x not in range(3, 7)])
        # Random depth (Y position) for tunnel
        tunnel_y = self.rng.randint(15, 50)
        # Random height (4-5 blocks tall)
        tunnel_height = self.rng.randint(4, 5)
        # Tunnel length (20-35 blocks)
        tunnel_length = self.rng.randint(20, 35)
        
        # Create mineshaft structure metadata
        structure_id = f"mineshaft_{self.structure_counter}"
        self.structure_counter += 1
        
        self.structures[structure_id] = {
            "type": "mineshaft",
            "name": f"Mineshaft #{i+1}",
            "x": start_x,
            "y": tunnel_y - tunnel_height + 1,  # Top of tunnel
            "width": tunnel_length,
            "height": tunnel_height,
            "discovered": False
        }
        
        # Build the horizontal mineshaft tunnel
        for x_offset in range(tunnel_length):
            current_x = start_x + x_offset
            
            # Build tunnel layers (top to bottom)
            for height_offset in range(tunnel_height):
                current_y = tunnel_y - height_offset
                
                # Floor (bottom) - rails
                if height_offset == 0:
                    self.map_data[(current_x, current_y)] = "mineshaft_rail"
                # Ceiling (top) - wood
                elif height_offset == tunnel_height - 1:
                    self.map_data[(current_x, current_y)] = "mineshaft_wood"
                # Middle - air for passage
                else:
                    self.map_data[(current_x, current_y)] = "air"
            
            # Support beams every 6 blocks
            if x_offset % 6 == 0 and x_offset > 0:
                for height_offset in range(tunnel_height):
                    current_y = tunnel_y - height_offset
                    self.map_data[(current_x, current_y)] = "mineshaft_support"
            
            # Torches every 5 blocks (on ceiling - 1)
            if x_offset % 5 == 2:
                torch_y = tunnel_y - 1
                self.torches[(current_x, torch_y)] = True
            
            # Chests (loot) - 10% chance per block
            if x_offset > 3 and self.rng.random() < 0.10:
                chest_y = tunnel_y - 1  # One block above floor
                self.map_data[(current_x, chest_y)] = "chest"
            
            # Entrance marker at start
            if x_offset == 0:
                entrance_y = tunnel_y - tunnel_height + 2
                self.map_data[(current_x, entrance_y)] = "mineshaft_entrance"
```

**Mineshaft Features:**
- **2-5 mineshafts** per world
- **20-35 blocks long** horizontally
- **4-5 blocks tall** vertically
- **Support beams** every 6 blocks
- **Torches** every 5 blocks (5-block lighting radius)
- **Loot chests** with 10% spawn rate
- **Entrance marker** at start position
- **Structure tracking** for discovery system

---

## Mining Gameplay

### Player State (Lines 45-96)

```python
class MiningGame:
    def __init__(self, user_id: int, seed: int = None, guild_id: int = None, is_shared: bool = False):
        # Core state
        self.user_id = user_id
        self.guild_id = guild_id
        self.is_shared = is_shared
        self.seed = seed or random.randint(1, 999999)
        self.rng = random.Random(self.seed)
        
        # Player position
        self.x = 1  # Starting X (left of shop)
        self.y = -1  # Starting Y (above grass)
        self.depth = 0  # Max depth reached
        
        # Energy system
        self.energy = 60
        self.max_energy = 60
        self.last_energy_regen = datetime.utcnow()
        
        # Equipment
        self.pickaxe_level = 1
        self.backpack_capacity = 20
        
        # Inventory
        self.inventory = {}  # {block_type: count}
        self.coins = 100
        
        # Items (tools/utilities)
        self.items = {
            "ladder": 5,   # Climb up without mining
            "portal": 2,   # Teleportation waypoints
            "torch": 10    # Lighting in darkness
        }
        
        # Developer flags
        self.infinite_energy = False
        self.infinite_backpack = False
        self.auto_reset_enabled = True
        
        # Map & structures
        self.width = 11  # Viewport width
        self.height = 10  # Viewport height
        self.map_data = {}  # {(x, y): block_type}
        self.last_map_regen = datetime.utcnow()
        
        # Placed items
        self.ladders = {}  # {(x, y): True}
        self.portals = {}  # {portal_id: {name, x, y, owner_id, public, linked_to}}
        self.torches = {}  # {(x, y): True}
        self.portal_counter = 0
        
        # Structures
        self.structures = {}  # {structure_id: metadata}
        self.structure_counter = 0
        
        # Multiplayer
        self.other_players = {}  # {user_id: {x, y, last_update, username}}
```

### Mining Mechanics (Lines 237-320)

**Block Mining with Energy System:**

```python
def mine_block(self, x: int, y: int) -> tuple[bool, str]:
    """Mine block at position"""
    # Check distance - can only mine adjacent blocks (1 block away)
    if abs(x - self.x) + abs(y - self.y) != 1:
        return False, "**❌ Too far! Can only mine adjacent blocks.**"
    
    block = self.get_block(x, y)
    if block == "air":
        return False, "**❌ Nothing to mine here!**"
    
    if block == "bedrock":
        return False, "**❌ Bedrock is unbreakable!**"
    
    # Energy cost based on biome hardness and pickaxe level
    biome = self.get_biome(y)
    speed_bonus = 1 + (self.pickaxe_level * 0.15)
    energy_cost = max(1, int(biome["hardness"] / speed_bonus))
    
    # Check energy (skip if infinite)
    if not self.infinite_energy and self.energy < energy_cost:
        return False, f"**❌ Not enough energy! Need {energy_cost}**"
    
    # Special: Chest blocks (loot system)
    if block == "chest":
        if not self.infinite_backpack:
            current_inventory_size = sum(self.inventory.values())
            if current_inventory_size >= self.backpack_capacity:
                return False, "**❌ Inventory full!**"
        
        # Consume energy
        if not self.infinite_energy:
            self.energy -= energy_cost
        
        # Remove chest
        self.map_data[(x, y)] = "air"
        
        # Loot table (40% empty, 60% loot)
        loot_roll = random.random()
        
        if loot_roll < 0.40:
            return True, "📦 **Chest opened... but it's empty!**", (x, y)
        else:
            # 70% blocks, 30% items
            if random.random() < 0.70:
                # Block loot (weighted)
                loot_options = [
                    ("coal", 3, 0.25),      # 25% - 3x coal
                    ("iron", 2, 0.20),      # 20% - 2x iron
                    ("gold", 1, 0.15),      # 15% - 1x gold
                    ("redstone", 2, 0.15),  # 15% - 2x redstone
                    ("diamond", 1, 0.10),   # 10% - 1x diamond
                    ("emerald", 1, 0.08),   # 8% - 1x emerald
                    ("ancient_debris", 1, 0.05),  # 5%
                    ("netherite", 1, 0.02)  # 2%
                ]
                # Select weighted random loot
                selected_loot, selected_count = weighted_random(loot_options)
                self.inventory[selected_loot] = self.inventory.get(selected_loot, 0) + selected_count
                value = BLOCK_VALUES[selected_loot] * selected_count
                return True, f"📦 **Chest opened! Found {selected_count}x {selected_loot}!** (+${value})", (x, y)
            else:
                # Item loot (ladder/torch/portal)
                item_options = [
                    ("ladder", 3, 0.50),   # 50% - 3x ladder
                    ("torch", 5, 0.40),    # 40% - 5x torch
                    ("portal", 1, 0.10)    # 10% - 1x portal
                ]
                selected_item, selected_count = weighted_random(item_options)
                self.items[selected_item] = self.items.get(selected_item, 0) + selected_count
                emoji = {"ladder": "🪜", "torch": "🔦", "portal": "🌀"}[selected_item]
                return True, f"📦 **Chest opened! Found {selected_count}x {emoji} {selected_item}!**", (x, y)
    
    # Normal block mining
    if not self.infinite_backpack:
        total_items = sum(self.inventory.values())
        if total_items >= self.backpack_capacity:
            return False, "**❌ Backpack full! Return to surface to sell.**"
    
    # Mine successful
    if not self.infinite_energy:
        self.energy -= energy_cost
    self.map_data[(x, y)] = "air"
    self.inventory[block] = self.inventory.get(block, 0) + 1
    
    # Update max depth
    if y > self.depth:
        self.depth = y
    
    value = BLOCK_VALUES.get(block, 0)
    return True, f"⛏️ Mined {block}! (+{value} value)", (x, y)
```

**Key Mining Features:**
- **Adjacent blocks only** (Manhattan distance = 1)
- **Energy cost formula:** `max(1, hardness / (1 + pickaxe_level * 0.15))`
- **Bedrock is unbreakable** (world bottom)
- **Chest loot system:**
  - 40% empty
  - 42% block loot (ores with weighted distribution)
  - 18% item loot (ladders/torches/portals)
- **Backpack capacity check** (20 default, upgradeable)
- **Depth tracking** for progression

### Energy System (Lines 378-385)

```python
def regenerate_energy(self):
    """Regenerate energy over time (1 per 30 seconds)"""
    now = datetime.utcnow()
    elapsed = (now - self.last_energy_regen).total_seconds()
    regen_count = int(elapsed // 30)
    
    if regen_count > 0:
        self.energy = min(self.max_energy, self.energy + regen_count)
        # Don't lose leftover time (preserve fractional seconds)
        self.last_energy_regen += timedelta(seconds=regen_count * 30)
```

**Energy Regeneration:**
- **1 energy per 30 seconds**
- **Passive regeneration** (no manual recharge needed)
- **Preserves fractional time** (no wasted seconds)
- **Max cap:** Determined by `max_energy` upgrade

### Movement System (Lines 322-345)

```python
def move_player(self, dx: int, dy: int) -> tuple[bool, str]:
    """Move player by delta (no energy cost)"""
    new_x = self.x + dx
    new_y = self.y + dy
    
    # Check bounds
    if new_x < -50 or new_x > 50:
        return False, "**❌ World boundary!**"
    
    # Check if position is blocked
    if not self.can_move(new_x, new_y):
        return False, "**❌ Blocked! Mine the block first.**"
    
    # Move (no energy cost)
    self.x = new_x
    self.y = new_y
    
    # Check if on shop
    if self.y == -1 and self.x in [4, 5]:
        return True, "🏪 You're at the shop! Use the shop menu to trade."
    
    return True, f"Moved to ({self.x}, {self.y})"
```

**Movement Features:**
- **No energy cost** for movement (only mining costs energy)
- **World bounds:** X ∈ [-50, 50]
- **Block collision** (must mine to pass)
- **Shop detection** at (4, -1) and (5, -1)

### Gravity & Falling (Lines 1500-1510 in MiningView)

```python
# After mining block below, player falls automatically
async def mine_callback(self, interaction: discord.Interaction):
    """Mine block below and fall to ground"""
    target_x = self.game.x
    target_y = self.game.y + 1
    
    # Check if can move down (already empty)
    if self.game.can_move(target_x, target_y):
        # Fall down until hitting ground
        while self.game.can_move(self.game.x, self.game.y + 1):
            self.game.y += 1
        msg = f"⬇️ Fell to ground at y={self.game.y}"
    else:
        # Mine block
        result = self.game.mine_block(target_x, target_y)
        if len(result) == 3 and result[0]:  # Successful mine
            success, msg, (new_x, new_y) = result
            self.game.x = new_x
            self.game.y = new_y
            
            # Apply gravity - fall to ground
            while self.game.can_move(self.game.x, self.game.y + 1):
                self.game.y += 1
                msg += f" → Fell to y={self.game.y}"
        else:
            _, msg = result
    
    await self.refresh(interaction, msg)
```

**Gravity System:**
- **Automatic descent** after mining below
- **Fall until solid ground** (no fall damage)
- **Instant gravity** (no animation delay)

### Shop System (Lines 1600-1680 in MiningView)

**Located at Y=-1, X=4 or 5 (above surface):**

```python
async def shop_callback(self, interaction: discord.Interaction):
    """Handle shop purchases"""
    action = selected[0]
    
    if action == "sell":
        # Sell all inventory items
        value, items = self.game.sell_inventory(interaction.client)
        await self.refresh(interaction, f"💰 Sold items for {value} psycoins!")
    
    elif action == "pickaxe":
        # Upgrade pickaxe (faster mining)
        cost = self.game.pickaxe_level * 500
        if economy_cog.remove_coins(interaction.user.id, cost):
            self.game.pickaxe_level += 1
            await self.refresh(interaction, f"⛏️ Upgraded pickaxe to level {self.game.pickaxe_level}!")
    
    elif action == "backpack":
        # Upgrade backpack (+10 capacity)
        cost = self.game.backpack_capacity * 100
        if economy_cog.remove_coins(interaction.user.id, cost):
            self.game.backpack_capacity += 10
            await self.refresh(interaction, f"🎒 Upgraded backpack to {self.game.backpack_capacity} slots!")
    
    elif action == "energy":
        # Upgrade max energy (+20 max)
        cost = self.game.max_energy * 50
        if economy_cog.remove_coins(interaction.user.id, cost):
            self.game.max_energy += 20
            self.game.energy = self.game.max_energy
            await self.refresh(interaction, f"⚡ Upgraded max energy to {self.game.max_energy}!")
```

**Shop Features:**
- **Sell inventory:** Convert all mined blocks to PsyCoins
- **Pickaxe Upgrade:** Cost = `level * 500`, Effect = 15% faster mining per level
- **Backpack Upgrade:** Cost = `capacity * 100`, Effect = +10 slots
- **Energy Upgrade:** Cost = `max_energy * 50`, Effect = +20 max energy

---

## Mining Items & Structures

### Ladder System (Lines 387-398)

**Climb upward without mining:**

```python
def place_ladder(self) -> tuple[bool, str]:
    """Place a ladder at current position"""
    if self.items.get("ladder", 0) <= 0:
        return False, "❌ No ladders in inventory!"
    
    if (self.x, self.y) in self.ladders:
        return False, "❌ Ladder already placed here!"
    
    # Place ladder (can place anywhere)
    self.ladders[(self.x, self.y)] = True
    self.items["ladder"] -= 1
    return True, f"🪜 Ladder placed! ({self.items['ladder']} left)"

def can_move_up(self) -> bool:
    """Check if player can move up (requires ladder)"""
    if (self.x, self.y) in self.ladders:
        return True
    if (self.x, self.y - 1) in self.ladders:
        return True
    return False
```

**Ladder Features:**
- **Enables upward movement** without mining
- **Placeable anywhere** (including surface/sky)
- **Persistent** (not destroyed by mining)
- **Starting amount:** 5 ladders
- **Obtainable from:** Shop purchases, chest loot

### Torch System (Lines 400-410)

**Lighting in dark caves:**

```python
def place_torch(self) -> tuple[bool, str]:
    """Place a torch at current position"""
    if self.items.get("torch", 0) <= 0:
        return False, "❌ No torches in inventory!"
    
    if (self.x, self.y) in self.torches:
        return False, "❌ Torch already placed here!"
    
    self.torches[(self.x, self.y)] = True
    self.items["torch"] -= 1
    return True, f"🔦 Torch placed! ({self.items['torch']} left)"
```

**Torch Lighting System (Lines 650-690 in render_map):**

```python
# Apply darkness based on depth (darker the deeper you go)
if self.y > 5:  # Below surface level
    darkness_overlay = Image.new('RGBA', (img_width, img_height), (0, 0, 0, 0))
    darkness_draw = ImageDraw.Draw(darkness_overlay)
    
    # Calculate darkness intensity (0-240 alpha based on depth)
    depth_factor = min((self.y - 5) / 55, 1.0)  # 0 at y=5, 1.0 at y=60
    darkness_alpha = int(depth_factor * 240)
    
    # Draw darkness over entire map
    for dy in range(self.height):
        for dx in range(self.width):
            world_x = start_x + dx
            world_y = start_y + dy
            
            # Check if there's a torch nearby (within 5 blocks)
            lit = False
            light_distance = 999
            for tx, ty in self.torches.keys():
                distance = abs(tx - world_x) + abs(ty - world_y)
                if distance <= 5:  # 5-block lighting radius
                    lit = True
                    light_distance = min(light_distance, distance)
            
            # Apply darkness if not lit by torch
            if not lit:
                darkness_draw.rectangle([x1, y1, x1 + block_size, y1 + block_size], 
                                        fill=(0, 0, 0, darkness_alpha))
            else:
                # Gradual light falloff based on distance
                light_alpha = int(darkness_alpha * (light_distance / 6.0))
                darkness_draw.rectangle([x1, y1, x1 + block_size, y1 + block_size], 
                                        fill=(0, 0, 0, light_alpha))
```

**Torch Features:**
- **5-block lighting radius** (Manhattan distance)
- **Gradual light falloff** (brighter closer to torch)
- **Darkness increases with depth** (y > 5)
- **100% darkness at Abyss** (y > 60) without torches
- **Starting amount:** 10 torches
- **Obtainable from:** Mineshaft generation, chest loot

### Portal System (Lines 2050-2100 in MiningView)

**Teleportation waypoints:**

```python
async def show_portal_modal(self, interaction: discord.Interaction):
    """Show modal for portal placement"""
    modal = discord.ui.Modal(title="Place Portal")
    name_input = discord.ui.TextInput(
        label="Portal Name",
        placeholder="Enter portal name (e.g., 'Home', 'Diamond Mine')",
        required=True,
        max_length=30
    )
    modal.add_item(name_input)
    
    # In multiplayer, ask if public
    if self.game.is_shared:
        public_input = discord.ui.TextInput(
            label="Public? (yes/no)",
            placeholder="yes = everyone can use, no = only you",
            required=True,
            max_length=3
        )
        modal.add_item(public_input)
    
    async def modal_callback(modal_interaction: discord.Interaction):
        portal_name = name_input.value
        is_public = True  # Default for singleplayer
        
        if self.game.is_shared:
            public_answer = public_input.value.lower()
            is_public = public_answer in ["yes", "y", "tak", "t"]
        
        # Place portal
        portal_id = f"portal_{self.game.portal_counter}"
        self.game.portal_counter += 1
        
        self.game.portals[portal_id] = {
            "name": portal_name,
            "x": self.game.x,
            "y": self.game.y,
            "owner_id": self.user_id,
            "public": is_public,
            "linked_to": None
        }
        
        self.game.items["portal"] -= 1
        await self.refresh(modal_interaction, f"🌀 Portal '{portal_name}' placed!")
```

**Portal Features:**
- **Named portals** (custom 30-char names)
- **Public/private access** (multiplayer only)
- **Teleportation menu** (shown when standing on portal)
- **Two-way travel** (any portal to any portal)
- **Owner restrictions** (private portals only usable by owner)
- **Starting amount:** 2 portals
- **Obtainable from:** Chest loot (10% chance)

---

## Mining Multiplayer

### Shared World System (Lines 3100-3200 in Mining cog)

**Server-wide shared world with per-player tracking:**

```python
async def start_mining(self, ctx, user_id: int, guild_id: int = None, dev_mode: bool = False):
    """Start or resume mining game"""
    # Check if server has shared mining enabled
    is_shared = False
    if guild_id:
        server_config_cog = self.bot.get_cog("ServerConfig")
        if server_config_cog:
            server_config = server_config_cog.get_server_config(guild_id)
            is_shared = server_config.get("shared_mining_world", False)
    
    if is_shared and guild_id:
        # SHARED WORLD MODE
        if guild_id not in self.shared_worlds:
            # Create new shared world for this guild
            world_game = MiningGame(user_id=0, guild_id=guild_id, is_shared=True)
            self.shared_worlds[guild_id] = {
                "world_data": world_game,  # Shared map
                "players": {}              # Per-player data
            }
        
        world_info = self.shared_worlds[guild_id]
        world_game = world_info["world_data"]
        
        # Get or create player data
        if str(user_id) not in world_info["players"]:
            world_info["players"][str(user_id)] = {
                "x": 1, "y": -1, "depth": 0,
                "energy": 60, "max_energy": 60,
                "pickaxe_level": 1, "backpack_capacity": 20,
                "inventory": {}, "coins": 100
            }
        
        player_data = world_info["players"][str(user_id)]
        
        # Create game instance for player (uses shared map)
        game = MiningGame(user_id=user_id, seed=world_game.seed, guild_id=guild_id, is_shared=True)
        game.map_data = world_game.map_data  # Share world map
        game.ladders = world_game.ladders    # Share structures
        game.torches = world_game.torches
        game.portals = world_game.portals
        
        # Load player-specific data
        game.x = player_data["x"]
        game.y = player_data["y"]
        game.energy = player_data["energy"]
        game.pickaxe_level = player_data["pickaxe_level"]
        game.inventory = player_data["inventory"]
        
        # Update other players positions for rendering
        game.other_players = {}
        for other_user_id, other_data in world_info["players"].items():
            if str(other_user_id) != str(user_id):
                user = bot.get_user(int(other_user_id))
                username = user.name if user else f"User {other_user_id}"
                
                game.other_players[other_user_id] = {
                    "x": other_data["x"],
                    "y": other_data["y"],
                    "username": username
                }
```

**Shared World Features:**
- **One world per server** (shared seed, shared map)
- **Individual player progress** (position, inventory, energy, upgrades)
- **Shared structures** (ladders, torches, portals placed by anyone)
- **Real-time player positions** (see other players on map)
- **Server config toggle:** `L!toggle sharedmining`

### Player Rendering (Lines 700-760 in render_map)

**Multiplayer player markers on map:**

```python
# Draw other players in multiplayer mode
if self.is_shared and self.other_players:
    player_colors = [
        (255, 100, 100),  # Red
        (100, 255, 100),  # Green
        (100, 100, 255),  # Blue
        (255, 255, 100),  # Yellow
        (255, 100, 255),  # Magenta
        (100, 255, 255),  # Cyan
        (255, 165, 0),    # Orange
        (255, 192, 203),  # Pink
    ]
    
    for idx, (other_user_id, other_data) in enumerate(self.other_players.items()):
        other_x = other_data["x"]
        other_y = other_data["y"]
        
        # Check if in viewport
        view_dx = other_x - start_x
        view_dy = other_y - start_y
        
        if 0 <= view_dx < self.width and 0 <= view_dy < self.height:
            # Draw colored circle for player
            color = player_colors[idx % len(player_colors)]
            
            marker = Image.new('RGBA', (block_size, block_size), (0, 0, 0, 0))
            marker_draw = ImageDraw.Draw(marker)
            
            center = block_size // 2
            radius = block_size // 3
            
            marker_draw.ellipse([center - radius, center - radius,
                               center + radius, center + radius],
                              fill=color + (200,),  # Semi-transparent
                              outline=(255, 255, 255, 255),
                              width=2)
            
            # Paste on map
            paste_x = view_dx * block_size
            paste_y = view_dy * block_size
            img_rgba.paste(marker, (paste_x, paste_y), marker)
            
            # Draw username above player
            username = other_data.get("username", "Player")
            # ... text rendering code ...
```

**Multiplayer Rendering Features:**
- **8 color-coded players** (wraps after 8)
- **Semi-transparent circles** with white border
- **Username labels** above players
- **Real-time position updates** (saved on every action)
- **Viewport filtering** (only render visible players)

---

## Mining Map Rendering

### Image Generation System (Lines 513-1000)

**32x32 pixel blocks rendered to 352x320 PNG image:**

```python
def render_map(self, bot=None) -> io.BytesIO:
    """Render current view as image"""
    block_size = 32
    img_width = self.width * block_size  # 11 * 32 = 352px
    img_height = self.height * block_size  # 10 * 32 = 320px
    
    img = Image.new('RGB', (img_width, img_height), color=(135, 206, 235))  # Sky blue
    
    # Texture cache
    texture_cache = {}
    
    def load_texture(block_type: str) -> Image.Image:
        """Load texture from assets folder"""
        if block_type in texture_cache:
            return texture_cache[block_type]
        
        asset_map = {
            "air": "assets/mining/blocks/layer1/air.png",
            "dirt": "assets/mining/blocks/layer1/dirt.png",
            "grass": "assets/mining/blocks/layer1/grass.png",
            "stone": "assets/mining/blocks/layer1/dirt.png",
            "coal": "assets/mining/blocks/layer1/coal.png",
            "iron": "assets/mining/blocks/layer1/iron.png",
            # ... 25+ block types ...
        }
        
        try:
            texture = Image.open(asset_path).convert("RGBA")
            texture = texture.resize((block_size, block_size), Image.LANCZOS)
            texture_cache[block_type] = texture
            return texture
        except:
            # Fallback to colored rectangle
            fallback = Image.new('RGBA', (block_size, block_size), self.BLOCK_COLORS[block_type])
            texture_cache[block_type] = fallback
            return fallback
    
    # Calculate viewport (centered on player)
    start_x = self.x - self.width // 2
    start_y = self.y - self.height // 2
    
    # Draw blocks
    for dy in range(self.height):
        for dx in range(self.width):
            world_x = start_x + dx
            world_y = start_y + dy
            block = self.get_block(world_x, world_y)
            
            x1 = dx * block_size
            y1 = dy * block_size
            texture = load_texture(block)
            img.paste(texture, (x1, y1), texture)
            
            # Overlay ladders/torches/portals
            if (world_x, world_y) in self.ladders:
                ladder_img = Image.open("assets/mining/items/ladder.png")
                img.paste(ladder_img, (x1, y1), ladder_img)
            
            if (world_x, world_y) in self.torches:
                torch_img = Image.open("assets/mining/items/torch.png")
                img.paste(torch_img, (x1 + block_size//4, y1), torch_img)
            
            # Portal with name label
            for portal_id, portal_data in self.portals.items():
                if portal_data["x"] == world_x and portal_data["y"] == world_y:
                    portal_img = Image.open("assets/mining/items/portal.png")
                    img.paste(portal_img, (x1, y1), portal_img)
                    # Draw portal name above
                    draw_text(portal_data["name"], (x1, y1 - 12), color=(255, 255, 255))
    
    # Apply darkness overlay (depth > 5)
    if self.y > 5:
        apply_darkness_with_torch_lighting()
    
    # Draw other players (multiplayer)
    if self.is_shared:
        draw_other_players()
    
    # Draw current player (yellow circle or avatar.png)
    player_x = self.width // 2
    player_y = self.height // 2
    try:
        player_texture = Image.open("assets/mining/character/avatar.png")
        img.paste(player_texture, (player_x * block_size, player_y * block_size))
    except:
        draw.ellipse([center_x - radius, center_y - radius, 
                    center_x + radius, center_y + radius], 
                   fill=(255, 255, 0))  # Yellow circle
    
    # Draw UI overlay (top bar)
    draw_ui_stats()
    
    # Save to BytesIO
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    return buffer
```

**Rendering Features:**
- **Texture loading** from `assets/mining/` folder
- **Texture caching** (prevents re-loading every frame)
- **Viewport centering** (player always in middle)
- **Layered rendering:**
  1. Blocks (terrain)
  2. Ladders/torches/portals
  3. Darkness overlay
  4. Other players
  5. Current player
  6. UI overlay
- **Async execution** (runs in executor to prevent blocking)
- **PNG compression** (saved to BytesIO for Discord attachment)

### UI Overlay (Lines 800-920)

**Stats bar at top of image:**

```python
# Draw UI overlay (semi-transparent dark bar)
ui_height = 35
overlay = Image.new('RGBA', (img_width, ui_height), (0, 0, 0, 180))
img_rgba.paste(overlay, (0, 0), overlay)

# Energy icon + text
energy_icon = load_ui_icon("assets/mining/ui/energy.png")
img_rgba.paste(energy_icon, (5, 3), energy_icon)
energy_text = "inf/inf" if self.infinite_energy else f"{self.energy}/{self.max_energy}"
draw.text((28, 5), energy_text, fill=(255, 255, 100), font=font)

# Energy bar (below text)
bar_x, bar_y = 5, 23
bar_width, bar_height = 80, 8
draw.rectangle([bar_x, bar_y, bar_x + bar_width, bar_y + bar_height], fill=(40, 40, 40))
fill_width = int((self.energy / self.max_energy) * bar_width)
bar_color = (100, 200, 255) if self.energy > self.max_energy * 0.3 else (255, 100, 100)
draw.rectangle([bar_x, bar_y, bar_x + fill_width, bar_y + bar_height], fill=bar_color)

# Coins icon + text
coins_icon = load_ui_icon("assets/mining/ui/coins.png")
img_rgba.paste(coins_icon, (95, 3), coins_icon)
draw.text((118, 5), f"{self.coins}", fill=(255, 215, 0), font=font)

# Backpack icon + text
backpack_level = (self.backpack_capacity - 20) // 10 + 1
backpack_icon = load_ui_icon(f"assets/mining/ui/backpack/backpack{backpack_level}.png")
img_rgba.paste(backpack_icon, (228, 3), backpack_icon)
inv_size = sum(self.inventory.values())
inv_text = f"{inv_size}/inf" if self.infinite_backpack else f"{inv_size}/{self.backpack_capacity}"
inv_color = (255, 100, 100) if inv_size >= self.backpack_capacity else (100, 255, 100)
draw.text((248, 5), inv_text, fill=inv_color, font=font)

# Pickaxe icon + level
pickaxe_icon = load_ui_icon("assets/mining/ui/pickaxe.png")
img_rgba.paste(pickaxe_icon, (300, 3), pickaxe_icon)
draw.text((324, 5), f"Lv.{self.pickaxe_level}", fill=(255, 255, 255), font=font)

# Biome info below top bar
biome = self.get_biome(self.y)
biome_text = f"{biome['name']} (Y: {self.y}) | reset in {hours}h {minutes}m"
draw.text((center_x, 41), biome_text, fill=(200, 200, 255), font=font_small)

# No energy warning (center of screen)
if self.energy <= 0:
    warning_overlay = Image.new('RGBA', (img_width, img_height), (0, 0, 0, 0))
    draw_warning = ImageDraw.Draw(warning_overlay)
    draw_warning.rectangle([bg_x1, bg_y1, bg_x2, bg_y2], fill=(139, 0, 0, 200))  # Dark red
    draw.text((text_x, text_y), "NO ENERGY!", fill=(255, 255, 100), font=warning_font)
```

**UI Elements:**
- **Energy bar:** Visual + numeric (inf/inf if infinite)
- **Coins:** Current balance (synced with economy)
- **Backpack:** Current/max inventory size (red if full)
- **Pickaxe:** Current level
- **Biome:** Current biome name + Y coordinate
- **Map reset timer:** Time until 12-hour reset
- **No energy warning:** Big red overlay when energy = 0

---

## Mining Developer Mode

### Owner-Only Features (Lines 1850-2850 in OwnerMiningView)

**Advanced debugging and testing tools:**

```python
class OwnerMiningView(discord.ui.LayoutView):
    """Developer mining interface with extra features"""
    
    def __init__(self, game: MiningGame, user_id: int, bot):
        self.dev_menu_state = "main"  # Submenu navigation
        # ... same as MiningView ...
    
    async def dev_menu_callback(self, interaction: discord.Interaction):
        """Handle developer menu"""
        action = selected[0]
        
        # Main menu actions
        if action == "infinite_energy":
            self.game.infinite_energy = not self.game.infinite_energy
            status = "ENABLED" if self.game.infinite_energy else "DISABLED"
            await self.refresh(interaction, f"⚡ Infinite Energy: {status}")
        
        elif action == "infinite_backpack":
            self.game.infinite_backpack = not self.game.infinite_backpack
            status = "ENABLED" if self.game.infinite_backpack else "DISABLED"
            await self.refresh(interaction, f"🎒 Infinite Backpack: {status}")
        
        elif action == "cleararea":
            # Clear 5x5 area around player
            cleared = 0
            for dx in range(-2, 3):
                for dy in range(-2, 3):
                    x, y = self.game.x + dx, self.game.y + dy
                    if (x, y) in self.game.map_data and y >= 0:
                        self.game.map_data[(x, y)] = "air"
                        cleared += 1
            await self.refresh(interaction, f"🗑️ Cleared {cleared} blocks!")
        
        elif action == "forcereset":
            # Regenerate entire map
            self.game.map_data = {}
            self.game.generate_world(regenerate=True)
            self.game.x, self.game.y = 5, -1
            await self.refresh(interaction, f"🔄 World regenerated (seed {self.game.seed})")
        
        elif action == "customseed":
            # Show modal for custom seed input
            modal = discord.ui.Modal(title="Enter Custom Seed")
            seed_input = discord.ui.TextInput(label="World Seed", placeholder="12345")
            modal.add_item(seed_input)
            
            async def modal_callback(modal_interaction):
                new_seed = int(seed_input.value)
                self.game.seed = new_seed
                self.game.rng = random.Random(new_seed)
                self.game.map_data = {}
                self.game.generate_world(regenerate=True)
                await self.refresh(modal_interaction, f"🌱 Seed {new_seed} applied!")
            
            modal.on_submit = modal_callback
            await interaction.response.send_modal(modal)
        
        elif action == "spawnitems":
            # Spawn valuable ores
            self.game.inventory["diamond"] = self.game.inventory.get("diamond", 0) + 10
            self.game.inventory["emerald"] = self.game.inventory.get("emerald", 0) + 10
            self.game.inventory["netherite"] = self.game.inventory.get("netherite", 0) + 10
            await self.refresh(interaction, "💎 Spawned 10x diamond, emerald, netherite!")
        
        elif action == "maxupgrades":
            # Max all upgrades
            self.game.pickaxe_level = 10
            self.game.backpack_capacity = 200
            self.game.max_energy = 200
            self.game.energy = 200
            await self.refresh(interaction, "🚀 Maxed: Pickaxe 10, Backpack 200, Energy 200!")
        
        # Teleport submenu
        elif action == "teleport_menu":
            self.dev_menu_state = "teleport"
            await self.refresh(interaction, "📍 Teleport Menu")
        
        elif action.startswith("tp_"):
            depths = {
                "tp_surface": -1, "tp_underground": 10, "tp_deep": 25,
                "tp_mineral": 50, "tp_ancient": 75, "tp_abyss": 100
            }
            if action in depths:
                self.game.y = depths[action]
                self.game.x = 5
                await self.refresh(interaction, f"📍 Teleported to Y={self.game.y}")
        
        elif action.startswith("tp_player_"):
            player_id = action.replace("tp_player_", "")
            player_data = self.game.other_players[player_id]
            self.game.x = player_data["x"]
            self.game.y = player_data["y"]
            await self.refresh(interaction, f"📍 Teleported to {player_data['username']}")
        
        elif action.startswith("tp_structure_"):
            structure_id = action.replace("tp_structure_", "")
            structure = self.game.structures[structure_id]
            self.game.x, self.game.y = structure["x"], structure["y"]
            await self.refresh(interaction, f"🏛️ Teleported to {structure['name']}")
        
        # Place blocks submenu
        elif action == "place_menu":
            self.dev_menu_state = "place_blocks"
            await self.refresh(interaction, "🧱 Place Blocks Menu")
        
        elif action.startswith("place_"):
            block_type = action.replace("place_", "")
            target_x, target_y = self.game.x, self.game.y + 1
            self.game.map_data[(target_x, target_y)] = block_type
            await self.refresh(interaction, f"🧱 Placed {block_type} at ({target_x}, {target_y})")
        
        # Items submenu
        elif action == "items_menu":
            self.dev_menu_state = "items"
            await self.refresh(interaction, "📦 Items Menu")
        
        elif action.startswith("spawn_"):
            item_type = action.replace("spawn_", "")
            # Show modal for quantity
            modal = discord.ui.Modal(title=f"Add {item_type.title()}s")
            quantity_input = discord.ui.TextInput(label="Quantity", placeholder="10")
            modal.add_item(quantity_input)
            
            async def item_modal_callback(modal_interaction):
                quantity = int(quantity_input.value)
                self.game.items[item_type] = self.game.items.get(item_type, 0) + quantity
                await self.refresh(modal_interaction, f"📦 Added {quantity}x {item_type}!")
            
            modal.on_submit = item_modal_callback
            await interaction.response.send_modal(modal)
        
        # Structures submenu
        elif action == "structures_menu":
            self.dev_menu_state = "structures"
            await self.refresh(interaction, "🏗️ Structures Menu")
        
        elif action == "gen_mineshaft":
            # Generate horizontal mineshaft at current position
            structure_id = f"mineshaft_{self.game.structure_counter}"
            self.game.structure_counter += 1
            
            tunnel_length = self.game.rng.randint(20, 35)
            tunnel_height = self.game.rng.randint(4, 5)
            
            # Build mineshaft structure (same code as generate_structures)
            for x_offset in range(tunnel_length):
                # ... mineshaft building code ...
            
            await self.refresh(interaction, f"⛏️ Mineshaft generated! Length: {tunnel_length}")
        
        elif action == "discover_all":
            # Reveal all structures
            count = 0
            for structure_data in self.game.structures.values():
                if not structure_data["discovered"]:
                    structure_data["discovered"] = True
                    count += 1
            await self.refresh(interaction, f"🏛️ Discovered {count} structures!")
```

**Developer Menu Features:**

**Main Menu:**
- ⚡ Toggle Infinite Energy (no mining cost)
- 🎒 Toggle Infinite Backpack (no size limit)
- 🗑️ Clear Area (5x5 instant clear)
- 📍 Teleport Menu (depths, players, structures)
- 🧱 Place Blocks Menu (spawn any block)
- 📦 Items Menu (spawn ladders/torches/portals)
- 🏗️ Structures Menu (generate mineshafts)
- 🔄 Force Map Reset (regenerate world)
- 🌱 Change Seed (custom seed input)
- 💎 Spawn Rare Items (10x diamond/emerald/netherite)
- 💰 Max Upgrades (pickaxe 10, backpack 200, energy 200)
- 🗺️ World Info (seed, blocks, biome, players)

**Teleport Submenu:**
- 📍 Surface (Y=-1)
- 📍 Underground (Y=10)
- 📍 Deep Caves (Y=25)
- 📍 Mineral Depths (Y=50)
- 📍 Ancient Depths (Y=75)
- 📍 Abyss (Y=100)
- 👤 Teleport to Player (multiplayer)
- 🏛️ Teleport to Structure (mineshafts)
- 🌀 Teleport to Portal (all portals, including private)

**Place Blocks Submenu:**
- 25+ block types (ores, terrain, mineshaft parts, chest)
- Instant placement below player
- No mining required

**Items Submenu:**
- Spawn ladders (custom quantity)
- Spawn torches (custom quantity)
- Spawn portals (custom quantity)

**Structures Submenu:**
- Generate mineshaft at current position
- Discover all hidden structures

---

## Mining Data Persistence

### JSON Serialization (Lines 1006-1100)

**Singleplayer & Multiplayer data storage:**

```python
def to_dict(self) -> dict:
    """Serialize game state to dictionary"""
    # Convert map_data keys from tuples to strings for JSON
    map_data_serialized = {f"{x},{y}": block for (x, y), block in self.map_data.items()}
    
    return {
        "user_id": self.user_id,
        "guild_id": self.guild_id,
        "is_shared": self.is_shared,
        "seed": self.seed,
        "x": self.x,
        "y": self.y,
        "depth": self.depth,
        "energy": self.energy,
        "max_energy": self.max_energy,
        "last_energy_regen": self.last_energy_regen.isoformat(),
        "pickaxe_level": self.pickaxe_level,
        "backpack_capacity": self.backpack_capacity,
        "inventory": self.inventory,
        "coins": self.coins,
        "last_map_regen": self.last_map_regen.isoformat(),
        "map_data": map_data_serialized,
        "items": self.items,
        "ladders": {f"{x},{y}": True for (x, y) in self.ladders.keys()},
        "portals": self.portals,
        "torches": {f"{x},{y}": True for (x, y) in self.torches.keys()},
        "portal_counter": self.portal_counter,
        "structures": self.structures,
        "structure_counter": self.structure_counter,
        "other_players": self.other_players,
        "infinite_energy": self.infinite_energy,
        "infinite_backpack": self.infinite_backpack,
        "auto_reset_enabled": self.auto_reset_enabled
    }

@classmethod
def from_dict(cls, data: dict):
    """Deserialize game state from dictionary"""
    game = cls.__new__(cls)
    game.user_id = data["user_id"]
    game.guild_id = data.get("guild_id")
    game.is_shared = data.get("is_shared", False)
    game.seed = data["seed"]
    game.rng = random.Random(game.seed)
    game.x = data["x"]
    game.y = data["y"]
    game.depth = data["depth"]
    game.energy = data["energy"]
    game.max_energy = data["max_energy"]
    game.last_energy_regen = datetime.fromisoformat(data["last_energy_regen"])
    game.pickaxe_level = data["pickaxe_level"]
    game.backpack_capacity = data["backpack_capacity"]
    game.inventory = data["inventory"]
    game.coins = data["coins"]
    game.last_map_regen = datetime.fromisoformat(data["last_map_regen"])
    game.items = data.get("items", {"ladder": 5, "portal": 2, "torch": 10})
    game.portal_counter = data.get("portal_counter", 0)
    game.structures = data.get("structures", {})
    game.structure_counter = data.get("structure_counter", 0)
    game.infinite_energy = data.get("infinite_energy", False)
    game.infinite_backpack = data.get("infinite_backpack", False)
    game.auto_reset_enabled = data.get("auto_reset_enabled", True)
    
    # Deserialize coordinate keys
    game.ladders = {}
    for key in data.get("ladders", {}).keys():
        x, y = map(int, key.split(","))
        game.ladders[(x, y)] = True
    
    game.portals = data.get("portals", {})
    
    game.torches = {}
    for key in data.get("torches", {}).keys():
        x, y = map(int, key.split(","))
        game.torches[(x, y)] = True
    
    # Deserialize map_data
    game.map_data = {}
    for key, block in data["map_data"].items():
        x, y = map(int, key.split(","))
        game.map_data[(x, y)] = block
    
    return game
```

**Data Structure (data/mining_data.json):**

```json
{
  "games": {
    "123456789": {
      "user_id": 123456789,
      "seed": 542891,
      "x": -15,
      "y": 32,
      "depth": 45,
      "energy": 42,
      "max_energy": 80,
      "pickaxe_level": 3,
      "backpack_capacity": 50,
      "inventory": {
        "diamond": 5,
        "gold": 12,
        "iron": 28
      },
      "coins": 15420,
      "map_data": {
        "0,0": "grass",
        "0,1": "stone",
        "15,32": "air",
        ...
      },
      "ladders": {
        "5,10": true,
        "5,20": true
      },
      "portals": {
        "portal_0": {
          "name": "Home Base",
          "x": 5,
          "y": -1,
          "owner_id": 123456789,
          "public": true
        }
      },
      "torches": {
        "10,25": true,
        "15,30": true
      },
      "structures": {
        "mineshaft_0": {
          "type": "mineshaft",
          "name": "Mineshaft #1",
          "x": -30,
          "y": 18,
          "width": 28,
          "height": 5,
          "discovered": true
        }
      }
    }
  },
  "shared_worlds": {
    "987654321": {
      "world_data": {
        "seed": 123456,
        "map_data": { ... },
        "ladders": { ... },
        "torches": { ... },
        "portals": { ... },
        "structures": { ... }
      },
      "players": {
        "111111111": {
          "x": 10,
          "y": 25,
          "depth": 25,
          "energy": 45,
          "pickaxe_level": 2,
          "inventory": { ... }
        },
        "222222222": {
          "x": -5,
          "y": 40,
          "depth": 50,
          "energy": 30,
          "pickaxe_level": 4,
          "inventory": { ... }
        }
      }
    }
  }
}
```

**Persistence Features:**
- **Automatic saving** after every action (mining, moving, upgrading)
- **Coordinate serialization** (tuples → strings for JSON)
- **Datetime handling** (ISO format strings)
- **Singleplayer:** Each user has own world (`games`)
- **Multiplayer:** One world per server (`shared_worlds`)
- **Backward compatibility:** Defaults for new fields

---

## Mining Commands

### 1. `/mine` - Start/Resume Adventure

**Slash Command (Lines 3060-3065):**

```python
@app_commands.command(name="mine", description="⛏️ Start a procedurally generated mining adventure!")
async def mine_slash(self, interaction: discord.Interaction):
    """Start a mining adventure!"""
    await interaction.response.defer()
    await self.start_mining(interaction, interaction.user.id, interaction.guild.id if interaction.guild else None)
```

**Command Flow:**
1. Check if server has shared mining enabled (`shared_mining_world` config)
2. **Singleplayer Mode:**
   - Load existing game or create new with random seed
   - Sync coins with main economy
   - Resume from saved position
3. **Multiplayer Mode:**
   - Load server's shared world or create new
   - Get player data from world's players dict
   - Apply player position/inventory/upgrades to shared world
   - Track other players' positions
4. Check for 12-hour map reset
5. Render map image (async in executor)
6. Send MiningView with interactive UI

### 2. `L!ownermine` - Developer Mode

**Prefix Command (Lines 3067-3072, owner only):**

```python
@commands.command(name="ownermine")
@commands.is_owner()
async def ownermine_prefix(self, ctx: commands.Context):
    """🔧 Start mining in developer mode (owner only)"""
    await self.start_mining(ctx, ctx.author.id, ctx.guild.id if ctx.guild else None, dev_mode=True)
```

**Developer Mode Features:**
- Same as `/mine` but uses `OwnerMiningView` instead
- Orange accent color (0xFF6600) instead of brown
- Extra developer menu with debugging tools
- Infinite energy/backpack toggles
- Teleportation system
- Block placement
- Structure generation
- Map regeneration

---

## Mining Server Config

### Shared World Toggle (Lines in server_config.py)

**Server Config Integration:**

```python
# In ServerConfig cog
default_config = {
    "shared_mining_world": False,  # Default: singleplayer
    "mining_map_reset": True       # Default: 12h reset enabled
}

# Toggle commands
L!toggle sharedmining  # Enable/disable shared world for server
L!toggle miningreset   # Enable/disable 12h map reset
```

**Config Effects:**

**`shared_mining_world = False` (Default):**
- Each player has own world with unique seed
- No interaction between players
- Personal map reset timer (configurable)
- Can toggle auto-reset per-player

**`shared_mining_world = True`:**
- All players in server share one world
- Same seed, same map_data
- Individual player progress (position, inventory, upgrades)
- Shared structures (ladders, torches, portals)
- See other players on map in real-time
- Server-wide map reset timer

**`mining_map_reset = True` (Default):**
- Map regenerates after 12 hours
- Preserves mined areas (air blocks)
- Resets structures (new mineshafts)
- Timer shown in UI biome bar

**`mining_map_reset = False`:**
- Map never resets automatically
- World persists indefinitely
- Structures stay discovered
- UI shows "reset is off"

---

## Summary

### Key Mining Features

**World Generation:**
- Procedural seed-based generation (100x150 world)
- 6 biomes with depth-based progression
- 25+ block types (ores, terrain, structures)
- Mineshaft structures with loot chests
- Deterministic per-position RNG

**Gameplay:**
- Energy system (1 per 30 seconds)
- Adjacent block mining only
- Backpack capacity management
- Gravity physics (auto-fall)
- Ladder/torch/portal items
- Shop upgrades (pickaxe, backpack, energy)

**Technical:**
- Real-time PNG rendering (PIL + async executor)
- 11x10 viewport (352x320px)
- Darkness overlay with torch lighting
- Multiplayer player tracking
- JSON persistence
- Server config integration

**Multiplayer:**
- Shared world per server (toggle)
- Individual player progress
- Real-time position updates
- Colored player markers
- Public/private portals

**Developer Mode:**
- Infinite energy/backpack
- Teleportation system
- Block placement
- Structure generation
- Map regeneration
- Custom seeds

**Mining Commands:**
- `/mine` - Start/resume adventure (singleplayer or multiplayer)
- `L!ownermine` - Developer mode (owner only)
- Arrow buttons - Movement & mining
- Shop dropdown - Buy upgrades (pickaxe, backpack, energy)
- Inventory dropdown - Place items, view inventory
- Portal menu - Teleport between portals
- Auto-reset toggle (singleplayer only)
