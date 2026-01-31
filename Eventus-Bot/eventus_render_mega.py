import os
import discord
import logging
from discord.ext import commands
from discord import app_commands
import sqlite3
import asyncio

# ============
# CONFIG
# ============
TOKEN = os.getenv("EVENTUS_TOKEN")
CLIENT_ID = os.getenv("CLIENT_ID")
DEFAULT_PREFIX = "E!"

# ============
# PREFIX MANAGEMENT
# ============
def get_prefix(bot, message):
    conn = get_db()
    c = conn.cursor()
    guild_id = getattr(message.guild, 'id', None)
    if guild_id:
        c.execute("SELECT prefix FROM guilds WHERE guild_id = ?", (guild_id,))
        row = c.fetchone()
        conn.close()
        if row and row['prefix']:
            return row['prefix']
    conn.close()
    return DEFAULT_PREFIX

def set_guild_prefix(guild_id, prefix):
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO guilds (guild_id, prefix) VALUES (?, ?) ON CONFLICT(guild_id) DO UPDATE SET prefix = ?", (guild_id, prefix, prefix))
    conn.commit()
    conn.close()
OWNER_IDS = {1311394031640776716, 1382187068373074001}

# ============
# INTENTS
# ============
intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.guilds = True

# ============
# BOT SETUP
# ============
bot = commands.Bot(
    command_prefix=get_prefix,
    intents=intents,
    help_command=None
)

# Configure logging
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()
logging.basicConfig(level=LOG_LEVEL, format='[%(asctime)s] %(levelname)s:%(name)s: %(message)s')
logger = logging.getLogger('eventus')
logger.info('Logging initialized at %s', LOG_LEVEL)

# ============
# DATABASE SETUP
# ============
DB_PATH = "eventus.db"
DATABASE_URL = os.getenv('DATABASE_URL')
try:
    import asyncpg
except Exception:
    asyncpg = None
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

async def init_db():
    """Initialize DB schema. Supports SQLite (default) and Postgres when DATABASE_URL is set.

    This function is async; callers in async contexts must `await init_db()`.
    """
    # Postgres path
    if DATABASE_URL and asyncpg:
        pool = await asyncpg.create_pool(DATABASE_URL)
        async with pool.acquire() as conn:
            await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY,
                username TEXT,
                activity_score BIGINT DEFAULT 0,
                momentum INTEGER DEFAULT 0,
                streak INTEGER DEFAULT 0,
                last_active TEXT,
                topic_influence DOUBLE PRECISION DEFAULT 0,
                multi_channel_presence TEXT DEFAULT ''
            )
            """)
            await conn.execute("""
            CREATE TABLE IF NOT EXISTS events (
                event_id SERIAL PRIMARY KEY,
                title TEXT,
                description TEXT,
                creator_id BIGINT,
                start_time TEXT,
                end_time TEXT,
                rsvp_list TEXT,
                recurring TEXT,
                archived INTEGER DEFAULT 0
            )
            """)
            await conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                message_id BIGINT PRIMARY KEY,
                guild_id BIGINT,
                channel_id BIGINT,
                author_id BIGINT,
                created_at TEXT,
                content TEXT
            )
            """)
            await conn.execute("""
            CREATE TABLE IF NOT EXISTS pings (
                ping_id SERIAL PRIMARY KEY,
                guild_id BIGINT,
                channel_id BIGINT,
                interval_minutes INTEGER DEFAULT 60,
                top_n INTEGER DEFAULT 3,
                last_sent TEXT
            )
            """)
            await conn.execute("""
            CREATE TABLE IF NOT EXISTS rewards (
                reward_id SERIAL PRIMARY KEY,
                guild_id BIGINT,
                role_id BIGINT,
                criteria TEXT,
                tier INTEGER DEFAULT 0
            )
            """)
            await conn.execute("""
            CREATE TABLE IF NOT EXISTS analytics (
                snapshot_id SERIAL PRIMARY KEY,
                created_at TEXT,
                data TEXT
            )
            """)
            await conn.execute("""
            CREATE TABLE IF NOT EXISTS guilds (
                guild_id BIGINT PRIMARY KEY,
                prefix TEXT DEFAULT 'E!'
            )
            """)
            await conn.execute("""
            CREATE TABLE IF NOT EXISTS topic_settings (
                guild_id BIGINT PRIMARY KEY,
                channel_id BIGINT,
                interval_minutes INTEGER DEFAULT 60,
                enabled INTEGER DEFAULT 1,
                last_sent TEXT,
                last_topic TEXT,
                custom_topics TEXT
            )
            """)
            await conn.execute("""
            CREATE TABLE IF NOT EXISTS topic_opt_out (
                guild_id BIGINT,
                user_id BIGINT,
                PRIMARY KEY (guild_id, user_id)
            )
            """)
            await conn.execute("""
            CREATE TABLE IF NOT EXISTS ignored_channels (
                guild_id BIGINT,
                channel_id BIGINT,
                PRIMARY KEY (guild_id, channel_id)
            )
            """)
            await conn.execute("""
            CREATE TABLE IF NOT EXISTS ignored_roles (
                guild_id BIGINT,
                role_id BIGINT,
                PRIMARY KEY (guild_id, role_id)
            )
            """)
        await pool.close()
        return

    # SQLite path (run in thread to avoid blocking)
    def _init_sqlite():
        conn = get_db()
        c = conn.cursor()
        c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            activity_score INTEGER DEFAULT 0,
            momentum INTEGER DEFAULT 0,
            streak INTEGER DEFAULT 0,
            last_active TEXT,
            topic_influence REAL DEFAULT 0,
            multi_channel_presence TEXT DEFAULT ''
        )
        """)
        c.execute("PRAGMA table_info('users')")
        cols = [r[1] for r in c.fetchall()]
        if 'username' not in cols:
            try:
                c.execute("ALTER TABLE users ADD COLUMN username TEXT")
                logging.info('Added missing column `username` to users table')
            except Exception as e:
                logging.exception('Failed to add username column to users table: %s', e)
        c.execute("""
        CREATE TABLE IF NOT EXISTS events (
            event_id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            description TEXT,
            creator_id INTEGER,
            start_time TEXT,
            end_time TEXT,
            rsvp_list TEXT,
            recurring TEXT,
            archived INTEGER DEFAULT 0
        )
        """)
        c.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            message_id INTEGER PRIMARY KEY,
            guild_id INTEGER,
            channel_id INTEGER,
            author_id INTEGER,
            created_at TEXT,
            content TEXT
        )
        """)
        c.execute("""
        CREATE TABLE IF NOT EXISTS pings (
            ping_id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER,
            channel_id INTEGER,
            interval_minutes INTEGER DEFAULT 60,
            top_n INTEGER DEFAULT 3,
            last_sent TEXT
        )
        """)
        c.execute("""
        CREATE TABLE IF NOT EXISTS rewards (
            reward_id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER,
            role_id INTEGER,
            criteria TEXT,
            tier INTEGER DEFAULT 0
        )
        """)
        c.execute("""
        CREATE TABLE IF NOT EXISTS analytics (
            snapshot_id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT,
            data TEXT
        )
        """)
        c.execute("""
        CREATE TABLE IF NOT EXISTS guilds (
            guild_id INTEGER PRIMARY KEY,
            prefix TEXT DEFAULT 'E!'
        )
        """)
        c.execute("""
        CREATE TABLE IF NOT EXISTS topic_settings (
            guild_id INTEGER PRIMARY KEY,
            channel_id INTEGER,
            interval_minutes INTEGER DEFAULT 60,
            enabled INTEGER DEFAULT 1,
            last_sent TEXT,
            last_topic TEXT,
            custom_topics TEXT
        )
        """)
        c.execute("""
        CREATE TABLE IF NOT EXISTS topic_opt_out (
            guild_id INTEGER,
            user_id INTEGER,
            PRIMARY KEY (guild_id, user_id)
        )
        """)
        c.execute("""
        CREATE TABLE IF NOT EXISTS ignored_channels (
            guild_id INTEGER,
            channel_id INTEGER,
            PRIMARY KEY (guild_id, channel_id)
        )
        """)
        c.execute("""
        CREATE TABLE IF NOT EXISTS ignored_roles (
            guild_id INTEGER,
            role_id INTEGER,
            PRIMARY KEY (guild_id, role_id)
        )
        """)
        conn.commit()
        conn.close()

    await asyncio.to_thread(_init_sqlite)

# ============
# MODULAR COG LOADING
# ============
COGS = [
    'activity',
    'eventos',
    'topicai',
        'help',
    'dashboard',
    'momentum',
    'rules',
    'owner',
    'importer',
    'admin',
    # topicai listed once; help command is in topicai.py
]



@bot.event
async def on_ready():
    print("[Eventus] on_ready triggered. Initializing DB and loading cogs...")
    try:
        await init_db()
    except Exception as e:
        print(f"[Eventus] init_db error: {e}")
    loaded = set()
    for cog in COGS:
        if cog in loaded:
            print(f"[Eventus] Skipping duplicate cog: {cog}")
            continue
        try:
            await bot.load_extension(cog)
            print(f"[Eventus] Loaded cog: {cog}")
            loaded.add(cog)
        except Exception as e:
            print(f"[Eventus] Failed to load cog {cog}: {e}")
    try:
        print("[Eventus] Syncing slash commands per-guild and globally...")
        # First attempt per-guild syncs for faster propagation in test servers
        for g in bot.guilds:
            try:
                synced = await bot.tree.sync(guild=discord.Object(id=g.id))
                print(f"[Eventus] Synced {len(synced)} commands for guild {g.id}")
            except Exception as e:
                print(f"[Eventus] Failed to sync guild {g.id}: {e}")
        # Then attempt a global sync (may take longer to propagate)
        try:
            global_synced = await bot.tree.sync()
            print(f"[Eventus] Globally synced {len(global_synced)} commands")
        except Exception as e:
            print("[Eventus] Global sync failed:", e)
    except Exception as e:
        print("[Eventus] Slash sync error:", e)
    print(f"[Eventus] Logged in as {bot.user}")
    # Print all registered commands for debug
    print("[Eventus] Registered prefix commands:")
    for cmd in bot.commands:
        print(f"  - {cmd.name}")
    print("[Eventus] Registered slash commands:")
    for cmd in bot.tree.get_commands():
        print(f"  - {cmd.name}")

# Add a simple test command to verify registration
@bot.hybrid_command(name="test", description="Test if commands are working.")
async def test(ctx):
    if hasattr(ctx, 'respond'):
        await ctx.respond("Test command works! (slash)")
    else:
        await ctx.send("Test command works! (prefix)")


if __name__ == "__main__":
    if not TOKEN:
        print("ERROR: Discord bot token not set. Set the EVENTUS_TOKEN environment variable.")
    else:
        try:
            bot.run(TOKEN)
        except Exception as e:
            print(f"Bot failed to start: {e}")
