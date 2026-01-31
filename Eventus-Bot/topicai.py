import discord
from discord.ext import commands, tasks
from discord import app_commands, Interaction
import random
import sqlite3
import datetime
import asyncio
import re

TOPIC_CATEGORIES = {
    "fun": [
        "What's a weird food combo you love?",
        "If you could teleport anywhere right now, where would you go?",
        "What's your favorite meme format?"
    ],
    "debate": [
        "Is AI a threat or a tool?",
        "Should pineapple go on pizza?",
        "Is social media good for society?"
    ]
}


class TopicAI(commands.Cog):
    DEFAULT_INTERVAL = 30  # minutes

    def __init__(self, bot):
        self.bot = bot
        self._ensure_db()
        self.topic_loop.start()

    def _get_db(self):
        conn = sqlite3.connect('eventus.db')
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_db(self):
        conn = self._get_db()
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS topic_settings (
                guild_id INTEGER PRIMARY KEY,
                channel_id INTEGER,
                interval_minutes INTEGER DEFAULT ?,
                enabled INTEGER DEFAULT 1,
                last_post TEXT,
                last_topic TEXT,
                custom_topics TEXT
            )
        ''', (self.DEFAULT_INTERVAL,))
        conn.commit()
        # Ensure legacy DBs get the last_topic column if missing
        try:
            c.execute("PRAGMA table_info(topic_settings)")
            cols = [r[1] for r in c.fetchall()]
            if 'last_topic' not in cols:
                c.execute("ALTER TABLE topic_settings ADD COLUMN last_topic TEXT")
                conn.commit()
        except Exception:
            pass
        conn.close()

    def _get_settings(self, guild_id):
        conn = self._get_db()
        c = conn.cursor()
        c.execute('SELECT * FROM topic_settings WHERE guild_id = ?', (guild_id,))
        row = c.fetchone()
        conn.close()
        return row

    def _ensure_row(self, guild_id):
        if not self._get_settings(guild_id):
            conn = self._get_db()
            c = conn.cursor()
            c.execute('INSERT OR IGNORE INTO topic_settings (guild_id, interval_minutes, enabled, custom_topics) VALUES (?, ?, ?, ?)',
                      (guild_id, self.DEFAULT_INTERVAL, 1, ''))
            conn.commit()
            conn.close()

    def _update_last_post(self, guild_id, when_iso):
        conn = self._get_db()
        c = conn.cursor()
        c.execute('UPDATE topic_settings SET last_post = ? WHERE guild_id = ?', (when_iso, guild_id))
        conn.commit()
        conn.close()

    def _update_last_post_and_topic(self, guild_id, when_iso, topic_text):
        conn = self._get_db()
        c = conn.cursor()
        c.execute('UPDATE topic_settings SET last_post = ?, last_topic = ? WHERE guild_id = ?', (when_iso, topic_text, guild_id))
        conn.commit()
        conn.close()

    def _set_channel(self, guild_id, channel_id):
        conn = self._get_db()
        c = conn.cursor()
        c.execute('UPDATE topic_settings SET channel_id = ? WHERE guild_id = ?', (channel_id, guild_id))
        conn.commit()
        conn.close()

    def _set_interval(self, guild_id, minutes):
        conn = self._get_db()
        c = conn.cursor()
        c.execute('UPDATE topic_settings SET interval_minutes = ? WHERE guild_id = ?', (minutes, guild_id))
        conn.commit()
        conn.close()

    def _set_enabled(self, guild_id, enabled: bool):
        conn = self._get_db()
        c = conn.cursor()
        c.execute('UPDATE topic_settings SET enabled = ? WHERE guild_id = ?', (1 if enabled else 0, guild_id))
        conn.commit()
        conn.close()

    def _add_custom_topic(self, guild_id, topic):
        row = self._get_settings(guild_id)
        existing = row['custom_topics'] if row and row['custom_topics'] else ''
        topics = [t for t in existing.split('||') if t] if existing else []
        topics.append(topic)
        conn = self._get_db()
        c = conn.cursor()
        c.execute('UPDATE topic_settings SET custom_topics = ? WHERE guild_id = ?', ('||'.join(topics), guild_id))
        conn.commit()
        conn.close()

    def _remove_custom_topic(self, guild_id, index):
        row = self._get_settings(guild_id)
        if not row or not row['custom_topics']:
            return False
        topics = [t for t in row['custom_topics'].split('||') if t]
        if index < 0 or index >= len(topics):
            return False
        topics.pop(index)
        conn = self._get_db()
        c = conn.cursor()
        c.execute('UPDATE topic_settings SET custom_topics = ? WHERE guild_id = ?', ('||'.join(topics), guild_id))
        conn.commit()
        conn.close()
        return True

    def _list_custom_topics(self, guild_id):
        row = self._get_settings(guild_id)
        if not row or not row['custom_topics']:
            return []
        return [t for t in row['custom_topics'].split('||') if t]

    def _compose_topic_pool(self, guild_id, category=None):
        pool = []
        if category and category in TOPIC_CATEGORIES:
            pool.extend(TOPIC_CATEGORIES[category])
        else:
            for v in TOPIC_CATEGORIES.values():
                pool.extend(v)
        pool.extend(self._list_custom_topics(guild_id))
        return pool

    def _normalize(self, text: str):
        if not text:
            return set()
        s = text.lower()
        s = re.sub(r"[^a-z0-9\s]", " ", s)
        words = [w for w in s.split() if len(w) > 2]
        stop = {"the", "and", "for", "with", "that", "this", "what", "your", "have", "just"}
        return set(w for w in words if w not in stop)

    def _is_similar(self, a: str, b: str, thresh: float = 0.6):
        A = self._normalize(a)
        B = self._normalize(b)
        if not A or not B:
            return False
        inter = A.intersection(B)
        base = min(len(A), len(B))
        if base == 0:
            return False
        score = len(inter) / base
        return score >= thresh

    @commands.hybrid_command(name="topic", description="Drop a new topic in chat.")
    async def topic(self, ctx, category: str = None):
        category = category or "fun"
        topic = random.choice(TOPIC_CATEGORIES.get(category, TOPIC_CATEGORIES["fun"]))
        if hasattr(ctx, 'respond'):
            await ctx.respond(f"💡 **TopicAI Suggests:** {topic}")
        else:
            await ctx.send(f"💡 **TopicAI Suggests:** {topic}")

    @commands.hybrid_command(name="set_topic_channel", description="Set channel where topics are auto-posted.")
    @commands.has_permissions(manage_guild=True)
    async def set_topic_channel(self, ctx, channel: discord.TextChannel):
        guild_id = ctx.guild.id
        self._ensure_row(guild_id)
        self._set_channel(guild_id, channel.id)
        await ctx.respond(f"Topic channel set to {channel.mention}") if hasattr(ctx, 'respond') else await ctx.send(f"Topic channel set to {channel.mention}")

    @commands.hybrid_command(name="set_topic_interval", description="Set topic interval in minutes.")
    @commands.has_permissions(manage_guild=True)
    async def set_topic_interval(self, ctx, minutes: int):
        minutes = max(1, min(24*60, minutes))
        guild_id = ctx.guild.id
        self._ensure_row(guild_id)
        self._set_interval(guild_id, minutes)
        await ctx.respond(f"Topic interval set to {minutes} minutes") if hasattr(ctx, 'respond') else await ctx.send(f"Topic interval set to {minutes} minutes")

    @commands.hybrid_command(name="add_topic", description="Add a custom topic for this server.")
    @commands.has_permissions(manage_guild=True)
    async def add_topic(self, ctx, *, topic_text: str):
        guild_id = ctx.guild.id
        self._ensure_row(guild_id)
        self._add_custom_topic(guild_id, topic_text)
        await ctx.respond("Custom topic added.") if hasattr(ctx, 'respond') else await ctx.send("Custom topic added.")

    @commands.hybrid_command(name="list_topics", description="List custom topics for this server.")
    async def list_topics(self, ctx):
        guild_id = ctx.guild.id
        self._ensure_row(guild_id)
        topics = self._list_custom_topics(guild_id)
        if not topics:
            await ctx.respond("No custom topics set.") if hasattr(ctx, 'respond') else await ctx.send("No custom topics set.")
            return
        text = "\n".join(f"{i}. {t}" for i, t in enumerate(topics))
        await ctx.respond(f"Custom topics:\n{text}") if hasattr(ctx, 'respond') else await ctx.send(f"Custom topics:\n{text}")

    @commands.hybrid_command(name="remove_topic", description="Remove a custom topic by index.")
    @commands.has_permissions(manage_guild=True)
    async def remove_topic(self, ctx, index: int):
        guild_id = ctx.guild.id
        ok = self._remove_custom_topic(guild_id, index)
        if ok:
            await ctx.respond("Topic removed.") if hasattr(ctx, 'respond') else await ctx.send("Topic removed.")
        else:
            await ctx.respond("Invalid index.") if hasattr(ctx, 'respond') else await ctx.send("Invalid index.")

    @commands.hybrid_command(name="enable_topics", description="Enable auto topic posting for this server.")
    @commands.has_permissions(manage_guild=True)
    async def enable_topics(self, ctx):
        guild_id = ctx.guild.id
        self._ensure_row(guild_id)
        self._set_enabled(guild_id, True)
        await ctx.respond("Auto topics enabled.") if hasattr(ctx, 'respond') else await ctx.send("Auto topics enabled.")

    @commands.hybrid_command(name="disable_topics", description="Disable auto topic posting for this server.")
    @commands.has_permissions(manage_guild=True)
    async def disable_topics(self, ctx):
        guild_id = ctx.guild.id
        self._ensure_row(guild_id)
        self._set_enabled(guild_id, False)
        await ctx.respond("Auto topics disabled.") if hasattr(ctx, 'respond') else await ctx.send("Auto topics disabled.")

    @tasks.loop(seconds=60.0)
    async def topic_loop(self):
        now = datetime.datetime.utcnow()
        for guild in list(self.bot.guilds):
            try:
                guild_id = guild.id
                self._ensure_row(guild_id)
                row = self._get_settings(guild_id)
                if not row or not row['enabled']:
                    continue
                interval = row['interval_minutes'] or self.DEFAULT_INTERVAL
                last_post = None
                if row['last_post']:
                    try:
                        last_post = datetime.datetime.fromisoformat(row['last_post'])
                    except:
                        last_post = None
                delta = (now - last_post).total_seconds() / 60 if last_post else float('inf')
                if delta >= interval:
                    channel_id = row['channel_id']
                    if not channel_id:
                        continue
                    channel = guild.get_channel(channel_id)
                    if not channel:
                        continue
                    pool = self._compose_topic_pool(guild_id)
                    if not pool:
                        continue
                    # avoid repeating the same topic (including near-duplicates)
                    last_topic = row.get('last_topic') if row else None
                    topic = None
                    tries = 0
                    while tries < 12:
                        candidate = random.choice(pool)
                        if not last_topic:
                            topic = candidate
                            break
                        # prefer candidates that are not semantically similar to last_topic
                        try:
                            if not self._is_similar(candidate, last_topic):
                                topic = candidate
                                break
                        except Exception:
                            # fallback to exact match avoidance
                            if candidate != last_topic:
                                topic = candidate
                                break
                        tries += 1
                    if not topic:
                        topic = random.choice(pool)
                    try:
                        await channel.send(f"💡 **Topic:** {topic}")
                        self._update_last_post_and_topic(guild_id, now.isoformat(), topic)
                        await asyncio.sleep(1)
                    except Exception:
                        continue
            except Exception:
                continue

    @topic_loop.before_loop
    async def before_topic_loop(self):
        await self.bot.wait_until_ready()

    def cog_unload(self):
        try:
            self.topic_loop.cancel()
        except Exception:
            pass

async def setup(bot):
    await bot.add_cog(TopicAI(bot))
