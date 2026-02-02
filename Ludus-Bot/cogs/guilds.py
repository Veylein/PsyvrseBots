import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button
import json
import os
from datetime import datetime
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.embed_styles import EmbedBuilder, Colors, Emojis

class GuildManager:
    """Manages guilds, shared resources, and guild battles"""
    
    def __init__(self, data_dir):
        self.data_dir = data_dir
        self.guilds_file = os.path.join(data_dir, "guilds.json")
        self.guilds = self.load_guilds()
    
    def load_guilds(self):
        if os.path.exists(self.guilds_file):
            try:
                with open(self.guilds_file, 'r') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}
    
    def save_guilds(self):
        try:
            with open(self.guilds_file, 'w') as f:
                json.dump(self.guilds, f, indent=4)
        except Exception as e:
            print(f"Error saving guilds: {e}")
    
    def create_guild(self, guild_id, name, leader_id, description="A new guild"):
        """Create a new guild"""
        guild_id = str(guild_id)
        if guild_id in self.guilds:
            return False, "Guild already exists with this name!"
        
        self.guilds[guild_id] = {
            "name": name,
            "description": description,
            "leader_id": str(leader_id),
            "officers": [],
            "members": [str(leader_id)],
            "created_at": datetime.utcnow().isoformat(),
            "level": 1,
            "xp": 0,
            "bank": 0,
            "perks": [],
            "battles_won": 0,
            "battles_lost": 0,
            "total_contribution": 0
        }
        self.save_guilds()
        return True, "Guild created successfully!"
    
    def get_guild(self, guild_id):
        """Get guild data"""
        return self.guilds.get(str(guild_id))
    
    def get_user_guild(self, user_id):
        """Find which guild a user is in"""
        user_id = str(user_id)
        for guild_id, guild in self.guilds.items():
            if user_id in guild["members"]:
                return guild_id, guild
        return None, None
    
    def join_guild(self, guild_id, user_id):
        """Join a guild"""
        guild_id = str(guild_id)
        user_id = str(user_id)
        
        # Check if already in a guild
        current_guild_id, _ = self.get_user_guild(user_id)
        if current_guild_id:
            return False, "You're already in a guild! Leave first."
        
        guild = self.get_guild(guild_id)
        if not guild:
            return False, "Guild not found!"
        
        if len(guild["members"]) >= 50:
            return False, "Guild is full! (Max 50 members)"
        
        guild["members"].append(user_id)
        self.save_guilds()
        return True, f"Joined {guild['name']}!"
    
    def leave_guild(self, user_id):
        """Leave guild"""
        guild_id, guild = self.get_user_guild(user_id)
        if not guild:
            return False, "You're not in a guild!"
        
        user_id = str(user_id)
        if guild["leader_id"] == user_id:
            return False, "Leaders can't leave! Transfer leadership or disband guild."
        
        guild["members"].remove(user_id)
        if user_id in guild["officers"]:
            guild["officers"].remove(user_id)
        
        self.save_guilds()
        return True, "Left the guild!"
    
    def deposit_to_guild(self, user_id, amount):
        """Deposit coins to guild bank"""
        guild_id, guild = self.get_user_guild(user_id)
        if not guild:
            return False, "You're not in a guild!"
        
        guild["bank"] += amount
        guild["total_contribution"] += amount
        self.save_guilds()
        return True, f"Deposited {amount} coins to guild bank!"
    
    def get_guild_leaderboard(self):
        """Get top guilds by level"""
        sorted_guilds = sorted(
            self.guilds.items(),
            key=lambda x: (x[1]["level"], x[1]["xp"]),
            reverse=True
        )
        return sorted_guilds[:10]

class Guilds(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        data_dir = os.getenv("RENDER_DISK_PATH", ".")
        self.manager = GuildManager(data_dir)
        # Economy handled by central Economy cog; fallback file reads/writes done inline when needed
    
    # Removed direct persistent economy helpers; prefer `Economy` cog.
    
    @commands.group(name="guild", aliases=["g"])
    async def guild(self, ctx):
        """Guild commands"""
        if ctx.invoked_subcommand is None:
            embed = EmbedBuilder.create(
                title=f"{Emojis.CROWN} Guild System",
                description="Build communities and compete together!\n\n"
                           "**Commands:**\n"
                           f"{Emojis.SPARKLES} `L!guild create <name>` - Create guild (1000 coins)\n"
                           f"{Emojis.HEART} `L!guild join <name>` - Join a guild\n"
                           f"{Emojis.FIRE} `L!guild info` - View guild info\n"
                           f"{Emojis.COIN} `L!guild deposit <amount>` - Donate to bank\n"
                           f"{Emojis.TROPHY} `L!guild top` - Guild leaderboards\n"
                           f"{Emojis.GAME} `L!guild leave` - Leave guild",
                color=Colors.PRIMARY
            )
            await ctx.send(embed=embed)
    
    @guild.command(name="create")
    async def guild_create(self, ctx, *, name: str):
        """Create a new guild"""
        economy_cog = self.bot.get_cog("Economy")
        user_id = str(ctx.author.id)

        if economy_cog:
            balance = economy_cog.get_balance(ctx.author.id)
            if balance < 1000:
                await ctx.send("❌ Need 1,000 PsyCoins to create a guild!")
                return
        else:
            economy_file = os.path.join(self.manager.data_dir, "economy.json")
            economy = {}
            if os.path.exists(economy_file):
                try:
                    with open(economy_file, 'r') as f:
                        economy = json.load(f)
                except Exception:
                    economy = {}

            if user_id not in economy:
                economy[user_id] = {"balance": 0}
            if economy[user_id]["balance"] < 1000:
                await ctx.send("❌ Need 1,000 PsyCoins to create a guild!")
                return
        
        # Check if already in guild
        _, current_guild = self.manager.get_user_guild(ctx.author.id)
        if current_guild:
            await ctx.send("❌ You're already in a guild!")
            return
        
        # Create guild with name as ID (simplified)
        guild_id = name.lower().replace(" ", "_")
        success, message = self.manager.create_guild(guild_id, name, ctx.author.id)
        
        if success:
            # Deduct coins via Economy cog if available
            if economy_cog:
                try:
                    economy_cog.remove_coins(ctx.author.id, 1000)
                except Exception:
                    pass
            else:
                economy[user_id]["balance"] -= 1000
                try:
                    with open(economy_file, 'w') as f:
                        json.dump(economy, f, indent=4)
                except Exception:
                    pass
            
            embed = EmbedBuilder.create(
                title=f"{Emojis.SUCCESS} Guild Created!",
                description=f"**{name}** has been founded!\n\n"
                           f"💰 Cost: 1,000 PsyCoins\n"
                           f"👑 You are the guild leader!\n\n"
                           f"Use `L!guild info` to manage your guild!",
                color=Colors.SUCCESS
            )
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"❌ {message}")
    
    @guild.command(name="info")
    async def guild_info(self, ctx):
        """View your guild info"""
        guild_id, guild = self.manager.get_user_guild(ctx.author.id)
        
        if not guild:
            await ctx.send("❌ You're not in a guild! Use `L!guild create` or `L!guild join`")
            return
        
        try:
            leader = await self.bot.fetch_user(int(guild["leader_id"]))
            leader_name = leader.display_name
        except:
            leader_name = "Unknown"
        
        embed = EmbedBuilder.create(
            title=f"{Emojis.CROWN} {guild['name']}",
            description=f"*{guild['description']}*\n\n"
                       f"**Leader:** {leader_name}\n"
                       f"**Level:** {guild['level']}\n"
                       f"**Members:** {len(guild['members'])}/50\n"
                       f"**Guild Bank:** {guild['bank']} PsyCoins\n"
                       f"**Record:** {guild['battles_won']}W - {guild['battles_lost']}L\n"
                       f"**Total Contributions:** {guild['total_contribution']} coins",
            color=Colors.PRIMARY
        )
        
        await ctx.send(embed=embed)
    
    @guild.command(name="deposit", aliases=["donate"])
    async def guild_deposit(self, ctx, amount: int):
        """Deposit coins to guild bank"""
        if amount <= 0:
            await ctx.send("❌ Amount must be positive!")
            return
        economy_cog = self.bot.get_cog("Economy")
        user_id = str(ctx.author.id)

        # Verify balance and deduct through Economy cog if available
        if economy_cog:
            balance = economy_cog.get_balance(ctx.author.id)
            if balance < amount:
                await ctx.send(f"❌ Not enough coins! You have {balance}.")
                return
        else:
            economy_file = os.path.join(self.manager.data_dir, "economy.json")
            economy = {}
            if os.path.exists(economy_file):
                try:
                    with open(economy_file, 'r') as f:
                        economy = json.load(f)
                except Exception:
                    economy = {}

            if user_id not in economy:
                economy[user_id] = {"balance": 0}
            if economy[user_id]["balance"] < amount:
                await ctx.send(f"❌ Not enough coins! You have {economy[user_id]['balance']}.")
                return

        success, message = self.manager.deposit_to_guild(ctx.author.id, amount)

        if success:
            if economy_cog:
                try:
                    economy_cog.remove_coins(ctx.author.id, amount)
                except Exception:
                    pass
            else:
                economy[user_id]["balance"] -= amount
                try:
                    with open(economy_file, 'w') as f:
                        json.dump(economy, f, indent=4)
                except Exception:
                    pass

            embed = EmbedBuilder.create(
                title=f"{Emojis.SUCCESS} Donation Complete!",
                description=f"Deposited **{amount} PsyCoins** to guild bank!\n"
                           f"Thank you for your contribution! 💖",
                color=Colors.SUCCESS
            )
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"❌ {message}")
    
    @guild.command(name="top", aliases=["leaderboard", "lb"])
    async def guild_leaderboard(self, ctx):
        """View top guilds"""
        leaderboard = self.manager.get_guild_leaderboard()
        
        if not leaderboard:
            await ctx.send("❌ No guilds exist yet!")
            return
        
        embed = EmbedBuilder.create(
            title=f"{Emojis.TROPHY} Top Guilds",
            description="The strongest guilds in Ludus!\n\n",
            color=Colors.WARNING
        )
        
        for i, (guild_id, guild) in enumerate(leaderboard, 1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"**{i}.**"
            
            embed.add_field(
                name=f"{medal} {guild['name']}",
                value=f"Level **{guild['level']}** • {len(guild['members'])} members\n"
                      f"Bank: {guild['bank']} coins • W/L: {guild['battles_won']}/{guild['battles_lost']}",
                inline=False
            )
        
        await ctx.send(embed=embed)
    
    @guild.command(name="join")
    async def guild_join(self, ctx, *, name: str):
        """Join a guild"""
        guild_id = name.lower().replace(" ", "_")
        success, message = self.manager.join_guild(guild_id, ctx.author.id)
        
        if success:
            embed = EmbedBuilder.create(
                title=f"{Emojis.SUCCESS} Joined Guild!",
                description=f"Welcome to **{name}**!\n"
                           f"Use `L!guild info` to view guild details!",
                color=Colors.SUCCESS
            )
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"❌ {message}")
    
    @guild.command(name="leave")
    async def guild_leave(self, ctx):
        """Leave your guild"""
        success, message = self.manager.leave_guild(ctx.author.id)
        
        if success:
            await ctx.send(f"✅ {message}")
        else:
            await ctx.send(f"❌ {message}")

async def setup(bot):
    await bot.add_cog(Guilds(bot))
