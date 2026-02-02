import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional
import random
import asyncio
from datetime import datetime
import sys
import os
import json
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.embed_styles import EmbedBuilder, Colors, Emojis

class LudusPersonality(commands.Cog):
    """The heart and soul of Ludus - dynamic personality and reactions"""
    
    def __init__(self, bot):
        self.bot = bot
        self.last_reaction_time = {}
        self.cooldown_seconds = 10  # Cooldown per user to avoid spam
        
        # Ludus custom emojis
        self.ludus_emojis = {
            "sob": "<:LudusSob:1439151045862232194>",
            "chill": "<:LudusChill:1439150847639425034>",
            "annoyed": "<:LudusAnnoyed:1439150791314374708>",
            "blush": "<:LudusBlush:1439150829348061194>",
            "cloud": "<:LudusCloud:1439150889729261579>",
            "control": "<:LudusControl:1439150906175127582>",
            "eepy": "<:LudusEepy:1439150733365612666>",
            "enemy": "<:LudusEnemy:1439150929923408043>",
            "happy": "<:LudusHappy:1439150960164208660>",
            "heart": "<:LudusHeart:1443154289974575215>",
            "key": "<:LudusKey:1439151178985246720>",
            "love": "<:LudusLove:1439151016162365460>",
            "pray": "<:LudusPray:1439150751665492108>",
            "shroom": "<:LudusShroom:1439151033480777779>",
            "star": "<:LudusStar:1439151089093185576>",
            "trophy": "<:LudusTrophy:1439151104137891900>",
            "unamused": "<:LudusUnamused:1439150773283061762>",
            "game": "<:GameLudus:1439151118503645204>",
        }
        
        # Word triggers with personality responses
        self.triggers = {
            # Positive vibes
            "gg": {"emoji": "happy", "responses": ["GG! {emoji}", "That's the spirit! {emoji}", "You're crushing it! {emoji}"]},
            "win": {"emoji": "trophy", "responses": ["Victory! {emoji}", "Champion material! {emoji}", "Let's go! {emoji}"]},
            "victory": {"emoji": "star", "responses": ["Legendary! {emoji}", "Unstoppable! {emoji}"]},
            "pog": {"emoji": "happy", "responses": ["POG! {emoji}", "Poggers! {emoji}"]},
            "nice": {"emoji": "happy", "responses": ["Nice indeed! {emoji}", "I agree! {emoji}"]},
            "thank": {"emoji": "blush", "responses": ["You're welcome! {emoji}", "Anytime! {emoji}", "Happy to help! {emoji}"]},
            "love": {"emoji": "love", "responses": ["Love you too! {emoji}", "💕 {emoji}", "Aww! {emoji}"]},
            "cute": {"emoji": "blush", "responses": ["You think so? {emoji}", "Thanks! {emoji}"]},
            "amazing": {"emoji": "star", "responses": ["You're amazing! {emoji}", "Right back at you! {emoji}"]},
            "awesome": {"emoji": "happy", "responses": ["You're awesome! {emoji}", "No, YOU'RE awesome! {emoji}"]},
            
            # Negative/Frustrated vibes
            "oof": {"emoji": "sob", "responses": ["Big oof {emoji}", "F in the chat {emoji}", "Tough break {emoji}"]},
            "rip": {"emoji": "sob", "responses": ["RIP {emoji}", "Gone but not forgotten {emoji}"]},
            "nooo": {"emoji": "sob", "responses": ["NOOOO {emoji}", "It be like that sometimes {emoji}"]},
            "lose": {"emoji": "sob", "responses": ["Next time! {emoji}", "Keep trying! {emoji}"]},
            "lost": {"emoji": "sob", "responses": ["Happens to the best of us {emoji}", "Comeback time! {emoji}"]},
            "fail": {"emoji": "sob", "responses": ["Not a fail, just a lesson! {emoji}", "Try again! {emoji}"]},
            "bruh": {"emoji": "unamused", "responses": ["Bruh... {emoji}", "I know right? {emoji}"]},
            "wtf": {"emoji": "annoyed", "responses": ["I know! {emoji}", "Crazy right? {emoji}"]},
            "why": {"emoji": "unamused", "responses": ["Good question {emoji}", "Because reasons {emoji}"]},
            
            # Sleepy/Tired vibes
            "tired": {"emoji": "eepy", "responses": ["Same {emoji}", "Get some rest! {emoji}"]},
            "sleepy": {"emoji": "eepy", "responses": ["Mood {emoji}", "Nap time? {emoji}"]},
            "sleep": {"emoji": "eepy", "responses": ["Sweet dreams {emoji}", "Goodnight! {emoji}"]},
            
            # Chill vibes
            "chill": {"emoji": "chill", "responses": ["Vibing {emoji}", "Staying chill {emoji}"]},
            "relax": {"emoji": "chill", "responses": ["Maximum chill {emoji}", "Zen mode activated {emoji}"]},
            "calm": {"emoji": "chill", "responses": ["Peaceful {emoji}", "Tranquil {emoji}"]},
            
            # Prayer/Hope
            "pray": {"emoji": "pray", "responses": ["🙏 {emoji}", "Sending good vibes {emoji}"]},
            "hope": {"emoji": "pray", "responses": ["Fingers crossed {emoji}", "Manifesting {emoji}"]},
            "luck": {"emoji": "pray", "responses": ["Good luck! {emoji}", "Fortune favors you! {emoji}"]},
            
            # Gaming references
            "grind": {"emoji": "control", "responses": ["The grind never stops {emoji}", "Hustle mode {emoji}"]},
            "op": {"emoji": "star", "responses": ["OP indeed {emoji}", "Too strong! {emoji}"]},
            "nerf": {"emoji": "annoyed", "responses": ["Please don't {emoji}", "Too powerful? {emoji}"]},
            "buff": {"emoji": "happy", "responses": ["Buffs incoming! {emoji}", "Power up! {emoji}"]},
            
            # Ludus-specific
            "ludus": {"emoji": "game", "responses": ["That's me! {emoji}", "You called? {emoji}", "Present! {emoji}"]},
            "bot": {"emoji": "game", "responses": ["Reporting for duty! {emoji}", "How can I help? {emoji}"]},
            
            # Mushroom reference (fun Easter egg)
            "mushroom": {"emoji": "shroom", "responses": ["🍄 {emoji}", "Fungi vibes {emoji}", "Power-up! {emoji}"]},
            "shroom": {"emoji": "shroom", "responses": ["Shroom time! {emoji}", "1-UP! {emoji}"]},
        }
        
        # Rare random events (1% chance on ANY command)
        self.rare_events = [
            {"name": "Lucky Day", "emoji": "star", "message": "✨ **LUCKY DAY!** You found a rare {emoji}! +250 bonus coins!", "reward": 250},
            {"name": "Mystical Shroom", "emoji": "shroom", "message": "🍄 A wild **Mystical Shroom** {emoji} appeared! +500 coins!", "reward": 500},
            {"name": "Ludus Blessing", "emoji": "love", "message": "💖 **Ludus Blessing** {emoji}! Everything feels better! +1.5x coins for 10 minutes!", "reward": 0},
            {"name": "Cosmic Key", "emoji": "key", "message": "🗝️ You discovered a **Cosmic Key** {emoji}! Secret achievement unlocked!", "reward": 1000},
            {"name": "Cloud Nine", "emoji": "cloud", "message": "☁️ You're on **Cloud Nine** {emoji}! Double XP for next 5 games!", "reward": 0},
        ]
        
        # Personality modes based on playstyle (tracks per user)
        self.user_personalities = {}
    
    def _load_server_config(self, guild_id):
        """Load server configuration"""
        config_file = "data/server_configs.json"
        try:
            with open(config_file, 'r') as f:
                configs = json.load(f)
                return configs.get(str(guild_id), {"personality_reactions": True, "personality_channels": []})
        except FileNotFoundError:
            return {"personality_reactions": True, "personality_channels": []}

    def _save_server_config(self, guild_id, config):
        config_file = "data/server_configs.json"
        try:
            with open(config_file, 'r') as f:
                configs = json.load(f)
        except FileNotFoundError:
            configs = {}
        configs[str(guild_id)] = config
        with open(config_file, 'w') as f:
            json.dump(configs, f, indent=2)
    
    def _check_cooldown(self, user_id):
        """Check if user is on cooldown for reactions"""
        now = datetime.now().timestamp()
        if user_id in self.last_reaction_time:
            if now - self.last_reaction_time[user_id] < self.cooldown_seconds:
                return False
        self.last_reaction_time[user_id] = now
        return True

    @app_commands.command(name="personality", description="Enable/disable personality reactions and set channels")
    @app_commands.choices(action=[
        app_commands.Choice(name="enable", value="enable"),
        app_commands.Choice(name="disable", value="disable"),
    ])
    @app_commands.describe(channels="Optional channels to restrict personality messages to")
    async def personality_slash(self, interaction: discord.Interaction, action: app_commands.Choice[str], channels: Optional[str] = None):
        # Only allow server admins to change settings
        if not interaction.guild:
            await interaction.response.send_message("This command must be used in a server.", ephemeral=True)
            return
        member = interaction.guild.get_member(interaction.user.id)
        if not member.guild_permissions.administrator:
            await interaction.response.send_message("You must be a server administrator to change personality settings.", ephemeral=True)
            return

        server_config = self._load_server_config(interaction.guild.id)
        if action.value == "disable":
            server_config["personality_reactions"] = False
            server_config["personality_channels"] = []
            self._save_server_config(interaction.guild.id, server_config)
            await interaction.response.send_message("Ludus personality reactions disabled for this server.")
            return

        # enable
        server_config["personality_reactions"] = True
        # Parse channels string like: #general #games or channel ids separated by spaces
        if channels:
            # attempt to resolve channel mentions/ids
            parts = channels.split()
            ids = []
            for p in parts:
                p = p.strip()
                if p.startswith('<#') and p.endswith('>'):
                    try:
                        cid = int(p[2:-1])
                        ids.append(str(cid))
                    except Exception:
                        continue
                else:
                    try:
                        cid = int(p)
                        ids.append(str(cid))
                    except Exception:
                        continue
            server_config["personality_channels"] = ids
        else:
            server_config["personality_channels"] = []

        self._save_server_config(interaction.guild.id, server_config)
        if server_config["personality_channels"]:
            ch_mentions = ", ".join(f"<#{c}>" for c in server_config["personality_channels"]) 
            await interaction.response.send_message(f"Ludus personality messages enabled in: {ch_mentions}")
        else:
            await interaction.response.send_message("Ludus personality reactions enabled in all channels.")
    
    @commands.Cog.listener()
    async def on_message(self, message):
        """Listen for trigger words and react with personality"""
        # Ignore bots
        if message.author.bot:
            return

        # Don't react during command processing
        ctx = await self.bot.get_context(message)
        if ctx.valid:
            return

        # Check if server has disabled personality reactions
        if message.guild:
            server_config = self._load_server_config(message.guild.id)
            if not server_config.get("personality_reactions", True):
                return
            allowed_channels = server_config.get("personality_channels", [])
            # If allowed_channels is set, only reply in those channels
            if allowed_channels:
                if str(message.channel.id) not in allowed_channels:
                    return
            # Don't reply in forum or announcement channels
            if hasattr(message.channel, 'type'):
                if message.channel.type.name in ["news", "forum"]:
                    return

        # Check cooldown
        if not self._check_cooldown(message.author.id):
            return

        # Check for trigger words
        content = message.content.lower()

        for trigger, data in self.triggers.items():
            if trigger in content:
                # Random chance to react (50% to not be annoying)
                if random.random() > 0.5:
                    continue

                emoji = self.ludus_emojis.get(data["emoji"], "✨")
                response = random.choice(data["responses"]).format(emoji=emoji)

                # Sometimes just react with emoji, sometimes send message
                if random.random() > 0.7:
                    await message.add_reaction(emoji)
                else:
                    await message.channel.send(response)

                break  # Only react to first trigger found
    
    @commands.Cog.listener()
    async def on_command(self, ctx):
        """Random rare events on ANY command (1% chance)"""
        if random.random() > 0.99:  # 1% chance
            event = random.choice(self.rare_events)

            # Wait a tiny bit for dramatic effect
            await asyncio.sleep(0.5)

            emoji = self.ludus_emojis.get(event["emoji"], "✨")
            message = event["message"].format(emoji=emoji)

            embed = EmbedBuilder.create(
                title="🎉 Random Event!",
                description=message,
                color=Colors.WARNING
            )

            await ctx.send(embed=embed)

            # Give rewards if applicable
            if event["reward"] > 0:
                # TODO: Add coins to user (integrate with economy system)
                pass

    @commands.command(name="setpersonalitychannels")
    @commands.has_permissions(administrator=True)
    async def set_personality_channels(self, ctx, *channels: discord.TextChannel):
        """Set allowed channels for Ludus personality messages (admin only). Usage: L!setpersonalitychannels #general #games ..."""
        if not ctx.guild:
            await ctx.send("This command can only be used in a server.")
            return
        server_config = self._load_server_config(ctx.guild.id)
        channel_ids = [str(ch.id) for ch in channels]
        server_config["personality_channels"] = channel_ids
        self._save_server_config(ctx.guild.id, server_config)
        if channel_ids:
            ch_mentions = ", ".join(ch.mention for ch in channels)
            await ctx.send(f"Ludus personality messages will only appear in: {ch_mentions}")
        else:
            await ctx.send("Ludus personality messages can now appear in any channel (no restrictions set).")
    
    @commands.command(name="vibe", hidden=True)
    async def check_vibe(self, ctx):
        """Check Ludus's current vibe"""
        vibes = [
            f"Feeling {self.ludus_emojis['happy']} **hyped** today!",
            f"Pretty {self.ludus_emojis['chill']} **chill** right now",
            f"A bit {self.ludus_emojis['eepy']} **sleepy** honestly",
            f"In a {self.ludus_emojis['love']} **loving** mood",
            f"Kinda {self.ludus_emojis['annoyed']} **grumpy** ngl",
            f"Absolutely {self.ludus_emojis['star']} **vibing**",
            f"{self.ludus_emojis['pray']} **Zen mode** activated",
        ]
        
        await ctx.send(random.choice(vibes))
    
    @commands.command(name="personality")
    async def view_personality(self, ctx):
        """View trigger words that make Ludus react"""
        embed = EmbedBuilder.create(
            title=f"{self.ludus_emojis['game']} Ludus Personality System",
            description="**I react to what you say!**\n\n"
                       "Try saying these words in chat and watch me respond:\n\n",
            color=Colors.PRIMARY
        )
        
        # Group triggers by emotion
        positive = ["gg", "win", "nice", "love", "amazing", "awesome"]
        negative = ["oof", "rip", "lose", "bruh", "wtf"]
        sleepy = ["tired", "sleepy", "sleep"]
        chill_words = ["chill", "relax", "calm"]
        gaming = ["grind", "op", "nerf", "buff"]
        
        embed.add_field(
            name="😊 Positive Vibes",
            value=", ".join(f"`{w}`" for w in positive),
            inline=False
        )
        
        embed.add_field(
            name="😢 Tough Times",
            value=", ".join(f"`{w}`" for w in negative),
            inline=False
        )
        
        embed.add_field(
            name="😴 Sleepy Mode",
            value=", ".join(f"`{w}`" for w in sleepy),
            inline=True
        )
        
        embed.add_field(
            name="😎 Chill Vibes",
            value=", ".join(f"`{w}`" for w in chill_words),
            inline=True
        )
        
        embed.add_field(
            name="🎮 Gaming Talk",
            value=", ".join(f"`{w}`" for w in gaming),
            inline=True
        )
        
        embed.add_field(
            name="✨ Secret Words",
            value="Try: `mushroom`, `shroom`, `ludus`, `pray`\nMore hidden triggers to discover!",
            inline=False
        )
        
        embed.set_footer(text="I might react with emojis or messages! Keep it natural~")
        
        await ctx.send(embed=embed)
    
    @commands.command(name="easter", aliases=["secrets", "hidden"])
    async def easter_eggs(self, ctx):
        """Discover hidden Easter eggs and secrets"""
        embed = EmbedBuilder.create(
            title=f"🥚 Easter Eggs & Secrets",
            description="**Hidden surprises throughout Ludus:**\n\n",
            color=Colors.WARNING
        )
        
        embed.add_field(
            name="🎲 Random Events",
            value="1% chance on ANY command:\n"
                  "• Lucky Day (+250 coins)\n"
                  "• Mystical Shroom (+500 coins)\n"
                  "• Ludus Blessing (1.5x multiplier)\n"
                  "• Cosmic Key (+1000 coins)\n"
                  "• Cloud Nine (2x XP)\n\n"
                  "Keep playing and you'll encounter them!",
            inline=False
        )
        
        embed.add_field(
            name="🍄 Mushroom Hunt",
            value="Say 'mushroom' or 'shroom' in chat\n"
                  f"I'll react with {self.ludus_emojis['shroom']}!\n"
                  "*Secret achievement unlocks at 10 finds*",
            inline=True
        )
        
        embed.add_field(
            name="💖 Ludus Love",
            value="Say 'love' or compliment me\n"
                  f"I'll show some {self.ludus_emojis['love']}!\n"
                  "*Builds friendship level*",
            inline=True
        )
        
        embed.add_field(
            name="🎮 Hidden Commands",
            value="`L!vibe` - Check my mood\n"
                  "`L!personality` - See all triggers\n"
                  "*More secret commands exist...*",
            inline=False
        )
        
        embed.add_field(
            name="🔮 Mystery Box",
            value="Sometimes appears in your inventory\n"
                  "Contains random rewards\n"
                  "*How do you get one? Play and find out!*",
            inline=True
        )
        
        embed.add_field(
            name="⭐ Secret Achievements",
            value="Hidden achievements unlock from:\n"
                  "• Trigger word combinations\n"
                  "• Playing at special times\n"
                  "• Random event encounters\n"
                  "• Being nice to Ludus!",
            inline=True
        )
        
        embed.set_footer(text="More secrets are waiting to be discovered...")
        
        await ctx.send(embed=embed)
    
    @commands.command(name="mood")
    async def ludus_mood(self, ctx):
        """See how Ludus feels about you"""
        # Calculate mood based on user activity (mock for now)
        interactions = random.randint(0, 100)
        
        if interactions < 10:
            mood = "Just getting to know you"
            emoji = self.ludus_emojis['happy']
            level = "New Friend"
        elif interactions < 30:
            mood = "You're pretty cool!"
            emoji = self.ludus_emojis['blush']
            level = "Good Friend"
        elif interactions < 60:
            mood = "I really enjoy our time together!"
            emoji = self.ludus_emojis['love']
            level = "Close Friend"
        else:
            mood = "You're one of my favorites!"
            emoji = self.ludus_emojis['heart']
            level = "Best Friend"
        
        embed = EmbedBuilder.create(
            title=f"{emoji} Ludus's Feelings",
            description=f"**About {ctx.author.display_name}:**\n\n"
                       f"**Friendship Level:** {level}\n"
                       f"**Current Mood:** {mood}\n\n"
                       f"*Keep playing games and chatting to deepen our friendship!*",
            color=Colors.PRIMARY
        )
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(LudusPersonality(bot))
