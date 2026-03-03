import discord
from discord.ext import commands
import json
import os
import random
from datetime import datetime, timezone, timedelta
from typing import Optional


def _parse_ts(s):
    """Parse ISO timestamp – handles both naive (old data) and tz-aware strings."""
    from datetime import datetime as _dt, timezone as _tz
    d = _dt.fromisoformat(str(s))
    return d if d.tzinfo else d.replace(tzinfo=_tz.utc)


class MarriageProposalView(discord.ui.View):
    """Interactive Accept / Decline buttons sent with a marriage proposal."""

    def __init__(self, cog: "Marriage", proposer_id: int, partner: discord.Member, marriage_cost: int):
        super().__init__(timeout=300)  # 5 minutes
        self.cog = cog
        self.proposer_id = proposer_id
        self.partner = partner
        self.marriage_cost = marriage_cost
        self.responded = False
        self.message: discord.Message | None = None

    # ── guard: only the target may click ────────────────────────────────────
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.partner.id:
            await interaction.response.send_message(
                "❌ This proposal isn’t for you!", ephemeral=True
            )
            return False
        return True

    def _disable(self) -> None:
        for item in self.children:
            item.disabled = True

    # ── Accept ─────────────────────────────────────────────────────────────────
    @discord.ui.button(label="Accept 💍", style=discord.ButtonStyle.success)
    async def accept_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.responded:
            await interaction.response.send_message("This proposal was already answered!", ephemeral=True)
            return
        self.responded = True
        self._disable()
        self.stop()

        cog = self.cog

        if cog.is_married(interaction.user.id):
            embed = discord.Embed(
                title="❌ Already Married",
                description=f"{interaction.user.mention} is already married!",
                color=discord.Color.red(),
            )
            await interaction.response.edit_message(embed=embed, view=self)
            cog.active_proposals.pop(self.proposer_id, None)
            return

        economy_cog = cog.bot.get_cog("Economy")
        if not economy_cog:
            await interaction.response.edit_message(
                content="❌ Economy system unavailable!", embed=None, view=self
            )
            cog.active_proposals.pop(self.proposer_id, None)
            return

        if economy_cog.get_balance(self.proposer_id) < self.marriage_cost:
            embed = discord.Embed(
                title="❌ Proposal Cancelled",
                description="The proposer no longer has enough coins.",
                color=discord.Color.red(),
            )
            await interaction.response.edit_message(embed=embed, view=self)
            cog.active_proposals.pop(self.proposer_id, None)
            return

        # --- process marriage ---
        economy_cog.remove_coins(self.proposer_id, self.marriage_cost)
        marriage_date = discord.utils.utcnow().isoformat()

        pm = cog.get_marriage(self.proposer_id)
        pm["spouse"] = interaction.user.id
        pm["married_since"] = marriage_date
        pm["shared_bank"] = 0
        pm["love_points"] = 0

        qm = cog.get_marriage(interaction.user.id)
        qm["spouse"] = self.proposer_id
        qm["married_since"] = marriage_date
        qm["shared_bank"] = 0
        qm["love_points"] = 0

        cog.save_data()
        cog.active_proposals.pop(self.proposer_id, None)

        # ── sync profile stats ──
        profile_cog = cog.bot.get_cog("Profile")
        if profile_cog:
            profile_cog.increment_stat(self.proposer_id, "marriages")
            profile_cog.increment_stat(interaction.user.id, "marriages")

        try:
            proposer = await cog.bot.fetch_user(self.proposer_id)
            proposer_mention = proposer.mention
        except Exception:
            proposer_mention = f"<@{self.proposer_id}>"

        embed = discord.Embed(
            title="💒 Just Married!",
            description=f"{proposer_mention} and {interaction.user.mention} are now married! 💕",
            color=discord.Color.gold(),
        )
        embed.add_field(
            name="Benefits Unlocked",
            value="✅ Shared bank\n✅ Couple quests\n✅ Daily bonuses",
            inline=True,
        )
        embed.add_field(
            name="Commands",
            value="`L!spouse` — View info\n`L!bank` — Shared bank\n`L!couplequests` — Quests",
            inline=True,
        )
        embed.set_footer(text=f"Married since {discord.utils.utcnow().strftime('%B %d, %Y')}")
        await interaction.response.edit_message(embed=embed, view=self)

    # ── Decline ───────────────────────────────────────────────────────────
    @discord.ui.button(label="Decline 💔", style=discord.ButtonStyle.danger)
    async def decline_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.responded:
            await interaction.response.send_message("This proposal was already answered!", ephemeral=True)
            return
        self.responded = True
        self._disable()
        self.stop()

        self.cog.active_proposals.pop(self.proposer_id, None)

        try:
            proposer = await self.cog.bot.fetch_user(self.proposer_id)
            proposer_mention = proposer.mention
        except Exception:
            proposer_mention = f"<@{self.proposer_id}>"

        embed = discord.Embed(
            title="💔 Proposal Declined",
            description=f"{interaction.user.mention} declined {proposer_mention}’s proposal.",
            color=discord.Color.dark_gray(),
        )
        await interaction.response.edit_message(embed=embed, view=self)

    # ── Timeout ──────────────────────────────────────────────────────────
    async def on_timeout(self) -> None:
        self.cog.active_proposals.pop(self.proposer_id, None)
        if not self.responded:
            self._disable()
            if self.message:
                try:
                    embed = discord.Embed(
                        title="⏰ Proposal Expired",
                        description=f"{self.partner.mention} didn’t respond in time.",
                        color=discord.Color.dark_gray(),
                    )
                    await self.message.edit(embed=embed, view=self)
                except Exception:
                    pass


# ─────────────────────────────────────────────────────────────────────────────
# Shared bank modals & view
# ─────────────────────────────────────────────────────────────────────────────

class DepositModal(discord.ui.Modal, title="Deposit to Shared Bank 💰"):
    amount = discord.ui.TextInput(
        label="Amount",
        placeholder="Enter the amount to deposit…",
        min_length=1,
        max_length=12,
    )

    def __init__(self, cog: "Marriage", user_id: int):
        super().__init__()
        self.cog = cog
        self.user_id = user_id

    async def on_submit(self, interaction: discord.Interaction) -> None:
        try:
            amount = int(self.amount.value.replace(",", "").strip())
        except ValueError:
            await interaction.response.send_message("❌ Enter a valid whole number!", ephemeral=True)
            return
        if amount <= 0:
            await interaction.response.send_message("❌ Amount must be positive!", ephemeral=True)
            return

        if not self.cog.is_married(self.user_id):
            await interaction.response.send_message("❌ You're not married!", ephemeral=True)
            return

        economy_cog = self.cog.bot.get_cog("Economy")
        balance = economy_cog.get_balance(self.user_id)
        if balance < amount:
            await interaction.response.send_message(
                f"❌ You only have **{balance:,}** coins!", ephemeral=True
            )
            return

        economy_cog.remove_coins(self.user_id, amount)

        marriage = self.cog.get_marriage(self.user_id)
        spouse_marriage = self.cog.get_marriage(marriage["spouse"])
        marriage["shared_bank"] += amount
        spouse_marriage["shared_bank"] += amount
        self.cog.save_data()

        embed = discord.Embed(
            title="🏦 Deposit Successful",
            description=f"✅ Added **{amount:,}** coins to the shared bank!",
            color=discord.Color.green(),
        )
        embed.add_field(name="New Balance", value=f"{marriage['shared_bank']:,} coins", inline=True)
        await interaction.response.send_message(embed=embed, ephemeral=True)


class WithdrawModal(discord.ui.Modal, title="Withdraw from Shared Bank 💸"):
    amount = discord.ui.TextInput(
        label="Amount",
        placeholder="Enter the amount to withdraw…",
        min_length=1,
        max_length=12,
    )

    def __init__(self, cog: "Marriage", user_id: int):
        super().__init__()
        self.cog = cog
        self.user_id = user_id

    async def on_submit(self, interaction: discord.Interaction) -> None:
        try:
            amount = int(self.amount.value.replace(",", "").strip())
        except ValueError:
            await interaction.response.send_message("❌ Enter a valid whole number!", ephemeral=True)
            return
        if amount <= 0:
            await interaction.response.send_message("❌ Amount must be positive!", ephemeral=True)
            return

        if not self.cog.is_married(self.user_id):
            await interaction.response.send_message("❌ You're not married!", ephemeral=True)
            return

        marriage = self.cog.get_marriage(self.user_id)
        if marriage["shared_bank"] < amount:
            await interaction.response.send_message(
                f"❌ Shared bank only has **{marriage['shared_bank']:,}** coins!", ephemeral=True
            )
            return

        economy_cog = self.cog.bot.get_cog("Economy")
        economy_cog.add_coins(self.user_id, amount, "shared_bank_withdraw")

        spouse_marriage = self.cog.get_marriage(marriage["spouse"])
        marriage["shared_bank"] -= amount
        spouse_marriage["shared_bank"] -= amount
        self.cog.save_data()

        embed = discord.Embed(
            title="🏦 Withdrawal Successful",
            description=f"✅ Withdrew **{amount:,}** coins from the shared bank!",
            color=discord.Color.green(),
        )
        embed.add_field(name="Remaining Balance", value=f"{marriage['shared_bank']:,} coins", inline=True)
        await interaction.response.send_message(embed=embed, ephemeral=True)


class SharedBankView(discord.ui.View):
    """Deposit / Withdraw buttons for the married couple's shared bank."""

    def __init__(self, cog: "Marriage", user_id: int, spouse_id: int):
        super().__init__(timeout=120)
        self.cog = cog
        self.user_id = user_id
        self.spouse_id = spouse_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id not in (self.user_id, self.spouse_id):
            await interaction.response.send_message(
                "❌ Only the couple can use this bank!", ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="Deposit 💰", style=discord.ButtonStyle.success)
    async def deposit_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(DepositModal(self.cog, interaction.user.id))

    @discord.ui.button(label="Withdraw 💸", style=discord.ButtonStyle.primary)
    async def withdraw_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(WithdrawModal(self.cog, interaction.user.id))


class Marriage(commands.Cog):
    """Marry other users and complete couple quests"""
    
    def __init__(self, bot):
        self.bot = bot
        data_dir = os.getenv("RENDER_DISK_PATH", "data")
        os.makedirs(data_dir, exist_ok=True)
        self.file_path = os.path.join(data_dir, "marriages.json")
        self._migrate_old_file()
        self.load_data()
        self.active_proposals = {}  # {user_id: {partner, channel_id, expires}}

    def _migrate_old_file(self):
        """Move legacy cogs/marriages.json → data/marriages.json on first run."""
        import shutil
        old = os.path.join("cogs", "marriages.json")
        if os.path.exists(old) and not os.path.exists(self.file_path):
            shutil.copy2(old, self.file_path)
            print(f"[MARRIAGE] Migrated data: {old} → {self.file_path}")
    
    def load_data(self):
        """Load marriage data"""
        if os.path.exists(self.file_path):
            with open(self.file_path, 'r') as f:
                self.marriage_data = json.load(f)
        else:
            self.marriage_data = {}
    
    def save_data(self):
        """Save marriage data"""
        with open(self.file_path, 'w') as f:
            json.dump(self.marriage_data, f, indent=4)
    
    def get_marriage(self, user_id):
        """Get user's marriage data"""
        user_key = str(user_id)
        if user_key not in self.marriage_data:
            self.marriage_data[user_key] = {
                "spouse": None,
                "married_since": None,
                "shared_bank": 0,
                "completed_quests": [],
                "love_points": 0,
                "divorces": 0
            }
        return self.marriage_data[user_key]
    
    def is_married(self, user_id):
        """Check if user is married"""
        marriage = self.get_marriage(user_id)
        return marriage["spouse"] is not None
    
    def get_couple_quests(self):
        """Get available couple quests — 15 quests across 3 tiers."""
        return {
            # ── Tier 1 — Easy (daily-ish) ──────────────────────────────
            "date_night": {
                "name": "💑 Date Night",
                "description": "Both partners send a message in the same channel on the same day",
                "reward": 2_000,
                "love_points": 5,
                "tier": 1,
            },
            "sweet_words": {
                "name": "🗣️ Sweet Words",
                "description": "Both partners use `L!rep` on each other in the same week",
                "reward": 1_500,
                "love_points": 4,
                "tier": 1,
            },
            "coinflip_together": {
                "name": "🪙 Heads or Tails",
                "description": "Both partners play `L!coinflip` on the same day",
                "reward": 1_000,
                "love_points": 3,
                "tier": 1,
            },
            "daily_duo": {
                "name": "📅 Daily Duo",
                "description": "Both partners claim their `L!daily` reward on the same day",
                "reward": 2_500,
                "love_points": 5,
                "tier": 1,
            },
            "fish_date": {
                "name": "🎣 Fishing Date",
                "description": "Both partners catch at least 3 fish on the same day",
                "reward": 3_000,
                "love_points": 6,
                "tier": 1,
            },
            # ── Tier 2 — Medium (weekly) ───────────────────────────────
            "gift_exchange": {
                "name": "🎁 Gift Exchange",
                "description": "Each partner deposits 1,000+ coins to the shared bank",
                "reward": 5_000,
                "love_points": 10,
                "tier": 2,
            },
            "gambler_pair": {
                "name": "🎰 Fortune Hunters",
                "description": "Together win 5,000+ coins from gambling on the same day",
                "reward": 7_500,
                "love_points": 12,
                "tier": 2,
            },
            "mine_together": {
                "name": "⛏️ Mining Duo",
                "description": "Both partners mine at least 10 times in a single day",
                "reward": 6_000,
                "love_points": 10,
                "tier": 2,
            },
            "farm_harvest": {
                "name": "🌾 Harvest Season",
                "description": "Both partners harvest crops at least 5 times in a week",
                "reward": 6_500,
                "love_points": 11,
                "tier": 2,
            },
            "trivia_night": {
                "name": "🧠 Trivia Night",
                "description": "Both partners answer 3+ trivia questions correctly on the same day",
                "reward": 4_000,
                "love_points": 8,
                "tier": 2,
            },
            # ── Tier 3 — Hard (monthly / milestone) ───────────────────
            "adventure": {
                "name": "🗺️ Adventure Together",
                "description": "Both partners complete a quest on the same day",
                "reward": 10_000,
                "love_points": 20,
                "tier": 3,
            },
            "heist_partners": {
                "name": "🦹 Heist Partners",
                "description": "Both partners participate in the same successful heist",
                "reward": 15_000,
                "love_points": 25,
                "tier": 3,
            },
            "card_champions": {
                "name": "🃏 Card Champions",
                "description": "Both partners win a poker or blackjack game on the same day",
                "reward": 12_000,
                "love_points": 20,
                "tier": 3,
            },
            "wealthy_couple": {
                "name": "💎 Wealthy Couple",
                "description": "Accumulate 50,000 coins in the shared bank",
                "reward": 20_000,
                "love_points": 30,
                "tier": 3,
            },
            "anniversary": {
                "name": "🥂 One Month Strong",
                "description": "Stay married for 30 days",
                "reward": 25_000,
                "love_points": 50,
                "tier": 3,
            },
        }
    
    @commands.group(name="marry", invoke_without_command=True)
    async def marry(self, ctx, partner: discord.Member):
        """Propose marriage to another user"""
        if partner.id == ctx.author.id:
            await ctx.send("❌ You can't marry yourself!")
            return
        
        if partner.bot:
            await ctx.send("❌ You can't marry bots!")
            return
        
        # Check if author is already married
        if self.is_married(ctx.author.id):
            await ctx.send("❌ You're already married! Divorce first with `L!divorce`")
            return
        
        # Check if partner is already married
        if self.is_married(partner.id):
            await ctx.send(f"❌ {partner.mention} is already married!")
            return
        
        # Check if there's already a pending proposal
        if ctx.author.id in self.active_proposals:
            await ctx.send("❌ You already have a pending proposal!")
            return
        
        # Marriage cost
        marriage_cost = 10000
        
        economy_cog = self.bot.get_cog("Economy")
        if not economy_cog:
            await ctx.send("❌ Economy system not loaded!")
            return
        
        balance = economy_cog.get_balance(ctx.author.id)
        if balance < marriage_cost:
            await ctx.send(f"❌ Marriage costs {marriage_cost:,} coins but you have {balance:,}")
            return
        
        # Create proposal
        self.active_proposals[ctx.author.id] = {
            "partner": partner.id,
            "channel_id": ctx.channel.id,
            "expires": discord.utils.utcnow() + timedelta(minutes=5)
        }
        
        embed = discord.Embed(
            title="💍 Marriage Proposal!",
            description=f"{ctx.author.mention} is proposing to {partner.mention}!",
            color=discord.Color.from_rgb(255, 182, 193)  # Pink
        )
        
        embed.add_field(name="Cost", value=f"{marriage_cost:,} coins", inline=True)
        embed.add_field(name="Benefits", value="Shared bank, couple quests, bonuses", inline=True)
        embed.set_footer(text=f"Proposal expires in 5 minutes • Only {partner.display_name} can respond")

        view = MarriageProposalView(self, ctx.author.id, partner, marriage_cost)
        msg = await ctx.send(content=partner.mention, embed=embed, view=view)
        view.message = msg
    
    @marry.command(name="accept")
    async def marry_accept(self, ctx):
        """Accept a marriage proposal"""
        # Find proposal for this user
        proposal = None
        proposer_id = None
        
        for user_id, prop in self.active_proposals.items():
            if prop["partner"] == ctx.author.id:
                proposal = prop
                proposer_id = user_id
                break
        
        if not proposal:
            await ctx.send("❌ You don't have any pending proposals!")
            return
        
        # Check if expired
        if discord.utils.utcnow() > proposal["expires"]:
            del self.active_proposals[proposer_id]
            await ctx.send("❌ The proposal has expired!")
            return
        
        # Check if already married
        if self.is_married(ctx.author.id):
            del self.active_proposals[proposer_id]
            await ctx.send("❌ You're already married!")
            return
        
        # Process marriage
        economy_cog = self.bot.get_cog("Economy")
        marriage_cost = 10000
        
        balance = economy_cog.get_balance(proposer_id)
        if balance < marriage_cost:
            del self.active_proposals[proposer_id]
            await ctx.send(f"❌ The proposer doesn't have enough coins anymore!")
            return
        
        # Deduct cost
        economy_cog.remove_coins(proposer_id, marriage_cost)
        
        # Create marriage
        marriage_date = discord.utils.utcnow().isoformat()
        
        proposer_marriage = self.get_marriage(proposer_id)
        proposer_marriage["spouse"] = ctx.author.id
        proposer_marriage["married_since"] = marriage_date
        proposer_marriage["shared_bank"] = 0
        proposer_marriage["love_points"] = 0
        
        partner_marriage = self.get_marriage(ctx.author.id)
        partner_marriage["spouse"] = proposer_id
        partner_marriage["married_since"] = marriage_date
        partner_marriage["shared_bank"] = 0
        partner_marriage["love_points"] = 0
        
        self.save_data()
        del self.active_proposals[proposer_id]

        # ── sync profile stats ──
        profile_cog = self.bot.get_cog("Profile")
        if profile_cog:
            profile_cog.increment_stat(proposer_id, "marriages")
            profile_cog.increment_stat(ctx.author.id, "marriages")

        proposer = await self.bot.fetch_user(proposer_id)

        embed = discord.Embed(
            title="💒 Just Married!",
            description=f"{proposer.mention} and {ctx.author.mention} are now married! 💕",
            color=discord.Color.gold()
        )
        
        embed.add_field(name="Benefits Unlocked", value="✅ Shared bank\n✅ Couple quests\n✅ Daily bonuses", inline=True)
        embed.add_field(name="Commands", value="`L!spouse` - View info\n`L!bank` - Shared bank\n`L!couplequests` - Quests", inline=True)
        
        embed.set_footer(text=f"Married since {discord.utils.utcnow().strftime('%B %d, %Y')}")
        
        await ctx.send(embed=embed)
    
    @marry.command(name="decline")
    async def marry_decline(self, ctx):
        """Decline a marriage proposal"""
        # Find proposal
        proposal = None
        proposer_id = None
        
        for user_id, prop in self.active_proposals.items():
            if prop["partner"] == ctx.author.id:
                proposal = prop
                proposer_id = user_id
                break
        
        if not proposal:
            await ctx.send("❌ You don't have any pending proposals!")
            return
        
        del self.active_proposals[proposer_id]
        
        proposer = await self.bot.fetch_user(proposer_id)
        await ctx.send(f"💔 {ctx.author.mention} declined {proposer.mention}'s proposal.")
    
    @commands.command(name="divorce")
    async def divorce(self, ctx):
        """Divorce your spouse"""
        if not self.is_married(ctx.author.id):
            await ctx.send("❌ You're not married!")
            return
        
        marriage = self.get_marriage(ctx.author.id)
        spouse_id = marriage["spouse"]
        spouse = await self.bot.fetch_user(spouse_id)
        
        # Divorce cost (lose shared bank and pay penalty)
        divorce_cost = 5000
        
        economy_cog = self.bot.get_cog("Economy")
        balance = economy_cog.get_balance(ctx.author.id)
        
        if balance < divorce_cost:
            await ctx.send(f"❌ Divorce costs {divorce_cost:,} coins but you have {balance:,}")
            return
        
        # Process divorce
        economy_cog.remove_coins(ctx.author.id, divorce_cost)
        
        # Reset marriages
        marriage["spouse"] = None
        marriage["married_since"] = None
        marriage["shared_bank"] = 0
        marriage["completed_quests"] = []
        marriage["love_points"] = 0
        marriage["divorces"] += 1
        
        spouse_marriage = self.get_marriage(spouse_id)
        spouse_marriage["spouse"] = None
        spouse_marriage["married_since"] = None
        spouse_marriage["shared_bank"] = 0
        spouse_marriage["completed_quests"] = []
        spouse_marriage["love_points"] = 0
        spouse_marriage["divorces"] += 1

        self.save_data()

        # ── sync profile stats ──
        profile_cog = self.bot.get_cog("Profile")
        if profile_cog:
            profile_cog.increment_stat(ctx.author.id, "divorces")
            profile_cog.increment_stat(spouse_id, "divorces")

        embed = discord.Embed(
            title="💔 Divorce Finalized",
            description=f"{ctx.author.mention} and {spouse.mention} are now divorced.",
            color=discord.Color.dark_gray()
        )
        
        embed.add_field(name="Divorce Cost", value=f"{divorce_cost:,} coins", inline=True)
        embed.add_field(name="Shared Bank Lost", value=f"{marriage['shared_bank']:,} coins", inline=True)
        
        await ctx.send(embed=embed)
    
    @commands.command(name="spouse")
    async def spouse(self, ctx, member: Optional[discord.Member] = None):
        """View your or someone's spouse info"""
        target = member or ctx.author
        
        if not self.is_married(target.id):
            await ctx.send(f"💔 {target.mention} is not married!")
            return
        
        marriage = self.get_marriage(target.id)
        spouse = await self.bot.fetch_user(marriage["spouse"])
        
        married_since = _parse_ts(marriage["married_since"])
        days_married = (discord.utils.utcnow() - married_since).days
        
        embed = discord.Embed(
            title=f"💑 {target.display_name}'s Marriage",
            color=discord.Color.from_rgb(255, 182, 193)
        )
        
        embed.add_field(name="Spouse", value=spouse.mention, inline=True)
        embed.add_field(name="Days Married", value=days_married, inline=True)
        embed.add_field(name="Love Points", value=f"❤️ {marriage['love_points']}", inline=True)
        
        embed.add_field(name="Shared Bank", value=f"{marriage['shared_bank']:,} coins", inline=True)
        embed.add_field(name="Quests Completed", value=len(marriage["completed_quests"]), inline=True)
        embed.add_field(name="Total Divorces", value=marriage["divorces"], inline=True)
        
        embed.set_footer(text=f"Married since {married_since.strftime('%B %d, %Y')}")
        
        await ctx.send(embed=embed)
    
    @commands.command(name="bank")
    async def bank(self, ctx):
        """View the shared bank with your spouse"""
        if not self.is_married(ctx.author.id):
            await ctx.send("❌ You need to be married to use the shared bank!")
            return

        marriage = self.get_marriage(ctx.author.id)
        spouse = await self.bot.fetch_user(marriage["spouse"])

        embed = discord.Embed(
            title="🏦 Shared Bank",
            description=f"Joint account with {spouse.mention}",
            color=discord.Color.blue(),
        )
        embed.add_field(name="Balance", value=f"{marriage['shared_bank']:,} coins", inline=True)
        embed.set_footer(text="Both partners can deposit and withdraw using the buttons below.")

        view = SharedBankView(self, ctx.author.id, marriage["spouse"])
        await ctx.send(embed=embed, view=view)
    
    @commands.command(name="couplequests")
    async def couplequests(self, ctx):
        """View available couple quests"""
        if not self.is_married(ctx.author.id):
            await ctx.send("❌ You need to be married to do couple quests!")
            return

        marriage = self.get_marriage(ctx.author.id)
        spouse = await self.bot.fetch_user(marriage["spouse"])
        quests = self.get_couple_quests()
        completed = set(marriage["completed_quests"])

        tier_labels = {1: "⭐ Tier 1 — Easy", 2: "⭐⭐ Tier 2 — Medium", 3: "⭐⭐⭐ Tier 3 — Hard"}
        tier_colors = {1: discord.Color.green(), 2: discord.Color.gold(), 3: discord.Color.from_rgb(200, 50, 255)}

        embeds = []
        for tier in (1, 2, 3):
            tier_quests = {k: v for k, v in quests.items() if v.get("tier") == tier}
            embed = discord.Embed(
                title=f"💕 Couple Quests — {tier_labels[tier]}",
                description=f"Partner: {spouse.mention}  •  Love Points: ❤️ {marriage['love_points']}",
                color=tier_colors[tier],
            )
            for quest_id, quest in tier_quests.items():
                status = "✅" if quest_id in completed else "📋"
                embed.add_field(
                    name=f"{status} {quest['name']}",
                    value=f"{quest['description']}\n"
                          f"**Reward:** {quest['reward']:,} coins + {quest['love_points']} ❤️",
                    inline=False,
                )
            embeds.append(embed)

        embeds[-1].set_footer(text=f"Completed: {len(completed)}/{len(quests)} • Quests reset weekly")
        await ctx.send(embeds=embeds)

async def setup(bot):
    await bot.add_cog(Marriage(bot))
