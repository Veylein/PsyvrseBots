import discord
from discord import app_commands
from discord.ext import commands

from .. import db_async


class AdminCog(commands.Cog):
    """Guild administration commands: prefix, topic settings, ignores."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def _param_style(self):
        return db_async.DATABASE_URL and db_async.asyncpg

    async def _upsert_guild_prefix(self, guild_id: int, prefix: str):
        if self._param_style():
            sql = """
            INSERT INTO guilds (guild_id, prefix) VALUES ($1,$2)
            ON CONFLICT (guild_id) DO UPDATE SET prefix = EXCLUDED.prefix
            """
            await db_async.execute(sql, (guild_id, prefix))
        else:
            sql = """
            INSERT INTO guilds (guild_id, prefix) VALUES (?,?)
            ON CONFLICT(guild_id) DO UPDATE SET prefix = excluded.prefix
            """
            await db_async.execute(sql, (guild_id, prefix), commit=True)

    async def _upsert_topic_settings(self, guild_id: int, channel_id: int = None, interval: int = None):
        # Fetch existing settings
        exists = await db_async.fetchone(
            "SELECT 1 FROM topic_settings WHERE guild_id = $1" if self._param_style() else "SELECT 1 FROM topic_settings WHERE guild_id = ?",
            (guild_id,),
        )
        if exists:
            if channel_id is not None:
                await db_async.execute(
                    "UPDATE topic_settings SET channel_id = $1 WHERE guild_id = $2" if self._param_style() else "UPDATE topic_settings SET channel_id = ? WHERE guild_id = ?",
                    (channel_id, guild_id),
                )
            if interval is not None:
                await db_async.execute(
                    "UPDATE topic_settings SET interval_minutes = $1 WHERE guild_id = $2" if self._param_style() else "UPDATE topic_settings SET interval_minutes = ? WHERE guild_id = ?",
                    (interval, guild_id),
                )
        else:
            # Insert defaults as needed
            ch = channel_id or 0
            itv = interval or 60
            if self._param_style():
                await db_async.execute(
                    "INSERT INTO topic_settings (guild_id, channel_id, interval_minutes) VALUES ($1,$2,$3)",
                    (guild_id, ch, itv),
                )
            else:
                await db_async.execute(
                    "INSERT INTO topic_settings (guild_id, channel_id, interval_minutes) VALUES (?,?,?)",
                    (guild_id, ch, itv),
                    commit=True,
                )

    async def _set_ignore_channel(self, guild_id: int, channel_id: int, add: bool = True):
        if add:
            if self._param_style():
                await db_async.execute("INSERT INTO ignored_channels (guild_id, channel_id) VALUES ($1,$2) ON CONFLICT DO NOTHING", (guild_id, channel_id))
            else:
                await db_async.execute("INSERT OR IGNORE INTO ignored_channels (guild_id, channel_id) VALUES (?,?)", (guild_id, channel_id), commit=True)
        else:
            await db_async.execute("DELETE FROM ignored_channels WHERE guild_id = $1 AND channel_id = $2" if self._param_style() else "DELETE FROM ignored_channels WHERE guild_id = ? AND channel_id = ?", (guild_id, channel_id))

    # Prefix commands
    @app_commands.command(name="set_prefix")
    @app_commands.describe(prefix="New command prefix for this guild")
    async def set_prefix_slash(self, interaction: discord.Interaction, prefix: str):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Administrator permissions required.", ephemeral=True)
            return
        await self._upsert_guild_prefix(interaction.guild.id, prefix)
        await interaction.response.send_message(f"Prefix set to: {prefix}", ephemeral=True)

    @commands.command(name="set_prefix")
    @commands.has_permissions(administrator=True)
    async def set_prefix(self, ctx: commands.Context, prefix: str):
        await self._upsert_guild_prefix(ctx.guild.id, prefix)
        await ctx.send(f"Prefix set to: {prefix}")

    # Topic settings
    @app_commands.command(name="set_topic_channel")
    @app_commands.describe(channel="Channel to post auto-topics in")
    async def set_topic_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Administrator permissions required.", ephemeral=True)
            return
        await self._upsert_topic_settings(interaction.guild.id, channel.id, None)
        await interaction.response.send_message(f"Topic channel set to {channel.mention}", ephemeral=True)

    @app_commands.command(name="set_topic_interval")
    @app_commands.describe(minutes="Interval in minutes between topics")
    async def set_topic_interval(self, interaction: discord.Interaction, minutes: int):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Administrator permissions required.", ephemeral=True)
            return
        await self._upsert_topic_settings(interaction.guild.id, None, minutes)
        await interaction.response.send_message(f"Topic interval set to {minutes} minutes", ephemeral=True)

    # Ignore channel management
    @app_commands.command(name="ignore_channel")
    @app_commands.describe(channel="Channel to ignore for scoring", remove="Remove ignore if true")
    async def ignore_channel(self, interaction: discord.Interaction, channel: discord.TextChannel, remove: bool = False):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Administrator permissions required.", ephemeral=True)
            return
        await self._set_ignore_channel(interaction.guild.id, channel.id, add=not remove)
        verb = "removed from" if remove else "added to"
        await interaction.response.send_message(f"Channel {channel.mention} {verb} ignore list.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(AdminCog(bot))
