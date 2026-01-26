import discord
from discord.ext import commands
from discord import app_commands
import json
import os
from typing import Optional

class Blacklist(commands.Cog):
    """Blacklist management for bot owners"""
    
    def __init__(self, bot):
        self.bot = bot
        self.file_path = "blacklist.json"
        self.load_data()
        self.owner_ids = bot.owner_ids
    
    def load_data(self):
        """Load blacklist data"""
        if os.path.exists(self.file_path):
            with open(self.file_path, 'r') as f:
                self.blacklist_data = json.load(f)
        else:
            self.blacklist_data = {
                "users": [],
                "servers": []
            }
            self.save_data()
    
    def save_data(self):
        """Save blacklist data"""
        with open(self.file_path, 'w') as f:
            json.dump(self.blacklist_data, f, indent=4)
    
    async def cog_check(self, ctx):
        """Global check - only allow owners"""
        user_id = None
        if hasattr(ctx, 'author'):
            user_id = ctx.author.id
        elif hasattr(ctx, 'user'):
            user_id = ctx.user.id
        
        is_owner = user_id in self.owner_ids
        return is_owner
    
    def is_blacklisted(self, user_id: int = None, guild_id: int = None) -> bool:
        """Check if user or guild is blacklisted"""
        if user_id and user_id in self.blacklist_data["users"]:
            return True
        if guild_id and guild_id in self.blacklist_data["servers"]:
            return True
        return False
    
    @commands.group(name="blacklist", invoke_without_command=True)
    async def blacklist(self, ctx):
        """Manage bot blacklist (Owner only)"""
        embed = discord.Embed(
            title="🚫 Blacklist Management",
            description="Control who can use the bot",
            color=discord.Color.red()
        )
        
        embed.add_field(
            name="📋 Commands",
            value="```\n"
                  "L!blacklist user add <user_id>    - Blacklist a user\n"
                  "L!blacklist user remove <user_id> - Remove user blacklist\n"
                  "L!blacklist server add <guild_id> - Blacklist a server\n"
                  "L!blacklist server remove <id>    - Remove server blacklist\n"
                  "L!blacklist list                  - View all blacklists\n"
                  "```",
            inline=False
        )
        
        # Show current blacklists
        user_count = len(self.blacklist_data["users"])
        server_count = len(self.blacklist_data["servers"])
        
        embed.add_field(name="Users Blacklisted", value=str(user_count), inline=True)
        embed.add_field(name="Servers Blacklisted", value=str(server_count), inline=True)
        
        await ctx.send(embed=embed)
    
    @blacklist.group(name="user", invoke_without_command=True)
    async def blacklist_user(self, ctx):
        """Manage user blacklist"""
        await ctx.send("Use: `L!blacklist user add <user_id>` or `L!blacklist user remove <user_id>`")
    
    @blacklist_user.command(name="add")
    async def blacklist_user_add(self, ctx, user_id: int):
        """Blacklist a user from using the bot"""
        if user_id in self.owner_ids:
            await ctx.send("❌ Cannot blacklist a bot owner!")
            return
        
        if user_id in self.blacklist_data["users"]:
            await ctx.send(f"❌ User `{user_id}` is already blacklisted!")
            return
        
        self.blacklist_data["users"].append(user_id)
        self.save_data()
        
        # Try to get user info
        try:
            user = await self.bot.fetch_user(user_id)
            user_name = f"{user.name} ({user_id})"
        except:
            user_name = f"User ID: {user_id}"
        
        embed = discord.Embed(
            title="🚫 User Blacklisted",
            description=f"**{user_name}** has been blacklisted from using the bot.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
    
    @blacklist_user.command(name="remove")
    async def blacklist_user_remove(self, ctx, user_id: int):
        """Remove a user from blacklist"""
        if user_id not in self.blacklist_data["users"]:
            await ctx.send(f"❌ User `{user_id}` is not blacklisted!")
            return
        
        self.blacklist_data["users"].remove(user_id)
        self.save_data()
        
        # Try to get user info
        try:
            user = await self.bot.fetch_user(user_id)
            user_name = f"{user.name} ({user_id})"
        except:
            user_name = f"User ID: {user_id}"
        
        embed = discord.Embed(
            title="✅ User Un-blacklisted",
            description=f"**{user_name}** can now use the bot again.",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
    
    @blacklist.group(name="server", invoke_without_command=True)
    async def blacklist_server(self, ctx):
        """Manage server blacklist"""
        await ctx.send("Use: `L!blacklist server add <guild_id>` or `L!blacklist server remove <guild_id>`")
    
    @blacklist_server.command(name="add")
    async def blacklist_server_add(self, ctx, guild_id: int):
        """Blacklist a server from using the bot"""
        if guild_id in self.blacklist_data["servers"]:
            await ctx.send(f"❌ Server `{guild_id}` is already blacklisted!")
            return
        
        self.blacklist_data["servers"].append(guild_id)
        self.save_data()
        
        # Try to get guild info
        try:
            guild = self.bot.get_guild(guild_id)
            if guild:
                guild_name = f"{guild.name} ({guild_id})"
            else:
                guild_name = f"Server ID: {guild_id}"
        except:
            guild_name = f"Server ID: {guild_id}"
        
        embed = discord.Embed(
            title="🚫 Server Blacklisted",
            description=f"**{guild_name}** has been blacklisted.\n\nThe bot will not respond to commands in this server.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
    
    @blacklist_server.command(name="remove")
    async def blacklist_server_remove(self, ctx, guild_id: int):
        """Remove a server from blacklist"""
        if guild_id not in self.blacklist_data["servers"]:
            await ctx.send(f"❌ Server `{guild_id}` is not blacklisted!")
            return
        
        self.blacklist_data["servers"].remove(guild_id)
        self.save_data()
        
        # Try to get guild info
        try:
            guild = self.bot.get_guild(guild_id)
            if guild:
                guild_name = f"{guild.name} ({guild_id})"
            else:
                guild_name = f"Server ID: {guild_id}"
        except:
            guild_name = f"Server ID: {guild_id}"
        
        embed = discord.Embed(
            title="✅ Server Un-blacklisted",
            description=f"**{guild_name}** can now use the bot again.",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
    
    @blacklist.command(name="list")
    async def blacklist_list(self, ctx):
        """View all blacklisted users and servers"""
        embed = discord.Embed(
            title="🚫 Blacklist Overview",
            color=discord.Color.red()
        )
        
        # Users
        if self.blacklist_data["users"]:
            user_list = []
            for user_id in self.blacklist_data["users"][:10]:  # Show max 10
                try:
                    user = await self.bot.fetch_user(user_id)
                    user_list.append(f"• {user.name} (`{user_id}`)")
                except:
                    user_list.append(f"• Unknown User (`{user_id}`)")
            
            user_text = "\n".join(user_list)
            if len(self.blacklist_data["users"]) > 10:
                user_text += f"\n... and {len(self.blacklist_data['users']) - 10} more"
            
            embed.add_field(name=f"👥 Blacklisted Users ({len(self.blacklist_data['users'])})", value=user_text, inline=False)
        else:
            embed.add_field(name="👥 Blacklisted Users", value="None", inline=False)
        
        # Servers
        if self.blacklist_data["servers"]:
            server_list = []
            for guild_id in self.blacklist_data["servers"][:10]:  # Show max 10
                try:
                    guild = self.bot.get_guild(guild_id)
                    if guild:
                        server_list.append(f"• {guild.name} (`{guild_id}`)")
                    else:
                        server_list.append(f"• Unknown Server (`{guild_id}`)")
                except:
                    server_list.append(f"• Unknown Server (`{guild_id}`)")
            
            server_text = "\n".join(server_list)
            if len(self.blacklist_data["servers"]) > 10:
                server_text += f"\n... and {len(self.blacklist_data['servers']) - 10} more"
            
            embed.add_field(name=f"🏰 Blacklisted Servers ({len(self.blacklist_data['servers'])})", value=server_text, inline=False)
        else:
            embed.add_field(name="🏰 Blacklisted Servers", value="None", inline=False)
        
        await ctx.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_command(self, ctx):
        """Check blacklist before command execution"""
        # Skip if owner
        if ctx.author.id in self.owner_ids:
            return
        
        # Check user blacklist
        if ctx.author.id in self.blacklist_data["users"]:
            await ctx.send("🚫 You are blacklisted from using this bot.")
            raise commands.CheckFailure("User is blacklisted")
        
        # Check server blacklist
        if ctx.guild and ctx.guild.id in self.blacklist_data["servers"]:
            await ctx.send("🚫 This server is blacklisted from using this bot.")
            raise commands.CheckFailure("Server is blacklisted")
    
    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        """Check blacklist for slash commands"""
        if interaction.type != discord.InteractionType.application_command:
            return
        
        # Skip if owner
        if interaction.user.id in self.owner_ids:
            return
        
        # Check user blacklist
        if interaction.user.id in self.blacklist_data["users"]:
            try:
                await interaction.response.send_message("🚫 You are blacklisted from using this bot.", ephemeral=True)
            except:
                pass
            return
        
        # Check server blacklist
        if interaction.guild and interaction.guild.id in self.blacklist_data["servers"]:
            try:
                await interaction.response.send_message("🚫 This server is blacklisted from using this bot.", ephemeral=True)
            except:
                pass
            return

async def setup(bot):
    await bot.add_cog(Blacklist(bot))
