import discord
from discord.ext import commands
from discord import app_commands
import json
import os
from typing import Optional

class Counting(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.file_path = "data/counting.json"
        self.load_data()

        # Milestone rewards: count -> PsyCoins bonus
        self.milestone_rewards = {
            25: 10,
            50: 20,
            100: 50,
            250: 100,
            500: 350,
            1000: 500
        }
        
        # Legacy milestones for role creation
        self.milestones = [
            25, 50, 100, 125, 250,
            500, 1000, 1250, 1500,
            5000, 10000, 25000
        ]
        
        self.message_numbers = {}
        
        # Track user counts for rewards (user_id -> {guild_id: count})
        self.user_counts = self.load_user_counts()
    
    def load_user_counts(self):
        """Load user count tracking for rewards"""
        counts_file = "data/counting_user_counts.json"
        if os.path.exists(counts_file):
            with open(counts_file, "r") as f:
                return json.load(f)
        return {}
    
    def save_user_counts(self):
        """Save user count tracking"""
        counts_file = "data/counting_user_counts.json"
        with open(counts_file, "w") as f:
            json.dump(self.user_counts, f, indent=4)

    def load_data(self):
        if os.path.exists(self.file_path):
            with open(self.file_path, "r") as f:
                self.count_data = json.load(f)
        else:
            self.count_data = {}

    def save_data(self):
        with open(self.file_path, "w") as f:
            json.dump(self.count_data, f, indent=4)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        guild_id = str(message.guild.id)

        if guild_id not in self.count_data:
            return

        counting_channel_id = self.count_data[guild_id].get("channel")
        if message.channel.id != counting_channel_id:
            return

        try:
            number = int(message.content)
        except ValueError:
            return await message.delete()

        server_data = self.count_data[guild_id]
        expected = server_data.get("current_count", 0) + 1
        last_user = server_data.get("last_user")

        if message.author.id == last_user:
            await message.delete()
            warning = await message.channel.send(
                f"❌ {message.author.mention}, you can't count twice in a row!"
            )
            await warning.delete(delay=5)
            return

        if number != expected:
            await message.delete()
            warning = await message.channel.send(
                f"❌ Wrong number! Expected {expected}, got {number}."
            )
            await warning.delete(delay=5)
            return

        server_data["current_count"] = number
        server_data["last_user"] = message.author.id
        self.save_data()

        self.message_numbers[message.id] = {
            "number": number,
            "user_id": message.author.id,
            "guild_id": message.guild.id
        }
        
        # Track user counts
        user_id_str = str(message.author.id)
        if user_id_str not in self.user_counts:
            self.user_counts[user_id_str] = {}
        if guild_id not in self.user_counts[user_id_str]:
            self.user_counts[user_id_str][guild_id] = 0
        
        self.user_counts[user_id_str][guild_id] += 1
        user_count = self.user_counts[user_id_str][guild_id]
        self.save_user_counts()
        
        # Give PsyCoins: 2 coins per 4 counts (0.5 per count)
        coins_earned = 0
        if user_count % 4 == 0:
            coins_earned = 2
        
        # Check for milestone bonuses
        bonus_coins = 0
        milestone_msg = ""
        if user_count in self.milestone_rewards:
            bonus_coins = self.milestone_rewards[user_count]
            milestone_msg = f"\n🎉 **Milestone Bonus: {bonus_coins} PsyCoins for {user_count} counts!**"
        
        total_coins = coins_earned + bonus_coins
        
        # Award coins via Economy cog
        if total_coins > 0:
            economy_cog = self.bot.get_cog("Economy")
            if economy_cog:
                economy_cog.add_coins(message.author.id, total_coins, "counting")
                
                if bonus_coins > 0:
                    # Show milestone achievement
                    embed = discord.Embed(
                        title="🎉 Counting Milestone!",
                        description=f"{message.author.mention} reached **{user_count}** counts!\n\n"
                                  f"💰 Earned: **{total_coins} PsyCoins** ({coins_earned} + {bonus_coins} bonus)",
                        color=discord.Color.gold()
                    )
                    notice = await message.channel.send(embed=embed)
                    await notice.delete(delay=15)

        try:
            await message.add_reaction("✅")
        except:
            pass

        # Give milestone roles
        if number in self.milestones:
            await self.give_milestone_role(message, number)
            if number not in self.milestone_rewards:  # Only show if not already shown above
                notice = await message.channel.send(
                    f"🎉 **{message.author.mention} reached {number} counts!**"
                )
                await notice.delete(delay=10)

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if message.id not in self.message_numbers:
            return

        msg_data = self.message_numbers[message.id]
        number = msg_data["number"]
        user_id = msg_data["user_id"]
        
        guild = self.bot.get_guild(msg_data["guild_id"])
        if not guild:
            return

        guild_id = str(guild.id)
        if guild_id not in self.count_data:
            return

        counting_channel_id = self.count_data[guild_id].get("channel")
        counting_channel = guild.get_channel(counting_channel_id)
        
        if not counting_channel:
            return

        embed = discord.Embed(
            title="🚫 Hey that's no fair!",
            description=f"<@{user_id}> deleted their number but don't worry I saw it was the number **{number}**",
            color=discord.Color.red()
        )
        
        try:
            await counting_channel.send(embed=embed)
        except:
            pass

        del self.message_numbers[message.id]

    async def give_milestone_role(self, message, number):
        guild = message.guild
        role_name = f"Counter {number}"

        role = discord.utils.get(guild.roles, name=role_name)

        if role is None:
            role = await guild.create_role(
                name=role_name,
                mentionable=True
            )

        await message.author.add_roles(role)

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def counting(self, ctx, channel: Optional[discord.TextChannel] = None):
        target_channel = channel if channel else ctx.channel
        await self._setup_counting(ctx.guild, target_channel, ctx)

    counting_group = app_commands.Group(name="counting", description="Counting game commands")

    @counting_group.command(name="setup", description="Set up the counting game")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(channel="The channel for counting (defaults to current)")
    async def counting_setup_slash(self, interaction: discord.Interaction, channel: Optional[discord.TextChannel] = None):
        await interaction.response.defer()
        if channel:
            target_channel = channel
        elif isinstance(interaction.channel, discord.TextChannel):
            target_channel = interaction.channel
        else:
            await interaction.followup.send("❌ Please specify a text channel!")
            return
        await self._setup_counting(interaction.guild, target_channel, interaction)
    
    @counting_group.command(name="remove", description="Disable the counting game")
    @app_commands.checks.has_permissions(administrator=True)
    async def counting_remove_slash(self, interaction: discord.Interaction):
        """Disable the counting game"""
        guild_id = str(interaction.guild.id)
        
        if guild_id not in self.count_data:
            await interaction.response.send_message("❌ Counting game is not set up in this server!", ephemeral=True)
            return
        
        del self.count_data[guild_id]
        self.save_data()
        
        await interaction.response.send_message("✅ Counting game disabled in this server!")

    async def _setup_counting(self, guild, channel, ctx_or_interaction):
        guild_id = str(guild.id)
        if guild_id not in self.count_data:
            self.count_data[guild_id] = {"current_count": 0, "last_user": None}

        self.count_data[guild_id]["channel"] = channel.id
        self.save_data()

        msg = f"✅ Counting game enabled in {channel.mention}! Start counting from 1!"
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.followup.send(msg)
        else:
            await ctx_or_interaction.send(msg)
    
    @commands.command(name="countingremove")
    @commands.has_permissions(administrator=True)
    async def counting_remove(self, ctx):
        """Disable the counting game (admin only)"""
        guild_id = str(ctx.guild.id)
        
        if guild_id not in self.count_data:
            await ctx.send("❌ Counting game is not set up in this server!")
            return
        
        del self.count_data[guild_id]
        self.save_data()
        
        await ctx.send("✅ Counting game disabled in this server!")

async def setup(bot):
    await bot.add_cog(Counting(bot))
