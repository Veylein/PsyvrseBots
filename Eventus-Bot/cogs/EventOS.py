import discord
from discord.ext import commands
from .. import db_async as db
import datetime

class EventOS(commands.Cog):
    """Handles event creation, RSVP, and other event management features."""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="create_event")
    @commands.has_permissions(manage_guild=True)
    async def create_event(self, ctx, title: str, start_time: str, end_time: str, *, description: str):
        """Create an event."""
        event_id = await db.execute(
            "INSERT INTO events (title, description, creator_id, start_time, end_time, rsvp_list) VALUES (?, ?, ?, ?, ?, ?)",
            (title, description, ctx.author.id, start_time, end_time, ""),
            commit=True
        )
        await ctx.send(f"Event created successfully! Event ID: {event_id}")
    
    @commands.command(name="rsvp")
    async def rsvp(self, ctx, event_id: int):
        """RSVP to an event."""
        row = await db.fetchone("SELECT rsvp_list FROM events WHERE event_id = ?", (event_id,))
        if not row:
            await ctx.send("Event not found.")
            return
        rsvp_list = row['rsvp_list'].split(',') if row and row['rsvp_list'] else []
        if str(ctx.author.id) in rsvp_list:
            await ctx.send("You have already RSVPed for this event.")
            return
        rsvp_list.append(str(ctx.author.id))
        await db.execute("UPDATE events SET rsvp_list = ? WHERE event_id = ?", (','.join(rsvp_list), event_id), commit=True)
        await ctx.send(f"{ctx.author.mention} RSVPed to event {event_id}!")

    @commands.command(name="event_info")
    async def event_info(self, ctx, event_id: int):
        """Show information about an event."""
        event = await db.fetchone("SELECT * FROM events WHERE event_id = ?", (event_id,))
        if not event:
            await ctx.send("Event not found.")
            return
        embed = discord.Embed(title=event['title'], description=event['description'], color=discord.Color.blue())
        embed.add_field(name="Start Time", value=event['start_time'])
        embed.add_field(name="End Time", value=event['end_time'])
        embed.add_field(name="RSVP List", value=event['rsvp_list'])
        await ctx.send(embed=embed)

    @commands.command(name="list_events")
    async def list_events(self, ctx):
        """List all upcoming events."""
        events = await db.fetchall("SELECT event_id, title, start_time, end_time FROM events WHERE start_time > ?", (datetime.datetime.utcnow().isoformat(),))
        if not events:
            await ctx.send("No upcoming events.")
            return
        embed = discord.Embed(title="Upcoming Events", color=discord.Color.green())
        for event in events:
            embed.add_field(name=event['title'], value=f"ID: {event['event_id']} | {event['start_time']} - {event['end_time']}", inline=False)
        await ctx.send(embed=embed)

    @commands.command(name="remove_event")
    @commands.has_permissions(manage_guild=True)
    async def remove_event(self, ctx, event_id: int):
        """Remove an event."""
        await db.execute("DELETE FROM events WHERE event_id = ?", (event_id,), commit=True)
        await ctx.send(f"Event {event_id} has been removed.")

    @commands.command(name="archive_event")
    async def archive_event(self, ctx, event_id: int):
        """Archive an event."""
        await db.execute("UPDATE events SET archived = 1 WHERE event_id = ?", (event_id,), commit=True)
        await ctx.send(f"Event {event_id} has been archived.")

async def setup(bot):
    await bot.add_cog(EventOS(bot))
