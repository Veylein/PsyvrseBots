import discord
from discord.ext import commands
import json
import os
import random
from datetime import datetime, timedelta
from typing import Optional

class Marriage(commands.Cog):
    """Marry other users and complete couple quests"""
    
    def __init__(self, bot):
        self.bot = bot
        self.file_path = "cogs/marriages.json"
        self.load_data()
        self.active_proposals = {}  # {user_id: {partner, channel_id, expires}}
    
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
        """Get available couple quests"""
        return {
            "date_night": {
                "name": "💑 Date Night",
                "description": "Both partners say 'I love you' in chat",
                "reward": 5000,
                "love_points": 10
            },
            "gift_exchange": {
                "name": "🎁 Gift Exchange",
                "description": "Send each other items worth 1000+ coins",
                "reward": 3000,
                "love_points": 5
            },
            "adventure": {
                "name": "🗺️ Adventure Together",
                "description": "Both complete a quest on the same day",
                "reward": 10000,
                "love_points": 20
            },
            "fortune": {
                "name": "🎰 Fortune Hunters",
                "description": "Win 5000+ coins from gambling together",
                "reward": 7500,
                "love_points": 15
            }
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
            "expires": datetime.utcnow() + timedelta(minutes=5)
        }
        
        embed = discord.Embed(
            title="💍 Marriage Proposal!",
            description=f"{ctx.author.mention} is proposing to {partner.mention}!",
            color=discord.Color.from_rgb(255, 182, 193)  # Pink
        )
        
        embed.add_field(name="Cost", value=f"{marriage_cost:,} coins", inline=True)
        embed.add_field(name="Benefits", value="Shared bank, couple quests, bonuses", inline=True)
        embed.add_field(
            name="Respond",
            value=f"{partner.mention}, type:\n"
                  f"✅ `L!marry accept` to accept\n"
                  f"❌ `L!marry decline` to decline",
            inline=False
        )
        
        embed.set_footer(text="Proposal expires in 5 minutes")
        
        await ctx.send(embed=embed)
    
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
        if datetime.utcnow() > proposal["expires"]:
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
        economy_cog.remove_coins(proposer_id, marriage_cost, "marriage")
        
        # Create marriage
        marriage_date = datetime.utcnow().isoformat()
        
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
        
        proposer = await self.bot.fetch_user(proposer_id)
        
        embed = discord.Embed(
            title="💒 Just Married!",
            description=f"{proposer.mention} and {ctx.author.mention} are now married! 💕",
            color=discord.Color.gold()
        )
        
        embed.add_field(name="Benefits Unlocked", value="✅ Shared bank\n✅ Couple quests\n✅ Daily bonuses", inline=True)
        embed.add_field(name="Commands", value="`L!spouse` - View info\n`L!bank` - Shared bank\n`L!couplequests` - Quests", inline=True)
        
        embed.set_footer(text=f"Married since {datetime.utcnow().strftime('%B %d, %Y')}")
        
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
        economy_cog.remove_coins(ctx.author.id, divorce_cost, "divorce")
        
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
        
        married_since = datetime.fromisoformat(marriage["married_since"])
        days_married = (datetime.utcnow() - married_since).days
        
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
    
    @commands.group(name="bank", invoke_without_command=True)
    async def bank(self, ctx):
        """View shared bank with your spouse"""
        if not self.is_married(ctx.author.id):
            await ctx.send("❌ You need to be married to use the shared bank!")
            return
        
        marriage = self.get_marriage(ctx.author.id)
        spouse = await self.bot.fetch_user(marriage["spouse"])
        
        embed = discord.Embed(
            title="🏦 Shared Bank",
            description=f"Joint account with {spouse.mention}",
            color=discord.Color.blue()
        )
        
        embed.add_field(name="Balance", value=f"{marriage['shared_bank']:,} coins", inline=True)
        embed.add_field(
            name="Commands",
            value="```\n"
                  "L!bank deposit <amount>\n"
                  "L!bank withdraw <amount>\n"
                  "```",
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    @bank.command(name="deposit")
    async def bank_deposit(self, ctx, amount: int):
        """Deposit coins to shared bank"""
        if not self.is_married(ctx.author.id):
            await ctx.send("❌ You need to be married to use the shared bank!")
            return
        
        if amount <= 0:
            await ctx.send("❌ Amount must be positive!")
            return
        
        economy_cog = self.bot.get_cog("Economy")
        balance = economy_cog.get_balance(ctx.author.id)
        
        if balance < amount:
            await ctx.send(f"❌ You only have {balance:,} coins!")
            return
        
        # Deposit
        economy_cog.remove_coins(ctx.author.id, amount, "shared_bank_deposit")
        
        marriage = self.get_marriage(ctx.author.id)
        spouse_marriage = self.get_marriage(marriage["spouse"])
        
        marriage["shared_bank"] += amount
        spouse_marriage["shared_bank"] += amount
        
        self.save_data()
        
        await ctx.send(f"✅ Deposited {amount:,} coins to shared bank! New balance: {marriage['shared_bank']:,}")
    
    @bank.command(name="withdraw")
    async def bank_withdraw(self, ctx, amount: int):
        """Withdraw coins from shared bank"""
        if not self.is_married(ctx.author.id):
            await ctx.send("❌ You need to be married to use the shared bank!")
            return
        
        if amount <= 0:
            await ctx.send("❌ Amount must be positive!")
            return
        
        marriage = self.get_marriage(ctx.author.id)
        
        if marriage["shared_bank"] < amount:
            await ctx.send(f"❌ Shared bank only has {marriage['shared_bank']:,} coins!")
            return
        
        # Withdraw
        economy_cog = self.bot.get_cog("Economy")
        economy_cog.add_coins(ctx.author.id, amount, "shared_bank_withdraw")
        
        spouse_marriage = self.get_marriage(marriage["spouse"])
        
        marriage["shared_bank"] -= amount
        spouse_marriage["shared_bank"] -= amount
        
        self.save_data()
        
        await ctx.send(f"✅ Withdrew {amount:,} coins from shared bank! Remaining: {marriage['shared_bank']:,}")
    
    @commands.command(name="couplequests")
    async def couplequests(self, ctx):
        """View available couple quests"""
        if not self.is_married(ctx.author.id):
            await ctx.send("❌ You need to be married to do couple quests!")
            return
        
        marriage = self.get_marriage(ctx.author.id)
        spouse = await self.bot.fetch_user(marriage["spouse"])
        quests = self.get_couple_quests()
        
        embed = discord.Embed(
            title="💕 Couple Quests",
            description=f"Complete quests with {spouse.mention} for rewards!",
            color=discord.Color.from_rgb(255, 182, 193)
        )
        
        for quest_id, quest in quests.items():
            status = "✅" if quest_id in marriage["completed_quests"] else "📋"
            embed.add_field(
                name=f"{status} {quest['name']}",
                value=f"{quest['description']}\n"
                      f"**Reward:** {quest['reward']:,} coins + {quest['love_points']} ❤️",
                inline=False
            )
        
        embed.set_footer(text="Quests reset weekly • Work together to complete them!")
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Marriage(bot))
