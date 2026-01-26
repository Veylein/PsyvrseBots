import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import random
import shlex
from typing import Optional

class Meme(commands.Cog):
    """Meme Generator - Create custom memes with popular templates!"""
    
    def __init__(self, bot):
        self.bot = bot
        
        # Popular meme templates (Imgflip API IDs)
        self.templates = {
            "drake": {"id": 181913649, "name": "Drake Hotline Bling", "boxes": 2},
            "distracted": {"id": 112126428, "name": "Distracted Boyfriend", "boxes": 3},
            "twobuttons": {"id": 87743020, "name": "Two Buttons", "boxes": 3},
            "exitramp": {"id": 124822590, "name": "Left Exit 12 Off Ramp", "boxes": 3},
            "brain": {"id": 93895088, "name": "Expanding Brain", "boxes": 4},
            "scroll": {"id": 101511, "name": "Ancient Aliens", "boxes": 2},
            "think": {"id": 89370399, "name": "Roll Safe Think About It", "boxes": 2},
            "change": {"id": 129242436, "name": "Change My Mind", "boxes": 2},
            "woman": {"id": 188390779, "name": "Woman Yelling At Cat", "boxes": 2},
            "stonks": {"id": 178591752, "name": "Stonks", "boxes": 1},
            "panik": {"id": 217743513, "name": "Panik Kalm Panik", "boxes": 3},
            "bernie": {"id": 222403160, "name": "Bernie I Am Once Again Asking", "boxes": 2},
            "spiderman": {"id": 101288, "name": "Spiderman Pointing", "boxes": 2},
            "buttons": {"id": 131940431, "name": "Gru's Plan", "boxes": 4},
            "disaster": {"id": 97984, "name": "Disaster Girl", "boxes": 2},
            "success": {"id": 61544, "name": "Success Kid", "boxes": 2},
            "doge": {"id": 8072285, "name": "Doge", "boxes": 2},
            "surprised": {"id": 155067746, "name": "Surprised Pikachu", "boxes": 1},
            "uno": {"id": 217743513, "name": "UNO Draw 25", "boxes": 2},
            "trade": {"id": 89655, "name": "Trade Offer", "boxes": 3}
        }
    
    @commands.command(name="meme")
    async def meme_prefix(self, ctx, template: str, *, texts: str):
        """Create a meme (prefix version). Usage: L!meme drake "Top text" "Bottom text" """
        # Parse quoted texts
        try:
            text_list = shlex.split(texts)
        except:
            text_list = texts.split("|")  # Fallback to | separator
        
        # Pad with None
        text1 = text_list[0] if len(text_list) > 0 else None
        text2 = text_list[1] if len(text_list) > 1 else None
        text3 = text_list[2] if len(text_list) > 2 else None
        text4 = text_list[3] if len(text_list) > 3 else None
        
        if not text1:
            await ctx.send("❌ Usage: `L!meme <template> \"text1\" \"text2\" ...`\nExample: `L!meme drake \"Old way\" \"New way\"`\nUse `L!memelist` to see templates!")
            return
        
        await self._generate_meme(template, text1, text2, text3, text4, ctx=ctx)
        # Update most played games
        profile_cog = self.bot.get_cog("Profile")
        if profile_cog and hasattr(profile_cog, "profile_manager"):
            profile_cog.profile_manager.record_game_played(ctx.author.id, "meme")
    
    @app_commands.command(name="meme", description="Create a custom meme!")
    @app_commands.describe(
        template="Meme template to use",
        text1="Top text / First text box",
        text2="Bottom text / Second text box (optional)",
        text3="Third text box (optional)",
        text4="Fourth text box (optional)"
    )
    @app_commands.choices(template=[
        app_commands.Choice(name="Drake Hotline Bling", value="drake"),
        app_commands.Choice(name="Distracted Boyfriend", value="distracted"),
        app_commands.Choice(name="Two Buttons", value="twobuttons"),
        app_commands.Choice(name="Left Exit 12 Off Ramp", value="exitramp"),
        app_commands.Choice(name="Expanding Brain", value="brain"),
        app_commands.Choice(name="Ancient Aliens", value="scroll"),
        app_commands.Choice(name="Roll Safe Think About It", value="think"),
        app_commands.Choice(name="Change My Mind", value="change"),
        app_commands.Choice(name="Woman Yelling At Cat", value="woman"),
        app_commands.Choice(name="Stonks", value="stonks"),
        app_commands.Choice(name="Panik Kalm Panik", value="panik"),
        app_commands.Choice(name="Bernie I Am Once Again Asking", value="bernie"),
        app_commands.Choice(name="Spiderman Pointing", value="spiderman"),
        app_commands.Choice(name="Gru's Plan", value="buttons"),
        app_commands.Choice(name="Disaster Girl", value="disaster"),
        app_commands.Choice(name="Success Kid", value="success"),
        app_commands.Choice(name="Doge", value="doge"),
        app_commands.Choice(name="Surprised Pikachu", value="surprised"),
        app_commands.Choice(name="UNO Draw 25", value="uno"),
        app_commands.Choice(name="Trade Offer", value="trade")
    ])
    async def meme_slash(
        self, 
        interaction: discord.Interaction, 
        template: str,
        text1: str,
        text2: Optional[str] = None,
        text3: Optional[str] = None,
        text4: Optional[str] = None
    ):
        """Generate a meme using Imgflip API (slash version)"""
        await interaction.response.defer()
        await self._generate_meme(template, text1, text2, text3, text4, interaction=interaction)
        # Update most played games
        profile_cog = self.bot.get_cog("Profile")
        if profile_cog and hasattr(profile_cog, "profile_manager"):
            profile_cog.profile_manager.record_game_played(interaction.user.id, "meme")
    
    async def _generate_meme(self, template, text1, text2=None, text3=None, text4=None, ctx=None, interaction=None):
        """Shared meme generation logic"""
        
        if template not in self.templates:
            msg = "❌ Invalid meme template!"
            if interaction:
                await interaction.followup.send(msg, ephemeral=True)
            else:
                await ctx.send(msg)
            return
        
        template_data = self.templates[template]
        template_id = template_data["id"]
        
        # Prepare text boxes
        texts = [text1]
        if text2:
            texts.append(text2)
        if text3:
            texts.append(text3)
        if text4:
            texts.append(text4)
        
        # Check if enough text boxes provided
        if len(texts) < template_data["boxes"]:
            msg = f"❌ This template requires {template_data['boxes']} text boxes!\nYou provided {len(texts)}."
            if interaction:
                await interaction.followup.send(msg, ephemeral=True)
            else:
                await ctx.send(msg)
            return
        
        # Generate meme using Imgflip API
        try:
            url = "https://api.imgflip.com/caption_image"
            
            # Build text box parameters
            params = {
                "template_id": template_id,
                "username": "imgflip_hubot",
                "password": "imgflip_hubot"
            }
            
            # Add text boxes
            for i, text in enumerate(texts):
                params[f"boxes[{i}][text]"] = text
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, data=params) as response:
                    data = await response.json()
                    
                    if not data.get("success"):
                        msg = f"❌ Failed to generate meme: {data.get('error_message', 'Unknown error')}"
                        if interaction:
                            await interaction.followup.send(msg, ephemeral=True)
                        else:
                            await ctx.send(msg)
                        return
                    
                    meme_url = data["data"]["url"]
                    
                    embed = discord.Embed(
                        title=f"🎭 {template_data['name']}",
                        color=discord.Color.blue()
                    )
                    embed.set_image(url=meme_url)
                    
                    if interaction:
                        embed.set_footer(text=f"Created by {interaction.user.display_name}")
                        await interaction.followup.send(embed=embed)
                    else:
                        embed.set_footer(text=f"Created by {ctx.author.display_name}")
                        await ctx.send(embed=embed)
        
        except Exception as e:
            msg = f"❌ Error generating meme: {str(e)}"
            if interaction:
                await interaction.followup.send(msg, ephemeral=True)
            else:
                await ctx.send(msg)
    
    @commands.command(name="randommeme")
    async def randommeme_prefix(self, ctx):
        """Get a random meme from Reddit (prefix version)"""
        await self._fetch_random_meme(ctx=ctx)
        # Update most played games
        profile_cog = self.bot.get_cog("Profile")
        if profile_cog and hasattr(profile_cog, "profile_manager"):
            profile_cog.profile_manager.record_game_played(ctx.author.id, "randommeme")
    
    @app_commands.command(name="randommeme", description="Get a random meme from Reddit!")
    async def randommeme_slash(self, interaction: discord.Interaction):
        """Fetch a random meme from Reddit (slash version)"""
        await interaction.response.defer()
        await self._fetch_random_meme(interaction=interaction)
        # Update most played games
        profile_cog = self.bot.get_cog("Profile")
        if profile_cog and hasattr(profile_cog, "profile_manager"):
            profile_cog.profile_manager.record_game_played(interaction.user.id, "randommeme")
    
    async def _fetch_random_meme(self, ctx=None, interaction=None):
        """Shared random meme fetching logic"""
        
        subreddits = [
            "memes",
            "dankmemes", 
            "wholesomememes",
            "me_irl",
            "AdviceAnimals",
            "MemeEconomy"
        ]
        
        try:
            subreddit = random.choice(subreddits)
            url = f"https://www.reddit.com/r/{subreddit}/random/.json"
            
            headers = {
                "User-Agent": "Discord Bot Meme Fetcher 1.0"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status != 200:
                        msg = "❌ Failed to fetch meme from Reddit!"
                        if interaction:
                            await interaction.followup.send(msg, ephemeral=True)
                        else:
                            await ctx.send(msg)
                        return
                    
                    data = await response.json()
                    
                    # Reddit returns array with post data
                    if not data or len(data) == 0:
                        msg = "❌ No meme found!"
                        if interaction:
                            await interaction.followup.send(msg, ephemeral=True)
                        else:
                            await ctx.send(msg)
                        return
                    
                    post = data[0]["data"]["children"][0]["data"]
                    
                    # Check if it's an image post
                    if not post.get("url") or not any(post["url"].endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif']):
                        # Try again with another random meme
                        msg = "🔄 That wasn't an image, trying again..."
                        if interaction:
                            await interaction.followup.send(msg, ephemeral=True)
                        else:
                            await ctx.send(msg)
                        return await self._fetch_random_meme(ctx=ctx, interaction=interaction)
                    
                    embed = discord.Embed(
                        title=post["title"][:256],
                        url=f"https://reddit.com{post['permalink']}",
                        color=discord.Color.orange()
                    )
                    embed.set_image(url=post["url"])
                    embed.set_footer(text=f"👍 {post['ups']:,} upvotes • r/{subreddit}")
                    
                    if interaction:
                        await interaction.followup.send(embed=embed)
                    else:
                        await ctx.send(embed=embed)
        
        except Exception as e:
            msg = f"❌ Error fetching meme: {str(e)}"
            if interaction:
                await interaction.followup.send(msg, ephemeral=True)
            else:
                await ctx.send(msg)
    
    @commands.command(name="memelist")
    async def memelist_prefix(self, ctx):
        """List all available meme templates (prefix version)"""
        await self._show_memelist(ctx=ctx)
    
    @app_commands.command(name="memelist", description="View all available meme templates!")
    async def memelist_slash(self, interaction: discord.Interaction):
        """List all available meme templates (slash version)"""
        await self._show_memelist(interaction=interaction)
    
    async def _show_memelist(self, ctx=None, interaction=None):
        """Shared memelist logic"""
        embed = discord.Embed(
            title="🎭 Available Meme Templates",
            description="Use `/meme template:[name]` to create a meme!\n\n",
            color=discord.Color.blue()
        )
        
        # Group templates by text box count
        by_boxes = {}
        for key, template in self.templates.items():
            boxes = template["boxes"]
            if boxes not in by_boxes:
                by_boxes[boxes] = []
            by_boxes[boxes].append(f"• **{template['name']}** (`{key}`)")
        
        # Add fields by text box requirement
        for box_count in sorted(by_boxes.keys()):
            template_list = "\n".join(by_boxes[box_count])
            embed.add_field(
                name=f"{box_count} Text Box{'es' if box_count > 1 else ''}",
                value=template_list,
                inline=False
            )
        
        embed.set_footer(text="💡 Tip: Use /randommeme for memes from Reddit!")
        
        if interaction:
            await interaction.response.send_message(embed=embed)
        else:
            await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Meme(bot))
