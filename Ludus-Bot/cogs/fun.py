import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import random

from discord import app_commands
from discord.ui import View, Button
from cogs.minigames import PaginatedHelpView

class Fun(commands.Cog):
    """Fun and random commands!"""

    @app_commands.command(name="funhelp", description="View all fun commands and info (paginated)")
    async def funhelp_slash(self, interaction: discord.Interaction):
        commands_list = []
        for cmd in self.get_commands():
            if not cmd.hidden:
                name = f"/{cmd.name}" if hasattr(cmd, 'app_command') else f"L!{cmd.name}"
                desc = cmd.help or cmd.short_doc or "No description."
                commands_list.append((name, desc))
        category_name = "Fun"
        category_desc = "Fun and random commands! Use the buttons below to see all commands."
        view = PaginatedHelpView(interaction, commands_list, category_name, category_desc)
        await view.send()

    def __init__(self, bot):
        self.bot = bot
        self.session = None

    async def get_session(self):
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session

    async def cog_unload(self):
        if self.session and not self.session.closed:
            await self.session.close()

    @commands.command(name="joke")
    async def random_joke(self, ctx):
        await self._fetch_joke(ctx)

    async def _fetch_joke(self, ctx_or_interaction):
        try:
            session = await self.get_session()
            async with session.get('https://official-joke-api.appspot.com/random_joke') as resp:
                if resp.status == 200:
                    data = await resp.json()
                    setup = data.get('setup', '')
                    punchline = data.get('punchline', '')
                    
                    embed = discord.Embed(
                        title="😄 Random Joke",
                        description=f"{setup}\n\n||{punchline}||",
                        color=discord.Color.gold()
                    )
                    
                    if isinstance(ctx_or_interaction, discord.Interaction):
                        await ctx_or_interaction.followup.send(embed=embed)
                    else:
                        await ctx_or_interaction.send(embed=embed)
                else:
                    msg = "❌ Couldn't fetch a joke right now. Try again later!"
                    if isinstance(ctx_or_interaction, discord.Interaction):
                        await ctx_or_interaction.followup.send(msg)
                    else:
                        await ctx_or_interaction.send(msg)
        except Exception as e:
            print(f"Joke API error: {e}")
            msg = "❌ Error fetching joke!"
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.followup.send(msg)
            else:
                await ctx_or_interaction.send(msg)

    @commands.command(name="dog")
    async def random_dog(self, ctx):
        await self._fetch_dog(ctx)

    async def _fetch_dog(self, ctx_or_interaction):
        try:
            session = await self.get_session()
            async with session.get('https://dog.ceo/api/breeds/image/random') as resp:
                if resp.status == 200:
                    data = await resp.json()
                    image_url = data.get('message', '')
                    
                    embed = discord.Embed(
                        title="🐶 Random Dog",
                        color=discord.Color.orange()
                    )
                    embed.set_image(url=image_url)
                    
                    if isinstance(ctx_or_interaction, discord.Interaction):
                        await ctx_or_interaction.followup.send(embed=embed)
                    else:
                        await ctx_or_interaction.send(embed=embed)
                else:
                    msg = "❌ Couldn't fetch a dog image right now!"
                    if isinstance(ctx_or_interaction, discord.Interaction):
                        await ctx_or_interaction.followup.send(msg)
                    else:
                        await ctx_or_interaction.send(msg)
        except Exception as e:
            print(f"Dog API error: {e}")
            msg = "❌ Error fetching dog image!"
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.followup.send(msg)
            else:
                await ctx_or_interaction.send(msg)

    @commands.command(name="cat")
    async def random_cat(self, ctx):
        await self._fetch_cat(ctx)

    async def _fetch_cat(self, ctx_or_interaction):
        try:
            session = await self.get_session()
            async with session.get('https://api.thecatapi.com/v1/images/search') as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data and len(data) > 0 and 'url' in data[0]:
                        image_url = data[0]['url']
                        
                        embed = discord.Embed(
                            title="🐱 Random Cat",
                            color=discord.Color.blue()
                        )
                        embed.set_image(url=image_url)
                        
                        if isinstance(ctx_or_interaction, discord.Interaction):
                            await ctx_or_interaction.followup.send(embed=embed)
                        else:
                            await ctx_or_interaction.send(embed=embed)
                    else:
                        msg = "❌ Couldn't fetch a cat image right now!"
                        if isinstance(ctx_or_interaction, discord.Interaction):
                            await ctx_or_interaction.followup.send(msg)
                        else:
                            await ctx_or_interaction.send(msg)
                else:
                    msg = "❌ Couldn't fetch a cat image right now!"
                    if isinstance(ctx_or_interaction, discord.Interaction):
                        await ctx_or_interaction.followup.send(msg)
                    else:
                        await ctx_or_interaction.send(msg)
        except Exception as e:
            print(f"Cat API error: {e}")
            msg = "❌ Error fetching cat image!"
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.followup.send(msg)
            else:
                await ctx_or_interaction.send(msg)

    @commands.command(name="duck")
    async def random_duck(self, ctx):
        await self._fetch_duck(ctx)

    async def _fetch_duck(self, ctx_or_interaction):
        try:
            session = await self.get_session()
            async with session.get('https://random-d.uk/api/random') as resp:
                if resp.status == 200:
                    data = await resp.json()
                    image_url = data.get('url', '')
                    
                    embed = discord.Embed(
                        title="🦆 Random Duck",
                        color=discord.Color.yellow()
                    )
                    embed.set_image(url=image_url)
                    
                    if isinstance(ctx_or_interaction, discord.Interaction):
                        await ctx_or_interaction.followup.send(embed=embed)
                    else:
                        await ctx_or_interaction.send(embed=embed)
                else:
                    msg = "❌ Couldn't fetch a duck image right now!"
                    if isinstance(ctx_or_interaction, discord.Interaction):
                        await ctx_or_interaction.followup.send(msg)
                    else:
                        await ctx_or_interaction.send(msg)
        except Exception as e:
            print(f"Duck API error: {e}")
            msg = "❌ Error fetching duck image!"
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.followup.send(msg)
            else:
                await ctx_or_interaction.send(msg)

    @commands.command(name="panda")
    async def random_panda(self, ctx):
        await self._fetch_panda(ctx)

    async def _fetch_panda(self, ctx_or_interaction):
        try:
            session = await self.get_session()
            async with session.get('https://some-random-api.com/animal/panda') as resp:
                if resp.status == 200:
                    data = await resp.json()
                    image_url = data.get('image', '')
                    fact = data.get('fact', 'No fact available')
                    
                    embed = discord.Embed(
                        title="🐼 Random Panda",
                        description=f"**Fun Fact:** {fact}",
                        color=discord.Color.green()
                    )
                    embed.set_image(url=image_url)
                    
                    if isinstance(ctx_or_interaction, discord.Interaction):
                        await ctx_or_interaction.followup.send(embed=embed)
                    else:
                        await ctx_or_interaction.send(embed=embed)
                else:
                    msg = "❌ Couldn't fetch a panda image right now!"
                    if isinstance(ctx_or_interaction, discord.Interaction):
                        await ctx_or_interaction.followup.send(msg)
                    else:
                        await ctx_or_interaction.send(msg)
        except Exception as e:
            print(f"Panda API error: {e}")
            msg = "❌ Error fetching panda image!"
            if isinstance(ctx_or_interaction, discord.Interaction):
                await ctx_or_interaction.followup.send(msg)
            else:
                await ctx_or_interaction.send(msg)

async def setup(bot):
    await bot.add_cog(Fun(bot))
