import discord
from discord.ext import commands
import sqlite3

MOMENTUM_ACTIONS = {
    'talk_consistently': 2,
    'reply_to_others': 1,
    'complete_topic': 3,
    'attend_event': 4,
    'start_high_engagement_thread': 5
}

MOMENTUM_REWARDS = {
    10: 'Participant Badge',
    25: 'Title: Engager',
    50: 'Profile Frame',
    100: 'Event Priority Seating',
    200: 'Custom RSVP Cosmetic',
    500: 'Flex Toy'
}

class Momentum(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_db(self):
        conn = sqlite3.connect('eventus.db')
        conn.row_factory = sqlite3.Row
        return conn

    def add_momentum(self, user_id, username, action):
        points = MOMENTUM_ACTIONS.get(action, 0)
        if points == 0:
            return
        conn = self.get_db()
        c = conn.cursor()
        c.execute("""
            INSERT INTO users (user_id, username, momentum)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                momentum = momentum + ?,
                username = excluded.username
        """, (user_id, username, points, points))
        conn.commit()
        conn.close()

    def get_rewards(self, momentum):
        rewards = []
        for threshold, name in sorted(MOMENTUM_REWARDS.items()):
            if momentum >= threshold:
                rewards.append(name)
        # Add unlocks for each reward type
        unlocks = []
        if momentum >= 10:
            unlocks.append('Participation Badge')
        if momentum >= 25:
            unlocks.append('Title: Engager')
        if momentum >= 50:
            unlocks.append('Profile Frame')
        if momentum >= 100:
            unlocks.append('Event Priority Seating')
        if momentum >= 200:
            unlocks.append('Custom RSVP Cosmetic')
        if momentum >= 500:
            unlocks.append('Flex Toy')
        return rewards + unlocks if rewards or unlocks else ['None']

    @commands.hybrid_command(name="momentum", description="Show your Momentum and unlocked rewards.")
    async def momentum(self, ctx, member: discord.Member = None):
        member = member or (ctx.author if hasattr(ctx, 'author') else ctx.user)
        conn = self.get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE user_id = ?", (member.id,))
        row = c.fetchone()
        conn.close()
        if not row:
            if hasattr(ctx, 'respond'):
                await ctx.respond(f"No momentum data for {member.display_name}.", ephemeral=True)
            else:
                await ctx.send(f"No momentum data for {member.display_name}.")
            return
        rewards = self.get_rewards(row['momentum'])
        embed = discord.Embed(title=f"Momentum for {member.display_name}", color=discord.Color.gold())
        embed.add_field(name="Momentum Points", value=row['momentum'])
        embed.add_field(name="Unlocked Rewards", value='\n'.join(rewards))
        if hasattr(ctx, 'respond'):
            await ctx.respond(embed=embed, ephemeral=True)
        else:
            await ctx.send(embed=embed)

    # Example: Hook into activity engine for demo
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        # Talking consistently
        self.add_momentum(message.author.id, str(message.author), 'talk_consistently')
        # Reply to others
        if message.reference:
            self.add_momentum(message.author.id, str(message.author), 'reply_to_others')
        # Completing topics (demo: if message contains 'done')
        if 'done' in message.content.lower():
            self.add_momentum(message.author.id, str(message.author), 'complete_topic')
        # Starting high-engagement threads (demo: if message starts with 'thread:')
        if message.content.lower().startswith('thread:'):
            self.add_momentum(message.author.id, str(message.author), 'start_high_engagement_thread')
    @commands.hybrid_command(name="attend_event", description="Mark yourself as attended for an event (demo integration)")
    async def attend_event(self, ctx, event_id: int):
        user = ctx.author if hasattr(ctx, 'author') else ctx.user
        self.add_momentum(user.id, str(user), 'attend_event')
        if hasattr(ctx, 'respond'):
            await ctx.respond(f"{user.mention} attended event {event_id} and earned Momentum!")
        else:
            await ctx.send(f"{user.mention} attended event {event_id} and earned Momentum!")

async def setup(bot):
    await bot.add_cog(Momentum(bot))
