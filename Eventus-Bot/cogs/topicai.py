import discord
from discord.ext import commands, tasks
from discord import app_commands, Interaction
import random
import re
from .. import db_async as db
from .. import llm
from collections import Counter
from datetime import datetime, timedelta
from typing import Optional

STOPWORDS = {
    'the','and','is','in','it','to','a','of','for','on','you','i','we','they','that','this','with','are','be','was','as','but','or'
}

DEFAULT_INTERVAL_MIN = 60

# Basic category keyword mapping and fallback topics (expandable / guild-overrides stored in DB)
CATEGORY_KEYWORDS = {
    'memes': {'meme', 'memes', 'lol', 'funny', 'haha', 'mfw'},
    'music': {'song', 'music', 'album', 'playlist', 'track', 'dj'},
    'gaming': {'game', 'gaming', 'gg', 'fps', 'mmorpg', 'rank'},
    'art': {'art', 'drawing', 'paint', 'sketch', 'design', 'color'},
    'tech': {'python', 'code', 'programming', 'tech', 'software', 'hardware'},
    'food': {'food', 'recipe', 'cook', 'meal', 'dinner', 'lunch'},
}

CATEGORY_TOPICS = {
    'memes': [
        'Share your favorite meme of the week!',
        'What meme format never gets old?',
        'Post a wholesome meme to brighten the channel.'
    ],
    'music': [
        'What are you listening to right now?',
        'Share a song that always lifts your mood.',
        'Which album should everyone listen to once?'
    ],
    'gaming': [
        'What game are you grinding lately?',
        'Single-player or multiplayer — which do you prefer?',
        'Show your best in-game clip or screenshot.'
    ],
    'art': [
        'Share a piece of art you made recently.',
        'What color palette are you loving right now?',
        'Sketch prompt: draw something that represents your mood.'
    ],
    'tech': [
        'What small programming tip saved you recently?',
        'Show us a tiny project you built this month.',
        'Which language/tool do you want to learn next?'
    ],
    'food': [
        'What did you cook recently? Share a photo!',
        'Sweet or savory — which team are you on?',
        'Share a quick recipe everyone should try.'
    ],
}

class TopicAI(commands.Cog):
    """Automatic topic generator and on-demand topic command.

    Behavior:
    - `auto_topic_task` runs periodically and posts a topic in each guild's active channel (default: #general or first text channel).
    - `/topic [category]` will force-generate a topic using recent messages and optionally ping top contributors.
    """
    def __init__(self, bot):
        self.bot = bot
        self.auto_topic_task.start()

    def cog_unload(self):
        try:
            self.auto_topic_task.cancel()
        except Exception:
            pass

    async def get_topic_settings(self, guild_id):
        row = await db.fetchone("SELECT guild_id, channel_id, enabled, interval_minutes, ping_top_n, last_sent FROM topic_settings WHERE guild_id = ?", (guild_id,))
        return dict(row) if row else None

    async def set_topic_setting(self, guild_id, **kwargs):
        # kwargs: channel_id, enabled, interval_minutes, ping_top_n, last_sent
        await db.execute("INSERT INTO topic_settings (guild_id, channel_id, enabled, interval_minutes, ping_top_n, last_sent) VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT(guild_id) DO UPDATE SET channel_id=excluded.channel_id, enabled=excluded.enabled, interval_minutes=excluded.interval_minutes, ping_top_n=excluded.ping_top_n, last_sent=excluded.last_sent",
                         (
                             guild_id,
                             kwargs.get('channel_id'),
                             kwargs.get('enabled', 1),
                             kwargs.get('interval_minutes', 60),
                             kwargs.get('ping_top_n', 2),
                             kwargs.get('last_sent')
                         ), commit=True)

    def extract_keywords(self, texts, top_n=5):
        words = []
        for t in texts:
            # basic tokenization
            for w in re.findall(r"\w+", t.lower()):
                if len(w) < 3: continue
                if w in STOPWORDS: continue
                words.append(w)
        counts = Counter(words)
        return [w for w, _ in counts.most_common(top_n)]

    async def craft_topic(self, keywords, guild=None, channel=None):
        """Choose a topic using (in order): channel-scoped templates, guild templates, global templates, LLM, heuristics."""
        try:
            # detect best category
            best_cat: Optional[str] = None
            best_score = 0
            kw_set = set([k.lower() for k in keywords]) if keywords else set()
            for cat, ks in CATEGORY_KEYWORDS.items():
                score = len(kw_set & ks)
                if score > best_score:
                    best_score = score
                    best_cat = cat

            if best_cat:
                # 1) Channel-scoped templates (guild + channel)
                try:
                    if guild and channel:
                        rows = await db.fetchall(
                            "SELECT template_text FROM topic_templates WHERE category = ? AND guild_id = ? AND channel_id = ? ORDER BY template_id DESC LIMIT 50",
                            (best_cat, guild.id, channel.id),
                        )
                        texts = [r['template_text'] for r in rows] if rows else []
                        if texts:
                            return random.choice(texts)
                except Exception:
                    pass

                # 2) Guild-scoped templates (guild only)
                try:
                    if guild:
                        rows = await db.fetchall(
                            "SELECT template_text FROM topic_templates WHERE category = ? AND guild_id = ? AND channel_id IS NULL ORDER BY template_id DESC LIMIT 50",
                            (best_cat, guild.id),
                        )
                        texts = [r['template_text'] for r in rows] if rows else []
                        if texts:
                            return random.choice(texts)
                except Exception:
                    pass

                # 3) Global templates (no guild)
                try:
                    rows = await db.fetchall(
                        "SELECT template_text FROM topic_templates WHERE category = ? AND guild_id IS NULL ORDER BY template_id DESC LIMIT 50",
                        (best_cat,),
                    )
                    texts = [r['template_text'] for r in rows] if rows else []
                    if texts:
                        return random.choice(texts)
                except Exception:
                    pass

                # 4) Code-provided defaults
                defaults = CATEGORY_TOPICS.get(best_cat, [])
                if defaults:
                    return random.choice(defaults)
        except Exception:
            pass

        # Prefer LLM-crafted topic when available
        try:
            if keywords and getattr(llm, 'OPENAI_API_KEY', None):
                out = await llm.craft_topic_from_keywords(keywords)
                if out:
                    return out
        except Exception:
            pass

        # Fallback heuristic
        if not keywords:
            return random.choice([
                "What's been the highlight of your week?",
                "Share a recent win — big or small!",
                "What's a hobby you're into right now?"
            ])
        if len(keywords) == 1:
            return f"What do you all think about {keywords[0]} lately?"
        if len(keywords) >= 2:
            return f"Quick poll: {keywords[0]} or {keywords[1]} — which do you prefer, and why?"

    async def post_topic(self, guild, channel, topic_text, top_mentions):
        try:
            msg_text = f"💡 **Auto Topic:** {topic_text}"
            if top_mentions:
                msg_text += "\n\n" + " ".join(top_mentions)
            await channel.send(msg_text)
        except Exception:
            pass

    @commands.hybrid_command(name="topic", description="Force-generate a topic from recent chat (optional: ping top N).")
    async def topic(self, ctx, ping_top: int = 0):
        # Use channel history to compile keywords quickly
        channel = ctx.channel if hasattr(ctx, 'channel') else None
        texts = []
        try:
            async for m in channel.history(limit=300):
                if m.author.bot: continue
                texts.append(m.content or '')
        except Exception:
            # fallback to DB
            rows = await db.fetchall("SELECT content FROM messages WHERE guild_id = ? ORDER BY created_at DESC LIMIT 300", (ctx.guild.id,))
            texts = [r['content'] for r in rows]
        keywords = self.extract_keywords(texts, top_n=5)
        topic_text = await self.craft_topic(keywords, ctx.guild if hasattr(ctx, 'guild') else None, ctx.channel if hasattr(ctx, 'channel') else None)
        top_mentions = []
        if ping_top and ctx.guild:
            rows = await db.fetchall("SELECT user_id FROM users ORDER BY activity_score DESC LIMIT ?", (ping_top,))
            for r in rows:
                member = ctx.guild.get_member(r['user_id'])
                if member:
                    # respect opt-out
                    opt = await db.fetchone("SELECT 1 FROM topic_opt_out WHERE guild_id = ? AND user_id = ?", (ctx.guild.id, r['user_id']))
                    if opt:
                        continue
                    top_mentions.append(member.mention)
        if hasattr(ctx, 'respond'):
            await ctx.respond(f"💡 **TopicAI Suggests:** {topic_text}")
            if top_mentions:
                await ctx.send(' '.join(top_mentions))
        else:
            await ctx.send(f"💡 **TopicAI Suggests:** {topic_text}")
            if top_mentions:
                await ctx.send(' '.join(top_mentions))

    @commands.command(name="list_topic_categories")
    async def list_topic_categories(self, ctx):
        """List available topic categories (memes, music, gaming, art, tech, food)."""
        await ctx.send("Available categories: " + ", ".join(sorted(CATEGORY_KEYWORDS.keys())))

    @commands.command(name="list_category_topics")
    async def list_category_topics(self, ctx, category: str):
        """Show example topics for a category or guild-specific templates."""
        cat = category.lower()
        if cat not in CATEGORY_KEYWORDS:
            await ctx.send(f"Unknown category '{category}'. Use `list_topic_categories`.")
            return
        rows = await db.fetchall("SELECT template_text FROM topic_templates WHERE category = ? AND (guild_id = ? OR guild_id IS NULL) ORDER BY guild_id DESC", (cat, ctx.guild.id))
        if rows:
            texts = [r['template_text'] for r in rows]
        else:
            texts = CATEGORY_TOPICS.get(cat, [])
        await ctx.send("Example topics for %s:\n%s" % (cat, '\n'.join(f"- {t}" for t in texts)))

    @commands.command(name="add_category_topic")
    @commands.has_permissions(manage_guild=True)
    async def add_category_topic(self, ctx, category: str, *, template_text: str):
        """Add a guild-specific topic template for a category."""
        cat = category.lower()
        if cat not in CATEGORY_KEYWORDS:
            await ctx.send(f"Unknown category '{category}'. Use `list_topic_categories`.")
            return
        await db.execute("INSERT INTO topic_templates (guild_id, category, template_text) VALUES (?, ?, ?)", (ctx.guild.id, cat, template_text), commit=True)
        await ctx.send(f"Added template to category '{cat}' for this server.")

    @commands.command(name="set_topic_channel")
    @commands.has_permissions(manage_guild=True)
    async def set_topic_channel(self, ctx, channel: discord.TextChannel):
        """Set the channel where auto-topics will be posted for this guild."""
        await self.set_topic_setting(ctx.guild.id, channel_id=channel.id)
        await ctx.send(f"Auto-topic channel set to {channel.mention}")

    @commands.command(name="enable_topics")
    @commands.has_permissions(manage_guild=True)
    async def enable_topics(self, ctx):
        await self.set_topic_setting(ctx.guild.id, enabled=1)
        await ctx.send("Auto-topics enabled for this server.")

    @commands.command(name="disable_topics")
    @commands.has_permissions(manage_guild=True)
    async def disable_topics(self, ctx):
        await self.set_topic_setting(ctx.guild.id, enabled=0)
        await ctx.send("Auto-topics disabled for this server.")

    @commands.command(name="set_topic_ping")
    @commands.has_permissions(manage_guild=True)
    async def set_topic_ping(self, ctx, top_n: int = 2):
        await self.set_topic_setting(ctx.guild.id, ping_top_n=top_n)
        await ctx.send(f"Auto-topic will ping top {top_n} members by activity.")

    @commands.command(name="opt_out_topics")
    async def opt_out_topics(self, ctx):
        await db.execute("INSERT OR IGNORE INTO topic_opt_out (guild_id, user_id) VALUES (?, ?)", (ctx.guild.id, ctx.author.id), commit=True)
        await ctx.send("You have opted out of being mentioned in auto-topics.")

    @commands.command(name="opt_in_topics")
    async def opt_in_topics(self, ctx):
        await db.execute("DELETE FROM topic_opt_out WHERE guild_id = ? AND user_id = ?", (ctx.guild.id, ctx.author.id), commit=True)
        await ctx.send("You have opted back in to auto-topic mentions.")

    @tasks.loop(minutes=DEFAULT_INTERVAL_MIN)
    async def auto_topic_task(self):
        # For each guild, attempt to generate and post a topic
        for guild in list(self.bot.guilds):
            # choose target channel: #general preferred
            channel = discord.utils.get(guild.text_channels, name='general') or (guild.text_channels[0] if guild.text_channels else None)
            if not channel:
                continue
            # respect per-guild topic settings (cooldown / enabled)
            ts = await self.get_topic_settings(guild.id)
            if ts and ts.get('enabled') == 0:
                continue
            if ts and ts.get('last_sent'):
                try:
                    last = datetime.fromisoformat(ts.get('last_sent'))
                    interval = int(ts.get('interval_minutes', DEFAULT_INTERVAL_MIN))
                    if (datetime.utcnow() - last).total_seconds() < interval * 60:
                        continue
                except Exception:
                    pass
            # try reading from DB messages for the guild
            conn = None
            texts = []
            try:
                rows = await db.fetchall("SELECT content FROM messages WHERE guild_id = ? ORDER BY created_at DESC LIMIT 500", (guild.id,))
                texts = [r['content'] for r in rows if r['content']]
            except Exception:
                texts = []
            # if not enough DB texts, try fetching recent channel history
            if len(texts) < 30:
                try:
                    async for m in channel.history(limit=200):
                        if m.author.bot: continue
                        texts.append(m.content or '')
                except Exception:
                    pass
            keywords = self.extract_keywords(texts, top_n=4)
            topic_text = await self.craft_topic(keywords, guild, channel)
            # find top 2 members to ping
            top_mentions = []
            try:
                rows = await db.fetchall("SELECT user_id FROM users ORDER BY activity_score DESC LIMIT 5")
                for r in rows[:3]:
                    user_id = r['user_id']
                    opt = await db.fetchone("SELECT 1 FROM topic_opt_out WHERE guild_id = ? AND user_id = ?", (guild.id, user_id))
                    if opt:
                        continue
                    member = guild.get_member(user_id)
                    if member:
                        top_mentions.append(member.mention)
            except Exception:
                pass
            await self.post_topic(guild, channel, topic_text, top_mentions)
            # update last_sent
            try:
                await self.set_topic_setting(guild.id, last_sent=datetime.utcnow().isoformat())
            except Exception:
                pass

    @auto_topic_task.before_loop
    async def before_auto_topic(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(TopicAI(bot))
