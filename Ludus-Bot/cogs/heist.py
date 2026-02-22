import discord
from discord.ext import commands
import json
import os
import random
import asyncio
from datetime import datetime, timedelta
from typing import Optional
try:
    from utils.stat_hooks import us_inc as _h_inc, us_mg as _h_mg
except Exception:
    _h_inc = _h_mg = None


# ─────────────────────────────────────────────────────────────────────────────
#  Discord V2 interactive lobby view
# ─────────────────────────────────────────────────────────────────────────────

class HeistJoinView(discord.ui.View):
    """Interactive heist lobby with join/launch buttons."""

    def __init__(self, cog: "Heist", channel_id: int, max_crew: int, timeout_secs: int):
        super().__init__(timeout=timeout_secs)
        self.cog = cog
        self.channel_id = channel_id
        self.max_crew = max_crew
        self.message: Optional[discord.Message] = None
        self._executed = False

    # ── helpers ──

    def _build_embed(self) -> discord.Embed:
        heist = self.cog.active_heists.get(self.channel_id)
        if not heist:
            return discord.Embed(title="Heist Over", color=discord.Color.grayed())

        crew_size = len(heist["crew"])
        heist_type = heist["type"]
        bet = heist["bet_amount"]

        if heist_type == "bank":
            title = "🏦 BANK HEIST — RECRUITING"
            color = discord.Color.red()
            reward_text = "10,000–50,000 coins split among crew"
        else:
            target_name = heist.get("target_name", "Unknown")
            title = f"🏢 BUSINESS HEIST — RECRUITING\nTarget: {target_name}"
            color = discord.Color.orange()
            reward_text = "Target's pending business income"

        embed = discord.Embed(title=title, color=color)
        embed.add_field(name="💰 Bet per person", value=f"{bet:,} coins", inline=True)
        embed.add_field(name="👥 Crew", value=f"{crew_size} / {self.max_crew}", inline=True)
        embed.add_field(name="🎯 Reward", value=reward_text, inline=True)

        success_rates = {2: 40, 3: 55, 4: 70, 5: 80, 6: 90}
        rate = success_rates.get(min(crew_size, 6), 40)
        embed.add_field(name="📊 Current success rate", value=f"{rate}%", inline=True)

        # List current crew members (fetch cached users)
        crew_lines = []
        for uid_str in heist["crew"]:
            user = self.cog.bot.get_user(int(uid_str))
            crew_lines.append(user.mention if user else f"<@{uid_str}>")
        if crew_lines:
            embed.add_field(name="🔫 Crew members", value="\n".join(crew_lines), inline=False)

        embed.set_footer(text=f"Need {bet:,} coins to join • Leader can launch once 2+ people are ready")
        return embed

    async def _execute(self) -> None:
        if self._executed:
            return
        self._executed = True
        self.stop()
        for item in self.children:
            item.disabled = True
        channel = self.cog.bot.get_channel(self.channel_id)
        if channel:
            await self.cog._run_heist(channel)

    async def on_timeout(self) -> None:
        await self._execute()

    # ── buttons ──

    @discord.ui.button(label="⚔️ Join Heist!", style=discord.ButtonStyle.success, custom_id="heist_join", row=0)
    async def join_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        heist = self.cog.active_heists.get(self.channel_id)
        if not heist:
            await interaction.response.send_message("❌ No active heist in this channel.", ephemeral=True)
            return

        user_key = str(interaction.user.id)
        if user_key in heist["crew"]:
            await interaction.response.send_message("✅ You're already in the crew!", ephemeral=True)
            return

        if len(heist["crew"]) >= self.max_crew:
            await interaction.response.send_message(f"❌ Crew is full! ({self.max_crew}/{self.max_crew})", ephemeral=True)
            return

        bet = heist["bet_amount"]
        economy_cog = self.cog.bot.get_cog("Economy")
        if not economy_cog:
            await interaction.response.send_message("❌ Economy system offline.", ephemeral=True)
            return

        balance = economy_cog.get_balance(interaction.user.id)
        if balance < bet:
            await interaction.response.send_message(
                f"❌ You need **{bet:,}** coins to join but only have **{balance:,}**.",
                ephemeral=True
            )
            return

        economy_cog.remove_coins(interaction.user.id, bet, "heist_bet")
        heist["crew"][user_key] = bet

        embed = self._build_embed()

        # Auto-launch when crew full
        if len(heist["crew"]) >= self.max_crew:
            for item in self.children:
                item.disabled = True
            await interaction.response.edit_message(embed=embed, view=self)
            await self._execute()
        else:
            await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="🚀 Launch Now!", style=discord.ButtonStyle.blurple, custom_id="heist_launch", row=0)
    async def launch_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        heist = self.cog.active_heists.get(self.channel_id)
        if not heist:
            await interaction.response.send_message("❌ No active heist.", ephemeral=True)
            return

        if interaction.user.id != heist["leader"]:
            await interaction.response.send_message("❌ Only the heist leader can launch early!", ephemeral=True)
            return

        if len(heist["crew"]) < 2:
            await interaction.response.send_message(
                "❌ Need at least **2 crew members** before launching!", ephemeral=True
            )
            return

        for item in self.children:
            item.disabled = True
        embed = self._build_embed()
        embed.set_footer(text="Heist launched by the leader!")
        await interaction.response.edit_message(embed=embed, view=self)
        await self._execute()

    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.danger, custom_id="heist_cancel", row=0)
    async def cancel_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        heist = self.cog.active_heists.get(self.channel_id)
        if not heist:
            await interaction.response.send_message("❌ No active heist.", ephemeral=True)
            return

        if interaction.user.id != heist["leader"]:
            await interaction.response.send_message("❌ Only the heist leader can cancel!", ephemeral=True)
            return

        # Refund everyone
        economy_cog = self.cog.bot.get_cog("Economy")
        if economy_cog:
            for uid_str, bet_amount in heist["crew"].items():
                economy_cog.add_coins(int(uid_str), bet_amount, "heist_cancelled")

        del self.cog.active_heists[self.channel_id]
        self._executed = True
        self.stop()

        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(
            embed=discord.Embed(
                title="🚫 Heist Cancelled",
                description="The leader called it off. All bets have been refunded.",
                color=discord.Color.grayed()
            ),
            view=self
        )


# ─────────────────────────────────────────────────────────────────────────────
#  Cog
# ─────────────────────────────────────────────────────────────────────────────

class Heist(commands.Cog):
    """Team up for heists and rob banks or players"""
    
    def __init__(self, bot):
        self.bot = bot
        self.file_path = "cogs/heists.json"
        self.load_data()
        self.active_heists = {}  # {channel_id: heist_data}
    
    def load_data(self):
        """Load heist data"""
        if os.path.exists(self.file_path):
            with open(self.file_path, 'r') as f:
                self.heist_data = json.load(f)
        else:
            self.heist_data = {}
    
    def save_data(self):
        """Save heist data"""
        with open(self.file_path, 'w') as f:
            json.dump(self.heist_data, f, indent=4)
    
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
    
    def can_start_heist(self, user_id):
        """Check if user can start a heist (30min cooldown)"""
        stats = self.get_user_stats(user_id)
        if not stats["last_heist"]:
            return True, None
        
        last_heist = datetime.fromisoformat(stats["last_heist"])
        cooldown = timedelta(minutes=30)
        time_passed = datetime.utcnow() - last_heist
        
        if time_passed < cooldown:
            time_left = cooldown - time_passed
            minutes = int(time_left.total_seconds() // 60)
            return False, minutes
        
        return True, None
    
    @commands.group(name="heist", invoke_without_command=True)
    async def heist(self, ctx):
        """View heist information"""
        embed = discord.Embed(
            title="🏴‍☠️ Heist System",
            description="Team up to rob banks or businesses!",
            color=discord.Color.dark_red()
        )
        
        embed.add_field(
            name="🏦 Bank Heist",
            value="Rob the bank with your crew!\n"
                  "**Reward:** 10,000-50,000 coins\n"
                  "**Risk:** Lose 10% of bet\n"
                  "**Required:** 2-6 players",
            inline=False
        )
        
        embed.add_field(
            name="🏢 Business Heist",
            value="Rob another player's business!\n"
                  "**Reward:** Their pending income\n"
                  "**Risk:** Lose your bet\n"
                  "**Required:** 2-4 players",
            inline=False
        )
        
        embed.add_field(
            name="📊 Success Rates",
            value="```\n"
                  "2 players: 40%\n"
                  "3 players: 55%\n"
                  "4 players: 70%\n"
                  "5 players: 80%\n"
                  "6 players: 90%\n"
                  "```",
            inline=False
        )
        
        embed.add_field(
            name="ℹ️ How it works",
            value="```\nL!heist bank <bet>         — Start bank job\n"
                  "L!heist business @user <bet> — Rob a business\n"
                  "L!heist stats [@user]        — View your stats\n```\n"
                  "Use the **⚔️ Join Heist!** button in the lobby to join.\n"
                  "Leader can **🚀 Launch** early or **❌ Cancel** at any time.",
            inline=False
        )
        
        embed.set_footer(text="30-minute cooldown between heists • All crew members must bet equally")
        
        await ctx.send(embed=embed)
    
    @heist.command(name="bank")
    async def heist_bank(self, ctx, bet: int):
        """Start a bank heist"""
        # Check cooldown
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
        if not economy_cog:
            await ctx.send("❌ Economy system not loaded!")
            return
        
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

        # Create heist record
        self.active_heists[ctx.channel.id] = {
            "type": "bank",
            "leader": ctx.author.id,
            "crew": {str(ctx.author.id): bet},
            "bet_amount": bet,
            "target": None,
            "target_name": None,
            "started": datetime.utcnow().isoformat()
        }

        view = HeistJoinView(self, ctx.channel.id, max_crew=6, timeout_secs=60)
        embed = view._build_embed()
        msg = await ctx.send(embed=embed, view=view)
        view.message = msg
    
    @heist.command(name="business")
    async def heist_business(self, ctx, target: discord.Member, bet: int):
        """Start a business heist against another player"""
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
        
        # Check protection
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
        
        # Check if heist already active
        if ctx.channel.id in self.active_heists:
            await ctx.send("❌ A heist is already being planned in this channel!")
            return
        
        # Deduct bet from leader
        economy_cog.remove_coins(ctx.author.id, bet, "heist_bet")

        # Create heist record
        self.active_heists[ctx.channel.id] = {
            "type": "business",
            "leader": ctx.author.id,
            "crew": {str(ctx.author.id): bet},
            "bet_amount": bet,
            "target": target.id,
            "target_name": target.display_name,
            "started": datetime.utcnow().isoformat()
        }

        view = HeistJoinView(self, ctx.channel.id, max_crew=4, timeout_secs=45)
        embed = view._build_embed()
        msg = await ctx.send(embed=embed, view=view)
        view.message = msg
    
    async def _run_heist(self, channel: discord.TextChannel) -> None:
        """Execute the heist and post result embed to channel."""
        heist = self.active_heists.get(channel.id)
        if not heist:
            return

        crew_size = len(heist["crew"])

        economy_cog = self.bot.get_cog("Economy")

        if crew_size < 2:
            # Refund everyone
            if economy_cog:
                for user_id, bet_amount in heist["crew"].items():
                    economy_cog.add_coins(int(user_id), bet_amount, "heist_cancelled")
            del self.active_heists[channel.id]
            await channel.send("❌ Heist cancelled — not enough crew members. All bets refunded.")
            return

        # Calculate success rate
        success_rates = {2: 0.40, 3: 0.55, 4: 0.70, 5: 0.80, 6: 0.90}
        success_rate = success_rates.get(min(crew_size, 6), 0.40)

        success = random.random() < success_rate

        if success:
            if heist["type"] == "bank":
                base_reward = random.randint(10000, 50000)
                reward_per_person = base_reward // crew_size

                embed = discord.Embed(
                    title="✅ HEIST SUCCESS — BANK ROBBED!",
                    description=f"The crew cracked the vault and escaped clean!",
                    color=discord.Color.green()
                )

                crew_mentions = []
                for user_id, _bet in heist["crew"].items():
                    uid = int(user_id)
                    if economy_cog:
                        economy_cog.add_coins(uid, reward_per_person, "heist_success")
                    stats = self.get_user_stats(uid)
                    stats["total_heists"] += 1
                    stats["successful"] += 1
                    stats["total_stolen"] += reward_per_person
                    stats["last_heist"] = datetime.utcnow().isoformat()
                    if _h_mg:
                        try:
                            _h_mg(uid, "heist", "win", reward_per_person)
                            _h_inc(uid, "heist_participated")
                            _h_inc(uid, "heist_successful")
                            _h_inc(uid, "heist_coins_earned", reward_per_person)
                        except Exception:
                            pass
                    user = await self.bot.fetch_user(uid)
                    crew_mentions.append(user.mention)

                embed.add_field(name="👥 Crew", value=crew_size, inline=True)
                embed.add_field(name="💰 Total Loot", value=f"{base_reward:,} coins", inline=True)
                embed.add_field(name="🏅 Per Person", value=f"{reward_per_person:,} coins", inline=True)
                embed.add_field(name="🔫 Crew Members", value=", ".join(crew_mentions), inline=False)

            else:  # Business heist
                business_cog = self.bot.get_cog("Business")
                total_stolen = 0
                if business_cog:
                    target_businesses = business_cog.get_user_businesses(heist["target"])
                    for _biz_id, biz_data in target_businesses.get("businesses", {}).items():
                        biz_type = biz_data["type"]
                        level = biz_data["level"]
                        income = business_cog.calculate_income(biz_type, level)
                        last_collect = datetime.fromisoformat(biz_data["last_collect"])
                        hours_passed = (datetime.utcnow() - last_collect).total_seconds() / 3600
                        total_stolen += int(income * hours_passed)
                        biz_data["last_collect"] = datetime.utcnow().isoformat()
                    business_cog.save_data()

                if total_stolen == 0:
                    total_stolen = 1000  # minimum payout

                reward_per_person = total_stolen // crew_size
                target_user = await self.bot.fetch_user(heist["target"])

                embed = discord.Embed(
                    title="✅ HEIST SUCCESS — BUSINESS HIT!",
                    description=f"The crew stripped {target_user.mention}'s income!",
                    color=discord.Color.green()
                )

                crew_mentions = []
                for user_id in heist["crew"]:
                    uid = int(user_id)
                    if economy_cog:
                        economy_cog.add_coins(uid, reward_per_person, "heist_success")
                    stats = self.get_user_stats(uid)
                    stats["total_heists"] += 1
                    stats["successful"] += 1
                    stats["total_stolen"] += reward_per_person
                    stats["last_heist"] = datetime.utcnow().isoformat()
                    if _h_mg:
                        try:
                            _h_mg(uid, "heist", "win", reward_per_person)
                            _h_inc(uid, "heist_participated")
                            _h_inc(uid, "heist_successful")
                            _h_inc(uid, "heist_coins_earned", reward_per_person)
                        except Exception:
                            pass
                    user = await self.bot.fetch_user(uid)
                    crew_mentions.append(user.mention)

                embed.add_field(name="👥 Crew", value=crew_size, inline=True)
                embed.add_field(name="💸 Total Stolen", value=f"{total_stolen:,} coins", inline=True)
                embed.add_field(name="🏅 Per Person", value=f"{reward_per_person:,} coins", inline=True)
                embed.add_field(name="🔫 Crew Members", value=", ".join(crew_mentions), inline=False)

        else:
            # Heist failed — bets already deducted, no refund
            embed = discord.Embed(
                title="❌ HEIST FAILED — GOT CAUGHT!",
                description="The police were waiting. The crew is in cuffs.",
                color=discord.Color.red()
            )

            total_lost = sum(heist["crew"].values())
            crew_mentions = []
            for user_id in heist["crew"]:
                uid = int(user_id)
                stats = self.get_user_stats(uid)
                stats["total_heists"] += 1
                stats["failed"] += 1
                stats["total_lost"] += heist["crew"][user_id]
                stats["last_heist"] = datetime.utcnow().isoformat()
                if _h_mg:
                    try:
                        _h_mg(uid, "heist", "loss", 0)
                        _h_inc(uid, "heist_participated")
                    except Exception:
                        pass
                user = await self.bot.fetch_user(uid)
                crew_mentions.append(user.mention)

            embed.add_field(name="👥 Crew", value=crew_size, inline=True)
            embed.add_field(name="📊 Success Chance Was", value=f"{int(success_rate * 100)}%", inline=True)
            embed.add_field(name="💸 Total Lost", value=f"{total_lost:,} coins", inline=True)
            embed.add_field(name="🔫 Arrested Crew", value=", ".join(crew_mentions), inline=False)

        self.save_data()
        if channel.id in self.active_heists:
            del self.active_heists[channel.id]

        await channel.send(embed=embed)
    
    @heist.command(name="stats")
    async def heist_stats(self, ctx, member: Optional[discord.Member] = None):
        """View heist statistics"""
        target = member or ctx.author
        stats = self.get_user_stats(target.id)
        
        if stats["total_heists"] == 0:
            await ctx.send(f"🏴‍☠️ {target.mention} hasn't participated in any heists yet!")
            return
        
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

async def setup(bot):
    await bot.add_cog(Heist(bot))
