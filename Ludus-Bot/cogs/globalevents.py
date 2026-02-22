import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import asyncio
import random
from datetime import datetime, timedelta
from typing import Optional

# ─── V2 Attack Button ────────────────────────────────────────────────────────

class AttackView(discord.ui.View):
    """Persistent ⚔️ Attack button shown while world boss is alive."""

    def __init__(self, cog: "GlobalEvents"):
        super().__init__(timeout=None)  # keep alive until boss dies
        self.cog = cog

    @discord.ui.button(label="⚔️ Attack!", style=discord.ButtonStyle.danger, custom_id="worldboss_attack")
    async def attack_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle button attack — same logic as L!attack but via button."""
        if "worldboss" not in self.cog.active_events:
            await interaction.response.send_message("❌ No World Boss is active!", ephemeral=True)
            return

        boss_data = self.cog.active_events["worldboss"]
        boss = self.cog.bosses[boss_data["boss"]]

        # Per-user cooldown (30 s)
        user_id = str(interaction.user.id)
        now = datetime.utcnow()
        last = boss_data.get("cooldowns", {}).get(user_id)
        if last:
            diff = (now - datetime.fromisoformat(last)).total_seconds()
            if diff < 30:
                remaining = int(30 - diff)
                await interaction.response.send_message(
                    f"⏳ Cooldown! Attack again in **{remaining}s**.", ephemeral=True
                )
                return

        if "cooldowns" not in boss_data:
            boss_data["cooldowns"] = {}
        boss_data["cooldowns"][user_id] = now.isoformat()

        # Enrage phase: >75% hp gone → 1.5× damage
        hp_gone_pct = 1 - (boss_data["hp"] / boss_data["max_hp"])
        dmg_min, dmg_max = boss["damage_range"]
        if hp_gone_pct >= 0.75:
            dmg_min = int(dmg_min * 1.5)
            dmg_max = int(dmg_max * 1.5)
            enraged = True
        else:
            enraged = False

        dmg = random.randint(dmg_min, dmg_max)
        boss_data["hp"] = max(0, boss_data["hp"] - dmg)
        boss_data["participants"][user_id] = boss_data["participants"].get(user_id, 0) + dmg
        server_id = str(interaction.guild_id) if interaction.guild_id else "dm"
        boss_data["server_damage"][server_id] = boss_data["server_damage"].get(server_id, 0) + dmg
        boss_data["last_hit"] = user_id

        if boss_data["hp"] <= 0:
            await interaction.response.defer()
            await self.cog.defeat_worldboss(interaction.channel)
            self.stop()
            return

        hp_pct = (boss_data["hp"] / boss_data["max_hp"]) * 100
        bars = int(hp_pct / 5)
        bar = "🟩" * bars + ("🟥" if enraged else "⬜") * (20 - bars)
        phase = " 🔥 **ENRAGED!**" if enraged else ""

        embed = discord.Embed(
            title=f"⚔️ {interaction.user.display_name} attacks!{phase}",
            description=(
                f"**Damage Dealt:** `{dmg:,}`\n\n"
                f"**{boss['emoji']} {boss['name']}**\n"
                f"`{bar}` {hp_pct:.1f}%\n"
                f"**HP:** {boss_data['hp']:,} / {boss_data['max_hp']:,}\n\n"
                f"**Total attackers:** {len(boss_data['participants'])}"
            ),
            color=discord.Color.red() if enraged else discord.Color.orange()
        )
        await interaction.response.send_message(embed=embed)


    """Epic server vs server global events - Owner only!"""
    
    def __init__(self, bot):
        self.bot = bot
        data_dir = os.getenv("RENDER_DISK_PATH", ".")
        self.events_file = os.path.join(data_dir, "global_events.json")
        self.events_data = self.load_events()
        self.active_events = {}
        
        # Factions for WAR event
        self.factions = {
            "iron": {"name": "⚔️ Iron Legion", "emoji": "⚔️", "color": 0x808080},
            "ash": {"name": "🔥 Ashborn", "emoji": "🔥", "color": 0xFF4500},
            "void": {"name": "🌑 Voidwalkers", "emoji": "🌑", "color": 0x4B0082},
            "sky": {"name": "🌬️ Skybound", "emoji": "🌬️", "color": 0x87CEEB}
        }
        
        # World bosses
        self.bosses = {
            "void_titan": {"name": "Void Titan", "hp": 50000000, "emoji": "👹", "damage_range": (1000, 5000)},
            "storm_king": {"name": "Storm King", "hp": 75000000, "emoji": "⚡", "damage_range": (1500, 6000)},
            "shadow_lord": {"name": "Shadow Lord", "hp": 100000000, "emoji": "👁️", "damage_range": (2000, 8000)},
            "chaos_beast": {"name": "Chaos Beast", "hp": 60000000, "emoji": "💀", "damage_range": (1200, 5500)}
        }
        
        # Hunt clues/challenges
        self.hunt_challenges = [
            {"type": "message", "desc": "Send a message containing the word '{word}'", "words": ["dragon", "treasure", "mystery", "adventure", "galaxy"]},
            {"type": "reaction", "desc": "React to this message with {emoji}", "emojis": ["🎯", "🎪", "🎭", "🎨", "🎸"]},
            {"type": "riddle", "desc": "Solve this riddle: {riddle}", "points": 100},
            {"type": "speed", "desc": "Type this phrase exactly: '{phrase}'", "phrases": ["the quick brown fox", "speed demon", "lightning fast"]},
        ]
    
    def load_events(self):
        """Load events data"""
        if os.path.exists(self.events_file):
            try:
                with open(self.events_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def save_events(self):
        """Save events data"""
        try:
            with open(self.events_file, 'w') as f:
                json.dump(self.events_data, f, indent=4)
        except Exception as e:
            print(f"Error saving events data: {e}")
    
    @commands.command(name="event")
    @commands.is_owner()
    async def start_event(self, ctx, event_type: str, duration: Optional[int] = None):
        """Start a global event (OWNER ONLY)
        
        Events:
        - war [hours] - Server vs Server faction war
        - worldboss [boss] - Global boss raid
        - hunt [minutes] - Global scavenger hunt
        - chaos [minutes] - Chaos festival
        - list - List active events
        - end <type> - End an event
        """
        if event_type.lower() == "list":
            if not self.active_events:
                await ctx.send("📋 No active events running.")
                return
            
            embed = discord.Embed(title="🌐 Active Global Events", color=discord.Color.gold())
            for evt_type, evt_data in self.active_events.items():
                end_time = datetime.fromisoformat(evt_data["end_time"])
                embed.add_field(
                    name=evt_type.upper(),
                    value=f"Ends: <t:{int(end_time.timestamp())}:R>",
                    inline=False
                )
            await ctx.send(embed=embed)
            return
        
        elif event_type.lower() == "end":
            if duration is None:
                await ctx.send("❌ Specify event type to end: war, worldboss, hunt, chaos")
                return
            event_to_end = str(duration).lower()  # duration parameter holds event name
            if event_to_end in self.active_events:
                await self.end_event(event_to_end, ctx.channel)
                await ctx.send(f"✅ Ended {event_to_end} event!")
            else:
                await ctx.send(f"❌ No active {event_to_end} event!")
            return
        
        elif event_type.lower() == "war":
            await self.start_war_event(ctx, duration or 24)
        
        elif event_type.lower() == "worldboss":
            boss_name = ctx.message.content.split()[2] if len(ctx.message.content.split()) > 2 else "void_titan"
            await self.start_worldboss_event(ctx, boss_name)
        
        elif event_type.lower() == "hunt":
            await self.start_hunt_event(ctx, duration or 30)
        
        elif event_type.lower() == "chaos":
            await self.start_chaos_event(ctx, duration or 30)
        
        else:
            await ctx.send(f"❌ Invalid event! Use: war, worldboss, hunt, chaos, list, or end")
    
    async def start_war_event(self, ctx, hours):
        """Start WAR event"""
        if "war" in self.active_events:
            await ctx.send("❌ A WAR event is already running!")
            return
        
        end_time = datetime.now() + timedelta(hours=hours)
        
        self.active_events["war"] = {
            "end_time": end_time.isoformat(),
            "factions": {faction: {"servers": [], "points": 0, "members": []} for faction in self.factions.keys()},
            "started_by": ctx.author.id
        }
        
        # Log event spawn
        logger = self.bot.get_cog("BotLogger")
        if logger:
            await logger.log_event_spawn(
                "WAR", 
                ctx.guild.id if ctx.guild else 0, 
                ctx.author.id,
                f"Duration: {hours} hours"
            )
        
        # Announce globally
        embed = discord.Embed(
            title="⚔️ GLOBAL WAR HAS BEGUN! ⚔️",
            description=f"**Duration:** {hours} hours\n"
                       f"**Ends:** <t:{int(end_time.timestamp())}:R>\n\n"
                       f"**Choose Your Faction:**\n" +
                       "\n".join([f"{data['emoji']} **{data['name']}**" for data in self.factions.values()]) +
                       "\n\n**Earn War Points By:**\n"
                       "⚔️ Winning games (chess, minigames)\n"
                       "🎯 Solving puzzles\n"
                       "💰 Gambling wins\n"
                       "🎣 Fishing tournaments\n\n"
                       f"**Rewards:** Massive PsyCoins + War Champion role + Global leaderboard fame!\n\n"
                       f"Use `L!joinfaction <iron/ash/void/sky>` to join!",
            color=discord.Color.red()
        )
        embed.set_footer(text=f"Started by {ctx.author.name}")
        
        # Announce to all servers
        for guild in self.bot.guilds:
            try:
                channel = guild.system_channel or guild.text_channels[0]
                await channel.send(embed=embed)
            except:
                pass
        
        await ctx.send("✅ WAR EVENT STARTED! Announced to all servers!")

        # Schedule end in background (non-blocking)
        asyncio.create_task(self._auto_end_war(ctx.channel, hours))

    async def _auto_end_war(self, channel: discord.TextChannel, hours: int) -> None:
        """Background task: auto-end WAR after given hours."""
        await asyncio.sleep(hours * 3600)
        if "war" in self.active_events:
            await self.end_event("war", channel)
    
    @commands.command(name="joinfaction")
    async def join_faction(self, ctx, faction: str):
        """Join a faction in the WAR event"""
        if "war" not in self.active_events:
            await ctx.send("❌ No WAR event is currently running!")
            return
        
        faction = faction.lower()
        if faction not in self.factions:
            await ctx.send(f"❌ Invalid faction! Choose: {', '.join(self.factions.keys())}")
            return
        
        war_data = self.active_events["war"]
        user_id = str(ctx.author.id)
        
        # Check if already in a faction
        for f_id, f_data in war_data["factions"].items():
            if user_id in f_data["members"]:
                await ctx.send(f"❌ You're already in {self.factions[f_id]['name']}!")
                return
        
        # Join faction
        war_data["factions"][faction]["members"].append(user_id)
        if str(ctx.guild.id) not in war_data["factions"][faction]["servers"]:
            war_data["factions"][faction]["servers"].append(str(ctx.guild.id))
        
        faction_data = self.factions[faction]
        embed = discord.Embed(
            title=f"{faction_data['emoji']} Welcome to {faction_data['name']}!",
            description=f"{ctx.author.mention} has joined the battle!\n\n"
                       f"Earn war points for your faction by:\n"
                       f"• Winning games\n"
                       f"• Completing challenges\n"
                       f"• Helping your server dominate!\n\n"
                       f"Use `L!warleaderboard` to check standings!",
            color=faction_data['color']
        )
        
        await ctx.send(embed=embed)
    
    @commands.command(name="warleaderboard")
    async def war_leaderboard(self, ctx):
        """View WAR leaderboard"""
        if "war" not in self.active_events:
            await ctx.send("❌ No WAR event is currently running!")
            return
        
        war_data = self.active_events["war"]
        end_time = datetime.fromisoformat(war_data["end_time"])
        
        # Sort factions by points
        sorted_factions = sorted(
            war_data["factions"].items(),
            key=lambda x: x[1]["points"],
            reverse=True
        )
        
        embed = discord.Embed(
            title="⚔️ WAR LEADERBOARD ⚔️",
            description=f"**Ends:** <t:{int(end_time.timestamp())}:R>\n\n",
            color=discord.Color.gold()
        )
        
        for i, (faction_id, faction_data) in enumerate(sorted_factions, 1):
            faction_info = self.factions[faction_id]
            medal = ["🥇", "🥈", "🥉", "4️⃣"][i-1] if i <= 4 else f"{i}️⃣"
            embed.add_field(
                name=f"{medal} {faction_info['name']}",
                value=f"**Points:** {faction_data['points']:,}\n"
                      f"**Servers:** {len(faction_data['servers'])}\n"
                      f"**Warriors:** {len(faction_data['members'])}",
                inline=False
            )
        
        await ctx.send(embed=embed)
    
    async def start_worldboss_event(self, ctx, boss_name):
        """Start World Boss event"""
        if "worldboss" in self.active_events:
            await ctx.send("❌ A World Boss is already active!")
            return
        
        if boss_name not in self.bosses:
            boss_name = "void_titan"
        
        boss = self.bosses[boss_name]
        
        self.active_events["worldboss"] = {
            "boss": boss_name,
            "hp": boss["hp"],
            "max_hp": boss["hp"],
            "participants": {},
            "server_damage": {},
            "cooldowns": {},
            "last_hit": None,
            "started": datetime.now().isoformat()
        }
        
        embed = discord.Embed(
            title=f"🐉 WORLD BOSS INVASION! 🐉",
            description=(
                f"**{boss['emoji']} {boss['name']}** has appeared!\n\n"
                f"**Global HP:** {boss['hp']:,}\n\n"
                f"Every attack from ANY server damages the boss!\n\n"
                f"**Click \u2694\ufe0f Attack! or use `L!attack`**\n"
                f"**Use `L!bossstats` to check progress!**\n\n"
                f"**All participants rewarded when defeated!**\n"
                f"🏆 Top damage dealers get bonus rewards!\n"
                f"⚡ Last hit bonus: **15,000 coins**!\n"
                f"💪 Enrage at 75% health lost (×1.5 dmg)!"
            ),
            color=discord.Color.dark_red()
        )

        view = AttackView(self)
        for guild in self.bot.guilds:
            try:
                channel = guild.system_channel or guild.text_channels[0]
                await channel.send(embed=embed, view=view)
            except:
                pass
        
        await ctx.send("✅ WORLD BOSS EVENT STARTED!")
    
    @commands.command(name="attack")
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def attack_boss(self, ctx):
        """Attack the world boss"""
        if "worldboss" not in self.active_events:
            await ctx.send("❌ No World Boss is currently active!")
            return

        boss_data = self.active_events["worldboss"]
        boss = self.bosses[boss_data["boss"]]

        # Enrage at 75% hp gone
        hp_gone_pct = 1 - (boss_data["hp"] / boss_data["max_hp"])
        dmg_min, dmg_max = boss["damage_range"]
        if hp_gone_pct >= 0.75:
            dmg_min = int(dmg_min * 1.5)
            dmg_max = int(dmg_max * 1.5)
            enraged = True
        else:
            enraged = False

        damage = random.randint(dmg_min, dmg_max)
        boss_data["hp"] = max(0, boss_data["hp"] - damage)

        user_id = str(ctx.author.id)
        server_id = str(ctx.guild.id) if ctx.guild else "dm"
        boss_data.setdefault("cooldowns", {})
        boss_data["participants"][user_id] = boss_data["participants"].get(user_id, 0) + damage
        boss_data["server_damage"][server_id] = boss_data["server_damage"].get(server_id, 0) + damage
        boss_data["last_hit"] = user_id

        if boss_data["hp"] <= 0:
            await self.defeat_worldboss(ctx.channel)
            return

        hp_pct = (boss_data["hp"] / boss_data["max_hp"]) * 100
        bars = int(hp_pct / 5)
        bar = "🟩" * bars + ("🟥" if enraged else "⬜") * (20 - bars)
        phase = " 🔥 **ENRAGED!**" if enraged else ""

        embed = discord.Embed(
            title=f"⚔️ {ctx.author.display_name} attacks!{phase}",
            description=(
                f"**Damage Dealt:** `{damage:,}`\n\n"
                f"**{boss['emoji']} {boss['name']}**\n"
                f"`{bar}` {hp_pct:.1f}%\n"
                f"**HP:** {boss_data['hp']:,} / {boss_data['max_hp']:,}\n\n"
                f"**Total attackers:** {len(boss_data['participants'])}"
            ),
            color=discord.Color.red() if enraged else discord.Color.orange()
        )
        await ctx.send(embed=embed)
    
    async def defeat_worldboss(self, channel: discord.TextChannel):
        """Handle world boss defeat"""
        boss_data = self.active_events.get("worldboss")
        if not boss_data:
            return
        boss = self.bosses[boss_data["boss"]]
        
        # Award rewards
        economy_cog = self.bot.get_cog("Economy")
        
        # Top 10 players
        top_players = sorted(boss_data["participants"].items(), key=lambda x: -x[1])[:10]
        
        # Reward all participants
        for user_id, damage in boss_data["participants"].items():
            base_reward = 5000
            damage_bonus = int(damage / 100)
            total = base_reward + damage_bonus
            
            if economy_cog:
                economy_cog.add_coins(int(user_id), total, "worldboss_participation")
        
        # Bonus for top 10
        if economy_cog:
            for i, (user_id, damage) in enumerate(top_players):
                bonus = 10000 - (i * 1000)
                economy_cog.add_coins(int(user_id), bonus, "worldboss_top_damage")
        
        # Last hit bonus
        if boss_data["last_hit"] and economy_cog:
            economy_cog.add_coins(int(boss_data["last_hit"]), 15000, "worldboss_last_hit")
        
        # Announce victory
        top_text = "\n".join([
            f"{i+1}. <@{user_id}> - {damage:,} damage"
            for i, (user_id, damage) in enumerate(top_players[:5])
        ])
        
        embed = discord.Embed(
            title=f"🎉 {boss['emoji']} {boss['name']} DEFEATED! 🎉",
            description=f"**Total Participants:** {len(boss_data['participants'])}\n"
                       f"**Total Damage:** {boss_data['max_hp']:,}\n\n"
                       f"**Top 5 Warriors:**\n{top_text}\n\n"
                       f"**Last Hit:** <@{boss_data['last_hit']}> 💀\n\n"
                       f"**All participants have been rewarded!**",
            color=discord.Color.gold()
        )
        
        for guild in self.bot.guilds:
            try:
                ch = guild.system_channel or guild.text_channels[0]
                await ch.send(embed=embed)
            except:
                pass

        del self.active_events["worldboss"]
        self.save_events()
    
    @commands.command(name="bossstats")
    async def boss_stats(self, ctx):
        """View world boss stats"""
        if "worldboss" not in self.active_events:
            await ctx.send("❌ No World Boss is currently active!")
            return
        
        boss_data = self.active_events["worldboss"]
        boss = self.bosses[boss_data["boss"]]
        
        hp_percent = (boss_data["hp"] / boss_data["max_hp"]) * 100
        
        # Top 5 servers with names
        top_servers = sorted(boss_data["server_damage"].items(), key=lambda x: -x[1])[:5]
        server_lines = []
        for i, (guild_id, damage) in enumerate(top_servers, 1):
            guild_obj = self.bot.get_guild(int(guild_id))
            guild_name = guild_obj.name if guild_obj else f"Server #{guild_id[:6]}"
            server_lines.append(f"{i}. **{guild_name}** — {damage:,} dmg")
        server_text = "\n".join(server_lines) or "None yet"
        
        embed = discord.Embed(
            title=f"{boss['emoji']} {boss['name']} Status",
            description=f"**HP:** {boss_data['hp']:,} / {boss_data['max_hp']:,}\n"
                       f"**HP %:** {hp_percent:.1f}%\n\n"
                       f"{'🟩' * int(hp_percent / 5)}{'⬜' * (20 - int(hp_percent / 5))}\n\n"
                       f"**Total Attackers:** {len(boss_data['participants'])}\n"
                       f"**Servers Participating:** {len(boss_data['server_damage'])}\n\n"
                       f"**Top 5 Servers:**\n{server_text}",
            color=discord.Color.red()
        )
        
        await ctx.send(embed=embed)
    
    async def start_hunt_event(self, ctx, minutes):
        """Start Target Hunt event"""
        if "hunt" in self.active_events:
            await ctx.send("❌ A Target Hunt is already running!")
            return
        
        end_time = datetime.now() + timedelta(minutes=minutes)
        
        self.active_events["hunt"] = {
            "end_time": end_time.isoformat(),
            "server_scores": {},
            "player_scores": {},
            "current_challenge": None
        }
        
        embed = discord.Embed(
            title="🎯 GLOBAL TARGET HUNT BEGINS! 🎯",
            description=f"**Duration:** {minutes} minutes\n"
                       f"**Ends:** <t:{int(end_time.timestamp())}:R>\n\n"
                       f"Random challenges will appear!\n"
                       f"Be the first to complete them!\n"
                       f"Earn points for your server!\n\n"
                       f"**Watch this channel for challenges!**",
            color=discord.Color.green()
        )
        
        for guild in self.bot.guilds:
            try:
                channel = guild.system_channel or guild.text_channels[0]
                await channel.send(embed=embed)
            except:
                pass
        
        await ctx.send("✅ TARGET HUNT STARTED!")
        
        # Schedule random challenges
        asyncio.create_task(self.run_hunt_challenges(ctx, minutes))
    
    async def run_hunt_challenges(self, ctx, duration_minutes):
        """Run random hunt challenges"""
        end_time = datetime.now() + timedelta(minutes=duration_minutes)
        
        while datetime.now() < end_time and "hunt" in self.active_events:
            await asyncio.sleep(random.randint(60, 180))  # 1-3 minutes between challenges
            
            if "hunt" not in self.active_events:
                break
            
            challenge = random.choice(self.hunt_challenges)
            
            if challenge["type"] == "message":
                word = random.choice(challenge["words"])
                desc = challenge["desc"].format(word=word)
                
                embed = discord.Embed(
                    title="🎯 NEW CHALLENGE!",
                    description=desc + f"\n\n**First to complete gets 100 points!**",
                    color=discord.Color.blue()
                )
                
                for guild in self.bot.guilds:
                    try:
                        channel = guild.system_channel or guild.text_channels[0]
                        await channel.send(embed=embed)
                    except:
                        pass
        
        if "hunt" in self.active_events:
            await self.end_event("hunt", ctx.channel)
    
    async def start_chaos_event(self, ctx, minutes):
        """Start Chaos Festival"""
        await ctx.send("🎭 CHAOS FESTIVAL - Coming in next update! This event causes random mayhem every minute!")
    
    async def end_event(self, event_type, channel):
        """End an event and announce results"""
        if event_type not in self.active_events:
            return
        
        event_data = self.active_events[event_type]
        
        # Log event end
        logger = self.bot.get_cog("BotLogger")
        if logger:
            await logger.log_event_end(event_type.upper(), f"Event completed")
        
        if event_type == "war":
            # Show final results
            sorted_factions = sorted(
                event_data["factions"].items(),
                key=lambda x: x[1]["points"],
                reverse=True
            )
            
            winner_id, winner_data = sorted_factions[0]
            winner_faction = self.factions[winner_id]
            
            embed = discord.Embed(
                title="⚔️ WAR HAS ENDED! ⚔️",
                description=f"**WINNER:** {winner_faction['emoji']} **{winner_faction['name']}**\n"
                           f"**Total Points:** {winner_data['points']:,}\n\n"
                           f"All warriors have been rewarded!",
                color=winner_faction['color']
            )
            
            # Reward winners
            economy_cog = self.bot.get_cog("Economy")
            if economy_cog:
                for user_id in winner_data["members"]:
                    economy_cog.add_coins(int(user_id), 10000, "war_victory")
            
            for guild in self.bot.guilds:
                try:
                    ch = guild.system_channel or guild.text_channels[0]
                    await ch.send(embed=embed)
                except:
                    pass
        
        del self.active_events[event_type]
        self.save_events()
    
    def add_war_points(self, user_id, guild_id, points):
        """Add war points when users win games"""
        if "war" not in self.active_events:
            return False
        
        user_id = str(user_id)
        guild_id = str(guild_id)
        
        # Find user's faction
        for faction_id, faction_data in self.active_events["war"]["factions"].items():
            if user_id in faction_data["members"]:
                faction_data["points"] += points
                return True
        
        return False

async def setup(bot):
    await bot.add_cog(GlobalEvents(bot))
