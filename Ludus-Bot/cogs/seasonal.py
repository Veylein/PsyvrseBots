import discord
from discord.ext import commands
from discord import app_commands
import asyncio
from datetime import datetime

class Seasonal(commands.Cog):
    """Seasonal events and activities that change monthly"""
    
    def __init__(self, bot):
        self.bot = bot
        
        # Thanksgiving Dinner Components (November)
        self.turkey_options = [
            "🦃 Roasted Turkey",
            "🦃 Deep-Fried Turkey",
            "🦃 Smoked Turkey",
            "🦃 Herb-Butter Turkey",
            "🦃 Honey-Glazed Turkey"
        ]
        
        self.sides = [
            "🥔 Mashed Potatoes",
            "🥗 Green Bean Casserole",
            "🌽 Buttered Corn",
            "🍠 Sweet Potato Casserole",
            "🥖 Dinner Rolls",
            "🥕 Glazed Carrots",
            "🥒 Cranberry Sauce",
            "🧈 Mac and Cheese"
        ]
        
        self.desserts = [
            "🥧 Pumpkin Pie",
            "🥧 Apple Pie",
            "🥧 Pecan Pie",
            "🍰 Cheesecake"
        ]
        
        self.drinks = [
            "🍷 Apple Cider",
            "🥤 Cranberry Juice",
            "☕ Hot Chocolate",
            "🍵 Spiced Tea"
        ]
    
    def get_current_month(self):
        """Get current month for seasonal content"""
        return datetime.now().month
    
    @app_commands.command(name="seasonal", description="Seasonal event - Currently: Thanksgiving Dinner!")
    async def seasonal_slash(self, interaction: discord.Interaction):
        """Slash command for seasonal event"""
        month = self.get_current_month()
        
        if month == 11:  # November - Thanksgiving
            await self.thanksgiving_dinner(interaction)
        else:
            await interaction.response.send_message(
                "🎉 No seasonal event active right now!\n"
                "Check back during special months for exclusive activities!",
                ephemeral=True
            )
    
    @commands.command(name="seasonal")
    async def seasonal_prefix(self, ctx):
        """Prefix command for seasonal event"""
        month = self.get_current_month()
        
        if month == 11:  # November - Thanksgiving
            await self.thanksgiving_dinner_prefix(ctx)
        else:
            await ctx.send(
                "🎉 No seasonal event active right now!\n"
                "Check back during special months for exclusive activities!"
            )
    
    async def thanksgiving_dinner(self, interaction: discord.Interaction):
        """Build the perfect Thanksgiving dinner (slash command version)"""
        dinner = {
            "turkey": None,
            "sides": [],
            "dessert": None,
            "drink": None
        }
        
        # Step 1: Choose Turkey
        embed = discord.Embed(
            title="🦃 Thanksgiving Dinner Builder",
            description="**Create your perfect Thanksgiving feast!**\n\n"
                       "**Step 1:** Choose your turkey\nReact with 1️⃣-5️⃣",
            color=discord.Color.orange()
        )
        
        for i, turkey in enumerate(self.turkey_options):
            embed.add_field(name=f"{i+1}️⃣", value=turkey, inline=True)
        
        await interaction.response.send_message(embed=embed)
        msg = await interaction.original_response()
        
        # Add reactions for turkey selection
        for i in range(len(self.turkey_options)):
            await msg.add_reaction(f"{i+1}️⃣")
        
        def check_number(reaction, user):
            return user.id == interaction.user.id and str(reaction.emoji) in ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]
        
        try:
            # Turkey selection
            reaction, user = await self.bot.wait_for('reaction_add', check=check_number, timeout=30.0)
            emoji_to_num = {"1️⃣": 0, "2️⃣": 1, "3️⃣": 2, "4️⃣": 3, "5️⃣": 4}
            dinner["turkey"] = self.turkey_options[emoji_to_num[str(reaction.emoji)]]
            
            # Step 2: Choose Sides
            embed = discord.Embed(
                title="🦃 Thanksgiving Dinner Builder",
                description=f"**Turkey:** {dinner['turkey']}\n\n"
                           "**Step 2:** Choose your sides (pick up to 4)\nReact when done: ✅",
                color=discord.Color.orange()
            )
            
            for i, side in enumerate(self.sides):
                embed.add_field(name=f"{i+1}️⃣", value=side, inline=True)
            
            await msg.edit(embed=embed)
            await msg.clear_reactions()
            
            for i in range(len(self.sides)):
                await msg.add_reaction(f"{i+1}️⃣")
            await msg.add_reaction("✅")
            
            def check_side(reaction, user):
                return user.id == interaction.user.id and str(reaction.emoji) in ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "✅"]
            
            # Sides selection
            while len(dinner["sides"]) < 4:
                reaction, user = await self.bot.wait_for('reaction_add', check=check_side, timeout=45.0)
                
                if str(reaction.emoji) == "✅":
                    break
                
                emoji_to_num = {"1️⃣": 0, "2️⃣": 1, "3️⃣": 2, "4️⃣": 3, "5️⃣": 4, "6️⃣": 5, "7️⃣": 6, "8️⃣": 7}
                if str(reaction.emoji) in emoji_to_num:
                    side = self.sides[emoji_to_num[str(reaction.emoji)]]
                    
                    if side not in dinner["sides"]:
                        dinner["sides"].append(side)
                        await interaction.followup.send(f"✅ Added {side}!", ephemeral=True)
                    
                    if len(dinner["sides"]) >= 4:
                        break
            
            # Step 3: Choose Dessert
            embed = discord.Embed(
                title="🦃 Thanksgiving Dinner Builder",
                description=f"**Turkey:** {dinner['turkey']}\n"
                           f"**Sides:** {', '.join(dinner['sides']) if dinner['sides'] else 'None'}\n\n"
                           "**Step 3:** Choose your dessert\nReact with 1️⃣-4️⃣",
                color=discord.Color.orange()
            )
            
            for i, dessert in enumerate(self.desserts):
                embed.add_field(name=f"{i+1}️⃣", value=dessert, inline=True)
            
            await msg.edit(embed=embed)
            await msg.clear_reactions()
            
            for i in range(len(self.desserts)):
                await msg.add_reaction(f"{i+1}️⃣")
            
            reaction, user = await self.bot.wait_for('reaction_add', check=check_number, timeout=30.0)
            emoji_to_num = {"1️⃣": 0, "2️⃣": 1, "3️⃣": 2, "4️⃣": 3}
            dinner["dessert"] = self.desserts[emoji_to_num[str(reaction.emoji)]]
            
            # Step 4: Choose Drink
            embed = discord.Embed(
                title="🦃 Thanksgiving Dinner Builder",
                description=f"**Turkey:** {dinner['turkey']}\n"
                           f"**Sides:** {', '.join(dinner['sides']) if dinner['sides'] else 'None'}\n"
                           f"**Dessert:** {dinner['dessert']}\n\n"
                           "**Step 4:** Choose your drink\nReact with 1️⃣-4️⃣",
                color=discord.Color.orange()
            )
            
            for i, drink in enumerate(self.drinks):
                embed.add_field(name=f"{i+1}️⃣", value=drink, inline=True)
            
            await msg.edit(embed=embed)
            await msg.clear_reactions()
            
            for i in range(len(self.drinks)):
                await msg.add_reaction(f"{i+1}️⃣")
            
            reaction, user = await self.bot.wait_for('reaction_add', check=check_number, timeout=30.0)
            emoji_to_num = {"1️⃣": 0, "2️⃣": 1, "3️⃣": 2, "4️⃣": 3}
            dinner["drink"] = self.drinks[emoji_to_num[str(reaction.emoji)]]
            
            # Calculate reward
            base_value = 75
            sides_bonus = len(dinner["sides"]) * 30
            total_value = base_value + sides_bonus
            
            economy_cog = self.bot.get_cog("Economy")
            if economy_cog:
                economy_cog.add_coins(interaction.user.id, total_value, "thanksgiving_dinner")
            
            # Final result
            embed = discord.Embed(
                title="🎉 Thanksgiving Feast Complete!",
                description=f"**Your Perfect Thanksgiving Dinner:**\n\n"
                           f"🦃 **Main:** {dinner['turkey']}\n\n"
                           f"🍽️ **Sides:**\n{chr(10).join(dinner['sides']) if dinner['sides'] else 'None'}\n\n"
                           f"🥧 **Dessert:** {dinner['dessert']}\n"
                           f"🍷 **Drink:** {dinner['drink']}\n\n"
                           f"**Feast Rating:** {'⭐' * (3 + len(dinner['sides']))}\n\n"
                           f"**Happy Thanksgiving! +{total_value} PsyCoins!**",
                color=discord.Color.gold()
            )
            embed.set_footer(text="🦃 Thank you for celebrating with us!")
            
            await msg.edit(embed=embed)
            await msg.clear_reactions()
            
        except asyncio.TimeoutError:
            await msg.edit(content="⏰ Time's up! The dinner got cold...", embed=None)
            await msg.clear_reactions()
    
    async def thanksgiving_dinner_prefix(self, ctx):
        """Build the perfect Thanksgiving dinner (prefix command version)"""
        dinner = {
            "turkey": None,
            "sides": [],
            "dessert": None,
            "drink": None
        }
        
        # Step 1: Choose Turkey
        embed = discord.Embed(
            title="🦃 Thanksgiving Dinner Builder",
            description="**Create your perfect Thanksgiving feast!**\n\n"
                       "**Step 1:** Choose your turkey\nReact with 1️⃣-5️⃣",
            color=discord.Color.orange()
        )
        
        for i, turkey in enumerate(self.turkey_options):
            embed.add_field(name=f"{i+1}️⃣", value=turkey, inline=True)
        
        msg = await ctx.send(embed=embed)
        
        # Add reactions for turkey selection
        for i in range(len(self.turkey_options)):
            await msg.add_reaction(f"{i+1}️⃣")
        
        def check_number(reaction, user):
            return user.id == ctx.author.id and str(reaction.emoji) in ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]
        
        try:
            # Turkey selection
            reaction, user = await self.bot.wait_for('reaction_add', check=check_number, timeout=30.0)
            emoji_to_num = {"1️⃣": 0, "2️⃣": 1, "3️⃣": 2, "4️⃣": 3, "5️⃣": 4}
            dinner["turkey"] = self.turkey_options[emoji_to_num[str(reaction.emoji)]]
            
            # Step 2: Choose Sides
            embed = discord.Embed(
                title="🦃 Thanksgiving Dinner Builder",
                description=f"**Turkey:** {dinner['turkey']}\n\n"
                           "**Step 2:** Choose your sides (pick up to 4)\nReact when done: ✅",
                color=discord.Color.orange()
            )
            
            for i, side in enumerate(self.sides):
                embed.add_field(name=f"{i+1}️⃣", value=side, inline=True)
            
            await msg.edit(embed=embed)
            await msg.clear_reactions()
            
            for i in range(len(self.sides)):
                await msg.add_reaction(f"{i+1}️⃣")
            await msg.add_reaction("✅")
            
            def check_side(reaction, user):
                return user.id == ctx.author.id and str(reaction.emoji) in ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "✅"]
            
            # Sides selection
            while len(dinner["sides"]) < 4:
                reaction, user = await self.bot.wait_for('reaction_add', check=check_side, timeout=45.0)
                
                if str(reaction.emoji) == "✅":
                    break
                
                emoji_to_num = {"1️⃣": 0, "2️⃣": 1, "3️⃣": 2, "4️⃣": 3, "5️⃣": 4, "6️⃣": 5, "7️⃣": 6, "8️⃣": 7}
                if str(reaction.emoji) in emoji_to_num:
                    side = self.sides[emoji_to_num[str(reaction.emoji)]]
                    
                    if side not in dinner["sides"]:
                        dinner["sides"].append(side)
                        await ctx.send(f"✅ Added {side}!", delete_after=3)
                    
                    if len(dinner["sides"]) >= 4:
                        break
            
            # Step 3: Choose Dessert
            embed = discord.Embed(
                title="🦃 Thanksgiving Dinner Builder",
                description=f"**Turkey:** {dinner['turkey']}\n"
                           f"**Sides:** {', '.join(dinner['sides']) if dinner['sides'] else 'None'}\n\n"
                           "**Step 3:** Choose your dessert\nReact with 1️⃣-4️⃣",
                color=discord.Color.orange()
            )
            
            for i, dessert in enumerate(self.desserts):
                embed.add_field(name=f"{i+1}️⃣", value=dessert, inline=True)
            
            await msg.edit(embed=embed)
            await msg.clear_reactions()
            
            for i in range(len(self.desserts)):
                await msg.add_reaction(f"{i+1}️⃣")
            
            reaction, user = await self.bot.wait_for('reaction_add', check=check_number, timeout=30.0)
            emoji_to_num = {"1️⃣": 0, "2️⃣": 1, "3️⃣": 2, "4️⃣": 3}
            dinner["dessert"] = self.desserts[emoji_to_num[str(reaction.emoji)]]
            
            # Step 4: Choose Drink
            embed = discord.Embed(
                title="🦃 Thanksgiving Dinner Builder",
                description=f"**Turkey:** {dinner['turkey']}\n"
                           f"**Sides:** {', '.join(dinner['sides']) if dinner['sides'] else 'None'}\n"
                           f"**Dessert:** {dinner['dessert']}\n\n"
                           "**Step 4:** Choose your drink\nReact with 1️⃣-4️⃣",
                color=discord.Color.orange()
            )
            
            for i, drink in enumerate(self.drinks):
                embed.add_field(name=f"{i+1}️⃣", value=drink, inline=True)
            
            await msg.edit(embed=embed)
            await msg.clear_reactions()
            
            for i in range(len(self.drinks)):
                await msg.add_reaction(f"{i+1}️⃣")
            
            reaction, user = await self.bot.wait_for('reaction_add', check=check_number, timeout=30.0)
            emoji_to_num = {"1️⃣": 0, "2️⃣": 1, "3️⃣": 2, "4️⃣": 3}
            dinner["drink"] = self.drinks[emoji_to_num[str(reaction.emoji)]]
            
            # Calculate reward
            base_value = 75
            sides_bonus = len(dinner["sides"]) * 30
            total_value = base_value + sides_bonus
            
            economy_cog = self.bot.get_cog("Economy")
            if economy_cog:
                economy_cog.add_coins(ctx.author.id, total_value, "thanksgiving_dinner")
            
            # Final result
            embed = discord.Embed(
                title="🎉 Thanksgiving Feast Complete!",
                description=f"**Your Perfect Thanksgiving Dinner:**\n\n"
                           f"🦃 **Main:** {dinner['turkey']}\n\n"
                           f"🍽️ **Sides:**\n{chr(10).join(dinner['sides']) if dinner['sides'] else 'None'}\n\n"
                           f"🥧 **Dessert:** {dinner['dessert']}\n"
                           f"🍷 **Drink:** {dinner['drink']}\n\n"
                           f"**Feast Rating:** {'⭐' * (3 + len(dinner['sides']))}\n\n"
                           f"**Happy Thanksgiving! +{total_value} PsyCoins!**",
                color=discord.Color.gold()
            )
            embed.set_footer(text="🦃 Thank you for celebrating with us!")
            
            await msg.edit(embed=embed)
            await msg.clear_reactions()
            
        except asyncio.TimeoutError:
            await msg.edit(content="⏰ Time's up! The dinner got cold...", embed=None)
            await msg.clear_reactions()

async def setup(bot):
    await bot.add_cog(Seasonal(bot))
