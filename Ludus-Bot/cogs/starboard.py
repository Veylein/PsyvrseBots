import discord
from discord.ext import commands
from discord import app_commands
import json
import os

STARBOARD_FILE = "data/starboard.json"

def load_starboards():
    if not os.path.exists(STARBOARD_FILE):
        with open(STARBOARD_FILE, "w") as f:
            json.dump({"boards": {}, "limit": 5, "posted_messages": {}}, f, indent=4)
    with open(STARBOARD_FILE, "r") as f:
        data = json.load(f)
        if "posted_messages" not in data:
            data["posted_messages"] = {}
        return data

def save_starboards(data):
    with open(STARBOARD_FILE, "w") as f:
        json.dump(data, f, indent=4)


class Starboard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data = load_starboards()

    @commands.group(name="starboard", invoke_without_command=True)
    async def starboard(self, ctx):
        await ctx.send("Starboard commands: `create`, `edit`, `remove`")

    @starboard.command(name="create")
    @commands.has_permissions(administrator=True)
    async def create(self, ctx, emoji: str, channel: discord.TextChannel, amount: int):
        await self._create_starboard(ctx.guild, emoji, channel, amount, ctx)
    
    @app_commands.command(name="starboard", description="Create a starboard")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(
        emoji="Emoji to react with",
        channel="Channel to post starred messages",
        amount="Number of reactions needed"
    )
    async def starboard_slash(self, interaction: discord.Interaction, emoji: str, channel: discord.TextChannel, amount: int):
        await interaction.response.defer()
        await self._create_starboard(interaction.guild, emoji, channel, amount, interaction)

    async def _create_starboard(self, guild, emoji, channel, amount, ctx_or_interaction):
        guild_id = str(guild.id)

        if guild_id not in self.data["boards"]:
            self.data["boards"][guild_id] = {}

        boards = self.data["boards"][guild_id]

        if len(boards) >= self.data["limit"]:
            msg = "❌ You already have 5 starboards!"
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.followup.send(msg)
            else:
                await ctx_or_interaction.send(msg)
            return

        if emoji in boards:
            msg = "❌ A starboard with that emoji already exists!"
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.followup.send(msg)
            else:
                await ctx_or_interaction.send(msg)
            return

        boards[emoji] = {
            "channel": channel.id,
            "amount": amount
        }

        save_starboards(self.data)
        msg = f"⭐ Created starboard for {emoji} → {channel.mention}, requires **{amount}** reacts"
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.followup.send(msg)
        else:
            await ctx_or_interaction.send(msg)

    @starboard.command(name="edit")
    @commands.has_permissions(administrator=True)
    async def edit(self, ctx, emoji: str, amount: int):
        await self._edit_starboard(ctx.guild, emoji, amount, ctx)
    
    @app_commands.command(name="starboard_edit", description="Edit a starboard's reaction requirement")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(
        emoji="Emoji of the starboard to edit",
        amount="New number of reactions needed"
    )
    async def starboard_edit_slash(self, interaction: discord.Interaction, emoji: str, amount: int):
        await interaction.response.defer()
        await self._edit_starboard(interaction.guild, emoji, amount, interaction)

    async def _edit_starboard(self, guild, emoji, amount, ctx_or_interaction):
        guild_id = str(guild.id)

        if guild_id not in self.data["boards"] or emoji not in self.data["boards"][guild_id]:
            msg = "❌ That starboard doesn't exist!"
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.followup.send(msg)
            else:
                await ctx_or_interaction.send(msg)
            return

        self.data["boards"][guild_id][emoji]["amount"] = amount
        save_starboards(self.data)
        msg = f"✏️ Updated `{emoji}` starboard → requires **{amount}** reactions"
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.followup.send(msg)
        else:
            await ctx_or_interaction.send(msg)

    @starboard.command(name="remove")
    @commands.has_permissions(administrator=True)
    async def remove(self, ctx, emoji: str):
        await self._remove_starboard(ctx.guild, emoji, ctx)
    
    @app_commands.command(name="starboard_delete", description="Delete a starboard")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(emoji="Emoji of the starboard to delete")
    async def starboard_delete_slash(self, interaction: discord.Interaction, emoji: str):
        await interaction.response.defer()
        await self._remove_starboard(interaction.guild, emoji, interaction)

    async def _remove_starboard(self, guild, emoji, ctx_or_interaction):
        guild_id = str(guild.id)

        if guild_id not in self.data["boards"] or emoji not in self.data["boards"][guild_id]:
            msg = "❌ That starboard doesn't exist!"
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.followup.send(msg)
            else:
                await ctx_or_interaction.send(msg)
            return

        del self.data["boards"][guild_id][emoji]
        save_starboards(self.data)
        msg = f"🗑️ Removed starboard `{emoji}`"
        if isinstance(ctx_or_interaction, discord.Interaction):
            await ctx_or_interaction.followup.send(msg)
        else:
            await ctx_or_interaction.send(msg)

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if user.bot:
            return

        message = reaction.message
        guild = message.guild

        if not guild:
            return

        guild_id = str(guild.id)
        boards = self.data["boards"].get(guild_id, {})

        emoji = str(reaction.emoji)

        if emoji not in boards:
            return

        board = boards[emoji]
        needed = board["amount"]
        channel_id = board["channel"]
        starboard_channel = guild.get_channel(channel_id)

        if not starboard_channel:
            return

        count = 0
        for r in message.reactions:
            if str(r.emoji) == emoji:
                count = r.count

        if count < needed:
            return

        message_key = f"{guild_id}_{message.id}_{emoji}"
        
        if "posted_messages" not in self.data:
            self.data["posted_messages"] = {}
        
        if message_key in self.data["posted_messages"]:
            return

        embed = discord.Embed(
            description=message.content or "*No content*",
            color=discord.Color.gold(),
            timestamp=message.created_at
        )
        embed.set_author(name=str(message.author), icon_url=message.author.display_avatar.url)
        embed.add_field(name="Original Message", value=f"[Jump to Message]({message.jump_url})", inline=False)
        embed.add_field(name="Channel", value=message.channel.mention, inline=True)
        embed.set_footer(text=f"{emoji} {count} reactions")

        if len(message.attachments) > 0:
            embed.set_image(url=message.attachments[0].url)

        try:
            await starboard_channel.send(embed=embed)
            self.data["posted_messages"][message_key] = True
            save_starboards(self.data)
        except Exception as e:
            print(f"[Starboard] Error sending embed: {e}")


async def setup(bot):
    await bot.add_cog(Starboard(bot))
