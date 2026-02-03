import discord
from discord.ext import commands
from discord import app_commands
import datetime
import json
import csv
import io

OWNER_IDS = {
    1382187068373074001,
    1300838678280671264,
    1311394031640776716,
    1138720397567742014,
    1445281424050618440
}

class Owner(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def is_owner(self, user_id):
        return user_id in OWNER_IDS

    @commands.command(name="reload", description="Reload a cog. Owner only.")
    async def reload(self, ctx, cog: str):
        if not self.is_owner(ctx.author.id):
            await ctx.send("You do not have permission to use this command.")
            return
        try:
            self.bot.reload_extension(f"cogs.{cog}")
            await ctx.send(f"Successfully reloaded {cog} cog.")
        except Exception as e:
            await ctx.send(f"Failed to reload {cog} cog. Error: {e}")

    @commands.command(name="shutdown", description="Shuts down the bot. Owner only.")
    async def shutdown(self, ctx):
        if not self.is_owner(ctx.author.id):
            await ctx.send("You do not have permission to use this command.")
            return
        await ctx.send("Shutting down...")
        await self.bot.close()

    @commands.command(name="sync", description="Sync the commands. Owner only.")
    async def sync(self, ctx):
        if not self.is_owner(ctx.author.id):
            await ctx.send("You do not have permission to use this command.")
            return
        try:
            synced = await self.bot.tree.sync()
            await ctx.send(f"Successfully synced commands: {[cmd.name for cmd in synced]}")
        except Exception as e:
            await ctx.send(f"Failed to sync commands. Error: {e}")

    @commands.command(name="audit", description="Show server audit (owner only)")
    async def audit(self, ctx):
        if not self.is_owner(ctx.author.id):
            await ctx.send("You do not have permission to use this command.")
            return
        # Placeholder for audit logic
        embed = discord.Embed(title="Server Audit", color=discord.Color.red())
        embed.add_field(name="Total Users", value="100")  # Example, replace with actual data
        embed.add_field(name="Total Events", value="50")  # Example, replace with actual data
        await ctx.send(embed=embed)

    @commands.command(name="export", description="Export analytics (owner only)")
    async def export(self, ctx, fmt: str = "json"):
        if not self.is_owner(ctx.author.id):
            await ctx.send("You do not have permission to use this command.")
            return
        rows = [{"created_at": "2022-12-01", "data": "Example analytics data"}]  # Replace with actual data
        if fmt == "json":
            data = json.dumps(rows, indent=2)
            await ctx.send(f"```json\n{data}```")
        elif fmt == "csv":
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=rows[0].keys())
            writer.writeheader()
            for row in rows:
                writer.writerow(row)
            await ctx.send(f"```csv\n{output.getvalue()}```")
        else:
            await ctx.send("Invalid export format. Use `json` or `csv`.")

    @commands.command(name="force_topic", description="Force a topic to drop right now (owner only)")
    async def force_topic(self, ctx, *, topic: str):
        if not self.is_owner(ctx.author.id):
            await ctx.send("You do not have permission to use this command.")
            return
        await ctx.send(f"💡 **Owner Forced Topic:** {topic}")

    @commands.command(name="override", description="Override event/RSVP/momentum/AI settings (owner only)")
    async def override(self, ctx, what: str, value: str):
        if not self.is_owner(ctx.author.id):
            await ctx.send("You do not have permission to use this command.")
            return
        await ctx.send(f"Override {what} with value {value}.")

    @commands.command(name="purge_inactive", description="DM inactive users (owner only)")
    async def purge_inactive(self, ctx, days: int = 7):
        if not self.is_owner(ctx.author.id):
            await ctx.send("You do not have permission to use this command.")
            return
        await ctx.send(f"Inactive users (> {days} days) notified.")

    @commands.command(name="silence", description="Mute auto-topics/messages (owner only)")
    async def silence(self, ctx, hours: int = 1):
        if not self.is_owner(ctx.author.id):
            await ctx.send("You do not have permission to use this command.")
            return
        await ctx.send(f"Auto-topics/messages silenced for {hours} hours.")

    @commands.command(name="tune", description="Tune AI personality (owner only)")
    async def tune(self, ctx, mode: str):
        if not self.is_owner(ctx.author.id):
            await ctx.send("You do not have permission to use this command.")
            return
        await ctx.send(f"AI personality tuned to: {mode}")

async def setup(bot):
    await bot.add_cog(Owner(bot))
