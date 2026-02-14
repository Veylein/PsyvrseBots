import discord
from discord.ext import commands, tasks
from discord import app_commands
from discord.ui import View, Button
from typing import Optional
import asyncio
import json
import os
import math
from datetime import datetime

# Optional: Import your embed styles if you have them
# from utils.embed_styles import EmbedBuilder, Colors, Emojis

# Fallbacks if you don’t have custom embed styles
class Colors: 
    PRIMARY = discord.Color.blue()
    SECONDARY = discord.Color.green()
    ERROR = discord.Color.red()

class Emojis:
    SPARKLES = "✨"
    COIN = "💰"
    TROPHY = "🏆"
    LEVEL_UP = "📈"
    MUSIC = "🎵"
    HEART = "❤️"
    FIRE = "🔥"
    ROCKET = "🚀"
    GAME = "🎮"

ALLOWED_SAY_USER_ID = (1382187068373074001, 1311394031640776716, 1138720397567742014)

class Paginator(View):
    def __init__(self, ctx, pages):
        super().__init__(timeout=120)
        self.ctx = ctx
        self.pages = pages
        self.current_page = 0
        self.message = None

    @discord.ui.button(label="◀️ Previous", style=discord.ButtonStyle.primary)
    async def previous(self, interaction: discord.Interaction, button: Button):
        if interaction.user != self.ctx.author:
            return await interaction.response.send_message("This menu isn't for you!", ephemeral=True)
        self.current_page = (self.current_page - 1) % len(self.pages)
        await interaction.response.edit_message(embed=self.pages[self.current_page])

    @discord.ui.button(label="▶️ Next", style=discord.ButtonStyle.primary)
    async def next(self, interaction: discord.Interaction, button: Button):
        if interaction.user != self.ctx.author:
            return await interaction.response.send_message("This menu isn't for you!", ephemeral=True)
        self.current_page = (self.current_page + 1) % len(self.pages)
        await interaction.response.edit_message(embed=self.pages[self.current_page])

    @discord.ui.button(label="❌ Close", style=discord.ButtonStyle.danger)
    async def close(self, interaction: discord.Interaction, button: Button):
        if interaction.user != self.ctx.author:
            return await interaction.response.send_message("This menu isn't for you!", ephemeral=True)
        await interaction.message.delete()
        self.stop()


class Utilities(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        data_dir = os.getenv("RENDER_DISK_PATH", ".")
        self.reminders_file = os.path.join(data_dir, "reminders.json")
        self.prefix_file = os.path.join(data_dir, "server_prefixes.json")
        self.reminders = self.load_json(self.reminders_file)
        self.prefixes = self.load_json(self.prefix_file)

    async def cog_load(self):
        self.check_reminders.start()

    # ---------- JSON Helpers ----------
    def load_json(self, path):
        if os.path.exists(path):
            try:
                with open(path, "r") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def save_json(self, path, data):
        try:
            with open(path, "w") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Error saving {path}: {e}")

    # ---------- Reminders ----------
    @tasks.loop(seconds=60)
    async def check_reminders(self):
        now = datetime.utcnow()
        updated = False
        for user_id, reminders in list(self.reminders.items()):
            for reminder in reminders[:]:
                remind_time = datetime.fromisoformat(reminder['time'])
                if now >= remind_time:
                    try:
                        user = await self.bot.fetch_user(int(user_id))
                        embed = discord.Embed(
                            title="⏰ Reminder!",
                            description=reminder['message'],
                            color=Colors.PRIMARY
                        )
                        embed.set_footer(text=f"Set {reminder.get('set_ago', 'some time ago')}")
                        await user.send(embed=embed)
                    except:
                        pass
                    reminders.remove(reminder)
                    updated = True
        if updated:
            self.save_json(self.reminders_file, self.reminders)

    # ---------- Core Commands ----------
    @commands.command(name="ping")
    async def ping(self, ctx):
        await ctx.send(f"Pong! {round(self.bot.latency*1000)}ms")

    @commands.command(name="invite")
    async def invite(self, ctx):
        await ctx.send("Invite me: <your_bot_invite_link_here>")

    @commands.command(name="setup")
    async def setup_cmd(self, ctx):
        embed = self.create_setup_embed()
        await ctx.send(embed=embed)

    @commands.command(name="say")
    async def say(self, ctx, *, text: str = None):
        if ctx.author.id not in ALLOWED_SAY_USER_ID:
            return await ctx.send("You are not authorized to use this command.")
        if not text:
            return await ctx.send("Please provide a message to echo.")
        await ctx.send(text)

    # ---------- Feedback ----------
    @commands.command(name="feedback")
    async def feedback(self, ctx, *, text: str):
        feedback_channel_id = 1467981316028108918  # Replace with your feedback channel
        feedback_channel = self.bot.get_channel(feedback_channel_id)
        if feedback_channel is None:
            return await ctx.send("Feedback channel not found.")

        embed = discord.Embed(title="New Feedback", description=text, color=Colors.SECONDARY)
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
        embed.set_footer(text=f"User ID: {ctx.author.id}")
        await feedback_channel.send(embed=embed)
        await ctx.send("✅ Thank you! Your feedback has been sent.")

    # ---------- Help / Guide ----------
    @commands.command(name="guide")
    async def guide(self, ctx, category: Optional[str] = None):
        await self.send_guide(ctx, category)

    @app_commands.command(name="guide", description="View command guide and help")
    @app_commands.describe(category="Category to view (optional)")
    async def guide_slash(self, interaction: discord.Interaction, category: Optional[str] = None):
        class FakeCtx:
            def __init__(self, interaction):
                self.author = interaction.user
                self.send = interaction.followup.send
        fake_ctx = FakeCtx(interaction)
        await interaction.response.defer()
        await self.send_guide(fake_ctx, category)

    async def send_guide(self, ctx, category: Optional[str]):
        categories = {
            "tcg": {"title":"🎴 TCG Commands","desc":"Complete trading card game system","color":discord.Color.purple(),"commands":["/tcg","/tcgbattle @user","/tcgbattleai","/tcganimate"]},
            "economy": {"title":"💰 Economy Commands","desc":"Coins & shop","color":discord.Color.gold(),"commands":["L!balance","L!daily","L!shop","L!buy <item>","L!inventory","L!use <item>","L!give @user","L!leaderboard"]},
            "mini": {"title":"🎮 Minigames","desc":"100+ fun quick games","color":Colors.PRIMARY,"commands":["L!wordle","L!trivia","L!gtn","L!typerace","L!coinflip"]},
            "social": {"title":"👥 Social","desc":"Community fun","color":discord.Color.green(),"commands":["L!compliment","L!roast","L!wyr","L!story"]},
            # Add all other categories here dynamically
        }

        if category is None:
            embed = discord.Embed(
                title=f"{Emojis.SPARKLES} Ludus Guide",
                description="Use `L!guide <category>` to view commands in a category",
                color=Colors.PRIMARY
            )
            for cat_key, cat_data in categories.items():
                embed.add_field(name=f"{cat_data['title']}", value=cat_data['desc'], inline=True)
            await ctx.send(embed=embed)
        else:
            cat_data = categories.get(category.lower())
            if not cat_data:
                return await ctx.send("Category not found.")
            embed = discord.Embed(title=cat_data["title"], description=cat_data["desc"], color=cat_data["color"])
            for cmd in cat_data["commands"]:
                embed.add_field(name=cmd, value="\u200b", inline=False)
            await ctx.send(embed=embed)

    # ---------- Setup Embed ----------
    def create_setup_embed(self):
        embed = discord.Embed(
            title="🎮 Welcome to Ludus!",
            description="Your ultimate Discord MMO universe. Use `L!` prefix or `/` commands.",
            color=Colors.PRIMARY
        )
        embed.add_field(name="💰 Economy", value="Check balance, daily rewards, shop, inventory.", inline=False)
        embed.add_field(name="🎲 Games", value="Board games, card games, minigames, TCG.", inline=False)
        embed.add_field(name="🎵 Music", value="Play music in voice channels.", inline=False)
        embed.add_field(name="⚙️ Admin", value="Setup leveling, starboard, counting channels.", inline=False)
        embed.set_footer(text="Ludus - Full Discord MMO")
        return embed

# ---------- Cog Setup ----------
async def setup(bot):
    await bot.add_cog(Utilities(bot))