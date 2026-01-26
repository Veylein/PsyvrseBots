import discord
from discord.ext import commands
from discord import app_commands
import random
from typing import Optional

class Actions(commands.Cog):
    """Fun action commands with GIF responses"""
    
    def __init__(self, bot):
        self.bot = bot
        
        # Action GIF databases
        self.gifs = {
            "slap": [
                "[⠀](https://tenor.com/view/orange-cat-cat-hitting-cat-cat-punching-cat-cat-slapping-cat-orange-cat-hitting-cat-gif-6585435513579432745)",
                "[⠀](https://tenor.com/view/penguin-slap-gif-5263949288532448516)",
                "[⠀](https://tenor.com/view/peach-goma-peach-and-goma-peach-peach-cat-slap-gif-26865200)",
                "[⠀](https://tenor.com/view/slap-slaps-enough-stop-stop-it-gif-13025908752997150429)",
                "[⠀](https://tenor.com/view/gap-slapped-knock-out-punch-gif-5122019)",
                "[⠀](https://tenor.com/view/slap-christmas-gif-24241359)",
                "[⠀](https://tenor.com/view/blu-zushi-black-and-white-emotes-gif-13851867247344432124)",
                "[⠀](https://tenor.com/view/shut-up-stfu-shut-your-mouth-slap-slapping-gif-8050553153066707611)",
                "[⠀](https://tenor.com/view/dungeong-gif-3654754744145897317)",
                "[⠀](https://tenor.com/view/slap-gif-20040176)"
            ],
            "punch": [
                "[⠀](https://tenor.com/view/meme-memes-memes2022funny-meme-face-punch-gif-25436787)",
                "[⠀](https://tenor.com/view/james-harden-throat-punch-gif-12838513952671974033)",
                "[⠀](https://tenor.com/view/cat-kitten-cat-meme-smack-hit-gif-14682331153624420698)",
                "[⠀](https://tenor.com/view/cat-punch-gif-16287607886277446870)",
                "[⠀](https://tenor.com/view/spy-family-spy-x-family-anya-cute-punch-gif-25751847)",
                "[⠀](https://tenor.com/view/weliton-amogos-arzkeir-jujutsu-kaisen-panda-gif-20161414)",
                "[⠀](https://tenor.com/view/boxing-tom-and-jerry-jerry-tom-punched-gif-14995820)",
                "[⠀](https://tenor.com/view/mortal-kombat-punch-shoot-video-game-gameplay-gif-17639183)",
                "[⠀](https://tenor.com/view/hook-hajime-no-ippo-kimura-boxing-gif-25832371)",
                "[⠀](https://tenor.com/view/funny-animals-cats-dogs-animal-attacks-monday-gif-11541288)"
            ],
            "kick": [
                "[ ](https://tenor.com/view/oh-yeah-high-kick-take-down-fight-gif-14272509)",
                "[ ](https://tenor.com/view/kickers-caught-gif-7775692)",
                "[ ](https://tenor.com/view/asdf-movie-punt-kick-donewiththis-gif-26537188)",
                "[ ](https://tenor.com/view/milk-and-mocha-bear-couple-bear-hug-kick-shut-up-gif-17443923)",
                "[ ](https://tenor.com/view/jaiden-jaiden-animations-jaiden-animations-meme-jaiden-animations-funny-kick-gif-12292976194770112705)",
                "[ ](https://tenor.com/view/wildfireuv-gif-26419033)",
                "[ ](https://tenor.com/view/kick-yeet-gtfo-kick-cliff-push-cliff-gif-9944415665032080774)",
                "[ ](https://tenor.com/view/asdf-movie-punt-kick-donewithus-gif-2178263242676691188)",
                "[ ](https://tenor.com/view/green-power-ranger-mmpr-kick-gif-20786021)",
                "[ ](https://tenor.com/view/dropkick-fight-wow-birdflu-gif-6203301)"
            ],
            "kiss": [
                "https://i.imgur.com/uc0nRah.gif",
                "https://i.imgur.com/C4eJlFX.gif",
                "https://i.imgur.com/xFLRiK8.gif",
                "https://i.imgur.com/TcGgKVE.gif",
                "https://i.imgur.com/HKRBpe8.gif",
                "https://i.imgur.com/7lRZ1TQ.gif",
                "https://i.imgur.com/SLM2nk7.gif",
                "https://i.imgur.com/FOr5bMW.gif",
                "https://i.imgur.com/P5FjQwH.gif",
                "https://i.imgur.com/M7R6wjn.gif"
            ],
            "dance": [
                "https://i.imgur.com/xI8xWFj.gif",
                "https://i.imgur.com/pN8O9N0.gif",
                "https://i.imgur.com/0ixfQrZ.gif",
                "https://i.imgur.com/K0naZ7x.gif",
                "https://i.imgur.com/j8dwqkH.gif",
                "https://i.imgur.com/ixPIrXL.gif",
                "https://i.imgur.com/VbGkJZy.gif",
                "https://i.imgur.com/q9gP4XA.gif",
                "https://i.imgur.com/QfqSbCJ.gif",
                "https://i.imgur.com/KZ0fMzS.gif"
            ],
            "stab": [
                "https://i.imgur.com/VsFUdJR.gif",
                "https://i.imgur.com/U5T0YZG.gif",
                "https://i.imgur.com/bEiLTCd.gif",
                "https://i.imgur.com/ZgxXt4D.gif",
                "https://i.imgur.com/NqBEP0m.gif",
                "https://i.imgur.com/8UJUV0u.gif",
                "https://i.imgur.com/r89utzJ.gif",
                "https://i.imgur.com/0qO8BPl.gif",
                "https://i.imgur.com/1HqO4hC.gif",
                "https://i.imgur.com/J8yM2XP.gif"
            ],
            "shoot": [
                "https://i.imgur.com/TKzRfUy.gif",
                "https://i.imgur.com/UeCDLRD.gif",
                "https://i.imgur.com/GvpO8fX.gif",
                "https://i.imgur.com/fmYEi2t.gif",
                "https://i.imgur.com/PvQPg2Y.gif",
                "https://i.imgur.com/ZdIxBSl.gif",
                "https://i.imgur.com/u3NQMXE.gif",
                "https://i.imgur.com/h0n7TBo.gif",
                "https://i.imgur.com/nzZxHkR.gif",
                "https://i.imgur.com/qvkGKfz.gif"
            ]
        }
        
        # Custom messages for each action
        self.messages = {
            "slap": [
                "{author} slapped {target}! That's gotta hurt! 🤚",
                "{author} just delivered a massive slap to {target}! 💥",
                "*SLAP!* {author} hits {target} right across the face!",
                "{author} slaps {target} into next week! 😤",
                "{target} just got slapped by {author}! Ouch!",
                "{author} winds up and SLAPS {target}! 🌪️",
                "POW! {author} slaps {target} silly!",
                "{author} slaps some sense into {target}! 👋",
                "{target} felt the wrath of {author}'s slap!",
                "That slap from {author} echoed! {target} won't forget that!"
            ],
            "punch": [
                "{author} punched {target} straight in the face! 👊",
                "BAM! {author} lands a solid punch on {target}!",
                "{author} throws a haymaker at {target}! 💪",
                "{target} just got rocked by {author}'s punch!",
                "{author} delivers a devastating punch to {target}! 💥",
                "K.O.! {author} punches {target} into orbit!",
                "{author} channels their inner boxer and punches {target}!",
                "WHAM! {author}'s punch connects with {target}!",
                "{author} unleashes a powerful punch on {target}! 🥊",
                "{target} didn't see that punch from {author} coming!"
            ],
            "kick": [
                "{author} kicked {target} right in the shin! 🦵",
                "BOOM! {author} delivers a flying kick to {target}!",
                "{author} roundhouse kicks {target} into oblivion!",
                "{target} just got kicked by {author}! That hurt!",
                "{author} channels their martial arts and kicks {target}! 🥋",
                "POW! {author}'s kick sends {target} flying!",
                "{author} gives {target} a taste of their boot! 👢",
                "Sparta kick! {author} boots {target} away!",
                "{author} delivers a devastating kick to {target}! 💥",
                "{target} felt the full force of {author}'s kick!"
            ],
            "kiss": [
                "{author} kissed {target}! How sweet! 💋",
                "Aww! {author} gives {target} a cute kiss! 😘",
                "{author} plants a kiss on {target}! Adorable! 💕",
                "{target} just received a kiss from {author}! ❤️",
                "*smooch!* {author} kisses {target}! 😍",
                "{author} shows some love and kisses {target}! 💖",
                "How romantic! {author} kisses {target}!",
                "{author} blows a kiss to {target}! 😚",
                "{target} is blushing from {author}'s kiss! 😊",
                "{author} and {target} share a sweet moment! 💗"
            ],
            "dance": [
                "{author} is dancing with {target}! 💃🕺",
                "{author} and {target} are busting moves together! 🎵",
                "Look at {author} and {target} dance! They've got rhythm!",
                "{author} invites {target} to dance! How fun! 🎶",
                "{author} and {target} are tearing up the dance floor!",
                "Dance party! {author} is grooving with {target}! 🪩",
                "{author} shows {target} their best dance moves!",
                "{author} and {target} are dancing the night away! ✨",
                "Someone call the dance police! {author} and {target} are too good!",
                "{author} spins {target} around on the dance floor! 🌟"
            ],
            "stab": [
                "{author} stabbed {target}! Call the medic! 🔪",
                "*STAB!* {author} attacks {target} with a blade!",
                "{author} just shanked {target}! Brutal! 😱",
                "{target} didn't see that stab from {author} coming!",
                "{author} goes full assassin mode on {target}! 🗡️",
                "Critical hit! {author} stabs {target}!",
                "{author} backstabs {target}! That's cold! 💀",
                "{target} has been stabbed by {author}! Ouch!",
                "{author} delivers a swift stab to {target}!",
                "Stealth attack! {author} stabs {target}! 🥷"
            ],
            "shoot": [
                "{author} shot {target}! Pew pew! 🔫",
                "BANG! {author} fires at {target}!",
                "{author} pulls the trigger on {target}! 💥",
                "{target} just got shot by {author}! Duck!",
                "{author} aims and shoots {target}! Headshot! 🎯",
                "Gunslinger {author} shoots {target}!",
                "{author} goes full action hero and shoots {target}!",
                "POW POW! {author} unloads on {target}!",
                "{author} channels their inner cowboy and shoots {target}! 🤠",
                "{target} is in the crosshairs of {author}! BANG!"
            ]
        }
    
    @commands.command(name="slap")
    async def slap(self, ctx, target: discord.Member = None):
        """Slap someone!"""
        if target is None:
            await ctx.send("❌ You need to mention someone to slap! Usage: `L!slap @user`")
            return
        
        if target.id == ctx.author.id:
            await ctx.send("🤔 Why would you slap yourself? Here, have a hug instead! 🤗")
            return
        
        # Get random message and GIF
        message = random.choice(self.messages["slap"]).format(author=ctx.author.mention, target=target.mention)
        gif = random.choice(self.gifs["slap"])
        
        # Send as regular message so Discord auto-embeds the GIF
        await ctx.send(f"{message}\n{gif}")
    
    @commands.command(name="punch")
    async def punch(self, ctx, target: discord.Member = None):
        """Punch someone!"""
        if target is None:
            await ctx.send("❌ You need to mention someone to punch! Usage: `L!punch @user`")
            return
        
        if target.id == ctx.author.id:
            await ctx.send("😅 Punching yourself? That's just silly! Maybe try a workout instead? 💪")
            return
        
        message = random.choice(self.messages["punch"]).format(author=ctx.author.mention, target=target.mention)
        gif = random.choice(self.gifs["punch"])
        
        # Send as regular message so Discord auto-embeds the GIF
        await ctx.send(f"{message}\n{gif}")
    
    @commands.command(name="kick")
    async def kick(self, ctx, target: discord.Member = None):
        """Kick someone!"""
        if target is None:
            await ctx.send("❌ You need to mention someone to kick! Usage: `L!kick @user`")
            return
        
        if target.id == ctx.author.id:
            await ctx.send("🦵 Kicking yourself? That's some impressive flexibility! 🤸")
            return
        
        message = random.choice(self.messages["kick"]).format(author=ctx.author.mention, target=target.mention)
        gif = random.choice(self.gifs["kick"])
        
        # Send as regular message so Discord auto-embeds the GIF
        await ctx.send(f"{message}\n{gif}")
    
    @commands.command(name="kiss")
    async def kiss(self, ctx, target: discord.Member = None):
        """Kiss someone!"""
        if target is None:
            await ctx.send("❌ You need to mention someone to kiss! Usage: `L!kiss @user`")
            return
        
        if target.id == ctx.author.id:
            await ctx.send("😘 Kissing yourself? Self-love is important! 💖")
            return
        
        message = random.choice(self.messages["kiss"]).format(author=ctx.author.mention, target=target.mention)
        gif = random.choice(self.gifs["kiss"])
        
        # Send as regular message so Discord auto-embeds the GIF
        await ctx.send(f"{message}\n{gif}")
    
    @commands.command(name="dance")
    async def dance(self, ctx, target: discord.Member = None):
        """Dance with someone!"""
        if target is None:
            await ctx.send("❌ You need to mention someone to dance with! Usage: `L!dance @user`")
            return
        
        if target.id == ctx.author.id:
            await ctx.send("🕺 Dancing solo! You've got the moves! 💃")
            return
        
        message = random.choice(self.messages["dance"]).format(author=ctx.author.mention, target=target.mention)
        gif = random.choice(self.gifs["dance"])
        
        # Send as regular message so Discord auto-embeds the GIF
        await ctx.send(f"{message}\n{gif}")
    
    @commands.command(name="stab")
    async def stab(self, ctx, target: discord.Member = None):
        """Stab someone! (Don't worry, it's just virtual)"""
        if target is None:
            await ctx.send("❌ You need to mention someone to stab! Usage: `L!stab @user`")
            return
        
        if target.id == ctx.author.id:
            await ctx.send("🔪 Stabbing yourself?! Someone get this person some help! 🆘")
            return
        
        message = random.choice(self.messages["stab"]).format(author=ctx.author.mention, target=target.mention)
        gif = random.choice(self.gifs["stab"])
        
        # Send as regular message so Discord auto-embeds the GIF
        await ctx.send(f"{message}\n{gif}")
    
    @commands.command(name="shoot")
    async def shoot(self, ctx, target: discord.Member = None):
        """Shoot someone! (It's all fun and games)"""
        if target is None:
            await ctx.send("❌ You need to mention someone to shoot! Usage: `L!shoot @user`")
            return
        
        if target.id == ctx.author.id:
            await ctx.send("🔫 Shooting yourself? That's not very wise... 😅")
            return
        
        message = random.choice(self.messages["shoot"]).format(author=ctx.author.mention, target=target.mention)
        gif = random.choice(self.gifs["shoot"])
        
        # Send as regular message so Discord auto-embeds the GIF
        await ctx.send(f"{message}\n{gif}")

async def setup(bot):
    await bot.add_cog(Actions(bot))
