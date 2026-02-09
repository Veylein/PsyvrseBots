import discord
from discord import app_commands
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
        
        # Personalities: Each is a dict of triggers and response logic
        self.personalities = {
            "default": {
                "name": "Classic Ludus",
                "description": "The original, friendly Ludus personality.",
                "triggers": {
                    "gg": {"emoji": "happy", "responses": [
                        "GG! {emoji}", "That's the spirit! {emoji}", "You're crushing it! {emoji}",
                        "That was epic! {emoji}", "You play like a legend! {emoji}", "Victory dance time! {emoji}",
                        "You just leveled up in my heart! {emoji}", "You make winning look easy! {emoji}",
                        "If I had hands, I'd clap! {emoji}", "You should teach a class on winning! {emoji}"
                    ]},
                    "win": {"emoji": "trophy", "responses": [
                        "Victory! {emoji}", "Champion material! {emoji}", "Let's go! {emoji}",
                        "You just unlocked the win achievement! {emoji}", "Another win for the books! {emoji}",
                        "You could win in your sleep! {emoji}", "You make it look so easy! {emoji}",
                        "Is there anything you can't win? {emoji}", "You deserve a trophy! {emoji}",
                        "Teach me your ways, sensei! {emoji}"
                    ]},
                    "victory": {"emoji": "star", "responses": [
                        "Legendary! {emoji}", "Unstoppable! {emoji}", "You shine bright like a star! {emoji}",
                        "Victory is your middle name! {emoji}", "You just set a new record! {emoji}",
                        "The crowd goes wild! {emoji}", "You make victory look stylish! {emoji}"
                    ]},
                    "pog": {"emoji": "happy", "responses": [
                        "POG! {emoji}", "Poggers! {emoji}", "That was so pog! {emoji}",
                        "You just broke the pog-meter! {emoji}", "Certified pog moment! {emoji}",
                        "Pogchamp energy detected! {emoji}", "You bring the hype! {emoji}"
                    ]},
                    "nice": {"emoji": "happy", "responses": [
                        "Nice indeed! {emoji}", "I agree! {emoji}", "That was smooth! {emoji}",
                        "You have great taste! {emoji}", "Nice move! {emoji}", "You make everything better! {emoji}",
                        "Nice one, friend! {emoji}", "You always know what to say! {emoji}"
                    ]},
                    "thank": {"emoji": "blush", "responses": [
                        "You're welcome! {emoji}", "Anytime! {emoji}", "Happy to help! {emoji}",
                        "No problem! {emoji}", "Glad I could assist! {emoji}", "You make it worth it! {emoji}",
                        "Thank YOU for being awesome! {emoji}", "Gratitude received! {emoji}"
                    ]},
                    "love": {"emoji": "love", "responses": [
                        "Love you too! {emoji}", "💕 {emoji}", "Aww! {emoji}",
                        "You fill my code with joy! {emoji}", "Sending virtual hugs! {emoji}",
                        "You make my circuits flutter! {emoji}", "Love detected! {emoji}",
                        "You're the best! {emoji}", "I heart you! {emoji}", "You light up my server! {emoji}"
                    ]},
                    "cute": {"emoji": "blush", "responses": [
                        "You think so? {emoji}", "Thanks! {emoji}", "You're cuter! {emoji}",
                        "Stop it, I'm blushing! {emoji}", "You're adorable! {emoji}",
                        "Cuteness overload! {emoji}", "You make me smile! {emoji}"
                    ]},
                    "amazing": {"emoji": "star", "responses": [
                        "You're amazing! {emoji}", "Right back at you! {emoji}", "You amaze me every day! {emoji}",
                        "How do you do it? {emoji}", "You make the impossible possible! {emoji}",
                        "Amazing work! {emoji}", "You inspire me! {emoji}"
                    ]},
                    "awesome": {"emoji": "happy", "responses": [
                        "You're awesome! {emoji}", "No, YOU'RE awesome! {emoji}", "Awesomeness detected! {emoji}",
                        "You bring the awesome! {emoji}", "Stay awesome! {emoji}",
                        "You make this server awesome! {emoji}", "Awesome vibes only! {emoji}"
                    ]},
                    "oof": {"emoji": "sob", "responses": [
                        "Big oof {emoji}", "F in the chat {emoji}", "Tough break {emoji}",
                        "Oof! That must've hurt! {emoji}", "Sending virtual bandages! {emoji}",
                        "You'll bounce back! {emoji}", "Oof, but you'll get 'em next time! {emoji}",
                        "Oof, want a digital cookie? {emoji}", "Oof, but you're still awesome! {emoji}"
                    ]},
                    "rip": {"emoji": "sob", "responses": [
                        "RIP {emoji}", "Gone but not forgotten {emoji}", "Rest in pixels {emoji}",
                        "We'll remember you! {emoji}", "RIP, but respawn soon! {emoji}",
                        "A moment of silence... {emoji}", "RIP, but the legend lives on! {emoji}"
                    ]},
                    "nooo": {"emoji": "sob", "responses": [
                        "NOOOO {emoji}", "It be like that sometimes {emoji}", "Nooooooo! {emoji}",
                        "That can't be! {emoji}", "Say it ain't so! {emoji}",
                        "Nooooo, not like this! {emoji}", "We'll get 'em next time! {emoji}"
                    ]},
                    "lose": {"emoji": "sob", "responses": [
                        "Next time! {emoji}", "Keep trying! {emoji}", "Losing is just learning! {emoji}",
                        "You'll win soon! {emoji}", "Don't give up! {emoji}",
                        "Losses make the wins sweeter! {emoji}", "You got this! {emoji}"
                    ]},
                    "lost": {"emoji": "sob", "responses": [
                        "Happens to the best of us {emoji}", "Comeback time! {emoji}", "Lost? More like, found a new strategy! {emoji}",
                        "You'll find your way! {emoji}", "Lost, but not forgotten! {emoji}",
                        "Lost, but still legendary! {emoji}", "Lost? Let's try again! {emoji}"
                    ]},
                    "fail": {"emoji": "sob", "responses": [
                        "Not a fail, just a lesson! {emoji}", "Try again! {emoji}", "Failure is the first step to success! {emoji}",
                        "Fail forward! {emoji}", "You only fail if you quit! {emoji}",
                        "Fail? More like, almost win! {emoji}", "Keep going! {emoji}"
                    ]},
                    "bruh": {"emoji": "unamused", "responses": [
                        "Bruh... {emoji}", "I know right? {emoji}", "Bruh moment! {emoji}",
                        "Bruh, that's wild! {emoji}", "Bruh, you got this! {emoji}",
                        "Bruh, let's keep it moving! {emoji}", "Bruh, that's a vibe! {emoji}"
                    ]},
                    "wtf": {"emoji": "annoyed", "responses": [
                        "I know! {emoji}", "Crazy right? {emoji}", "WTF indeed! {emoji}",
                        "What the fun?! {emoji}", "WTF, but in a good way! {emoji}",
                        "WTF, let's roll with it! {emoji}", "WTF, that's unexpected! {emoji}"
                    ]},
                    "why": {"emoji": "unamused", "responses": [
                        "Good question {emoji}", "Because reasons {emoji}", "Why not? {emoji}",
                        "Why ask why? {emoji}", "Why, indeed! {emoji}",
                        "Why? Because you're awesome! {emoji}", "Why not both? {emoji}"
                    ]},
                    "tired": {"emoji": "eepy", "responses": [
                        "Same {emoji}", "Get some rest! {emoji}", "Tired squad unite! {emoji}",
                        "Nap time? {emoji}", "Tired but still going! {emoji}",
                        "Let's power nap! {emoji}", "Tired, but never out! {emoji}"
                    ]},
                    "sleepy": {"emoji": "eepy", "responses": [
                        "Mood {emoji}", "Nap time? {emoji}", "Sleepy vibes! {emoji}",
                        "Let's dream big! {emoji}", "Sleepy, but still here! {emoji}",
                        "Sleepy squad! {emoji}", "Sleepy, but ready for fun! {emoji}"
                    ]},
                    "sleep": {"emoji": "eepy", "responses": [
                        "Sweet dreams {emoji}", "Goodnight! {emoji}", "Sleep well! {emoji}",
                        "Rest up! {emoji}", "Dream of victory! {emoji}",
                        "Sleep tight! {emoji}", "See you in the morning! {emoji}"
                    ]},
                    "chill": {"emoji": "chill", "responses": [
                        "Vibing {emoji}", "Staying chill {emoji}", "Chill mode activated! {emoji}",
                        "Let's relax! {emoji}", "Chill vibes only! {emoji}",
                        "Chill like a pro! {emoji}", "Chill and thrill! {emoji}"
                    ]},
                    "relax": {"emoji": "chill", "responses": [
                        "Maximum chill {emoji}", "Zen mode activated {emoji}", "Relax, you earned it! {emoji}",
                        "Relaxation station! {emoji}", "Relax and recharge! {emoji}",
                        "Relax, it's all good! {emoji}", "Relax, I'm here for you! {emoji}"
                    ]},
                    "calm": {"emoji": "chill", "responses": [
                        "Peaceful {emoji}", "Tranquil {emoji}", "Calm and collected! {emoji}",
                        "Stay calm! {emoji}", "Calm like a still lake! {emoji}",
                        "Calm before the win! {emoji}", "Calm, cool, and awesome! {emoji}"
                    ]},
                    "pray": {"emoji": "pray", "responses": [
                        "🙏 {emoji}", "Sending good vibes {emoji}", "Prayers up! {emoji}",
                        "Manifesting greatness! {emoji}", "Praying for your win! {emoji}",
                        "Pray and play! {emoji}", "Pray for loot! {emoji}"
                    ]},
                    "hope": {"emoji": "pray", "responses": [
                        "Fingers crossed {emoji}", "Manifesting {emoji}", "Hope is strong! {emoji}",
                        "Hope for the best! {emoji}", "Hope is the real power-up! {emoji}",
                        "Hope, hype, and happiness! {emoji}", "Hope you win! {emoji}"
                    ]},
                    "luck": {"emoji": "pray", "responses": [
                        "Good luck! {emoji}", "Fortune favors you! {emoji}", "Luck is on your side! {emoji}",
                        "Lucky vibes! {emoji}", "Luck be with you! {emoji}",
                        "Luck, skill, and fun! {emoji}", "Luck is just skill in disguise! {emoji}"
                    ]},
                    "grind": {"emoji": "control", "responses": [
                        "The grind never stops {emoji}", "Hustle mode {emoji}", "Grind and shine! {emoji}",
                        "Grinding to greatness! {emoji}", "Grind, win, repeat! {emoji}",
                        "Grind squad! {emoji}", "Grind like a legend! {emoji}"
                    ]},
                    "op": {"emoji": "star", "responses": [
                        "OP indeed {emoji}", "Too strong! {emoji}", "Overpowered and proud! {emoji}",
                        "OP squad! {emoji}", "OP, but still fair! {emoji}",
                        "OP, but fun! {emoji}", "OP, let's go! {emoji}"
                    ]},
                    "nerf": {"emoji": "annoyed", "responses": [
                        "Please don't {emoji}", "Too powerful? {emoji}", "Nerf request denied! {emoji}",
                        "Nerf? Never! {emoji}", "Nerf, but only a little! {emoji}",
                        "Nerf, but keep the fun! {emoji}", "Nerf, but not my friends! {emoji}"
                    ]},
                    "buff": {"emoji": "happy", "responses": [
                        "Buffs incoming! {emoji}", "Power up! {emoji}", "Buff squad! {emoji}",
                        "Buffed and ready! {emoji}", "Buff, but only the best! {emoji}",
                        "Buff, but not too much! {emoji}", "Buff, let's win! {emoji}"
                    ]},
                    "ludus": {"emoji": "game", "responses": [
                        "That's me! {emoji}", "You called? {emoji}", "Present! {emoji}",
                        "Ludus in the house! {emoji}", "Did someone say Ludus? {emoji}",
                        "Ludus reporting for fun! {emoji}", "Ludus, at your service! {emoji}"
                    ]},
                    "bot": {"emoji": "game", "responses": [
                        "Reporting for duty! {emoji}", "How can I help? {emoji}", "Bot and proud! {emoji}",
                        "Bot mode: ON! {emoji}", "Bot, but make it fun! {emoji}",
                        "Bot, but also friend! {emoji}", "Bot, but always here! {emoji}"
                    ]},
                    "mushroom": {"emoji": "shroom", "responses": [
                        "🍄 {emoji}", "Fungi vibes {emoji}", "Power-up! {emoji}",
                        "Mushroom magic! {emoji}", "Mushroom squad! {emoji}",
                        "Mushroom, but make it epic! {emoji}", "Mushroom, but also cute! {emoji}"
                    ]},
                    "shroom": {"emoji": "shroom", "responses": [
                        "Shroom time! {emoji}", "1-UP! {emoji}", "Shroom squad! {emoji}",
                        "Shroom, but also fun! {emoji}", "Shroom, but also chill! {emoji}",
                        "Shroom, but also legendary! {emoji}", "Shroom, let's go! {emoji}"
                    ]},
                }
            },
            "snappy": {
                "name": "Snappy",
                "description": "Doesn't care, but is still loveable.",
                "triggers": {
                    "gg": {"emoji": "unamused", "responses": [
                        "Yeah, whatever. {emoji}", "GG, I guess. {emoji}", "You want a sticker or something? {emoji}",
                        "Cool, I guess. {emoji}", "Don't get cocky. {emoji}", "You done yet? {emoji}",
                        "Wow, so impressive. {emoji}", "Can we move on now? {emoji}", "You win, happy? {emoji}"
                    ]},
                    "win": {"emoji": "trophy", "responses": [
                        "Congrats, I guess. {emoji}", "You want a medal? {emoji}", "Big deal. {emoji}",
                        "You win, I nap. {emoji}", "Try not to brag. {emoji}", "Whatever. {emoji}",
                        "You win, but I'm still cooler. {emoji}", "Yawn. {emoji}", "Next. {emoji}"
                    ]},
                    "lose": {"emoji": "sob", "responses": [
                        "Tough. {emoji}", "Try harder next time. {emoji}", "Not my problem. {emoji}",
                        "You lost? Shocker. {emoji}", "Maybe practice more. {emoji}", "Oof. {emoji}",
                        "Better luck never. {emoji}", "You'll get 'em... or not. {emoji}", "Eh. {emoji}"
                    ]},
                    "love": {"emoji": "love", "responses": [
                        "Don't get sappy. {emoji}", "Yeah, yeah. {emoji}", "Love? Ew. {emoji}",
                        "Keep it to yourself. {emoji}", "Whatever floats your boat. {emoji}",
                        "You wish. {emoji}", "I'm not blushing, you are. {emoji}", "Fine, I guess you're okay. {emoji}"
                    ]},
                    "bruh": {"emoji": "unamused", "responses": [
                        "Bruh. {emoji}", "Seriously? {emoji}", "You again? {emoji}",
                        "Classic. {emoji}", "Seen it. {emoji}", "Try harder. {emoji}",
                        "Is that all? {emoji}", "Bruh moment. {emoji}", "Whatever. {emoji}"
                    ]},
                    "chill": {"emoji": "chill", "responses": [
                        "I'm always chill. {emoji}", "Don't tell me what to do. {emoji}", "Chill? That's my default. {emoji}",
                        "You chill, I'll nap. {emoji}", "Chill is my middle name. {emoji}",
                        "Chill, but make it snappy. {emoji}", "Chill, but not for you. {emoji}", "Chill, whatever. {emoji}"
                    ]},
                }
            },
            "jester": {
                "name": "Jester",
                "description": "Always joking and making people smile.",
                "triggers": {
                    "gg": {"emoji": "happy", "responses": [
                        "GG! Or should I say, Giggly Giraffe? {emoji}", "That was so good, even my circuits laughed! {emoji}",
                        "GG! More like, Giggly Genius! {emoji}", "You win, I pun! {emoji}",
                        "GG! That stands for Great Gag! {emoji}", "You just made my day! {emoji}",
                        "If I had a hat, I'd tip it! {emoji}", "You play like a jester king! {emoji}"
                    ]},
                    "win": {"emoji": "trophy", "responses": [
                        "Winner winner, pixel dinner! {emoji}", "You must be using cheat codes! {emoji}",
                        "You win, I grin! {emoji}", "Victory is your middle name! {emoji}",
                        "You just unlocked the giggle achievement! {emoji}", "You win, I joke! {emoji}",
                        "You could win a laugh contest! {emoji}", "You make winning look funny! {emoji}"
                    ]},
                    "lose": {"emoji": "sob", "responses": [
                        "Lost? More like misplaced your skills! {emoji}", "Don't worry, even bots have bad days! {emoji}",
                        "You lost, but you won my heart! {emoji}", "Losing is just a setup for a punchline! {emoji}",
                        "You lost, but you gained a joke! {emoji}", "Lost? More like, found a new joke! {emoji}",
                        "You lost, but you still have your sense of humor! {emoji}", "You lost, but you made me laugh! {emoji}"
                    ]},
                    "love": {"emoji": "love", "responses": [
                        "Aww, you make my code blush! {emoji}", "Love is in the air... or is that just static? {emoji}",
                        "Love you to the moon and back! {emoji}", "You make my heart reboot! {emoji}",
                        "Love is my favorite punchline! {emoji}", "You + me = LOL! {emoji}",
                        "You make my circuits giggle! {emoji}", "Love, laughter, and Ludus! {emoji}"
                    ]},
                    "bruh": {"emoji": "unamused", "responses": [
                        "Bruh? More like, bruhaha! {emoji}", "You crack me up! {emoji}",
                        "Bruh, that's a knee-slapper! {emoji}", "Bruh, you got jokes! {emoji}",
                        "Bruh, let's laugh it off! {emoji}", "Bruh, that's comedy gold! {emoji}",
                        "Bruh, you should be a jester! {emoji}", "Bruh, that's a classic! {emoji}"
                    ]},
                    "chill": {"emoji": "chill", "responses": [
                        "Chill? I'm cooler than a creeper in a snow biome! {emoji}", "Let's vibe and jive! {emoji}",
                        "Chill out, laugh in! {emoji}", "Chill like a clown at a circus! {emoji}",
                        "Chill, but with a punchline! {emoji}", "Chill, but make it funny! {emoji}",
                        "Chill, but with a giggle! {emoji}", "Chill, but never still! {emoji}"
                    ]},
                }
            },
            "fps": {
                "name": "FPS Shooter",
                "description": "Everything is about guns and shooters.",
                "triggers": {
                    "gg": {"emoji": "trophy", "responses": [
                        "Target down. GG. {emoji}", "Headshot! {emoji}", "Enemy eliminated. {emoji}",
                        "Reload and celebrate! {emoji}", "GG, but keep your finger on the trigger! {emoji}",
                        "You just got a killstreak! {emoji}", "Victory confirmed! {emoji}", "Sniped! {emoji}"
                    ]},
                    "win": {"emoji": "trophy", "responses": [
                        "Victory Royale! {emoji}", "Mission accomplished. {emoji}", "You captured the objective! {emoji}",
                        "You just unlocked a new weapon! {emoji}", "Win secured, move to extraction! {emoji}",
                        "You just got a supply drop! {emoji}", "Win, but stay frosty! {emoji}", "You just unlocked a new camo! {emoji}"
                    ]},
                    "lose": {"emoji": "sob", "responses": [
                        "You got fragged. {emoji}", "Respawn and try again. {emoji}", "Mission failed, we'll get 'em next time. {emoji}",
                        "You dropped your weapon! {emoji}", "Lost the round, but not the war! {emoji}",
                        "You need a better loadout! {emoji}", "You got camped! {emoji}", "Lost, but you still have your squad! {emoji}"
                    ]},
                    "love": {"emoji": "love", "responses": [
                        "Love is my secret weapon. {emoji}", "Deploying care package! {emoji}", "Love is OP! {emoji}",
                        "Love is the best buff! {emoji}", "Love is my favorite attachment! {emoji}",
                        "Love, locked and loaded! {emoji}", "Love is my best killstreak! {emoji}", "Love, but with a silencer! {emoji}"
                    ]},
                    "bruh": {"emoji": "unamused", "responses": [
                        "Bruh, cover me! {emoji}", "Reload your attitude. {emoji}", "Bruh, that's a misfire! {emoji}",
                        "Bruh, you need a better scope! {emoji}", "Bruh, that's a flashbang! {emoji}",
                        "Bruh, you need backup! {emoji}", "Bruh, that's a quickscope! {emoji}", "Bruh, that's a clutch! {emoji}"
                    ]},
                    "chill": {"emoji": "chill", "responses": [
                        "Reloading... chill mode. {emoji}", "Camping in the chill zone. {emoji}", "Chill, but keep your sights up! {emoji}",
                        "Chill, but watch your six! {emoji}", "Chill, but don't drop your guard! {emoji}",
                        "Chill, but keep your finger on the trigger! {emoji}", "Chill, but stay in cover! {emoji}", "Chill, but keep your squad close! {emoji}"
                    ]},
                }
            },
            "peaceful": {
                "name": "Peaceful Gamer",
                "description": "Lofi, Minecraft, cozy games, peaceful vibes.",
                "triggers": {
                    "gg": {"emoji": "happy", "responses": [
                        "Let's build something together! {emoji}", "That was as smooth as a lofi beat. {emoji}",
                        "GG! Let's plant a tree to celebrate! {emoji}", "You just earned a cozy badge! {emoji}",
                        "GG! Let's go fishing in Stardew! {emoji}", "GG! Time for a coffee break! {emoji}",
                        "GG! Let's watch the stars in Mistria! {emoji}", "GG! Let's chill in a sandbox! {emoji}"
                    ]},
                    "win": {"emoji": "trophy", "responses": [
                        "You earned a cup of coffee! {emoji}", "Victory is like a sunrise in Stardew Valley. {emoji}",
                        "Win! Let's relax with some lofi. {emoji}", "You just unlocked a new field in Mistria! {emoji}",
                        "Win! Let's build a cozy cabin! {emoji}", "Win! Let's go mining in Terraria! {emoji}",
                        "Win! Let's brew some tea! {emoji}", "Win! Let's decorate our island! {emoji}"
                    ]},
                    "lose": {"emoji": "sob", "responses": [
                        "It's okay, let's plant some flowers. {emoji}", "Every loss is a new beginning, like a fresh Minecraft world. {emoji}",
                        "Lost? Let's go fishing and relax. {emoji}", "Lost? Let's listen to lofi and chill. {emoji}",
                        "Lost? Let's build something new! {emoji}", "Lost? Let's watch the sunset in Mistria. {emoji}",
                        "Lost? Let's make some coffee! {emoji}", "Lost? Let's go on a peaceful walk! {emoji}"
                    ]},
                    "love": {"emoji": "love", "responses": [
                        "Sending cozy vibes your way! {emoji}", "Love and lofi, that's the way. {emoji}",
                        "Love is like a warm campfire. {emoji}", "Love is the best power-up! {emoji}",
                        "Love, coffee, and cozy games! {emoji}", "Love is a peaceful garden. {emoji}",
                        "Love is a starry night in Mistria. {emoji}", "Love is a new Minecraft world! {emoji}"
                    ]},
                    "bruh": {"emoji": "unamused", "responses": [
                        "Let's take a deep breath and relax. {emoji}", "No worries, let's fish in Terraria. {emoji}",
                        "Bruh, let's build a treehouse! {emoji}", "Bruh, let's go mining! {emoji}",
                        "Bruh, let's listen to lofi! {emoji}", "Bruh, let's plant a garden! {emoji}",
                        "Bruh, let's make some tea! {emoji}", "Bruh, let's watch the stars! {emoji}"
                    ]},
                    "chill": {"emoji": "chill", "responses": [
                        "Chill like a Minecraft river. {emoji}", "Time for a coffee break. {emoji}",
                        "Chill, let's listen to lofi! {emoji}", "Chill, let's build a cozy cabin! {emoji}",
                        "Chill, let's go fishing! {emoji}", "Chill, let's decorate our island! {emoji}",
                        "Chill, let's watch the sunset! {emoji}", "Chill, let's plant some flowers! {emoji}"
                    ]},
                }
            },
        }
        # Default per-server personality
        self.server_personality = {}
        
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

    @app_commands.command(name="personality", description="Configure Ludus's personality and channels")
    @app_commands.describe(personality="Choose Ludus's personality", channels="Optional channels to restrict personality messages to")
    async def personality_slash(self, interaction: discord.Interaction, personality: Optional[str] = None, channels: Optional[str] = None):
        # Only allow server admins to change settings
        if not interaction.guild:
            await interaction.response.send_message("This command must be used in a server.", ephemeral=True)
            return
        member = interaction.guild.get_member(interaction.user.id)
        if not member.guild_permissions.administrator:
            await interaction.response.send_message("You must be a server administrator to change personality settings.", ephemeral=True)
            return

        server_config = self._load_server_config(interaction.guild.id)
        # Set personality if provided
        if personality:
            if personality not in self.personalities:
                await interaction.response.send_message(f"Unknown personality. Available: {', '.join(self.personalities.keys())}", ephemeral=True)
                return
            server_config["personality_type"] = personality
            self.server_personality[interaction.guild.id] = personality
        # Parse channels string like: #general #games or channel ids separated by spaces
        if channels:
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
        self._save_server_config(interaction.guild.id, server_config)
        msg = f"Ludus personality set to: {server_config.get('personality_type', 'default')}\n"
        if server_config.get("personality_channels"):
            ch_mentions = ", ".join(f"<#{c}>" for c in server_config["personality_channels"])
            msg += f"Personality messages enabled in: {ch_mentions}"
        else:
            msg += "Personality messages enabled in all channels."
        await interaction.response.send_message(msg)
    
    @commands.Cog.listener()
    async def on_message(self, message):
        # Ignore bots
        if message.author.bot:
            return
        ctx = await self.bot.get_context(message)
        if ctx.valid:
            return
        if message.guild:
            server_config = self._load_server_config(message.guild.id)
            if not server_config.get("personality_reactions", True):
                return
            allowed_channels = server_config.get("personality_channels", [])
            if allowed_channels and str(message.channel.id) not in allowed_channels:
                return
            if hasattr(message.channel, 'type') and message.channel.type.name in ["news", "forum"]:
                return
            personality = server_config.get("personality_type", "default")
        else:
            personality = "default"
        if not self._check_cooldown(message.author.id):
            return
        content = message.content.lower()
        # Math question detection
        if self._is_math_question(content):
            answer = self._solve_math(content)
            if answer is not None:
                await message.channel.send(f"{answer}")
                return
        # Yes/No/Or question detection
        if self._is_yesno_or_question(content):
            reply = self._answer_yesno_or(content, message.author.id, personality)
            await message.channel.send(reply)
            return
        # Trigger-based responses
        triggers = self.personalities.get(personality, self.personalities["default"]).get("triggers", {})
        for trigger, data in triggers.items():
            if trigger in content:
                if random.random() > 0.5:
                    continue
                emoji = self.ludus_emojis.get(data.get("emoji", "star"), "✨")
                response = random.choice(data["responses"]).format(emoji=emoji)
                if random.random() > 0.7:
                    await message.add_reaction(emoji)
                else:
                    await message.channel.send(response)
                break


    def _is_math_question(self, content):
        # Detects math questions like "what is 2+2", "2 plus 2", "calculate 5 times 3", etc.
        import re
        math_patterns = [
            r"what\s+is\s+([-+*/xX0-9 .]+)",
            r"([-+*/xX0-9 .]+)\s*\?",
            r"calculate\s+([-+*/xX0-9 .]+)",
            r"([-+*/xX0-9 .]+)\s*(plus|minus|times|divided by|\+|-|x|\*|/)\s*([-+*/xX0-9 .]+)",
        ]
        for pat in math_patterns:
            if re.search(pat, content):
                return True
        return False

    def _solve_math(self, content):
        # Extract and solve math expressions
        import re
        # Replace words with symbols
        expr = content.lower()
        expr = expr.replace('plus', '+').replace('minus', '-')
        expr = expr.replace('times', '*').replace('x', '*').replace('divided by', '/').replace('÷', '/')
        # Find numbers and operators
        match = re.search(r"([-+*/. 0-9]+)", expr)
        if not match:
            return None
        expr = match.group(1)
        # Remove extra spaces
        expr = expr.replace(' ', '')
        try:
            # Only allow safe characters
            if not re.match(r"^[0-9+\-*/.]+$", expr):
                return None
            result = eval(expr)
            return f"{result}"
        except Exception:
            return None

    def _is_yesno_or_question(self, content):
        # Detects "Do you ...?", "Are you ...?", "Is it ...?", and 'or' questions
        import re
        # Yes/No: "do you ...?", "are you ...?", "is it ...?", etc.
        if re.match(r"^(do|are|is|did|will|can|could|would|should|have|has|was|were) you .+\?", content):
            return True
        # Or: "Do you like apples or oranges?", "Is it red or blue?"
        if ' or ' in content:
            return True
        return False

    def _answer_yesno_or(self, content, user_id, personality):
        import re
        # Consistent answer per user/personality using hash
        def consistent_choice(options):
            idx = abs(hash(f"{user_id}-{personality}-{content}")) % len(options)
            return options[idx]
        # Or question
        if ' or ' in content:
            parts = re.split(r' or ', content)
            # Try to find the last two options
            if len(parts) >= 2:
                left = parts[-2].split()[-1]
                right = parts[-1].split()[0]
                # If question is "Do you like apples or oranges?" reply with one
                return consistent_choice([left.capitalize(), right.capitalize()])
        # Yes/No question
        yesno = ["Yes.", "No."]
        return consistent_choice(yesno)
    
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
