import os
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
from googletrans import Translator

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.members = True
intents.guilds = True
intents.message_content = True

bot = commands.Bot(command_prefix="/", intents=intents)

log_channel_id = None
welcome_channel_id = None

translator = Translator()

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} commands.")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

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

@bot.event
async def on_member_join(member):
    if welcome_channel_id:
        channel = member.guild.get_channel(welcome_channel_id)
        if channel:
            await channel.send(f"Welcome to the server, {member.mention}!")

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
    Example: /translate text:Hola src:es dest:en
    """
    try:
        result = translator.translate(text, src=src if src else 'auto', dest=dest)
        await interaction.response.send_message(f"**Translated ({result.src} → {result.dest}):**\n{result.text}")
    except Exception as e:
        await interaction.response.send_message(f"Translation failed: {e}", ephemeral=True)

if __name__ == "__main__":
    bot.run(TOKEN)
