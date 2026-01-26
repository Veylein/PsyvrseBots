import discord
from discord.ext import commands, tasks
from discord import app_commands
import json
import os
import random
from datetime import datetime, timedelta
from typing import Optional

class PassiveBusinesses(commands.Cog):
    """Buy and manage businesses for passive income"""
    
    def __init__(self, bot):
        self.bot = bot
        self.file_path = "cogs/businesses.json"
        self.load_data()
        
        # Available businesses
        self.business_types = {
            "cafe": {
                "name": "☕ Coffee Cafe",
                "cost": 5000,
                "base_income": 50,
                "max_level": 10,
                "upgrade_cost_multiplier": 1.5
            },
            "casino": {
                "name": "🎰 Mini Casino",
                "cost": 15000,
                "base_income": 150,
                "max_level": 10,
                "upgrade_cost_multiplier": 1.5
            },
            "mine": {
                "name": "⛏️ Gold Mine",
                "cost": 25000,
                "base_income": 250,
                "max_level": 10,
                "upgrade_cost_multiplier": 1.5
            },
            "farm": {
                "name": "🌾 Farm",
                "cost": 10000,
                "base_income": 100,
                "max_level": 10,
                "upgrade_cost_multiplier": 1.5
            },
            "factory": {
                "name": "🏭 Factory",
                "cost": 50000,
                "base_income": 500,
                "max_level": 10,
                "upgrade_cost_multiplier": 1.5
            }
        }
        
        # Start passive income generation
        self.generate_income.start()
    
    def load_data(self):
        """Load business data"""
        if os.path.exists(self.file_path):
            with open(self.file_path, 'r') as f:
                self.business_data = json.load(f)
        else:
            self.business_data = {}
    
    def save_data(self):
        """Save business data"""
        with open(self.file_path, 'w') as f:
            json.dump(self.business_data, f, indent=4)
    
    def get_user_businesses(self, user_id):
        """Get user's businesses"""
        user_key = str(user_id)
        if user_key not in self.business_data:
            self.business_data[user_key] = {
                "businesses": {},  # {business_id: {type, level, last_collect}}
                "total_earned": 0,
                "protection": None  # Timestamp when protection expires
            }
        return self.business_data[user_key]
    
    def calculate_income(self, business_type, level):
        """Calculate income for a business"""
        base = self.business_types[business_type]["base_income"]
        return int(base * (1 + (level - 1) * 0.3))  # +30% per level
    
    def calculate_upgrade_cost(self, business_type, current_level):
        """Calculate cost to upgrade"""
        base_cost = self.business_types[business_type]["cost"]
        multiplier = self.business_types[business_type]["upgrade_cost_multiplier"]
        return int(base_cost * (multiplier ** current_level))
    
    def cog_unload(self):
        """Stop task when cog unloads"""
        self.generate_income.cancel()
    
    @tasks.loop(hours=1)
    async def generate_income(self):
        """Generate passive income every hour"""
        # This happens automatically, income accumulates until collected
        pass
    
    @generate_income.before_loop
    async def before_generate_income(self):
        """Wait until bot is ready"""
        await self.bot.wait_until_ready()
    
    @commands.group(name="mybusiness", aliases=['mybiz', 'passivebiz'], invoke_without_command=True)
    async def business(self, ctx):
        """View available passive income businesses"""
        embed = discord.Embed(
            title="🏢 Business Empire (Passive Income)",
            description="Buy businesses to generate passive income!",
            color=discord.Color.blue()
        )
        
        for biz_id, biz in self.business_types.items():
            income = self.calculate_income(biz_id, 1)
            embed.add_field(
                name=biz["name"],
                value=f"**Cost:** {biz['cost']:,} coins\n"
                      f"**Income:** {income} coins/hour\n"
                      f"**Max Level:** {biz['max_level']}",
                inline=True
            )
        
        embed.add_field(
            name="ℹ️ Commands",
            value="```\n"
                  "L!business buy <type>\n"
                  "L!business list\n"
                  "L!business collect [id]\n"
                  "L!business upgrade <id>\n"
                  "L!business protect\n"
                  "```",
            inline=False
        )
        
        embed.set_footer(text="Income accumulates hourly • Can be robbed by other players!")
        
        await ctx.send(embed=embed)
    
    @business.command(name="buy")
    async def business_buy(self, ctx, business_type: str):
        """Buy a business"""
        business_type = business_type.lower()
        
        if business_type not in self.business_types:
            await ctx.send(f"❌ Invalid business type! Choose from: {', '.join(self.business_types.keys())}")
            return
        
        biz = self.business_types[business_type]
        cost = biz["cost"]
        
        # Check balance
        economy_cog = self.bot.get_cog("Economy")
        if not economy_cog:
            await ctx.send("❌ Economy system not loaded!")
            return
        
        balance = economy_cog.get_balance(ctx.author.id)
        if balance < cost:
            await ctx.send(f"❌ Not enough coins! You need {cost:,} but have {balance:,}")
            return
        
        # Buy business
        user_businesses = self.get_user_businesses(ctx.author.id)
        
        # Check if user already has 5 businesses
        if len(user_businesses["businesses"]) >= 5:
            await ctx.send("❌ You can only own 5 businesses at a time!")
            return
        
        business_id = f"{business_type}_{len(user_businesses['businesses']) + 1}"
        
        user_businesses["businesses"][business_id] = {
            "type": business_type,
            "level": 1,
            "last_collect": datetime.utcnow().isoformat(),
            "total_earned": 0
        }
        
        economy_cog.remove_coins(ctx.author.id, cost, "business_purchase")
        self.save_data()
        
        income = self.calculate_income(business_type, 1)
        
        embed = discord.Embed(
            title="🏢 Business Purchased!",
            description=f"You bought **{biz['name']}**!",
            color=discord.Color.green()
        )
        
        embed.add_field(name="Cost", value=f"{cost:,} coins", inline=True)
        embed.add_field(name="Income", value=f"{income} coins/hour", inline=True)
        embed.add_field(name="Business ID", value=business_id, inline=True)
        
        embed.set_footer(text="Collect income with: L!business collect")
        
        await ctx.send(embed=embed)
    
    @business.command(name="list", aliases=['my', 'owned'])
    async def business_list(self, ctx, member: Optional[discord.Member] = None):
        """View your businesses"""
        target = member or ctx.author
        user_businesses = self.get_user_businesses(target.id)
        
        if not user_businesses["businesses"]:
            await ctx.send(f"🏢 {target.mention} doesn't own any businesses yet!")
            return
        
        embed = discord.Embed(
            title=f"🏢 {target.display_name}'s Businesses",
            color=discord.Color.blue()
        )
        
        total_hourly_income = 0
        
        for biz_id, biz_data in user_businesses["businesses"].items():
            biz_type = biz_data["type"]
            biz_info = self.business_types[biz_type]
            level = biz_data["level"]
            income = self.calculate_income(biz_type, level)
            total_hourly_income += income
            
            # Calculate pending income
            last_collect = datetime.fromisoformat(biz_data["last_collect"])
            hours_passed = (datetime.utcnow() - last_collect).total_seconds() / 3600
            pending = int(income * hours_passed)
            
            embed.add_field(
                name=f"{biz_info['name']} (Lv. {level})",
                value=f"**ID:** {biz_id}\n"
                      f"**Income:** {income}/hour\n"
                      f"**Pending:** {pending:,} coins\n"
                      f"**Total Earned:** {biz_data['total_earned']:,}",
                inline=True
            )
        
        embed.add_field(
            name="📊 Total Stats",
            value=f"**Businesses:** {len(user_businesses['businesses'])}/5\n"
                  f"**Hourly Income:** {total_hourly_income:,} coins\n"
                  f"**Total Earned:** {user_businesses['total_earned']:,} coins",
            inline=False
        )
        
        # Protection status
        if user_businesses["protection"]:
            protection_expires = datetime.fromisoformat(user_businesses["protection"])
            if datetime.utcnow() < protection_expires:
                time_left = protection_expires - datetime.utcnow()
                hours = int(time_left.total_seconds() // 3600)
                embed.add_field(name="🛡️ Protection", value=f"{hours}h remaining", inline=False)
        
        await ctx.send(embed=embed)
    
    @business.command(name="collect")
    async def business_collect(self, ctx, business_id: Optional[str] = None):
        """Collect income from your businesses"""
        user_businesses = self.get_user_businesses(ctx.author.id)
        
        if not user_businesses["businesses"]:
            await ctx.send("❌ You don't own any businesses!")
            return
        
        economy_cog = self.bot.get_cog("Economy")
        if not economy_cog:
            await ctx.send("❌ Economy system not loaded!")
            return
        
        total_collected = 0
        businesses_updated = []
        
        # Collect from all or specific business
        businesses_to_collect = [business_id] if business_id else list(user_businesses["businesses"].keys())
        
        for biz_id in businesses_to_collect:
            if biz_id not in user_businesses["businesses"]:
                await ctx.send(f"❌ You don't own business: {biz_id}")
                continue
            
            biz_data = user_businesses["businesses"][biz_id]
            biz_type = biz_data["type"]
            level = biz_data["level"]
            income = self.calculate_income(biz_type, level)
            
            # Calculate pending income
            last_collect = datetime.fromisoformat(biz_data["last_collect"])
            hours_passed = (datetime.utcnow() - last_collect).total_seconds() / 3600
            pending = int(income * hours_passed)
            
            if pending > 0:
                economy_cog.add_coins(ctx.author.id, pending, "business_income")
                biz_data["last_collect"] = datetime.utcnow().isoformat()
                biz_data["total_earned"] += pending
                user_businesses["total_earned"] += pending
                total_collected += pending
                businesses_updated.append((biz_id, pending))
        
        self.save_data()
        
        if total_collected == 0:
            await ctx.send("💼 No income to collect yet! Check back later.")
            return
        
        embed = discord.Embed(
            title="💰 Income Collected!",
            description=f"**Total: {total_collected:,} PsyCoins**",
            color=discord.Color.gold()
        )
        
        for biz_id, amount in businesses_updated:
            biz_type = user_businesses["businesses"][biz_id]["type"]
            biz_name = self.business_types[biz_type]["name"]
            embed.add_field(name=biz_name, value=f"{amount:,} coins", inline=True)
        
        await ctx.send(embed=embed)
    
    @business.command(name="upgrade")
    async def business_upgrade(self, ctx, business_id: str):
        """Upgrade a business"""
        user_businesses = self.get_user_businesses(ctx.author.id)
        
        if business_id not in user_businesses["businesses"]:
            await ctx.send(f"❌ You don't own business: {business_id}")
            return
        
        biz_data = user_businesses["businesses"][business_id]
        biz_type = biz_data["type"]
        biz_info = self.business_types[biz_type]
        current_level = biz_data["level"]
        
        if current_level >= biz_info["max_level"]:
            await ctx.send(f"❌ {biz_info['name']} is already max level!")
            return
        
        upgrade_cost = self.calculate_upgrade_cost(biz_type, current_level)
        
        # Check balance
        economy_cog = self.bot.get_cog("Economy")
        balance = economy_cog.get_balance(ctx.author.id)
        
        if balance < upgrade_cost:
            await ctx.send(f"❌ Not enough coins! Upgrade costs {upgrade_cost:,} but you have {balance:,}")
            return
        
        # Upgrade
        economy_cog.remove_coins(ctx.author.id, upgrade_cost, "business_upgrade")
        biz_data["level"] += 1
        self.save_data()
        
        new_level = biz_data["level"]
        new_income = self.calculate_income(biz_type, new_level)
        old_income = self.calculate_income(biz_type, current_level)
        
        embed = discord.Embed(
            title="⬆️ Business Upgraded!",
            description=f"**{biz_info['name']}** upgraded to Level {new_level}!",
            color=discord.Color.green()
        )
        
        embed.add_field(name="Cost", value=f"{upgrade_cost:,} coins", inline=True)
        embed.add_field(name="Old Income", value=f"{old_income}/hour", inline=True)
        embed.add_field(name="New Income", value=f"{new_income}/hour", inline=True)
        
        if new_level < biz_info["max_level"]:
            next_cost = self.calculate_upgrade_cost(biz_type, new_level)
            embed.set_footer(text=f"Next upgrade: {next_cost:,} coins")
        else:
            embed.set_footer(text="MAX LEVEL!")
        
        await ctx.send(embed=embed)
    
    @business.command(name="protect")
    async def business_protect(self, ctx):
        """Buy 24-hour protection from robberies"""
        user_businesses = self.get_user_businesses(ctx.author.id)
        
        if not user_businesses["businesses"]:
            await ctx.send("❌ You don't own any businesses to protect!")
            return
        
        protection_cost = 5000
        
        # Check if already protected
        if user_businesses["protection"]:
            protection_expires = datetime.fromisoformat(user_businesses["protection"])
            if datetime.utcnow() < protection_expires:
                time_left = protection_expires - datetime.utcnow()
                hours = int(time_left.total_seconds() // 3600)
                await ctx.send(f"🛡️ Your businesses are already protected for {hours} more hours!")
                return
        
        # Check balance
        economy_cog = self.bot.get_cog("Economy")
        balance = economy_cog.get_balance(ctx.author.id)
        
        if balance < protection_cost:
            await ctx.send(f"❌ Protection costs {protection_cost:,} coins but you have {balance:,}")
            return
        
        # Buy protection
        economy_cog.remove_coins(ctx.author.id, protection_cost, "business_protection")
        user_businesses["protection"] = (datetime.utcnow() + timedelta(hours=24)).isoformat()
        self.save_data()
        
        await ctx.send(f"🛡️ Your businesses are now protected from robberies for 24 hours!")

async def setup(bot):
    await bot.add_cog(PassiveBusinesses(bot))
