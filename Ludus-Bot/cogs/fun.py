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

    @app_commands.command(name="8ball", description="Ask the magic 8-ball a yes/no question")
    @app_commands.describe(question="Your yes/no question")
    async def eightball_slash(self, interaction: discord.Interaction, question: str):
        responses = [
            "🎱 It is certain.", "🎱 It is decidedly so.", "🎱 Without a doubt.",
            "🎱 Yes, definitely.", "🎱 You may rely on it.", "🎱 As I see it, yes.",
            "🎱 Most likely.", "🎱 Outlook good.", "🎱 Yes.", "🎱 Signs point to yes.",
            "🎱 Reply hazy, try again.", "🎱 Ask again later.",
            "🎱 Better not tell you now.", "🎱 Cannot predict now.",
            "🎱 Concentrate and ask again.", "🎱 Don't count on it.",
            "🎱 My reply is no.", "🎱 My sources say no.",
            "🎱 Outlook not so good.", "🎱 Very doubtful.",
        ]
        answer = random.choice(responses)
        embed = discord.Embed(
            title="🎱 Magic 8-Ball",
            description=f"**Q:** {question}\n\n**A:** {answer}",
            color=discord.Color.dark_gray(),
        )
        ask_again = discord.ui.Button(label="🎱 Ask Again", style=discord.ButtonStyle.primary)

        class AskAgainView(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=120)

            @discord.ui.button(label="🎱 Ask Again", style=discord.ButtonStyle.primary)
            async def ask_again_btn(self, inter: discord.Interaction, button: discord.ui.Button):
                await inter.response.send_modal(_8BallFollowModal(inter))

        class _8BallFollowModal(discord.ui.Modal, title="🎱 Magic 8-Ball"):
            def __init__(self, orig: discord.Interaction):
                super().__init__()
                self._orig = orig
                self.question_input = discord.ui.TextInput(
                    label="Your question", placeholder="Will I pass my exam?", max_length=200
                )
                self.add_item(self.question_input)

            async def on_submit(self, inter: discord.Interaction):
                ans = random.choice(responses)
                em = discord.Embed(
                    title="🎱 Magic 8-Ball",
                    description=f"**Q:** {self.question_input.value.strip()}\n\n**A:** {ans}",
                    color=discord.Color.dark_gray(),
                )
                await inter.response.send_message(embed=em, view=AskAgainView())

        await interaction.response.send_message(embed=embed, view=AskAgainView())

    @app_commands.command(name="tarot", description="Draw 3 tarot cards for a past/present/future reading")
    async def tarot_slash(self, interaction: discord.Interaction):
        cards = [
            ("0 — The Fool", "🌬️", "New beginnings, innocence, spontaneity."),
            ("I — The Magician", "✨", "Manifestation, resourcefulness, power."),
            ("II — The High Priestess", "🌙", "Intuition, sacred knowledge, the subconscious."),
            ("III — The Empress", "🌿", "Femininity, beauty, nurturing, abundance."),
            ("IV — The Emperor", "🏰", "Authority, establishment, structure."),
            ("V — The Hierophant", "⛪", "Spiritual wisdom, tradition, conformity."),
            ("VI — The Lovers", "💞", "Love, harmony, relationships, choices."),
            ("VII — The Chariot", "⚔️", "Control, willpower, success, determination."),
            ("VIII — Strength", "🦁", "Strength, courage, compassion."),
            ("IX — The Hermit", "🕯️", "Soul-searching, introspection, inner guidance."),
            ("X — Wheel of Fortune", "☸️", "Good luck, karma, destiny, a turning point."),
            ("XI — Justice", "⚖️", "Justice, fairness, truth, cause and effect."),
            ("XII — The Hanged Man", "🌀", "Pause, surrender, new perspectives."),
            ("XIII — Death", "🌑", "Endings, change, transformation, transition."),
            ("XIV — Temperance", "🌊", "Balance, moderation, patience, purpose."),
            ("XVI — The Tower", "⚡", "Sudden change, upheaval, revelation."),
            ("XVII — The Star", "⭐", "Hope, faith, renewal, spirituality."),
            ("XVIII — The Moon", "🌛", "Illusion, fear, intuition, the unconscious."),
            ("XIX — The Sun", "☀️", "Positivity, warmth, success, vitality."),
            ("XXI — The World", "🌍", "Completion, accomplishment, travel."),
            ("Ace of Wands", "🔥", "Inspiration, new opportunities, growth."),
            ("Two of Wands", "🌟", "Planning, decisions, discovery."),
            ("Three of Wands", "🚢", "Progress, expansion, foresight."),
            ("Four of Wands", "🏡", "Celebration, harmony, home, community."),
            ("Five of Wands", "⚔️", "Conflict, competition, tension."),
            ("Six of Wands", "🏆", "Victory, success, public recognition."),
            ("Seven of Wands", "🛡️", "Challenge, competition, perseverance."),
            ("Eight of Wands", "💨", "Movement, fast-paced change, action."),
            ("Nine of Wands", "🧱", "Resilience, courage, persistence."),
            ("Ten of Wands", "🌪️", "Burden, responsibility, hard work."),
            ("Page of Wands", "📜", "Exploration, excitement, freedom."),
            ("Knight of Wands", "🏇", "Energy, passion, adventure."),
            ("King of Wands", "👑", "Natural leader, vision, entrepreneur."),
            ("Queen of Wands", "🌻", "Courage, confidence, independence."),
            ("Ace of Cups", "💧", "Love, new relationships, compassion."),
            ("Two of Cups", "💕", "Unified love, partnership, mutual attraction."),
            ("Three of Cups", "🥂", "Celebration, friendship, creativity."),
            ("Four of Cups", "☁️", "Apathy, contemplation, disconnectedness."),
            ("Five of Cups", "😢", "Loss, regret, disappointment, despair."),
            ("Six of Cups", "🌸", "Reunion, nostalgia, childhood memories."),
            ("Seven of Cups", "🍭", "Opportunities, choices, wishful thinking."),
            ("Eight of Cups", "🚶", "Disappointment, abandonment, withdrawal."),
            ("Nine of Cups", "🍷", "Contentment, satisfaction, gratitude."),
            ("Ten of Cups", "🌈", "Divine love, blissful relationships, harmony."),
            ("Page of Cups", "📖", "Creative opportunities, curiosity, possibility."),
            ("Knight of Cups", "🏹", "Romance, charm, 'knight in shining armor'."),
            ("Queen of Cups", "🌊", "Emotional balance, intuition, compassion."),
            ("King of Cups", "🌊", "Emotional balance, generosity, compassion."),
            ("Ace of Swords", "⚔️", "Breakthroughs, new ideas, mental clarity."),
            ("Two of Swords", "⚔️", "Difficult decisions, weighing options, stalemate."),
            ("Three of Swords", "💔", "Heartbreak, emotional pain, sorrow."),
            ("Four of Swords", "🛌", "Rest, recovery, contemplation."),
            ("Five of Swords", "⚔️", "Conflict, tension, loss, defeat."),
            ("Six of Swords", "🛶", "Transition, change, rite of passage."),
            ("Seven of Swords", "🗡️", "Deception, trickery, strategy, tactics."),
            ("Eight of Swords", "🔒", "Imprisonment, entrapment, self-victimization."),
            ("Nine of Swords", "😱", "Anxiety, worry, fear, nightmares."),
            ("Ten of Swords", "⚔️", "Betrayal, backstabbing, defeat, crisis."),
            ("Page of Swords", "📜", "New ideas, curiosity, thirst for knowledge."),
            ("Knight of Swords", "🏇", "Action, impulsiveness, defending beliefs."),
            ("King of Swords", "👑", "Mental clarity, intellectual power, authority."),
            ("Queen of Swords", "🗡️", "Clarity, truth, directness, independence."),
            ("Ace of Pentacles", "🪙", "New beginnings, prosperity, opportunity."),
            ("Two of Pentacles", "⚖️", "Balance, adaptability, time management."),
            ("Three of Pentacles", "🔨", "Collaboration, skill, teamwork."),
            ("Four of Pentacles", "💰", "Control, stability, security."),
            ("Five of Pentacles", "❄️", "Hardship, financial loss, isolation."),
            ("Six of Pentacles", "⚖️", "Generosity, charity, giving and receiving."),
            ("Seven of Pentacles", "🌱", "Patience, assessment, long-term view."),
            ("Eight of Pentacles", "🔨", "Apprenticeship, mastery, skill."),
            ("Nine of Pentacles", "🌿", "Luxury, self-sufficiency, financial gain."),
            ("Ten of Pentacles", "🏰", "Wealth, inheritance, family legacy."),
            ("Page of Pentacles", "📜", "New opportunities, study, manifestation."),
            ("Knight of Pentacles", "🪙", "Hard work, routine, dependability."),
            ("Queen of Pentacles", "👑", "Nurturing, practicality, financial security."),
            ("King of Pentacles", "👑", "Wealth, stability, leadership."),
        ]
        drawn = random.sample(cards, 3)
        past, present, future = drawn
        embed = discord.Embed(
            title="🔮 Tarot Reading — Past · Present · Future",
            description=(
                f"**🕰️ Past** — {past[1]} **{past[0]}**\n*{past[2]}*\n\n"
                f"**⚡ Present** — {present[1]} **{present[0]}**\n*{present[2]}*\n\n"
                f"**🌟 Future** — {future[1]} **{future[0]}**\n*{future[2]}*"
            ),
            color=discord.Color.dark_purple(),
        )
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Fun(bot))
