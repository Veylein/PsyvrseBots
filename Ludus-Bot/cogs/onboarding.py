import discord
from discord.ext import commands
from discord.ui import View, Button
import json
import os
from datetime import datetime
import random
import asyncio
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.embed_styles import EmbedBuilder, Colors, Emojis

class WelcomeAdventureView(View):
    def __init__(self, ctx, onboarding_cog):
        super().__init__(timeout=300)
        self.ctx = ctx
        self.onboarding_cog = onboarding_cog
        self.current_step = 0
    
    @discord.ui.button(label="Let's Go!", style=discord.ButtonStyle.primary, emoji="🚀")
    async def start_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("Start your own adventure with L!start!", ephemeral=True)
            return
        
        await interaction.response.defer()
        await self.onboarding_cog._continue_adventure(self.ctx, self.current_step + 1)
        self.stop()

class FirstExperience(commands.Cog):
    """Dynamic first-time user experience - an adventure, not a tutorial"""
    
    def __init__(self, bot):
        self.bot = bot
        self.data_dir = os.getenv("RENDER_DISK_PATH", ".")
        self.onboarding_file = os.path.join(self.data_dir, "user_onboarding.json")
        self.onboarding_data = self._load_data()
        
        # Ludus custom emojis
        self.ludus = {
            "happy": "<:LudusHappy:1439150960164208660>",
            "love": "<:LudusLove:1439151016162365460>",
            "star": "<:LudusStar:1439151089093185576>",
            "trophy": "<:LudusTrophy:1439151104137891900>",
            "game": "<:GameLudus:1439151118503645204>",
            "key": "<:LudusKey:1439151178985246720>",
            "shroom": "<:LudusShroom:1439151033480777779>",
            "heart": "<:LudusHeart:1443154289974575215>",
        }
    
    def _load_data(self):
        """Load onboarding data"""
        try:
            if os.path.exists(self.onboarding_file):
                with open(self.onboarding_file, 'r') as f:
                    return json.load(f)
        except:
            pass
        return {}
    
    def _save_data(self):
        """Save onboarding data"""
        try:
            with open(self.onboarding_file, 'w') as f:
                json.dump(self.onboarding_data, f, indent=2)
        except Exception as e:
            print(f"Error saving onboarding: {e}")
    
    def is_new_user(self, user_id):
        """Check if user is brand new"""
        return str(user_id) not in self.onboarding_data
    
    def mark_onboarded(self, user_id):
        """Mark user as onboarded"""
        self.onboarding_data[str(user_id)] = {
            "completed": True,
            "date": datetime.now().isoformat(),
            "steps_completed": []
        }
        self._save_data()
    
    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Welcome new members with personality"""
        # DISABLED: Welcome happens via DM on first command use (see bot.py on_command event)
        # This prevents spamming servers with join messages
        pass
    
    @commands.hybrid_command(
        name="start",
        aliases=["begin", "adventure"],
        description="Start your Ludus adventure (perfect for new players)"
    )
    async def start_adventure(self, ctx):
        """Start your Ludus adventure (for new users)"""
        user_id = str(ctx.author.id)
        
        # Check if already completed
        if user_id in self.onboarding_data:
            await ctx.send(f"You've already started your adventure! {self.ludus['happy']}\n"
                          f"Try `L!help` or `L!tutorial` to explore more!")
            return
        
        # Step 1: The Mysterious Beginning
        embed = EmbedBuilder.create(
            title=f"{self.ludus['game']} A New Adventure Begins...",
            description=f"*You find yourself in a mystical Discord realm...*\n\n"
                       f"A friendly spirit appears before you!\n\n"
                       f"**Ludus:** \"Hey there, traveler! {self.ludus['happy']}\n"
                       f"Welcome to my world of games and treasures!\n\n"
                       f"I sense great potential in you...\n"
                       f"Are you ready to embark on an epic journey?\"\n\n"
                       f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                       f"**Click below to continue your adventure!**",
            color=Colors.PRIMARY
        )
        
        view = WelcomeAdventureView(ctx, self)
        await ctx.send(embed=embed, view=view)
    
    async def _continue_adventure(self, ctx, step):
        """Continue the adventure sequence"""
        if step == 1:
            # Step 2: The First Gift
            embed = EmbedBuilder.create(
                title=f"{self.ludus['star']} The First Gift",
                description=f"**Ludus:** \"First things first! {self.ludus['love']}\n"
                           f"Every adventurer needs a starter kit!\"\n\n"
                           f"*Ludus waves their hand and coins appear!*\n\n"
                           f"✨ **You received 500 PsyCoins!** {Emojis.COIN}\n\n"
                           f"**Ludus:** \"These coins are the currency of our realm.\n"
                           f"You can earn more by playing games, completing quests,\n"
                           f"or even starting your own business!\"\n\n"
                           f"Type `L!balance` to check your wealth!",
                color=Colors.WARNING
            )
            
            await ctx.send(embed=embed)
            await asyncio.sleep(3)
            
            # TODO: Actually give 500 coins to user
            
            await self._continue_adventure(ctx, 2)
        
        elif step == 2:
            # Step 3: The First Challenge
            embed = EmbedBuilder.create(
                title=f"{self.ludus['trophy']} Your First Challenge",
                description=f"**Ludus:** \"Now, let's see what you're made of! {self.ludus['game']}\n\n"
                           f"I challenge you to your first game...\n"
                           f"Let's play **Wordle**!\"\n\n"
                           f"*A mystical word puzzle appears before you*\n\n"
                           f"🎯 **Mission:** Guess the secret 5-letter word\n"
                           f"💰 **Reward:** 100+ coins\n"
                           f"⭐ **Bonus:** First game achievement!\n\n"
                           f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                           f"**Type `L!wordle` to play!**\n"
                           f"*(I'll wait for you here...)*",
                color=Colors.PRIMARY
            )
            
            await ctx.send(embed=embed)
            
            # Wait for user to complete wordle (simplified - just wait 30s)
            await asyncio.sleep(30)
            
            await self._continue_adventure(ctx, 3)
        
        elif step == 3:
            # Step 4: The Revelation
            embed = EmbedBuilder.create(
                title=f"{self.ludus['happy']} Well Done, Adventurer!",
                description=f"**Ludus:** \"Excellent work! {self.ludus['star']}\n\n"
                           f"I can see you're a natural!\n"
                           f"But this is just the beginning...\"\n\n"
                           f"*The realm around you expands, revealing more possibilities*\n\n"
                           f"**Ludus:** \"This world has so much more to offer:\n\n"
                           f"🎮 **100+ Minigames** - From puzzles to speed challenges\n"
                           f"🏪 **Business Empire** - Create your own shop\n"
                           f"🌾 **Farming** - Grow and sell crops\n"
                           f"👥 **Guilds** - Join forces with friends\n"
                           f"🏆 **200+ Achievements** - Endless goals to chase\n"
                           f"💎 **Daily Challenges** - Bonus rewards every day\"\n\n"
                           f"━━━━━━━━━━━━━━━━━━━━━━━━",
                color=Colors.SUCCESS
            )
            
            await ctx.send(embed=embed)
            await asyncio.sleep(2)
            
            await self._continue_adventure(ctx, 4)
        
        elif step == 4:
            # Step 5: The Secret
            embed = EmbedBuilder.create(
                title=f"{self.ludus['key']} A Secret Revealed",
                description=f"**Ludus:** \"Before you go explore... {self.ludus['love']}\n\n"
                           f"Let me share a secret with you.\"\n\n"
                           f"*Ludus leans in closer*\n\n"
                           f"**Ludus:** \"This realm is **alive**.\n"
                           f"I react to what you say...\n"
                           f"Random events happen when you least expect them...\n"
                           f"Hidden achievements wait to be discovered...\n\n"
                           f"Say 'gg' after a good game, and I'll cheer with you.\n"
                           f"Say 'oof' when things go wrong, and I'll comfort you.\n"
                           f"Find the hidden mushrooms for secret rewards...\"\n\n"
                           f"*Ludus smiles mysteriously*\n\n"
                           f"**Ludus:** \"There's so much hidden magic here.\n"
                           f"The more you play, the more you'll discover!\"\n\n"
                           f"━━━━━━━━━━━━━━━━━━━━━━━━",
                color=Colors.WARNING
            )
            
            await ctx.send(embed=embed)
            await asyncio.sleep(2)
            
            await self._continue_adventure(ctx, 5)
        
        elif step == 5:
            # Step 6: The Gift
            embed = EmbedBuilder.create(
                title=f"{self.ludus['shroom']} The Mystical Gift",
                description=f"**Ludus:** \"For completing your first adventure... {self.ludus['heart']}\n\n"
                           f"I have a special gift for you!\"\n\n"
                           f"*A glowing mushroom materializes in your hands*\n\n"
                           f"🍄 **You received: Mystical Shroom**\n"
                           f"✨ **Effect:** 2x coins for your next 5 games!\n"
                           f"🎁 **Achievement Unlocked:** First Adventure\n"
                           f"💰 **Bonus:** +250 coins\n\n"
                           f"**Ludus:** \"You're all set now!\n\n"
                           f"Remember:\n"
                           f"• Check `L!daily` every day for free coins\n"
                           f"• Try `L!challenges` for extra rewards\n"
                           f"• Use `L!help` if you ever get lost\n"
                           f"• Most importantly... **have fun!** {self.ludus['happy']}\"\n\n"
                           f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                           f"🎮 **Your adventure has only just begun!**",
                color=Colors.SUCCESS
            )
            
            await ctx.send(embed=embed)
            
            # Mark user as onboarded
            self.mark_onboarded(ctx.author.id)
            
            # TODO: Give actual rewards (mystical shroom buff, 250 coins, achievement)
    
    @commands.command(name="firsttime", hidden=True)
    async def reset_onboarding(self, ctx):
        """Reset your onboarding status (for testing)"""
        user_id = str(ctx.author.id)
        if user_id in self.onboarding_data:
            del self.onboarding_data[user_id]
            self._save_data()
            await ctx.send("✅ Onboarding reset! Try `L!start` again!")
        else:
            await ctx.send("You haven't completed onboarding yet!")
    
    @commands.command(name="mysticalshroom", aliases=["shroom"])
    async def mystical_shroom_info(self, ctx):
        """Learn about mystical shrooms"""
        embed = EmbedBuilder.create(
            title=f"{self.ludus['shroom']} Mystical Shrooms",
            description=f"**Rare power-ups found throughout Ludus!**\n\n"
                       f"🍄 **Effects:**\n"
                       f"• 2x coin multiplier\n"
                       f"• 2x XP gain\n"
                       f"• Lasts 5 games or 30 minutes\n\n"
                       f"🔮 **How to Get:**\n"
                       f"• Complete first adventure\n"
                       f"• 1% chance from random events\n"
                       f"• Say 'mushroom' in chat (rare chance)\n"
                       f"• Hidden in achievements\n"
                       f"• Mystery boxes\n\n"
                       f"💎 **Pro Tip:**\n"
                       f"Use them on high-reward games for maximum profit!",
            color=Colors.WARNING
        )
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(FirstExperience(bot))
