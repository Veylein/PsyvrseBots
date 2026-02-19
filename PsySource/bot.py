

import os
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
from discord.ui import View, Button
from discord import Interaction, TextChannel, Thread
from googletrans import Translator

load_dotenv()
TOKEN = os.getenv('PSYVRSE_TOKEN')


intents = discord.Intents.default()
intents.members = True
intents.guilds = True
intents.message_content = True

bot = commands.Bot(command_prefix="/", intents=intents)

log_channel_id = None
welcome_channel_id = None
translator = Translator()

# --- Ticket Panel Command ---
class TicketPanelView(View):
    def __init__(self, log_channel_id=None):
        super().__init__(timeout=None)
        self.log_channel_id = log_channel_id
        self.add_item(TicketButton(log_channel_id))

class TicketButton(Button):
    def __init__(self, log_channel_id=None):
        super().__init__(label="Create Ticket", style=discord.ButtonStyle.primary)
        self.log_channel_id = log_channel_id

    async def callback(self, interaction: Interaction):
        user = interaction.user
        guild = interaction.guild
        channel = interaction.channel
        # Create a private thread for the ticket
        thread = await channel.create_thread(name=f"ticket-{user.name}", type=discord.ChannelType.private_thread, invitable=False)
        await thread.add_user(user)
        await thread.send(f"{user.mention}, your ticket has been created. Please describe your issue.")
        # Log ticket creation
        if self.log_channel_id:
            log_channel = guild.get_channel(self.log_channel_id)
            if log_channel:
                await log_channel.send(f"🎟️ Ticket created by {user.mention} in {thread.mention}")
        await interaction.response.send_message(f"Ticket created: {thread.mention}", ephemeral=True)

@bot.tree.command(name="ticketpanel", description="Send a ticket panel for users to create tickets.")
@app_commands.describe(channel="Channel to send the ticket panel in")
async def ticketpanel(interaction: discord.Interaction, channel: discord.TextChannel):
    view = TicketPanelView(log_channel_id=log_channel_id)
    await channel.send("Need help? Click below to open a private ticket.", view=view)
    await interaction.response.send_message(f"Ticket panel sent in {channel.mention}", ephemeral=True)
import os
import discord

@bot.tree.command(name="ban", description="Ban a user from the server.")
@app_commands.describe(user="User to ban", reason="Reason for ban")
async def ban(interaction: discord.Interaction, user: discord.Member, reason: str = None):
    if not interaction.user.guild_permissions.ban_members:
        await interaction.response.send_message("You do not have permission to ban members.", ephemeral=True)
        return
    await user.ban(reason=reason)
    await interaction.response.send_message(f"{user} has been banned. Reason: {reason}")
    await log_action(interaction.guild, f"{user} was banned by {interaction.user}. Reason: {reason}")

@bot.tree.command(name="kick", description="Kick a user from the server.")
@app_commands.describe(user="User to kick", reason="Reason for kick")
async def kick(interaction: discord.Interaction, user: discord.Member, reason: str = None):
    if not interaction.user.guild_permissions.kick_members:
        await interaction.response.send_message("You do not have permission to kick members.", ephemeral=True)
        return
    await user.kick(reason=reason)
    await interaction.response.send_message(f"{user} has been kicked. Reason: {reason}")
    await log_action(interaction.guild, f"{user} was kicked by {interaction.user}. Reason: {reason}")

@bot.tree.command(name="setlog", description="Set the log channel.")
@app_commands.describe(channel="Channel to log moderation actions")
async def setlog(interaction: discord.Interaction, channel: discord.TextChannel):
    global log_channel_id
    log_channel_id = channel.id
    await interaction.response.send_message(f"Log channel set to {channel.mention}")

@bot.tree.command(name="setwelcome", description="Set the welcome channel.")
@app_commands.describe(channel="Channel to send welcome messages")
async def setwelcome(interaction: discord.Interaction, channel: discord.TextChannel):
    global welcome_channel_id
    welcome_channel_id = channel.id
    await interaction.response.send_message(f"Welcome channel set to {channel.mention}")

async def log_action(guild, message):
    if log_channel_id:
        channel = guild.get_channel(log_channel_id)
        if channel:
            await channel.send(message)


# --- Moderation: Welcome, Logging, Punishments, Edits ---
@bot.event
async def on_member_join(member):
    if welcome_channel_id:
        channel = member.guild.get_channel(welcome_channel_id)
        if channel:
            await channel.send(f"Welcome to the server, {member.mention}!")
    # Log join
    await log_action(member.guild, f"{member} joined the server.")

@bot.event
async def on_message_delete(message):
    if message.guild and log_channel_id:
        channel = message.guild.get_channel(log_channel_id)
        if channel:
            author = getattr(message.author, 'mention', str(message.author))
            content = message.content or '[no content]'
            await channel.send(f"🗑️ Message deleted in {message.channel.mention} by {author}: {content}")

@bot.event
async def on_message_edit(before, after):
    if before.guild and log_channel_id:
        channel = before.guild.get_channel(log_channel_id)
        if channel and before.content != after.content:
            author = getattr(before.author, 'mention', str(before.author))
            await channel.send(f"✏️ Message edited in {before.channel.mention} by {author}:\nBefore: {before.content}\nAfter: {after.content}")

# --- Moderation: Mute, Timeout, Warn, Custom ---
from datetime import timedelta

@bot.tree.command(name="mute", description="Mute a user (timeout)")
@app_commands.describe(user="User to mute", duration="Duration in minutes", reason="Reason for mute")
async def mute(interaction: discord.Interaction, user: discord.Member, duration: int = 10, reason: str = None):
    if not interaction.user.guild_permissions.moderate_members:
        await interaction.response.send_message("You do not have permission to mute members.", ephemeral=True)
        return
    try:
        await user.timeout(timedelta(minutes=duration), reason=reason)
        await interaction.response.send_message(f"{user} has been muted for {duration} minutes. Reason: {reason}")
        await log_action(interaction.guild, f"{user} was muted by {interaction.user} for {duration} minutes. Reason: {reason}")
    except Exception as e:
        await interaction.response.send_message(f"Failed to mute: {e}", ephemeral=True)

@bot.tree.command(name="unmute", description="Unmute a user (remove timeout)")
@app_commands.describe(user="User to unmute")
async def unmute(interaction: discord.Interaction, user: discord.Member):
    if not interaction.user.guild_permissions.moderate_members:
        await interaction.response.send_message("You do not have permission to unmute members.", ephemeral=True)
        return
    try:
        await user.timeout(None)
        await interaction.response.send_message(f"{user} has been unmuted.")
        await log_action(interaction.guild, f"{user} was unmuted by {interaction.user}.")
    except Exception as e:
        await interaction.response.send_message(f"Failed to unmute: {e}", ephemeral=True)

@bot.tree.command(name="warn", description="Warn a user")
@app_commands.describe(user="User to warn", reason="Reason for warning")
async def warn(interaction: discord.Interaction, user: discord.Member, reason: str = None):
    if not interaction.user.guild_permissions.kick_members:
        await interaction.response.send_message("You do not have permission to warn members.", ephemeral=True)
        return
    await interaction.response.send_message(f"{user.mention} has been warned. Reason: {reason}")
    await log_action(interaction.guild, f"{user} was warned by {interaction.user}. Reason: {reason}")

@bot.tree.command(name="timeout", description="Timeout a user (mute for seconds)")
@app_commands.describe(user="User to timeout", seconds="Timeout duration in seconds", reason="Reason for timeout")
async def timeout(interaction: discord.Interaction, user: discord.Member, seconds: int = 60, reason: str = None):
    if not interaction.user.guild_permissions.moderate_members:
        await interaction.response.send_message("You do not have permission to timeout members.", ephemeral=True)
        return
    try:
        await user.timeout(timedelta(seconds=seconds), reason=reason)
        await interaction.response.send_message(f"{user} has been timed out for {seconds} seconds. Reason: {reason}")
        await log_action(interaction.guild, f"{user} was timed out by {interaction.user} for {seconds} seconds. Reason: {reason}")
    except Exception as e:
        await interaction.response.send_message(f"Failed to timeout: {e}", ephemeral=True)

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    # $say command
    if message.content.startswith("$say "):
        text = message.content[5:]
        await message.channel.send(text)
    elif message.content.startswith("$embed "):
        text = message.content[7:]
        embed = discord.Embed(description=text)
        await message.channel.send(embed=embed)
    # Allow other commands to work
    await bot.process_commands(message)

@bot.tree.command(name="translate", description="Translate text from one language to another.")
@app_commands.describe(text="Text to translate", src="Source language code (optional)", dest="Target language code (default: en)")
async def translate(interaction: discord.Interaction, text: str, src: str = None, dest: str = "en"):
    """
    Translate text from src language to dest language using googletrans.
    Example: /translate text:Hola src:es dest:en or /translate text:Hello dest:spanish
    """
    from googletrans import LANGUAGES
    lang_code = dest.lower()
    # Accept language names as well as codes
    if lang_code not in LANGUAGES and lang_code not in LANGUAGES.values():
        # Try to match by name
        for code, name in LANGUAGES.items():
            if name.lower() == lang_code:
                lang_code = code
                break
        else:
            await interaction.response.send_message(f"❌ Language '{dest}' not recognized!\n\nTry: english, spanish, french, german, japanese, etc.", ephemeral=True)
            return
    elif lang_code in LANGUAGES.values():
        # Convert name to code
        for code, name in LANGUAGES.items():
            if name.lower() == lang_code:
                lang_code = code
                break
    try:
        # Run translation in a thread to avoid coroutine issues
        import asyncio
        loop = asyncio.get_running_loop()
        def do_translate():
            translator = __import__('googletrans').Translator()
            return translator.translate(text, src=src if src else 'auto', dest=lang_code)
        result = await loop.run_in_executor(None, do_translate)
        src_lang = LANGUAGES.get(getattr(result, 'src', 'auto'), getattr(result, 'src', 'auto')).title() if getattr(result, 'src', 'auto') in LANGUAGES else getattr(result, 'src', 'auto')
        tgt_lang = LANGUAGES.get(lang_code, lang_code).title() if lang_code in LANGUAGES else lang_code
        await interaction.response.send_message(
            f"🌐 **Translated from {src_lang} to {tgt_lang}:**\n{result.text}\n\n*To translate, use language names like 'english', 'spanish', 'japanese', or codes like 'en', 'es', 'ja'.*",
            ephemeral=True
        )
    except Exception as e:
        await interaction.response.send_message(
            f"Translation failed: {e}\n\n*Tip: Use language names like 'english', 'spanish', 'japanese', or codes like 'en', 'es', 'ja'.*",
            ephemeral=True
        )

if __name__ == "__main__":
    bot.run(TOKEN)
