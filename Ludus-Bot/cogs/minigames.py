import discord
from discord.ext import commands
import random
import asyncio
import time


# Lightweight PaginatedHelpView for external imports that expect it.
class PaginatedHelpView(discord.ui.View):
    """Compatibility paginator for other cogs.

    Construct with `(interaction, commands_list, category_name, category_desc)`
    where `commands_list` is a list of `(name, desc)` tuples. Callers expect
    an async `send()` method, so this class exposes `send()` which will
    deliver an initial message via the provided `interaction` and allow
    paging with buttons.
    """

    def __init__(self, interaction: discord.Interaction, commands_list, category_name: str = "Commands", category_desc: str = "", per_page: int = 10, timeout: int = 120):
        super().__init__(timeout=timeout)
        self.interaction = interaction
        self.author = interaction.user
        self.category_name = category_name
        self.category_desc = category_desc
        self.per_page = per_page
        # commands_list is a flat list of (name, desc) pairs
        self.pages = [commands_list[i:i+per_page] for i in range(0, len(commands_list), per_page)] if commands_list else [[("No commands", "None")]]
        self.page = 0
        self.message: discord.Message | None = None

    def _make_embed(self):
        embed = discord.Embed(title=f"{self.category_name} (page {self.page+1}/{len(self.pages)})",
                              description=self.category_desc,
                              color=discord.Color.blurple())
        for name, desc in self.pages[self.page]:
            embed.add_field(name=name, value=desc or "-", inline=False)
        return embed

    async def send(self):
        """Send the paginated message via the original interaction.

        This prioritizes `interaction.response.send_message` then falls back
        to `interaction.followup` or the interaction user's DM as needed.
        """
        try:
            await self.interaction.response.send_message(embed=self._make_embed(), view=self)
            # response was used; fetch the message via followup
            self.message = await self.interaction.original_response()
        except Exception:
            # fallback: try followup or channel
            try:
                self.message = await self.interaction.followup.send(embed=self._make_embed(), view=self)
            except Exception:
                # last resort: send in channel if available
                if self.interaction.channel:
                    self.message = await self.interaction.channel.send(embed=self._make_embed(), view=self)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.author.id

    @discord.ui.button(label="Prev", style=discord.ButtonStyle.secondary)
    async def prev(self, button: discord.ui.Button, interaction: discord.Interaction):
        if self.page > 0:
            self.page -= 1
            await interaction.response.edit_message(embed=self._make_embed(), view=self)
        else:
            await interaction.response.defer()

    @discord.ui.button(label="Next", style=discord.ButtonStyle.secondary)
    async def next(self, button: discord.ui.Button, interaction: discord.Interaction):
        if self.page < len(self.pages) - 1:
            self.page += 1
            await interaction.response.edit_message(embed=self._make_embed(), view=self)
        else:
            await interaction.response.defer()

    @discord.ui.button(label="Close", style=discord.ButtonStyle.danger)
    async def close(self, button: discord.ui.Button, interaction: discord.Interaction):
        try:
            if self.message:
                await self.message.delete()
            else:
                await interaction.message.delete()
        except Exception:
            await interaction.response.defer()


class Minigames(commands.Cog):
    """Minigames cog (minimal, stable implementation).

    This trimmed implementation provides a working `gamelist` and a few
    simple interactive commands so the extension can load successfully.
    Expand or restore the full set of microgames later as needed.
    """

    def __init__(self, bot):
        self.bot = bot
        self.active_games = {}

    def _send_simple(self, ctx, title: str, text: str):
        embed = discord.Embed(title=title, description=text, color=discord.Color.blurple())
        return ctx.send(embed=embed)

    def _author_channel_check(self, ctx):
        return lambda m: m.author == ctx.author and m.channel == ctx.channel

    @commands.command(name="gamelist", aliases=["games", "minigames", "mg"])
    async def game_list(self, ctx):
        """List all available prefix minigames in this cog."""
        cmds = [
            cmd for cmd in self.bot.commands
            if getattr(cmd, "cog_name", None) == self.__class__.__name__ and isinstance(cmd, commands.Command)
        ]
        cmds = [c for c in cmds if c.name != "gamelist"]
        if not cmds:
            await self._send_simple(ctx, "🎮 Minigames", "No prefix minigames found.")
            return

        entries = []
        for c in sorted(cmds, key=lambda x: x.name):
            brief = c.help or (c.callback.__doc__.strip().splitlines()[0] if getattr(c.callback, "__doc__", None) else None)
            if not brief:
                brief = f"Run L!{c.name}"
            entries.append((f"L!{c.name}", brief))

        per_page = 10
        pages = [entries[i:i+per_page] for i in range(0, len(entries), per_page)]

        def make_embed(page_index: int):
            page = pages[page_index]
            embed = discord.Embed(title=f"🎮 Minigames (page {page_index+1}/{len(pages)})",
                                  color=discord.Color.blurple())
            for name, brief in page:
                embed.add_field(name=name, value=brief, inline=False)
            embed.set_footer(text="Use the buttons below to navigate pages.")
            return embed

        class Paginator(discord.ui.View):
            def __init__(self, author, timeout=120):
                super().__init__(timeout=timeout)
                self.page = 0
                self.author = author

            async def interaction_check(self, interaction: discord.Interaction) -> bool:
                return interaction.user.id == self.author.id

            @discord.ui.button(label="Prev", style=discord.ButtonStyle.secondary)
            async def prev(self, button: discord.ui.Button, interaction: discord.Interaction):
                if self.page > 0:
                    self.page -= 1
                    await interaction.response.edit_message(embed=make_embed(self.page), view=self)
                else:
                    await interaction.response.defer()

            @discord.ui.button(label="Next", style=discord.ButtonStyle.secondary)
            async def next(self, button: discord.ui.Button, interaction: discord.Interaction):
                if self.page < len(pages) - 1:
                    self.page += 1
                    await interaction.response.edit_message(embed=make_embed(self.page), view=self)
                else:
                    await interaction.response.defer()

            @discord.ui.button(label="Close", style=discord.ButtonStyle.danger)
            async def close(self, button: discord.ui.Button, interaction: discord.Interaction):
                try:
                    await interaction.message.delete()
                except Exception:
                    await interaction.response.defer()

        view = Paginator(ctx.author)
        await ctx.send(embed=make_embed(0), view=view)

    @commands.command(name="wordle")
    async def wordle(self, ctx):
        """Simple 5-letter guess demo."""
        choices = ["apple", "bread", "crane", "delta", "eagle"]
        word = random.choice(choices)
        await ctx.send("I picked a 5-letter word. You have 6 guesses. Reply with a guess.")
        attempts = 6
        for i in range(attempts):
            try:
                msg = await self.bot.wait_for('message', timeout=30.0, check=self._author_channel_check(ctx))
            except asyncio.TimeoutError:
                await ctx.send(f"Time's up! The word was **{word}**")
                return
            guess = msg.content.lower().strip()
            if len(guess) != 5:
                await ctx.send("Please send a 5-letter word.")
                continue
            if guess == word:
                await ctx.send(f"Correct! You guessed **{word}** in {i+1} tries.")
                return
            feedback = []
            for idx, ch in enumerate(guess):
                if ch == word[idx]:
                    feedback.append(f":green_square:`{ch}`")
                elif ch in word:
                    feedback.append(f":yellow_square:`{ch}`")
                else:
                    feedback.append(f":black_large_square:`{ch}`")
            await ctx.send(" ".join(feedback))
        await ctx.send(f"Out of guesses — the word was **{word}**")

    @commands.command(name="typing_race")
    async def typing_race(self, ctx):
        sentence = "The quick brown fox jumps over the lazy dog"
        await ctx.send(f"Type this sentence as fast as you can and press enter:\n{sentence}")
        start = time.perf_counter()
        try:
            msg = await self.bot.wait_for('message', timeout=20.0, check=self._author_channel_check(ctx))
        except asyncio.TimeoutError:
            await ctx.send("Timed out — you took too long.")
            return
        end = time.perf_counter()
        user_text = msg.content.strip()
        correct = user_text == sentence
        await ctx.send(f"Time: {end-start:.2f}s — {'Correct' if correct else 'Incorrect'}")

    @commands.command(name="hangman")
    async def hangman(self, ctx):
        words = ["python", "discord", "ludus", "minigame"]
        word = random.choice(words)
        revealed = ['_' for _ in word]
        tries = 6
        used = set()
        await ctx.send(f"Hangman started. Word: {' '.join(revealed)} — you have {tries} wrong guesses allowed.")
        while tries > 0 and '_' in revealed:
            try:
                msg = await self.bot.wait_for('message', timeout=40.0, check=self._author_channel_check(ctx))
            except asyncio.TimeoutError:
                await ctx.send(f"Timed out. The word was **{word}**")
                return
            guess = msg.content.lower().strip()
            if not guess.isalpha() or len(guess) != 1:
                await ctx.send("Reply with a single letter.")
                continue
            if guess in used:
                await ctx.send("You already tried that letter.")
                continue
            used.add(guess)
            if guess in word:
                for i, ch in enumerate(word):
                    if ch == guess:
                        revealed[i] = guess
                await ctx.send(f"Good! {' '.join(revealed)}")
            else:
                tries -= 1
                await ctx.send(f"Wrong. {tries} tries left.")
        if '_' not in revealed:
            await ctx.send(f"You guessed the word: **{word}**")
        else:
            await ctx.send(f"Out of tries. The word was **{word}**")


async def setup(bot):
    cog = Minigames(bot)
    # Avoid command name collisions: if a command or alias from this cog
    # already exists on the bot, rename the cog command to a unique name
    # by prefixing with 'mg_'. Also drop aliases that collide.
    existing = set()
    for c in bot.commands:
        existing.add(c.name)
        for a in getattr(c, 'aliases', ()): 
            existing.add(a)

    for cmd in list(cog.get_commands()):
        # filter aliases that conflict
        safe_aliases = [a for a in getattr(cmd, 'aliases', []) if a not in existing]
        try:
            cmd.aliases = safe_aliases
        except Exception:
            # some Command implementations may not allow setting aliases; ignore
            pass

        if cmd.name in existing:
            base = f"mg_{cmd.name}"
            new_name = base
            i = 1
            while new_name in existing:
                new_name = f"{base}_{i}"
                i += 1
            try:
                cmd.name = new_name
                print(f"Renamed command '{base}' to '{new_name}' to avoid collision.")
            except Exception:
                # best-effort: if we can't rename, skip and let add_cog raise
                print(f"Could not rename command {cmd.name}; collision may occur.")

    await bot.add_cog(cog)