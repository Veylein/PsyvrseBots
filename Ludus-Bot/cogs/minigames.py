import discord
from discord.ext import commands
from discord import app_commands
import random
import asyncio
import time
from typing import Any, cast
import math

# ── Tiny ctx-like wrapper so _award_win still works from interactions ─────────

class _InteractionCtx:
    """Minimal ctx shim for _award_win calls from interaction context."""

    def __init__(self, user: discord.User | discord.Member):
        self.author = user
        self.channel = None

    async def send(self, *a, **kw):  # swallow coin-award chat messages
        pass


# ── Hub ctx shim (for text-command path, kept for compatibility) ──────────────

class _HubCtx:
    """Lightweight ctx proxy routing ctx.send() to the interaction channel."""

    def __init__(self, bot: commands.Bot, interaction: discord.Interaction):
        self.bot = bot
        self._interaction = interaction
        self.author = interaction.user
        self.channel = interaction.channel
        self.guild = interaction.guild

    async def send(self, content=None, **kwargs):
        kwargs.pop("reference", None)
        kwargs.pop("embed", None)
        kwargs.pop("view", None)
        try:
            ch = self._interaction.channel
            if ch:
                return await ch.send(content or "", **kwargs)
        except Exception:
            pass


# ─────────────────────────────────────────────────────────────────────────────
# BASE GAME VIEW
# ─────────────────────────────────────────────────────────────────────────────

class _BaseGameView(discord.ui.LayoutView):
    """Base for every in-message minigame.  Subclasses call _finish() when done."""

    # difficulty: 0=Endless  1=Easy  2=Normal  3=Hard
    DIFF_LABEL = {0: "♾️ Endless", 1: "🟢 Easy", 2: "🔵 Normal", 3: "🔴 Hard"}

    def __init__(
        self,
        cog: "Minigames",
        user: discord.User | discord.Member,
        key: str,
        name: str,
        category: str,
        page: int = 0,
        difficulty: int = 2,
    ):
        super().__init__(timeout=120)
        self.cog = cog
        self.user = user
        self.key = key
        self.name = name
        self.category = category
        self.page = page
        self.difficulty = difficulty

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("❌ Not your game!", ephemeral=True)
            return False
        return True

    def _nav_row(self) -> discord.ui.ActionRow:
        pa = discord.ui.Button(label="🔄 Play Again", style=discord.ButtonStyle.success, custom_id="nav_pa")
        pa.callback = self._nav_play_again
        bk = discord.ui.Button(label="◀ Back", style=discord.ButtonStyle.secondary, custom_id="nav_bk")
        bk.callback = self._nav_back
        hb = discord.ui.Button(label="🏠 Hub", style=discord.ButtonStyle.primary, custom_id="nav_hub")
        hb.callback = self._nav_hub
        return discord.ui.ActionRow(pa, bk, hb)

    async def _finish(
        self,
        interaction: discord.Interaction,
        won: bool,
        headline: str,
        body: str = "",
    ):
        """Rebuild view as result + nav buttons and edit the message."""
        if not won:
            # profile tracker
            try:
                profile_cog = self.cog.bot.get_cog("Profile")
                if profile_cog and hasattr(profile_cog, "profile_manager"):
                    profile_cog.profile_manager.increment_stat(interaction.user.id, "minigames_played")
            except Exception:
                pass
            # persistent storage — record the loss
            try:
                from utils.user_storage import record_minigame_result as _r
                await _r(
                    int(interaction.user.id), self.key, 'loss', 0,
                    str(getattr(interaction.user, 'name', ''))
                )
            except Exception as e:
                import traceback; traceback.print_exc()
        if won:
            try:
                ctx = _InteractionCtx(interaction.user)
                await self.cog._award_win(ctx, self.key)
            except Exception:
                import traceback; traceback.print_exc()
        self.clear_items()
        icon = "✅" if won else "❌"
        full = f"## {icon} {headline}\n{body}" if body else f"## {icon} {headline}"
        self.add_item(discord.ui.Container(
            discord.ui.TextDisplay(full),
            discord.ui.Separator(),
            self._nav_row(),
            accent_colour=discord.Colour.green() if won else discord.Colour.red(),
        ))
        await interaction.response.edit_message(view=self)

    async def _nav_play_again(self, interaction: discord.Interaction):
        view = _DifficultyPickerView(self.cog, self.user, self.key, self.category, self.page)
        await interaction.response.edit_message(view=view)

    async def _nav_back(self, interaction: discord.Interaction):
        await interaction.response.edit_message(
            view=MinigamesCategoryView(self.cog, self.user, self.category, self.page)
        )

    async def _nav_hub(self, interaction: discord.Interaction):
        await interaction.response.edit_message(
            view=MinigamesHubView(self.cog, self.user)
        )


# ─────────────────────────────────────────────────────────────────────────────
# GENERIC MULTIPLE-CHOICE VIEW
# ─────────────────────────────────────────────────────────────────────────────

class _MCView(_BaseGameView):
    """Shows a question + N option buttons.  One is correct."""

    def __init__(self, cog, user, key, name, category, page,
                 question: str, options: list[str], correct: int,
                 colour: discord.Colour | None = None, difficulty: int = 2):
        super().__init__(cog, user, key, name, category, page, difficulty=difficulty)
        self._question = question
        self._options = options
        self._correct = correct
        self._colour = colour or discord.Colour.blurple()
        self._build()

    def _build(self):
        self.clear_items()
        btns = []
        for i, opt in enumerate(self._options):
            btn = discord.ui.Button(
                label=opt,
                style=discord.ButtonStyle.primary,
                custom_id=f"mc_opt_{i}",
            )
            btn.callback = self._make_cb(i, opt)
            btns.append(btn)
        rows = [discord.ui.ActionRow(*btns[r:r + 4]) for r in range(0, len(btns), 4)]
        diff_tag = self.DIFF_LABEL.get(self.difficulty, "")
        self.add_item(discord.ui.Container(
            discord.ui.TextDisplay(f"## 🎮 {self.name} {diff_tag}\n{self._question}"),
            discord.ui.Separator(),
            *rows,
            accent_colour=self._colour,
        ))

    def _make_cb(self, idx: int, label: str):
        async def cb(interaction: discord.Interaction):
            won = (idx == self._correct)
            correct_label = self._options[self._correct]
            if won:
                await self._finish(interaction, True, f"{self.name} — Correct!", f"You chose **{label}**. 🎉")
            else:
                await self._finish(interaction, False, f"{self.name} — Wrong!", f"You chose **{label}**. Correct: **{correct_label}**.")
        return cb


# ─────────────────────────────────────────────────────────────────────────────
# STONES / NIM
# ─────────────────────────────────────────────────────────────────────────────

class _StonesView(_BaseGameView):
    def __init__(self, cog, user, key, name, category, page, difficulty: int = 2):
        super().__init__(cog, user, key, name, category, page, difficulty=difficulty)
        pile_ranges = {1: (5, 9), 2: (7, 15), 3: (13, 21)}
        self._pile = random.randint(*pile_ranges[difficulty])
        self._build()

    def _build(self):
        self.clear_items()
        row_btns = []
        for n in range(1, min(4, self._pile + 1)):
            btn = discord.ui.Button(
                label=f"Take {n}",
                style=discord.ButtonStyle.primary,
                custom_id=f"stones_{n}",
            )
            btn.callback = self._make_take(n)
            row_btns.append(btn)
        self.add_item(discord.ui.Container(
            discord.ui.TextDisplay(
                f"## 🪨 Stones (Nim)\n"
                f"There are **{self._pile}** stones.\n"
                f"Take 1, 2, or 3. The one who takes the **last stone loses**. You go first!"
            ),
            discord.ui.Separator(),
            discord.ui.ActionRow(*row_btns),
            accent_colour=discord.Colour.dark_gray(),
        ))

    def _make_take(self, n: int):
        async def cb(interaction: discord.Interaction):
            self._pile -= n
            if self._pile == 0:
                self.clear_items()
                await self._finish(interaction, False, "Stones — You Lose!", f"You took the last stone. 😈")
                return
            # Bot plays optimally (leave pile % 4 == 0) or random
            bot_take = self._pile % 4 or random.randint(1, min(3, self._pile))
            bot_take = max(1, min(bot_take, min(3, self._pile)))
            self._pile -= bot_take
            if self._pile == 0:
                await self._finish(interaction, True, "Stones — You Win!", f"Bot took the last stone! 🎉")
                return
            self._build()
            await interaction.response.edit_message(view=self)
        return cb


# ─────────────────────────────────────────────────────────────────────────────
# MEMORY / EMOJI MEMORY
# ─────────────────────────────────────────────────────────────────────────────

class _MemoryView(_BaseGameView):
    _POOL = ["🍎", "🍌", "🍒", "🍇", "🍉", "🍓", "🍍", "🍑", "🥝", "🍋",
             "🐶", "🐱", "🦁", "🐸", "🦊", "🦋", "🌸", "⭐", "🔥", "💎"]

    def __init__(self, cog, user, key, name, category, page, length=4, difficulty: int = 2):
        super().__init__(cog, user, key, name, category, page, difficulty=difficulty)
        length = {1: max(3, length - 1), 2: length, 3: length + 2}[difficulty]
        self._seq = [random.choice(self._POOL) for _ in range(length)]
        self._answer: list[str] = []
        self._phase = "show"  # show → recall
        self._build()

    def _build(self):
        self.clear_items()
        if self._phase == "show":
            seq_display = " ".join(self._seq)
            ready = discord.ui.Button(label="✅ I've memorized it!", style=discord.ButtonStyle.success, custom_id="mem_ready")
            ready.callback = self._on_ready
            self.add_item(discord.ui.Container(
                discord.ui.TextDisplay(
                    f"## 🧠 {self.name}\nMemorize this sequence:\n\n**{seq_display}**\n\n*Press ready when done!*"
                ),
                discord.ui.Separator(),
                discord.ui.ActionRow(ready),
                accent_colour=discord.Colour.gold(),
            ))
        else:
            # Recall phase — show chosen so far + unique emoji buttons
            chosen_display = " ".join(self._answer) if self._answer else "*(nothing yet)*"
            unique = list(dict.fromkeys(self._seq))  # keep order, deduplicate
            # shuffle unique for buttons
            pool_for_btns = list(self._POOL[:12])
            for e in self._seq:
                if e not in pool_for_btns:
                    pool_for_btns.append(e)
            btn_pool = list(dict.fromkeys(self._seq + random.sample([e for e in self._POOL if e not in self._seq], min(8, 20 - len(self._seq)))))
            random.shuffle(btn_pool)
            btn_pool = btn_pool[:12]

            btns = []
            for e in btn_pool:
                btn = discord.ui.Button(label=e, style=discord.ButtonStyle.secondary, custom_id=f"mem_e_{e}")
                btn.callback = self._make_pick(e)
                btns.append(btn)
            rows = [discord.ui.ActionRow(*btns[r:r + 4]) for r in range(0, len(btns), 4)]

            clear_btn = discord.ui.Button(label="🗑 Clear", style=discord.ButtonStyle.danger, custom_id="mem_clear")
            clear_btn.callback = self._on_clear
            self.add_item(discord.ui.Container(
                discord.ui.TextDisplay(
                    f"## 🧠 {self.name} — Recall Phase\n"
                    f"Recreate the **{len(self._seq)}-emoji** sequence:\n\n"
                    f"Your answer so far: **{chosen_display}** ({len(self._answer)}/{len(self._seq)})"
                ),
                discord.ui.Separator(),
                *rows,
                discord.ui.ActionRow(clear_btn),
                accent_colour=discord.Colour.blurple(),
            ))

    async def _on_ready(self, interaction: discord.Interaction):
        self._phase = "recall"
        self._build()
        await interaction.response.edit_message(view=self)

    async def _on_clear(self, interaction: discord.Interaction):
        self._answer = []
        self._build()
        await interaction.response.edit_message(view=self)

    def _make_pick(self, emoji: str):
        async def cb(interaction: discord.Interaction):
            self._answer.append(emoji)
            if len(self._answer) == len(self._seq):
                won = self._answer == self._seq
                seq_str = " ".join(self._seq)
                ans_str = " ".join(self._answer)
                if won:
                    await self._finish(interaction, True, f"{self.name} — Correct!", f"Sequence: **{seq_str}** ✅")
                else:
                    await self._finish(interaction, False, f"{self.name} — Wrong!", f"Correct: **{seq_str}**\nYours: **{ans_str}**")
                return
            self._build()
            await interaction.response.edit_message(view=self)
        return cb


# ─────────────────────────────────────────────────────────────────────────────
# HANGMAN
# ─────────────────────────────────────────────────────────────────────────────

class _HangmanView(_BaseGameView):
    _WORDS_EASY   = [
        "cat","dog","sun","moon","star","book","tree","fish","bird","milk",
        "bread","chair","table","phone","mouse","glass","water","stone","river","light",
        "plant","smile","laugh","drink","sugar","salt","beach","cloud","grass","shell",
        "green","red","blue","white","black","happy","sad","fast","slow","warm",
        "cold","rain","wind","fire","sand","leaf","road","map","bell","key",
        "box","bag","hat","coat","shoe","sock","cake","pie","jam","egg",
        "cup","fork","spoon","knife","plate","door","wall","floor","roof","yard",
        "park","lake","hill","field","farm","horse","sheep","cow","pig","duck",
        "goat","frog","ant","bee","bug","web","nest","seed","root","bark",
        "coin","note","shop","sale","buy","sell","work","rest","play","game",
        "time","day","week","year","hour","minute","today","night","morning","evening",
        "north","south","east","west","left","right","up","down","near","far",
        "open","close","start","stop","push","pull","give","take","keep","hold",
        "read","write","draw","sing","jump","walk","run","sit","stand","look"
    ]
    _WORDS_NORMAL = [
        "engine","mirror","ladder","hammer","tunnel","island","museum","artist","doctor","lawyer",
        "banker","driver","singer","dancer","writer","reader","planet","comet","galaxy","oxygen",
        "energy","magnet","signal","system","server","client","button","screen","cursor","folder",
        "upload","download","search","filter","random","score","winner","loser","battle","damage",
        "window","garden","pencil","bottle","school","teacher","picture","library","country","weather",
        "station","holiday","airport","kitchen","blanket","monster","diamond","plastic","chicken","battery",
        "whisper","shadow","rocket","painter","lantern","desert","forest","silver","hunter","castle",
        "market","bridge","ticket","camera","pocket","carpet","pillow","bakery","farmer","sailor",
        "puzzle","riddle","secret","danger","travel","flight","border","police","rescue","shelter",
        "memory","future","past","choice","result","chance","effort","talent","vision","spirit",
        "leader","member","friend","enemy","stranger","family","parent","child","brother","sister",
        "village","city","street","avenue","corner","square","tower","temple","statue","fountain"

    ]
    _WORDS_HARD   = [
        "awkward","buffalo","cryptic","dwarfism","fjord","gazette","ivory","jazzy","jukebox","khaki",
        "mystify","nightclub","pixel","puzzling","quartz","rhythm","scratch","sphinx","strength","subway",
        "swivel","transcript","unknown","vortex","walkways","wizardry","xylophone","yacht","zephyr","zigzagging",
        "backpacker","blacksmith","checkpoint","clockwork","daydreaming","framework","graveyard","handcuffs",
        "jackhammer","locksmith","nightfall","overgrowth","playfully","quicksand","shipwreck","stronghold",
        "thumbprint","underground","viewpoint","windstorm","workbench","youthfully","aftershock","brainstorm",
        "crossroad","downstream","earthquake","flashback","greenhouse","headhunter",
        "independent","journalism","knowledge","landscape","mastermind","networking","observation","philosophy",
        "questioning","revolution","simulation","technology","underestimate","verification","workstation",
        "yesterday","zoological","architecture","biography","calculation","development","environment",
        "foundation","generation","historical","imagination","jurisdiction","laboratory","mathematics","navigation"
    ]
    _STAGES = ["😃", "😐", "😟", "😰", "😱", "💀"]

    def __init__(self, cog, user, key, name, category, page, difficulty: int = 2):
        super().__init__(cog, user, key, name, category, page, difficulty=difficulty)
        pool_map  = {1: self._WORDS_EASY, 2: self._WORDS_NORMAL, 3: self._WORDS_HARD}
        lives_map = {1: 7, 2: 6, 3: 4}
        self._word = random.choice(pool_map[difficulty])
        self._guessed: set[str] = set()
        self._lives = lives_map[difficulty]
        self._max_lives = self._lives
        self._build()

    @property
    def _display(self) -> str:
        return " ".join(c if c in self._guessed else "\_" for c in self._word)

    def _build(self):
        self.clear_items()
        alphabet = "abcdefghijklmnopqrstuvwxyz"
        btns = []
        for letter in alphabet:
            btn = discord.ui.Button(
                label=letter.upper(),
                style=discord.ButtonStyle.secondary if letter not in self._guessed else
                      (discord.ButtonStyle.success if letter in self._word else discord.ButtonStyle.danger),
                custom_id=f"hm_{letter}",
                disabled=letter in self._guessed,
            )
            btn.callback = self._make_guess(letter)
            btns.append(btn)
        rows = [discord.ui.ActionRow(*btns[r:r + 5]) for r in range(0, len(btns), 5)]
        max_l = getattr(self, "_max_lives", 6)
        diff_tag = self.DIFF_LABEL.get(self.difficulty, "")
        stage_idx = min(len(self._STAGES) - 1, max_l - self._lives)
        stage = self._STAGES[stage_idx]
        self.add_item(discord.ui.Container(
            discord.ui.TextDisplay(
                f"## 🎯 Hangman {stage} {diff_tag}\n"
                f"`{self._display}`\n\n"
                f"Lives left: **{self._lives}** | "
                f"Guessed: {', '.join(sorted(self._guessed)) or '—'}"
            ),
            discord.ui.Separator(),
            *rows,
            accent_colour=discord.Colour.orange(),
        ))

    def _make_guess(self, letter: str):
        async def cb(interaction: discord.Interaction):
            self._guessed.add(letter)
            if letter not in self._word:
                self._lives -= 1
            if "_" not in self._display:
                await self._finish(interaction, True, f"Hangman — Solved!", f"Word was **{self._word}** 🎉")
                return
            if self._lives <= 0:
                await self._finish(interaction, False, "Hangman — Game Over!", f"Word was **{self._word}**")
                return
            self._build()
            await interaction.response.edit_message(view=self)
        return cb


# ─────────────────────────────────────────────────────────────────────────────
# TAP COUNT
# ─────────────────────────────────────────────────────────────────────────────

class _TapCountView(_BaseGameView):
    def __init__(self, cog, user, key, name, category, page, difficulty: int = 2):
        super().__init__(cog, user, key, name, category, page, difficulty=difficulty)
        ranges = {1: (3, 6), 2: (5, 10), 3: (8, 15)}
        lo, hi = ranges[difficulty]
        self._target = random.randint(lo, hi)
        self._taps = 0
        self._timed_out = False
        self._deadline: float | None = None
        self._time_limit: float | None = {1: None, 2: 20.0, 3: 12.0}[difficulty]
        self._interaction_ref = None
        self._build()

    def _build(self):
        self.clear_items()
        diff_tag = self.DIFF_LABEL.get(self.difficulty, "")
        show_count = self.difficulty < 3
        count_str = f" ({self._taps}/{self._target})" if show_count else ""
        time_str = f"\n⏱ You have **{self._time_limit:.0f}s** from your first tap!" if self._time_limit else ""
        tap_btn = discord.ui.Button(label=f"👆 Tap!{count_str}", style=discord.ButtonStyle.primary, custom_id="tap_tap")
        tap_btn.callback = self._on_tap
        submit_btn = discord.ui.Button(label="✅ Submit", style=discord.ButtonStyle.success, custom_id="tap_submit")
        submit_btn.callback = self._on_submit
        self.add_item(discord.ui.Container(
            discord.ui.TextDisplay(
                f"## 👆 Tap Count {diff_tag}\nTap the button exactly **{self._target}** times, then press Submit.{time_str}"
            ),
            discord.ui.Separator(),
            discord.ui.ActionRow(tap_btn, submit_btn),
            accent_colour=discord.Colour.blurple(),
        ))

    def set_interaction_ref(self, interaction):
        self._interaction_ref = interaction

    def _start_timed(self):
        if self._time_limit and self._deadline is None:
            self._deadline = time.perf_counter() + self._time_limit
            asyncio.create_task(self._timer_task())

    async def _timer_task(self):
        await asyncio.sleep(self._time_limit)
        if self._timed_out:
            return
        self._timed_out = True
        self.clear_items()
        self.add_item(discord.ui.Container(
            discord.ui.TextDisplay(f"## ⏰ Time's Up!\nYou didn't finish in **{self._time_limit:.0f}s**. Target was **{self._target}** taps."),
            discord.ui.Separator(),
            self._nav_row(),
            accent_colour=discord.Colour.red(),
        ))
        try:
            if self._interaction_ref:
                await self._interaction_ref.edit_original_response(view=self)
        except Exception:
            pass

    async def _on_tap(self, interaction: discord.Interaction):
        if self._timed_out:
            await interaction.response.send_message("⏰ Time's up!", ephemeral=True)
            return
        if self._taps == 0:
            self._start_timed()
        self._taps += 1
        self._build()
        await interaction.response.edit_message(view=self)

    async def _on_submit(self, interaction: discord.Interaction):
        if self._timed_out:
            await interaction.response.send_message("⏰ Time's up!", ephemeral=True)
            return
        self._timed_out = True
        if self._taps == self._target:
            await self._finish(interaction, True, "Tap Count — Correct!", f"**{self._taps}** taps — exactly right! 🎉")
        else:
            await self._finish(interaction, False, "Tap Count — Wrong!", f"You tapped **{self._taps}** times, target was **{self._target}**.")


# ─────────────────────────────────────────────────────────────────────────────
# REACTION TIME
# ─────────────────────────────────────────────────────────────────────────────

class _ReactionView(_BaseGameView):
    def __init__(self, cog, user, key, name, category, page, difficulty: int = 2):
        super().__init__(cog, user, key, name, category, page, difficulty=difficulty)
        delay_ranges = {1: (2.0, 4.0), 2: (2.0, 5.0), 3: (1.0, 3.5)}
        lo, hi = delay_ranges[difficulty]
        self._delay = random.uniform(lo, hi)
        self._threshold = {1: 2.0, 2: 1.5, 3: 0.8}[difficulty]
        self._ready = False
        self._start_time: float | None = None
        self._build_wait()
        asyncio.create_task(self._arm())

    def _build_wait(self):
        self.clear_items()
        diff_tag = self.DIFF_LABEL.get(self.difficulty, "")
        thresh = getattr(self, "_threshold", 1.5)
        btn = discord.ui.Button(label="💤 Wait for it…", style=discord.ButtonStyle.secondary, custom_id="react_wait", disabled=True)
        self.add_item(discord.ui.Container(
            discord.ui.TextDisplay(f"## ⚡ Reaction Time {diff_tag}\nWait for the **GO!** button, then click it as fast as possible!\nBeat **{thresh:.1f}s** to win."),
            discord.ui.Separator(),
            discord.ui.ActionRow(btn),
            accent_colour=discord.Colour.dark_gray(),
        ))

    async def _arm(self):
        await asyncio.sleep(self._delay)
        self._ready = True
        self._start_time = time.perf_counter()
        self.clear_items()
        go_btn = discord.ui.Button(label="⚡ GO!", style=discord.ButtonStyle.success, custom_id="react_go")
        go_btn.callback = self._on_go
        self.add_item(discord.ui.Container(
            discord.ui.TextDisplay("## ⚡ Reaction Time\n**CLICK NOW!**"),
            discord.ui.Separator(),
            discord.ui.ActionRow(go_btn),
            accent_colour=discord.Colour.green(),
        ))
        # Try to edit the original response (may fail if expired)
        try:
            # We need the interaction token — stored it in _interaction_ref
            if hasattr(self, "_interaction_ref") and self._interaction_ref:
                await self._interaction_ref.edit_original_response(view=self)
        except Exception:
            pass

    async def _on_go(self, interaction: discord.Interaction):
        if not self._ready or self._start_time is None:
            await interaction.response.send_message("Too early! 🚫", ephemeral=True)
            return
        elapsed = time.perf_counter() - self._start_time
        threshold = getattr(self, "_threshold", 1.5)
        won = elapsed < threshold
        msg = f"⚡ **{elapsed:.3f}s** (threshold: {threshold:.1f}s) — {'Amazing! 🔥' if elapsed < threshold * 0.4 else 'Fast! ✅' if won else 'Too slow. ❌'}"
        await self._finish(interaction, won, "Reaction Time!", msg)

    def set_interaction_ref(self, interaction: discord.Interaction):
        self._interaction_ref = interaction


# ─────────────────────────────────────────────────────────────────────────────
# MULTI-ROUND MATH RACE
# ─────────────────────────────────────────────────────────────────────────────

class _MathRaceView(_BaseGameView):
    def __init__(self, cog, user, key, name, category, page, rounds=3, difficulty: int = 2):
        super().__init__(cog, user, key, name, category, page, difficulty=difficulty)
        rounds = {1: 3, 2: 4, 3: 5}[difficulty]
        self._rounds = rounds
        self._round = 0
        self._score = 0
        self._next_question()

    def _next_question(self):
        diff = getattr(self, "difficulty", 2)
        if diff == 3:
            # Hard: normal ops PLUS powers and bracketed expressions
            expr_type = random.choice(["basic", "basic", "power", "bracket"])
            if expr_type == "power":
                a = random.randint(2, 9)
                b = random.randint(2, 4)
                self._answer = a ** b
                self._question = f"**{a} ^ {b} = ?**"
            elif expr_type == "bracket":
                a, b, c = random.randint(1, 15), random.randint(1, 15), random.randint(2, 6)
                op2 = random.choice(["+", "-"])
                inner = a + b if op2 == "+" else a - b
                self._answer = inner * c
                self._question = f"**({a} {op2} {b}) × {c} = ?**"
            else:
                # basic hard
                max_n = 50
                ops = ["+", "-", "*", "//"]
                op = random.choice(ops)
                a, b = random.randint(1, max_n), random.randint(1, max_n)
                if op == "//":
                    b = max(1, b % 10 or 1)
                    a = b * random.randint(1, max(1, max_n // b))
                self._answer = int(eval(f"{a}{op}{b}"))
                op_display = "÷" if op == "//" else op
                self._question = f"**{a} {op_display} {b} = ?**"
        else:
            max_n = {1: 12, 2: 20}[diff]
            ops = {1: ["+", "-"], 2: ["+", "-", "*"]}[diff]
            op = random.choice(ops)
            a, b = random.randint(1, max_n), random.randint(1, max_n)
            self._answer = int(eval(f"{a}{op}{b}"))
            self._question = f"**{a} {op} {b} = ?**"
        # Generate 3 wrong distractors
        wrongs: list[int] = []
        while len(wrongs) < 3:
            d = self._answer + random.choice([-3, -2, -1, 1, 2, 3, 4, 5])
            if d not in wrongs and d != self._answer:
                wrongs.append(d)
        opts = [self._answer] + wrongs
        random.shuffle(opts)
        self._options = [str(o) for o in opts]
        self._correct_idx = self._options.index(str(self._answer))
        self._build()

    def _build(self):
        self.clear_items()
        btns = []
        for i, opt in enumerate(self._options):
            btn = discord.ui.Button(label=opt, style=discord.ButtonStyle.primary, custom_id=f"mr_{i}")
            btn.callback = self._make_cb(i)
            btns.append(btn)
        diff_tag = self.DIFF_LABEL.get(getattr(self, "difficulty", 2), "")
        self.add_item(discord.ui.Container(
            discord.ui.TextDisplay(
                f"## 🧮 Math Race {diff_tag} — Round {self._round + 1}/{self._rounds}\n"
                f"Score: {self._score}/{self._round}\n\n"
                f"{self._question}"
            ),
            discord.ui.Separator(),
            discord.ui.ActionRow(*btns),
            accent_colour=discord.Colour.gold(),
        ))

    def _make_cb(self, idx: int):
        async def cb(interaction: discord.Interaction):
            won_this = (idx == self._correct_idx)
            if won_this:
                self._score += 1
            self._round += 1
            if self._round >= self._rounds:
                won = self._score == self._rounds
                await self._finish(
                    interaction, won,
                    f"Math Race — {self._score}/{self._rounds}!",
                    "Perfect score! 🎉" if won else f"Got {self._score} right."
                )
                return
            self._next_question()
            await interaction.response.edit_message(view=self)
        return cb


# ─────────────────────────────────────────────────────────────────────────────
# NUMBER CHAIN (multi-round)
# ─────────────────────────────────────────────────────────────────────────────

class _NumberChainView(_BaseGameView):
    def __init__(self, cog, user, key, name, category, page):
        super().__init__(cog, user, key, name, category, page)
        self._start = random.randint(1, 10)
        self._step = random.randint(2, 5)
        self._current = self._start
        self._round = 0
        self._rounds = 5
        self._score = 0
        self._build()

    def _build(self):
        self.clear_items()
        expected = self._current + self._step
        # Generate distractors
        opts = [expected]
        while len(opts) < 4:
            d = expected + random.choice([-3, -2, -1, 1, 2, 3])
            if d not in opts and d > 0:
                opts.append(d)
        random.shuffle(opts)
        self._correct_idx = opts.index(expected)
        self._expected = expected
        btns = []
        for i, o in enumerate(opts):
            btn = discord.ui.Button(label=str(o), style=discord.ButtonStyle.primary, custom_id=f"nc_{i}")
            btn.callback = self._make_cb(i)
            btns.append(btn)
        chain_so_far = ", ".join(str(self._start + self._step * k) for k in range(-1, self._round)) if self._round > 0 else str(self._start)
        self.add_item(discord.ui.Container(
            discord.ui.TextDisplay(
                f"## 🔢 Number Chain (step +{self._step})\n"
                f"Round {self._round + 1}/{self._rounds} | Score: {self._score}\n\n"
                f"Chain so far: **{self._current}**, **?**"
            ),
            discord.ui.Separator(),
            discord.ui.ActionRow(*btns),
            accent_colour=discord.Colour.blurple(),
        ))

    def _make_cb(self, idx: int):
        async def cb(interaction: discord.Interaction):
            won_this = (idx == self._correct_idx)
            if won_this:
                self._score += 1
                self._current = self._expected
            else:
                # wrong — fail early
                await self._finish(
                    interaction, False,
                    f"Number Chain — Wrong!",
                    f"Expected **{self._expected}** (step +{self._step}). Score: {self._score}/{self._rounds}."
                )
                return
            self._round += 1
            if self._round >= self._rounds:
                await self._finish(
                    interaction, True,
                    f"Number Chain — Complete!",
                    f"Full chain correct! Step was +{self._step}. 🎉"
                )
                return
            self._build()
            await interaction.response.edit_message(view=self)
        return cb


# ─────────────────────────────────────────────────────────────────────────────
# MODAL-BASED GAMES
# ─────────────────────────────────────────────────────────────────────────────

class _ModalLauncherView(_BaseGameView):
    """Shows a game prompt + 'Answer' button that opens a modal."""

    def __init__(self, cog, user, key, name, category, page,
                 prompt: str, label: str, answer: str,
                 check_fn=None, colour: discord.Colour | None = None,
                 difficulty: int = 2):
        super().__init__(cog, user, key, name, category, page, difficulty=difficulty)
        self._prompt = prompt
        self._label = label
        self._answer = answer.strip().lower()
        self._check_fn = check_fn  # optional custom checker(user_input, answer) → bool
        self._colour = colour or discord.Colour.blurple()
        self._build()

    def _build(self):
        self.clear_items()
        diff_tag = self.DIFF_LABEL.get(self.difficulty, "")
        btn = discord.ui.Button(label="✏️ Answer", style=discord.ButtonStyle.success, custom_id="modal_open")
        btn.callback = self._open_modal
        self.add_item(discord.ui.Container(
            discord.ui.TextDisplay(f"## ✏️ {self.name} {diff_tag}\n{self._prompt}"),
            discord.ui.Separator(),
            discord.ui.ActionRow(btn),
            accent_colour=self._colour,
        ))

    async def _open_modal(self, interaction: discord.Interaction):
        modal = _AnswerModal(title=self.name, label=self._label, view=self)
        await interaction.response.send_modal(modal)

    async def _handle_modal_submit(self, interaction: discord.Interaction, value: str):
        user_val = value.strip()
        if self._check_fn:
            won = self._check_fn(user_val, self._answer)
        else:
            won = user_val.lower() == self._answer
        if won:
            await self._finish(interaction, True, f"{self.name} — Correct!", f"Your answer: **{user_val}** ✅")
        else:
            await self._finish(interaction, False, f"{self.name} — Wrong!", f"Your answer: **{user_val}**\nCorrect: **{self._answer}**")


class _AnswerModal(discord.ui.Modal):
    def __init__(self, title: str, label: str, view: _ModalLauncherView):
        super().__init__(title=title)
        self._view = view
        self.answer = discord.ui.TextInput(label=label, placeholder="Type your answer…", max_length=200)
        self.add_item(self.answer)

    async def on_submit(self, interaction: discord.Interaction):
        await self._view._handle_modal_submit(interaction, self.answer.value)


# ─────────────────────────────────────────────────────────────────────────────
# INFO / DISPLAY-ONLY GAMES (predict, choose, short_story)
# ─────────────────────────────────────────────────────────────────────────────

class _InfoView(_BaseGameView):
    """Shows a result and auto-wins — for fortune/choose/story games."""

    def __init__(self, cog, user, key, name, category, page, content: str, won: bool = True):
        super().__init__(cog, user, key, name, category, page)
        icon = "🔮" if "predict" in key else "🎲" if key == "choose" else "📝"
        self.clear_items()
        colour = discord.Colour.og_blurple()
        self.add_item(discord.ui.Container(
            discord.ui.TextDisplay(f"## {icon} {name}\n{content}"),
            discord.ui.Separator(),
            self._nav_row(),
            accent_colour=colour,
        ))
        if won:
            asyncio.create_task(self._give_coins())

    async def _give_coins(self):
        try:
            ctx = _InteractionCtx(self.user)
            await self.cog._award_win(ctx, self.key)
        except Exception:
            pass


# ─────────────────────────────────────────────────────────────────────────────
# QUICK DRAW (letter buttons)
# ─────────────────────────────────────────────────────────────────────────────

class _QuickDrawView(_BaseGameView):
    _CHARS_EASY   = list("ASDF")
    _CHARS_NORMAL = list("ASDFJKL")
    _CHARS_HARD   = list("ASDFJKLQWERTY")

    def __init__(self, cog, user, key, name, category, page, difficulty: int = 2):
        super().__init__(cog, user, key, name, category, page, difficulty=difficulty)
        chars_map = {1: self._CHARS_EASY, 2: self._CHARS_NORMAL, 3: self._CHARS_HARD}
        self._CHARS = chars_map[difficulty]
        self._char = random.choice(self._CHARS)
        self._threshold = {1: 2.5, 2: 1.5, 3: 1.0}[difficulty]
        arm_lo, arm_hi = {1: (2.0, 4.0), 2: (1.5, 3.5), 3: (0.5, 2.5)}[difficulty]
        self._arm_delay = random.uniform(arm_lo, arm_hi)
        self._started = False
        self._start_time: float | None = None
        self._build()
        asyncio.create_task(self._arm())

    def _build(self):
        self.clear_items()
        diff_tag = self.DIFF_LABEL.get(self.difficulty, "")
        thresh = getattr(self, "_threshold", 1.5)
        if not self._started:
            btn = discord.ui.Button(label="💤 Get Ready…", style=discord.ButtonStyle.secondary, custom_id="qd_wait", disabled=True)
            self.add_item(discord.ui.Container(
                discord.ui.TextDisplay(f"## 🔫 Quick Draw {diff_tag}\nWhen the letter appears, click it FAST! Beat **{thresh:.1f}s** to win."),
                discord.ui.Separator(),
                discord.ui.ActionRow(btn),
                accent_colour=discord.Colour.dark_gray(),
            ))
        else:
            btns = [
                discord.ui.Button(label=c, style=discord.ButtonStyle.primary, custom_id=f"qd_{c}")
                for c in self._CHARS
            ]
            for btn in btns:
                btn.callback = self._make_cb(btn.label)
            rows = [discord.ui.ActionRow(*btns[r:r+4]) for r in range(0, len(btns), 4)]
            self.add_item(discord.ui.Container(
                discord.ui.TextDisplay(f"## 🔫 Quick Draw {diff_tag}\n**Click:** `{self._char}`"),
                discord.ui.Separator(),
                *rows,
                accent_colour=discord.Colour.yellow(),
            ))

    async def _arm(self):
        await asyncio.sleep(getattr(self, "_arm_delay", random.uniform(1.5, 3.5)))
        self._started = True
        self._start_time = time.perf_counter()
        self._build()
        try:
            if hasattr(self, "_interaction_ref") and self._interaction_ref:
                await self._interaction_ref.edit_original_response(view=self)
        except Exception:
            pass

    def _make_cb(self, char: str):
        async def cb(interaction: discord.Interaction):
            if not self._started or self._start_time is None:
                await interaction.response.send_message("Too early! 🚫", ephemeral=True)
                return
            elapsed = time.perf_counter() - self._start_time
            threshold = getattr(self, "_threshold", 1.5)
            if char == self._char:
                won = elapsed < threshold
                await self._finish(interaction, won, "Quick Draw!", f"⚡ {elapsed:.3f}s (threshold: {threshold:.1f}s) — {'Perfect! 🔥' if elapsed < threshold * 0.4 else 'Good! ✅' if won else 'Too slow. ❌'}")
            else:
                await self._finish(interaction, False, "Quick Draw — Wrong Key!", f"Needed `{self._char}`, you pressed `{char}`.")
        return cb

    def set_interaction_ref(self, interaction: discord.Interaction):
        self._interaction_ref = interaction


# ─────────────────────────────────────────────────────────────────────────────
# GAME FACTORY
# ─────────────────────────────────────────────────────────────────────────────

def _mc(cog, user, key, name, category, page, question, options, correct, colour=None, difficulty=2) -> _MCView:
    return _MCView(cog, user, key, name, category, page, question, options, correct, colour, difficulty)


def _make_capitals_options(country: str, capital: str) -> tuple[list[str], int]:
    pool = ["Paris", "Tokyo", "Berlin", "Madrid", "Rome", "Ottawa", "Cairo",
            "Brasília", "Buenos Aires", "Canberra", "Nairobi", "Beijing",
            "Moscow", "London", "Sydney", "Seoul", "Bangkok", "Lima",
            "Lisbon", "Vienna", "Warsaw", "Prague", "Amsterdam", "Athens"]
    wrongs = [c for c in pool if c != capital]
    random.shuffle(wrongs)
    opts = [capital] + wrongs[:3]
    random.shuffle(opts)
    return opts, opts.index(capital)


# ─────────────────────────────────────────────────────────────────────────────
# WORDLE
# ─────────────────────────────────────────────────────────────────────────────

class _WordleView(_BaseGameView):
    _WORDS_EASY = [
        "apple","brave","chair","dance","eagle","fable","grace","horse","ivory","jewel",
        "knife","lemon","mango","night","ocean","piano","queen","river","stone","tiger",
        "angel","beach","candy","diner","earth","flame","giant","index","joker","lunar",
        "music","noble","olive","quest","radar","tower","viral","wheat","youth","zebra",
    ]
    _WORDS_NORMAL = [
        "blaze","clamp","crisp","depth","ember","flint","gloom","handy","ingot","joust",
        "knack","lofty","mirth","notch","optic","plumb","quirk","risky","scald","tramp",
        "aglow","brisk","chasm","drift","elude","frown","grime","haste","imply","jumpy",
        "kudos","lanky","marsh","nudge","onset","perch","raven","shard","thump","vouch",
    ]
    _WORDS_HARD = [
        "crypt","dwarf","glyph","fjord","bumpy","jumbo","whack","expat","pygmy","boxer",
        "fizzy","jazzy","topaz","waltz","blitz","fluff","tryst","lynch","gawky","havoc",
        "squib","rhyme","nymph","girth","knave","psalm","civic","proxy","maxim","taboo",
        "vexed","quill","stomp","plaid","borax","tryst","slyly","vinyl","ethyl","twerp",
    ]

    def __init__(self, cog, user, key, name, category, page, difficulty: int = 2):
        super().__init__(cog, user, key, name, category, page, difficulty=difficulty)
        pools = {1: self._WORDS_EASY, 2: self._WORDS_NORMAL, 3: self._WORDS_HARD}
        self._word = random.choice(pools[difficulty]).upper()
        self._max_guesses = {1: 7, 2: 6, 3: 5}[difficulty]
        self._guesses: list[str] = []
        self._done = False
        self._build()

    def _render_guess(self, guess: str) -> str:
        result = list("⬜" * 5)
        remaining = list(self._word)
        # First pass: correct positions
        for i, (g, w) in enumerate(zip(guess, self._word)):
            if g == w:
                result[i] = "🟩"
                remaining[i] = None
        # Second pass: present but wrong position
        for i, g in enumerate(guess):
            if result[i] == "🟩":
                continue
            if g in remaining:
                result[i] = "🟨"
                remaining[remaining.index(g)] = None
        return " ".join(result) + "  " + " ".join(guess)

    def _build(self):
        self.clear_items()
        diff_tag = self.DIFF_LABEL.get(self.difficulty, "")
        lines = [f"## 🟩 Wordle {diff_tag} — Guess the 5-letter word!\n*Guesses: {len(self._guesses)}/{self._max_guesses}*"]
        if self._guesses:
            lines.append("")
            for g in self._guesses:
                lines.append(self._render_guess(g))
        else:
            lines.append("\n🟩 = Correct position  🟨 = Wrong position  ⬜ = Not in word")
        if not self._done:
            btn = discord.ui.Button(label="✏️ Type Guess", style=discord.ButtonStyle.success, custom_id="wordle_guess")
            btn.callback = self._open_modal
            self.add_item(discord.ui.Container(
                discord.ui.TextDisplay("\n".join(lines)),
                discord.ui.Separator(),
                discord.ui.ActionRow(btn),
                accent_colour=discord.Colour.green(),
            ))

    async def _open_modal(self, interaction: discord.Interaction):
        await interaction.response.send_modal(_WordleModal(view=self))

    async def _handle_guess(self, interaction: discord.Interaction, guess: str):
        guess = guess.strip().upper()
        if len(guess) != 5 or not guess.isalpha():
            await interaction.response.send_message("❌ Must be a 5-letter word (letters only)!", ephemeral=True)
            return
        self._guesses.append(guess)
        if guess == self._word:
            self._done = True
            await self._finish(interaction, True, "Wordle — Solved! 🎉",
                f"The word was **{self._word}** — found in **{len(self._guesses)}** guess{'es' if len(self._guesses) != 1 else ''}!")
            return
        if len(self._guesses) >= self._max_guesses:
            self._done = True
            await self._finish(interaction, False, "Wordle — Out of guesses!",
                f"The word was **{self._word}**.")
            return
        self._build()
        await interaction.response.edit_message(view=self)


class _WordleModal(discord.ui.Modal):
    def __init__(self, view: "_WordleView"):
        super().__init__(title="Wordle — Type your 5-letter guess")
        self._view = view
        self.guess = discord.ui.TextInput(
            label="5-letter word", placeholder="e.g. CRANE", min_length=5, max_length=5
        )
        self.add_item(self.guess)

    async def on_submit(self, interaction: discord.Interaction):
        await self._view._handle_guess(interaction, self.guess.value)


# ─────────────────────────────────────────────────────────────────────────────
# FLOOD FILL  (PIL-rendered board image)
# ─────────────────────────────────────────────────────────────────────────────

class _FloodView(_BaseGameView):
    """Flood fill — pick a colour each turn to flood from the top-left corner.
    The board is rendered as a PNG via Pillow and sent as an attachment."""

    _NAMES   = ['Red', 'Orange', 'Yellow', 'Green', 'Blue', 'Purple', 'Teal']
    _EMOJIS  = ['🟥',  '🟧',    '🟨',    '🟩',   '🟦',  '🟪',    '🩵']
    _COLORS  = [  # RGB values matching the emojis
        (220,  55,  55),  # Red
        (220, 140,  50),  # Orange
        (220, 210,  50),  # Yellow
        ( 50, 185,  65),  # Green
        ( 55, 110, 220),  # Blue
        (148,  55, 215),  # Purple
        ( 40, 195, 175),  # Teal
    ]

    # size × size board, n_colors, max_moves, cell_px
    _PARAMS = {
        1: (14, 5,  50, 28),   # Easy   — 14×14
        2: (25, 6,  90, 18),   # Normal — 25×25
        3: (35, 7, 150, 14),   # Hard   — 35×35
    }

    def __init__(self, cog, user, key, name, category, page, difficulty=2):
        super().__init__(cog, user, key, name, category, page, difficulty=difficulty)
        gs, nc, mm, cp = self._PARAMS[difficulty]
        self._size      = gs
        self._nc        = nc
        self._max_moves = mm
        self._cell_px   = cp
        self._moves     = 0
        self._board     = [[random.randint(0, nc - 1) for _ in range(gs)] for _ in range(gs)]
        self._build()

    # ── PIL render ────────────────────────────────────────────────────────────

    def render_file(self, filename: str = "flood.png") -> "discord.File":
        import io
        from PIL import Image, ImageDraw

        cell = self._cell_px
        gap  = 2
        pad  = 8
        sz   = self._size
        dim  = pad * 2 + sz * cell + (sz - 1) * gap

        img  = Image.new("RGB", (dim, dim), (30, 30, 35))
        draw = ImageDraw.Draw(img)

        # Flood region (connected component from top-left) — draw with bright border
        flood_c   = self._board[0][0]
        flood_set = self._flood_region()

        for r in range(sz):
            for c in range(sz):
                ci  = self._board[r][c]
                rgb = self._COLORS[ci]
                x0  = pad + c * (cell + gap)
                y0  = pad + r * (cell + gap)
                x1  = x0 + cell - 1
                y1  = y0 + cell - 1
                draw.rectangle([x0, y0, x1, y1], fill=rgb)
                # white outline on the flood region cells
                if (r, c) in flood_set:
                    draw.rectangle([x0, y0, x1, y1], outline=(255, 255, 255), width=max(1, cell // 10))

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return discord.File(buf, filename=filename)

    def _flood_region(self) -> set:
        """BFS to find the top-left connected region."""
        color, visited, queue = self._board[0][0], set(), [(0, 0)]
        while queue:
            r, c = queue.pop()
            if (r, c) in visited or not (0 <= r < self._size) or not (0 <= c < self._size):
                continue
            if self._board[r][c] != color:
                continue
            visited.add((r, c))
            queue.extend([(r+1,c),(r-1,c),(r,c+1),(r,c-1)])
        return visited

    # ── game logic ────────────────────────────────────────────────────────────

    def _flood_fill(self, new_c: int):
        old_c = self._board[0][0]
        if old_c == new_c:
            return
        stack, visited = [(0, 0)], set()
        while stack:
            r, c = stack.pop()
            if (r, c) in visited or not (0 <= r < self._size) or not (0 <= c < self._size):
                continue
            if self._board[r][c] != old_c:
                continue
            visited.add((r, c))
            self._board[r][c] = new_c
            stack.extend([(r+1,c),(r-1,c),(r,c+1),(r,c-1)])

    def _is_done(self) -> bool:
        first = self._board[0][0]
        return all(self._board[r][c] == first for r in range(self._size) for c in range(self._size))

    def _filled_count(self) -> int:
        return len(self._flood_region())

    # ── build UI (no board text — image is the attachment) ────────────────────

    def _build(self):
        self.clear_items()
        diff_tag   = self.DIFF_LABEL.get(self.difficulty, "")
        filled     = self._filled_count()
        total      = self._size * self._size
        moves_left = self._max_moves - self._moves
        current    = self._board[0][0]

        btns = []
        for i in range(self._nc):
            btn = discord.ui.Button(
                label=self._NAMES[i],
                emoji=self._EMOJIS[i],
                style=discord.ButtonStyle.secondary if i == current else discord.ButtonStyle.primary,
                custom_id=f"flood_c{i}",
                disabled=(i == current),
            )
            btn.callback = self._make_cb(i)
            btns.append(btn)

        btn_rows = [discord.ui.ActionRow(*btns[r:r+4]) for r in range(0, len(btns), 4)]

        self.add_item(discord.ui.Container(
            discord.ui.TextDisplay(
                f"## 🌊 Flood {diff_tag}  ({self._size}×{self._size})\n"
                f"Click a colour to flood from the **top-left** corner (white outline = current region).\n"
                f"Moves left: **{moves_left}/{self._max_moves}** | Filled: **{filled}/{total}**"
            ),
            discord.ui.MediaGallery(
                discord.MediaGalleryItem(discord.UnfurledMediaItem("attachment://flood.png"))
            ),
            discord.ui.Separator(),
            *btn_rows,
            accent_colour=discord.Colour.blue(),
        ))

    def _make_cb(self, color_idx: int):
        async def cb(interaction: discord.Interaction):
            self._flood_fill(color_idx)
            self._moves += 1
            if self._is_done():
                await self._finish(interaction, True, "Flood — Board Filled!",
                                   f"Filled the **{self._size}×{self._size}** board in **{self._moves}** moves! 🎉")
                return
            if self._moves >= self._max_moves:
                filled = self._filled_count()
                total  = self._size * self._size
                await self._finish(interaction, False, "Flood — Out of Moves!",
                                   f"Filled **{filled}/{total}** cells. Better luck next time!")
                return
            self._build()
            await interaction.response.edit_message(view=self, attachments=[self.render_file()])
        return cb


# ─────────────────────────────────────────────────────────────────────────────
# LIGHTS OUT
# ─────────────────────────────────────────────────────────────────────────────

class _LightsOutView(_BaseGameView):
    """Lights Out — toggle a cell and its orthogonal neighbours; turn all lights off."""

    #                   size  scramble_presses
    _PARAMS = {1: (3, 5), 2: (4, 8), 3: (5, 12)}

    def __init__(self, cog, user, key, name, category, page, difficulty=2):
        super().__init__(cog, user, key, name, category, page, difficulty=difficulty)
        gs, scramble = self._PARAMS[difficulty]
        self._size  = gs
        self._moves = 0
        self._grid  = [[False] * gs for _ in range(gs)]  # False = off

        # Scramble by pressing random cells (always solvable)
        for _ in range(scramble):
            self._toggle(random.randint(0, gs - 1), random.randint(0, gs - 1))
        # Edge-case: already solved → press one more random cell
        while self._is_done():
            self._toggle(random.randint(0, gs - 1), random.randint(0, gs - 1))
        self._build()

    # ── helpers ───────────────────────────────────────────────────────────────

    def _toggle(self, row: int, col: int):
        for dr, dc in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)):
            r, c = row + dr, col + dc
            if 0 <= r < self._size and 0 <= c < self._size:
                self._grid[r][c] = not self._grid[r][c]

    def _is_done(self):
        return not any(self._grid[r][c]
                       for r in range(self._size) for c in range(self._size))

    # ── build ─────────────────────────────────────────────────────────────────

    def _build(self):
        self.clear_items()
        diff_tag = self.DIFF_LABEL.get(self.difficulty, "")
        on_count = sum(self._grid[r][c]
                       for r in range(self._size) for c in range(self._size))

        btn_rows = []
        for r in range(self._size):
            row_btns = []
            for c in range(self._size):
                lit = self._grid[r][c]
                btn = discord.ui.Button(
                    emoji="💡" if lit else "⬛",
                    label="\u200b",
                    style=discord.ButtonStyle.success if lit else discord.ButtonStyle.secondary,
                    custom_id=f"lo_{r}_{c}",
                )
                btn.callback = self._make_cb(r, c)
                row_btns.append(btn)
            btn_rows.append(discord.ui.ActionRow(*row_btns))

        self.add_item(discord.ui.Container(
            discord.ui.TextDisplay(
                f"## 💡 Lights Out {diff_tag}\n"
                f"Turn off all **{self._size}×{self._size}** lights!\n"
                f"Clicking a light **toggles it and its neighbours**.\n"
                f"Lights still on: **{on_count}** | Moves: **{self._moves}**"
            ),
            discord.ui.Separator(),
            *btn_rows,
            accent_colour=discord.Colour.yellow(),
        ))

    def _make_cb(self, row: int, col: int):
        async def cb(interaction: discord.Interaction):
            self._toggle(row, col)
            self._moves += 1
            if self._is_done():
                await self._finish(interaction, True, "Lights Out — All Off!",
                                   f"Solved in **{self._moves}** moves! 🎉")
                return
            self._build()
            await interaction.response.edit_message(view=self)
        return cb


# ─────────────────────────────────────────────────────────────────────────────
# SLIDING PUZZLE
# ─────────────────────────────────────────────────────────────────────────────

class _SlidingPuzzleView(_BaseGameView):
    """Sliding puzzle — slide tiles to arrange 1…N² in order (blank at bottom-right)."""

    #                   size  scramble_moves
    _PARAMS = {1: (3, 15), 2: (4, 30), 3: (5, 50)}

    def __init__(self, cog, user, key, name, category, page, difficulty=2):
        super().__init__(cog, user, key, name, category, page, difficulty=difficulty)
        gs, scramble = self._PARAMS[difficulty]
        self._size  = gs
        self._moves = 0
        # Solved: 1..gs²-1 followed by 0 (blank)
        self._tiles = list(range(1, gs * gs)) + [0]
        self._blank = gs * gs - 1
        # Scramble via legal moves (always produces solvable state)
        last = -1
        for _ in range(scramble):
            nb = [n for n in self._blank_neighbors() if n != last]
            swap = random.choice(nb or self._blank_neighbors())
            last = self._blank
            self._do_swap(swap)
        # Ensure not already solved
        while self._is_solved():
            nb = self._blank_neighbors()
            self._do_swap(random.choice(nb))
        self._build()

    # ── helpers ───────────────────────────────────────────────────────────────

    def _blank_neighbors(self) -> list:
        gs = self._size
        r, c = divmod(self._blank, gs)
        result = []
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < gs and 0 <= nc < gs:
                result.append(nr * gs + nc)
        return result

    def _do_swap(self, idx: int):
        self._tiles[self._blank], self._tiles[idx] = self._tiles[idx], self._tiles[self._blank]
        self._blank = idx

    def _is_solved(self) -> bool:
        n = len(self._tiles)
        for i, t in enumerate(self._tiles):
            if t != (i + 1 if i < n - 1 else 0):
                return False
        return True

    # ── build ─────────────────────────────────────────────────────────────────

    def _build(self):
        self.clear_items()
        diff_tag = self.DIFF_LABEL.get(self.difficulty, "")
        gs       = self._size
        nb_set   = set(self._blank_neighbors())

        btn_rows = []
        for r in range(gs):
            row_btns = []
            for c in range(gs):
                idx      = r * gs + c
                tile     = self._tiles[idx]
                is_blank  = (tile == 0)
                can_slide = (idx in nb_set)
                btn = discord.ui.Button(
                    label="⬜" if is_blank else str(tile),
                    style=(discord.ButtonStyle.success  if can_slide
                           else discord.ButtonStyle.danger  if is_blank
                           else discord.ButtonStyle.secondary),
                    custom_id=f"sp_{r}_{c}",
                    disabled=(not can_slide),
                )
                if can_slide:
                    btn.callback = self._make_cb(idx)
                row_btns.append(btn)
            btn_rows.append(discord.ui.ActionRow(*row_btns))

        self.add_item(discord.ui.Container(
            discord.ui.TextDisplay(
                f"## 🔢 Sliding Puzzle {diff_tag}\n"
                f"Arrange tiles **1–{gs * gs - 1}** in order (blank at bottom-right).\n"
                f"Click a **highlighted green** tile to slide it into the blank.\n"
                f"Moves: **{self._moves}**"
            ),
            discord.ui.Separator(),
            *btn_rows,
            accent_colour=discord.Colour.orange(),
        ))

    def _make_cb(self, tile_idx: int):
        async def cb(interaction: discord.Interaction):
            self._do_swap(tile_idx)
            self._moves += 1
            if self._is_solved():
                await self._finish(interaction, True, "Sliding Puzzle — Solved!",
                                   f"Solved in **{self._moves}** moves! 🎉")
                return
            self._build()
            await interaction.response.edit_message(view=self)
        return cb


# ─────────────────────────────────────────────────────────────────────────────
# GAME FACTORY  (8-ball and tarot available as /8ball and /tarot in fun.py)
# ─────────────────────────────────────────────────────────────────────────────

def get_game_view(
    cog: "Minigames",
    user: discord.User | discord.Member,
    key: str,
    category: str,
    page: int = 0,
    difficulty: int = 2,
) -> discord.ui.LayoutView:
    """Return a fully-built LayoutView for the given game key."""

    name = _KEY_TO_NAME.get(key, key.replace("_", " ").title())
    kw = dict(cog=cog, user=user, key=key, name=name, category=category, page=page, difficulty=difficulty)

    # ── binary_guess ────────────────────────────────────────────────────────
    if key == "binary_guess":
        pick = random.choice([0, 1])
        return _mc(**kw,
            question=f"I'm thinking of **0** or **1**. Which is it?",
            options=["0", "1"], correct=pick)

    # ── coinflip ────────────────────────────────────────────────────────────
    if key == "coinflip":
        result = random.choice([0, 1])  # 0=heads 1=tails
        return _mc(**kw,
            question="🪙 I flipped a coin — **Heads or Tails**?",
            options=["Heads", "Tails"], correct=result)

    # ── higher_lower ─────────────────────────────────────────────────────────
    if key == "higher_lower":
        a, b = random.randint(1, 100), random.randint(1, 100)
        if b > a:
            correct = 0
        elif b < a:
            correct = 1
        else:
            correct = 2
        return _mc(**kw,
            question=f"First number: **{a}**\nWill the second number be…",
            options=["Higher", "Lower", "Equal"], correct=correct)

    # ── rps ─────────────────────────────────────────────────────────────────
    if key == "rps":
        bot_pick = random.choice(["rock", "paper", "scissors"])
        wins = {"rock": "scissors", "paper": "rock", "scissors": "paper"}
        # Find which player move beats bot
        best = next(k for k, v in wins.items() if v == bot_pick)
        opts = ["🪨 Rock", "📄 Paper", "✂️ Scissors"]
        labels_lower = ["rock", "paper", "scissors"]
        correct = labels_lower.index(best)
        return _mc(**kw,
            question=f"Rock, Paper, or Scissors? *(beat the bot!)*",
            options=opts, correct=correct,
            colour=discord.Colour.purple())

    # ── guess_number ────────────────────────────────────────────────────────
    if key == "guess_number":
        secret = random.randint(1, 12)
        opts = list(range(1, 13))
        random.shuffle(opts)
        opts = [str(o) for o in opts]
        correct = opts.index(str(secret))
        return _mc(**kw,
            question=f"I'm thinking of a number between **1 and 12**. Which is it?",
            options=opts, correct=correct)

    # ── roll ────────────────────────────────────────────────────────────────
    if key == "roll":
        ranges = [(1, 25), (26, 50), (51, 75), (76, 100)]
        result = random.randint(1, 100)
        correct = next(i for i, (lo, hi) in enumerate(ranges) if lo <= result <= hi)
        return _mc(**kw,
            question=f"I rolled a number from 1–100. In which range does it fall?",
            options=["1–25", "26–50", "51–75", "76–100"], correct=correct)

    # ── trivia ──────────────────────────────────────────────────────────────
    if key == "trivia":
        pool = [
            ("Bats are mammals.", True),
            ("Sharks are mammals.", False),
            ("The Pacific Ocean is the largest ocean on Earth.", True),
            ("Mount Everest is the tallest mountain above sea level.", True),
            ("Sound travels faster than light.", False),
            ("Humans can breathe in space without equipment.", False),
            ("Gold is heavier than silver.", True),
            ("Penguins can fly.", False),
            ("The human heart has four chambers.", True),
            ("Spiders have six legs.", False),

            ("Bananas grow on trees.", False),
            ("An octopus has three hearts.", True),
            ("Venus is the closest planet to the Sun.", False),
            ("Mercury is the closest planet to the Sun.", True),
            ("The Great Wall of China is visible from the Moon.", False),
            ("Glass is made mainly from sand.", True),
            ("Adult humans have 32 teeth.", True),
            ("Camels store water in their humps.", False),
            ("A leap year has 366 days.", True),
            ("The Atlantic Ocean is bigger than the Pacific.", False),

            ("Python is a type of snake.", True),
            ("Cheetahs are the fastest land animals.", True),
            ("Owls can rotate their heads about 270 degrees.", True),
            ("All turtles can leave their shells.", False),
            ("The Amazon is the longest river in the world.", False),
            ("The Nile is one of the longest rivers in the world.", True),
            ("The human body has five senses.", True),
            ("Plants produce oxygen during photosynthesis.", True),
            ("The Earth is perfectly round.", False),
            ("Some metals are liquid at room temperature.", True),

            ("Mercury is liquid at room temperature.", True),
            ("Pluto is officially classified as a major planet.", False),
            ("Jupiter is the largest planet in our solar system.", True),
            ("Saturn is known for its rings.", True),
            ("Mars is called the Blue Planet.", False),
            ("Earth is called the Blue Planet.", True),
            ("The Sun is a star.", True),
            ("Stars only exist in our galaxy.", False),
            ("Light travels in a straight line.", True),
            ("Ice sinks in water.", False),

            ("A triangle always has three sides.", True),
            ("Zero is a positive number.", False),
            ("There are 25 hours in a day.", False),
            ("There are 60 seconds in a minute.", True),
            ("A kilometer is longer than a mile.", False),
            ("Sound cannot travel through a vacuum.", True),
            ("Humans share DNA with bananas.", True),
            ("Blood in the human body is blue before exposure to air.", False),
            ("Your fingernails keep growing after death.", False),
            ("The brain uses electricity to send signals.", True),

            ("Coffee is made from berries.", True),
            ("Chocolate comes from cocoa beans.", True),
            ("Carrots were originally purple.", True),
            ("Honey never spoils.", True),
            ("Salt dissolves in water.", True),
            ("Oil mixes easily with water.", False),
            ("The human body is mostly water.", True),
            ("Dogs can see only in black and white.", False),
            ("Cats always land on their feet.", False),
            ("Some frogs can freeze and survive.", True),

            ("A group of lions is called a pride.", True),
            ("A group of crows is called a murder.", True),
            ("All birds migrate in winter.", False),
            ("Dolphins are fish.", False),
            ("Whales breathe through lungs.", True),
            ("Coral is a plant.", False),
            ("Some turtles live over 100 years.", True),
            ("Snakes blink with eyelids.", False),
            ("Butterflies taste with their feet.", True),
            ("Bees can recognize human faces.", True)
        ]
        statement, is_true = random.choice(pool)
        correct = 0 if is_true else 1
        return _mc(**kw,
            question=f"**True or False?**\n\n*{statement}*",
            options=["✅ True", "❌ False"], correct=correct)

    # ── palindrome ──────────────────────────────────────────────────────────
    if key == "palindrome":
        pool = [
            ("racecar", True),
            ("hello", False),
            ("level", True),
            ("world", False),
            ("civic", True),
            ("python", False),
            ("madam", True),
            ("lemon", False),
            ("radar", True),
            ("apple", False),
            ("refer", True),
            ("banana", False),
            ("rotor", True),
            ("chair", False),
            ("kayak", True),
            ("window", False),
            ("reviver", True),
            ("screen", False),
            ("redder", True),
            ("mouse", False),
            ("wow", True),
            ("keyboard", False),
            ("noon", True),
            ("coffee", False),
            ("stats", True),
            ("bottle", False),
            ("tenet", True),
            ("pillow", False),
            ("mom", True),
            ("paper", False),
            ("dad", True),
            ("planet", False),
            ("peep", True),
            ("garden", False),
            ("deed", True),
            ("river", False),
            ("leveler", False),
            ("cable", False),
            ("malayalam", True),
            ("puzzle", False),
            ("anna", True),
            ("stone", False),
            ("solos", True),
            ("engine", False),
            ("minim", True),
            ("pocket", False),
            ("repaper", True),
            ("orange", False),
            ("detartrated", True),
            ("random", False),
            ("civic", True),
            ("travel", False),
            ("rotavator", True),
            ("spoon", False),
            ("redivider", True),
            ("house", False),
            ("pop", True),
            ("train", False),
            ("nun", True),
            ("cloud", False),
            ("gig", True),
            ("forest", False),
            ("level", True),
            ("desert", False),
            ("radar", True),
            ("island", False),
            ("refer", True),
            ("hammer", False),
            ("stats", True),
            ("market", False),
            ("tenet", True),
            ("silver", False),
            ("wow", True),
            ("castle", False),
            ("mom", True),
            ("rocket", False),
            ("dad", True),
            ("signal", False),
            ("peep", True),
            ("bridge", False),
            ("deed", True),
            ("energy", False),
            ("noon", True),
            ("fabric", False),
            ("kayak", True),
            ("border", False),
            ("rotor", True),
            ("system", False),
            ("reviver", True),
            ("network", False),
            ("redder", True),
            ("folder", False),
            ("civic", True),
            ("number", False),
            ("leveler", False),
            ("design", False),
            ("repaper", True),
            ("artist", False),
            ("solos", True),
            ("memory", False),
            ("minim", True),
            ("thread", False),
            ("anna", True),
            ("object", False),
            ("malayalam", True),
            ("server", False),
        ]
        word, is_p = random.choice(pool)
        correct = 0 if is_p else 1
        return _mc(**kw,
            question=f"Is the word **{word}** a palindrome?",
            options=["✅ Yes", "❌ No"], correct=correct)

    # ── quick_math ──────────────────────────────────────────────────────────
    if key == "quick_math":
        a, b = random.randint(1, 20), random.randint(1, 20)
        op = random.choice(["+", "-", "*"])
        ans = int(eval(f"{a}{op}{b}"))
        wrongs: list[int] = []
        while len(wrongs) < 3:
            d = ans + random.choice([-3, -2, -1, 1, 2, 3, 4, 5, -5])
            if d not in wrongs and d != ans:
                wrongs.append(d)
        opts = [str(ans)] + [str(w) for w in wrongs]
        random.shuffle(opts)
        return _mc(**kw,
            question=f"Solve: **{a} {op} {b} = ?**",
            options=opts, correct=opts.index(str(ans)))

    # ── count_vowels ─────────────────────────────────────────────────────────
    if key == "count_vowels":
        pool = ["strawberry", "programming", "encyclopedia", "mystery", "beautiful", "rhythm", "facetious"]
        word = random.choice(pool)
        count = sum(1 for c in word if c in "aeiou")
        opts_set: list[int] = [count]
        while len(opts_set) < 4:
            d = count + random.choice([-2, -1, 1, 2, 3])
            if d not in opts_set and d >= 0:
                opts_set.append(d)
        random.shuffle(opts_set)
        opts = [str(x) for x in opts_set]
        return _mc(**kw,
            question=f"How many **vowels** are in the word **{word}**?",
            options=opts, correct=opts.index(str(count)))

    # ── sequence_complete ────────────────────────────────────────────────────
    if key == "sequence_complete":
        start = random.randint(1, 10)
        step = random.randint(2, 5)
        seq = [start + step * i for i in range(4)]
        nxt = seq[-1] + step
        opts: list[int] = [nxt]
        while len(opts) < 4:
            d = nxt + random.choice([-step * 2, -step, step // 2 or 1, step + 1, step + 2, step - 1])
            if d not in opts and d > 0 and d != nxt:
                opts.append(d)
        random.shuffle(opts)
        sopts = [str(x) for x in opts]
        return _mc(**kw,
            question=f"Complete the sequence: **{', '.join(map(str, seq))}, ?**",
            options=sopts, correct=sopts.index(str(nxt)))

    # ── reverse_word ─────────────────────────────────────────────────────────
    if key == "reverse_word":
        pool = ["python", "discord", "banana", "keyboard", "dragon", "puzzle", "castle"]
        word = random.choice(pool)
        rev = word[::-1]
        fakes = [w[::-1] for w in pool if w != word][:3]
        random.shuffle(fakes)
        opts = [rev] + fakes[:3]
        random.shuffle(opts)
        return _mc(**kw,
            question=f"Type **{word}** backwards:",
            options=opts, correct=opts.index(rev))

    # ── flip_words ───────────────────────────────────────────────────────────
    if key == "flip_words":
        pool = [("the cat sat", "sat cat the"),
                ("I love pizza", "pizza love I"),
                ("sky is blue", "blue is sky"),
                ("dogs are loyal", "loyal are dogs")]
        sentence, flipped = random.choice(pool)
        other_flips = [f for _, f in pool if f != flipped]
        random.shuffle(other_flips)
        opts = [flipped] + other_flips[:3]
        random.shuffle(opts)
        return _mc(**kw,
            question=f"Reverse the word order of: **{sentence}**",
            options=opts, correct=opts.index(flipped))

    # ── scramble_sentence ────────────────────────────────────────────────────
    if key == "scramble_sentence":
        pool = [
            ("cats love napping", ["dogs hate barking", "birds fly south", "fish swim fast"]),
            ("dogs chase their tails", ["cats clean their paws", "birds sing at dawn", "fish swim upstream"]),
            ("birds fly south in winter", ["cats sleep all day", "dogs love playing", "fish jump high"]),
        ]
        sentence, distractors = random.choice(pool)
        words = sentence.split()
        shuffled = words[:]
        while shuffled == words:
            random.shuffle(shuffled)
        opts = [sentence] + distractors[:3]
        random.shuffle(opts)
        return _mc(**kw,
            question=f"Unscramble: **{' '.join(shuffled)}**",
            options=opts, correct=opts.index(sentence))

    # ── text_twist ───────────────────────────────────────────────────────────
    if key == "text_twist":
        groups = [
            ("listen", ["silent", "enlist", "tinsel"]),
            ("earth", ["heart", "hater", "harte"]),
            ("below", ["elbow", "bowel", "lobes"]),
        ]
        word, anagrams = random.choice(groups)
        letters = sorted(word)
        random.shuffle(letters)
        correct_ans = anagrams[0]
        opts = [correct_ans] + anagrams[1:] + [word[::-1]]
        random.shuffle(opts)
        opts = opts[:4]
        if correct_ans not in opts:
            opts[0] = correct_ans
            random.shuffle(opts)
        return _mc(**kw,
            question=f"Make a word using all these letters: **{' '.join(letters).upper()}**",
            options=opts, correct=opts.index(correct_ans))

    # ── unscramble ───────────────────────────────────────────────────────────
    if key == "unscramble":
        pool = ["python", "discord", "castle", "wizard", "dragon", "puzzle", "button", "frozen", "bridge", "cobalt"]
        word = random.choice(pool)
        scrambled = word
        while scrambled == word:
            scrambled = "".join(random.sample(word, len(word)))
        fakes = [w for w in pool if w != word]
        random.shuffle(fakes)
        opts = [word] + fakes[:3]
        random.shuffle(opts)
        return _mc(**kw,
            question=f"Unscramble: **{scrambled}**",
            options=opts, correct=opts.index(word))

    # ── first_letter ─────────────────────────────────────────────────────────
    if key == "first_letter":
        pool = ["elephant", "umbrella", "dragon", "python", "castle", "octopus", "flamingo"]
        word = random.choice(pool)
        correct_letter = word[0].upper()
        all_letters = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
        wrongs = [l for l in all_letters if l != correct_letter]
        random.shuffle(wrongs)
        opts = [correct_letter] + wrongs[:3]
        random.shuffle(opts)
        return _mc(**kw,
            question=f"What is the **first letter** of the word `{word}`?",
            options=opts, correct=opts.index(correct_letter))

    # ── last_letter ──────────────────────────────────────────────────────────
    if key == "last_letter":
        pool = ["elephant", "umbrella", "dragon", "python", "castle", "octopus", "flamingo"]
        word = random.choice(pool)
        correct_letter = word[-1].upper()
        all_letters = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
        wrongs = [l for l in all_letters if l != correct_letter]
        random.shuffle(wrongs)
        opts = [correct_letter] + wrongs[:3]
        random.shuffle(opts)
        return _mc(**kw,
            question=f"What is the **last letter** of the word `{word}`?",
            options=opts, correct=opts.index(correct_letter))

    # ── capitals ─────────────────────────────────────────────────────────────
    if key == "capitals":
        pool = [("France", "Paris"), ("Japan", "Tokyo"), ("Brazil", "Brasília"),
                ("Australia", "Canberra"), ("Germany", "Berlin"), ("Canada", "Ottawa"),
                ("Egypt", "Cairo"), ("Argentina", "Buenos Aires"), ("Spain", "Madrid"),
                ("Italy", "Rome"), ("Poland", "Warsaw"), ("Greece", "Athens")]
        country, capital = random.choice(pool)
        opts, correct = _make_capitals_options(country, capital)
        return _mc(**kw,
            question=f"🌍 What is the capital of **{country}**?",
            options=opts[:4], correct=correct % 4)

    # ── synonym ──────────────────────────────────────────────────────────────
    if key == "synonym":
        pool = [
            ("happy", "joyful", ["sad", "fast", "cold"]),
            ("fast", "quick", ["slow", "big", "loud"]),
            ("big", "large", ["tiny", "quiet", "cold"]),
            ("sad", "unhappy", ["glad", "hot", "fast"]),
            ("brave", "courageous", ["cowardly", "weak", "lazy"]),
        ]
        word, correct_syn, wrongs = random.choice(pool)
        opts = [correct_syn] + wrongs
        random.shuffle(opts)
        return _mc(**kw,
            question=f"Give a **synonym** (same meaning) for the word **{word}**:",
            options=opts, correct=opts.index(correct_syn))

    # ── antonym ──────────────────────────────────────────────────────────────
    if key == "antonym":
        pool = [
            ("happy", "sad", ["joyful", "quick", "warm"]),
            ("fast", "slow", ["quick", "loud", "warm"]),
            ("big", "small", ["large", "bright", "cold"]),
            ("hot", "cold", ["warm", "cool", "fast"]),
            ("brave", "cowardly", ["bold", "fast", "tall"]),
        ]
        word, correct_ant, wrongs = random.choice(pool)
        opts = [correct_ant] + wrongs
        random.shuffle(opts)
        return _mc(**kw,
            question=f"Give an **antonym** (opposite) of the word **{word}**:",
            options=opts, correct=opts.index(correct_ant))

    # ── month_quiz ───────────────────────────────────────────────────────────
    if key == "month_quiz":
        pool = [
            ("📅 How many days in February (non-leap)?", "28", ["29", "30", "31"]),
            ("📅 Which is the 7th month?", "July", ["June", "August", "September"]),
            ("📅 How many months have 31 days?", "7", ["6", "5", "8"]),
            ("📅 Which month comes after March?", "April", ["May", "February", "June"]),
            ("📅 Which month comes before August?", "July", ["June", "September", "May"]),
            ("📅 How many months are in a year?", "12", ["10", "11", "13"]),
            ("📅 Which month has the fewest days?", "February", ["January", "April", "June"]),
        ]
        return _QuizRaceView(**kw, pool=pool)

    # ── weekday_quiz ─────────────────────────────────────────────────────────
    if key == "weekday_quiz":
        pool = [
            ("📅 How many days in a week?", "7", ["5", "6", "8"]),
            ("📅 Day after Wednesday?", "Thursday", ["Friday", "Tuesday", "Monday"]),
            ("📅 Day before Friday?", "Thursday", ["Wednesday", "Saturday", "Monday"]),
            ("📅 First day of the week (ISO)?", "Monday", ["Sunday", "Saturday", "Tuesday"]),
            ("📅 Day after Sunday?", "Monday", ["Tuesday", "Saturday", "Friday"]),
            ("📅 How many weekdays in a standard work week?", "5", ["4", "6", "7"]),
            ("📅 Which day comes two days after Tuesday?", "Thursday", ["Wednesday", "Friday", "Monday"]),
        ]
        return _QuizRaceView(**kw, pool=pool)

    # ── emoji_quiz / guess_the_emoji ─────────────────────────────────────────
    if key in ("emoji_quiz", "guess_the_emoji"):
        pool = [
            ("What does 🍕 represent?", "pizza", ["burger", "taco", "pasta"]),
            ("What does 🐶 represent?", "dog", ["cat", "wolf", "rabbit"]),
            ("What does 🚀 represent?", "rocket", ["plane", "satellite", "comet"]),
            ("What does 🎸 represent?", "guitar", ["violin", "drum", "piano"]),
            ("What does ⚽ represent?", "soccer", ["tennis", "baseball", "basketball"]),
            ("What does 🦁 represent?", "lion", ["tiger", "cheetah", "leopard"]),
            ("What does 🌈 represent?", "rainbow", ["sunset", "aurora", "lightning"]),
            ("What does 🎂 represent?", "cake", ["bread", "cookie", "pie"]),
            ("What does 🌍 represent?", "earth", ["moon", "sun", "planet"]),
            ("What does 🎯 represent?", "target", ["arrow", "bullseye", "dart"]),
        ]
        return _QuizRaceView(**kw, pool=pool)

    # ── simon_says ────────────────────────────────────────────────────────────
    if key == "simon_says":
        return _SimonSaysView(**kw)

    # ── color_guess ──────────────────────────────────────────────────────────
    if key == "color_guess":
        colors = ["Red", "Blue", "Green", "Yellow", "Purple", "Orange"]
        picked = random.choice(colors)
        others = [c for c in colors if c != picked]
        random.shuffle(others)
        opts = [picked] + others[:3]
        random.shuffle(opts)
        return _mc(**kw,
            question=f"🎨 I'm thinking of a color. Which one?",
            options=opts, correct=opts.index(picked))

    # ── odd_one_out ──────────────────────────────────────────────────────────
    if key == "odd_one_out":
        groups = [
            (["cat", "dog", "fish", "car"], "car"),
            (["red", "blue", "green", "piano"], "piano"),
            (["apple", "banana", "laptop", "cherry"], "laptop"),
            (["run", "jump", "swim", "table"], "table"),
            (["oxygen", "nitrogen", "gold", "helium"], "gold"),
        ]
        items, odd = random.choice(groups)
        random.shuffle(items)
        return _mc(**kw,
            question=f"Which one doesn't belong?\n**{' | '.join(items)}**",
            options=items, correct=items.index(odd))

    # ── find_pair ────────────────────────────────────────────────────────────
    if key == "find_pair":
        pairs = [("apple", "banana"), ("cat", "dog"), ("red", "blue"), ("sun", "moon")]
        pair = random.choice(pairs)
        other_pair = random.choice([p for p in pairs if p != pair])
        opts = list(pair) + list(other_pair)
        random.shuffle(opts)
        # Both items in the chosen pair are correct — ask user to identify either
        # Show a composite question: "Which two form a pair?" → pick one of the pair words
        target = random.choice(pair)
        correct_idx = opts.index(target)
        return _mc(**kw,
            question=f"🔍 I have a hidden pair. One of these words is part of it — which? *(Hint: words that go together)*\nPair theme: **{pair[0]} & {pair[1]}** — pick either!",
            options=opts, correct=correct_idx)

    # ── treasure_hunt ────────────────────────────────────────────────────────
    if key == "treasure_hunt":
        words = ["chest", "gold", "map", "island", "compass"]
        hidden = random.choice(words)
        opts = words[:]
        random.shuffle(opts)
        return _mc(**kw,
            question=f"🗺️ The treasure word starts with **{hidden[0].upper()}**. Which is it?",
            options=opts, correct=opts.index(hidden))

    # ── labelling ────────────────────────────────────────────────────────────
    if key == "labelling":
        categories = [
            ("🍎🍌🍒🍇", "Fruits", ["Animals", "Vehicles", "Sports", "Tools", "Colors"]),
            ("🍔🍟🌭🍕", "Fast Food", ["Fruits", "Desserts", "Vehicles", "Animals", "Tools"]),
            ("🍩🍪🎂🧁", "Desserts", ["Fruits", "Vegetables", "Animals", "Vehicles", "Tools"]),
            ("🥕🌽🥦🍆", "Vegetables", ["Fruits", "Desserts", "Animals", "Vehicles", "Music"]),

            ("🐶🐱🐭🐹", "Animals", ["Fruits", "Vehicles", "Sports", "Tools", "Colors"]),
            ("🦁🐯🐻🐼", "Wild Animals", ["Pets", "Food", "Tools", "Music", "Sports"]),
            ("🐬🐳🦈🐟", "Sea Animals", ["Birds", "Vehicles", "Fruits", "Tools", "Sports"]),
            ("🦜🦅🐦🕊️", "Birds", ["Reptiles", "Vehicles", "Tools", "Fruits", "Sports"]),

            ("🚗🚕🚙🚌", "Vehicles", ["Animals", "Fruits", "Colors", "Tools", "Music"]),
            ("🚲🛴🏍️🛵", "Two Wheelers", ["Tools", "Animals", "Food", "Sports", "Fruits"]),
            ("✈️🚁🛩️🚀", "Air Transport", ["Sea Animals", "Sports", "Fruits", "Animals", "Tools"]),
            ("🚢⛴️🛥️🚤", "Water Transport", ["Air Transport", "Animals", "Tools", "Food", "Music"]),

            ("⚽🏀🏈⚾", "Sports balls", ["Tools", "Fruits", "Animals", "Vehicles", "Colors"]),
            ("🎾🏐🏉🥎", "Sports Equipment", ["Weapons", "Food", "Books", "Animals", "Vehicles"]),
            ("🥊🥋🎯⛳", "Sports Gear", ["Music", "Transport", "Animals", "Fruits", "Tools"]),

            ("🔨🪛🔧🪚", "Tools", ["Food", "Animals", "Sports", "Vehicles", "Fruits"]),
            ("💻🖥️⌨️🖱️", "Computers", ["Books", "Kitchen", "Vehicles", "Animals", "Music"]),
            ("📱📲☎️📞", "Phones", ["Tools", "Transport", "Animals", "Food", "Music"]),
            ("📷🎥📹📼", "Camera Equipment", ["Music", "Books", "Sports", "Vehicles", "Animals"]),

            ("🎸🥁🎹🎺", "Music Instruments", ["Tools", "Vehicles", "Food", "Animals", "Books"]),
            ("🎲♟️🃏🧩", "Games", ["Music", "Animals", "Transport", "Fruits", "Tools"]),
            ("📚📖📝📘", "Books", ["Food", "Weapons", "Sports", "Animals", "Tools"]),

            ("🔥⚡❄️🌪️", "Elements", ["Weather", "Animals", "Food", "Tools", "Vehicles"]),
            ("🌈☀️🌙⭐", "Sky", ["Transport", "Music", "Tools", "Animals", "Sports"]),
            ("⭐✨🌟💫", "Stars", ["Fire", "Animals", "Food", "Vehicles", "Music"]),

            ("👑💍💎🪙", "Treasure", ["Tools", "Food", "Sports", "Vehicles", "Animals"]),
            ("❤️💙💚💛", "Hearts", ["Shapes", "Transport", "Animals", "Fruits", "Music"]),
        ]
        emojis, label, wrongs = random.choice(categories)
        opts = [label] + wrongs
        random.shuffle(opts)
        return _mc(**kw,
            question=f"🏷️ What category do these belong to?\n{emojis}",
            options=opts, correct=opts.index(label))

    # ── pick_a_card ──────────────────────────────────────────────────────────
    if key == "pick_a_card":
        suits = ["♠️ Spades", "♥️ Hearts", "♦️ Diamonds", "♣️ Clubs"]
        ranks = ["2","3","4","5","6","7","8","9","10","Jack","Queen","King","Ace"]
        suit = random.choice(suits)
        rank = random.choice(ranks)
        card = f"{rank} of {suit.split()[1]}"
        opts = suits[:]
        random.shuffle(opts)
        return _mc(**kw,
            question=f"🃏 I drew the **{card}**. What **suit** does it belong to?",
            options=opts, correct=opts.index(suit))

    # ── bubble_pop ───────────────────────────────────────────────────────────
    if key == "bubble_pop":
        pool = [("🔴", "Red"), ("🔵", "Blue"), ("🟢", "Green"), ("🟡", "Yellow")]
        emoji_c, color = random.choice(pool)
        others = [c for _, c in pool if c != color]
        opts = [color] + others
        random.shuffle(opts)
        return _mc(**kw,
            question=f"💥 Pop the **{color}** bubble!\n\n{emoji_c}",
            options=opts, correct=opts.index(color))

    # ── memory / emoji_memory ────────────────────────────────────────────────
    if key in ("memory", "emoji_memory"):
        length = 4 if key == "memory" else 6
        return _MemoryView(**kw, length=length)

    # ── hangman ──────────────────────────────────────────────────────────────
    if key == "hangman":
        return _HangmanView(cog, user, key, name, category, page, difficulty=difficulty)

    # ── stones ───────────────────────────────────────────────────────────────
    if key == "stones":
        return _StonesView(cog, user, key, name, category, page, difficulty=difficulty)

    # ── tap_count ────────────────────────────────────────────────────────────
    if key == "tap_count":
        return _TapCountView(cog, user, key, name, category, page, difficulty=difficulty)

    # ── reaction_time ────────────────────────────────────────────────────────
    if key == "reaction_time":
        return _ReactionView(cog, user, key, name, category, page, difficulty=difficulty)

    # ── quick_draw ───────────────────────────────────────────────────────────
    if key == "quick_draw":
        return _QuickDrawView(cog, user, key, name, category, page, difficulty=difficulty)

    # ── math_race ────────────────────────────────────────────────────────────
    if key == "math_race":
        return _MathRaceView(cog, user, key, name, category, page, difficulty=difficulty)

    # ── number_chain ─────────────────────────────────────────────────────────
    if key == "number_chain":
        return _NumberChainView(**kw)

    # ── spelling_bee ─────────────────────────────────────────────────────────
    if key == "spelling_bee":
        pool = [
            ("necessary", "necessary"),
            ("rhythm", "rhythm"),
            ("occurrence", "occurrence"),
            ("accommodate", "accommodate"),
            ("embarrass", "embarrass"),
        ]
        word, correct = random.choice(pool)
        return _ModalLauncherView(**kw,
            prompt=f"🐝 Spell the word correctly:\n\n**{word}**\n\n*Type your spelling in the box.*",
            label="Your spelling",
            answer=correct,
            colour=discord.Colour.yellow())

    # ── mimic ────────────────────────────────────────────────────────────────
    if key == "mimic":
        phrases = ["The quick brown fox", "Hello world!", "1 2 3 go",
                   "Discord is fun", "Minigames rock"]
        phrase = random.choice(phrases)
        return _ModalLauncherView(**kw,
            prompt=f"🦜 Type this text **exactly**:\n\n`{phrase}`",
            label="Type it exactly",
            answer=phrase,
            check_fn=lambda u, a: u == a,  # case-sensitive
            colour=discord.Colour.teal())

    # ── typing_race ──────────────────────────────────────────────────────────
    if key == "typing_race":
        sentences_by_diff = {
            1: [
                "The sun rises in the east",
                "Dogs love to play fetch",
                "She smiled at the stranger",
                "He reads every single night",
                "Fresh bread smells wonderful",
                "Music makes people feel alive",
                "Rain falls softly on the roof",
                "The cat sat on the warm mat",
            ],
            2: [
                "A journey of a thousand miles begins with one step",
                "The early bird always catches the worm",
                "Laughter is the best medicine in the world",
                "Every cloud has a silver lining after the storm",
                "Actions speak much louder than words ever will",
                "Time flies when you are having genuine fun",
                "You only live once so make every moment count",
                "Hard work and patience always pay off in the end",
                "Kindness costs nothing but means absolutely everything",
                "The best views come after the hardest climbs",
            ],
            3: [
                "The phenomenon of bioluminescence fascinates marine biologists around the world",
                "Approximately seventy one percent of the Earth surface is covered by water",
                "Extraordinary claims require extraordinary evidence to be taken seriously",
                "The universe is estimated to be around fourteen billion years old",
                "Procrastination is the thief of time and the enemy of all ambition",
                "Opportunities are disguised as hard work which is why most people miss them",
                "The strength of a team lies in the commitment of each individual member",
                "Perseverance and resilience are the foundations of every great achievement",
            ],
        }
        sentence = random.choice(sentences_by_diff[difficulty])
        time_hint = {1: "", 2: "\n*Take your time — accuracy matters!*", 3: "\n⏱ *Type quickly and accurately!*"}[difficulty]
        return _ModalLauncherView(**kw,
            prompt=f"⌨️ Type this sentence **exactly**:{time_hint}\n\n`{sentence}`",
            label="Type the sentence",
            answer=sentence,
            check_fn=lambda u, a: u.strip() == a,
            colour=discord.Colour.blue())

    # ── word_chain ───────────────────────────────────────────────────────────
    if key == "word_chain":
        starters = ["apple", "eagle", "elephant", "orange"]
        word = random.choice(starters)
        last_letter = word[-1].upper()
        return _ModalLauncherView(**kw,
            prompt=f"🔗 Word Chain!\n\nI say: **{word}**\n\nGive a word starting with **{last_letter}**:",
            label=f"Word starting with {last_letter}",
            answer=last_letter,
            check_fn=lambda u, a: bool(u) and u[0].upper() == a.upper(),
            colour=discord.Colour.green())

    # ── predict ──────────────────────────────────────────────────────────────
    if key == "predict":
        fortunes = [
            "🌟 Great things await you!",
            "⚡ Stay alert today — something unexpected is coming.",
            "🍀 Luck is very much on your side.",
            "🌧️ Patience will be richly rewarded.",
            "🔥 Take a bold step forward — you won't regret it.",
            "🌈 Good news is just around the corner.",
        ]
        return _InfoView(**kw, content=f"**Your fortune:**\n\n{random.choice(fortunes)}")

    # ── choose ───────────────────────────────────────────────────────────────
    if key == "choose":
        options = ["🍕 Pizza", "🌮 Tacos", "🍣 Sushi", "🍔 Burger", "🍝 Pasta"]
        pick = random.choice(options)
        return _InfoView(**kw, content=f"I have spoken — today's choice is:\n\n## {pick}")

    # ── short_story ──────────────────────────────────────────────────────────
    if key == "short_story":
        prompts = ["adventure", "mystery", "robot", "dragon", "space", "wizard"]
        prompt_word = random.choice(prompts)
        def story_check(u, _a):
            return prompt_word.lower() in u.lower() and len(u.split()) >= 5
        return _ModalLauncherView(**kw,
            prompt=f"📝 Write a **one-sentence story** containing the word **{prompt_word}**:",
            label="Your story",
            answer=prompt_word,
            check_fn=story_check,
            colour=discord.Colour.purple())

    # ── wordle ───────────────────────────────────────────────────────────────
    if key == "wordle":
        return _WordleView(**kw)

    # ── riddle ───────────────────────────────────────────────────────────────
    if key == "riddle":
        pool_easy = [
            ("I have hands but cannot clap. What am I?", "clock"),
            ("I speak without a mouth and hear without ears. What am I?", "echo"),
            ("The more you take, the more you leave behind. What am I?", "footsteps"),
            ("I am always hungry and must always be fed. The finger I touch will soon turn red. What am I?", "fire"),
            ("What has keys but no locks, space but no room, and you can enter but can't go inside?", "keyboard"),
            ("I go up but never come down. What am I?", "age"),
            ("What has to be broken before you can use it?", "egg"),
            ("What begins with T, ends with T, and has T in it?", "teapot"),
            ("What gets wetter as it dries?", "towel"),
            ("What has one eye but cannot see?", "needle"),
        ]
        pool_normal = [
            ("I have cities, but no houses live there. I have mountains, but no trees grow. I have water, but no fish swim. I have roads, but no cars travel. What am I?", "map"),
            ("The more you have of me, the less you see. What am I?", "darkness"),
            ("I shave every day, but my beard stays the same. What am I?", "barber"),
            ("I can fly without wings. I can cry without eyes. Wherever I go, darkness follows me. What am I?", "cloud"),
            ("What two things can you never eat for breakfast?", "lunch and dinner"),
            ("I have branches but no fruit, trunk or leaves. What am I?", "bank"),
            ("What can run but never walks, has a mouth but never talks, has a head but never weeps?", "river"),
            ("What is so fragile that saying its name breaks it?", "silence"),
        ]
        pool_hard = [
            ("I am not alive, but I grow; I don't have lungs, but I need air; I don't have a mouth, but water kills me. What am I?", "fire"),
            ("The more you remove from me, the bigger I get. What am I?", "hole"),
            ("I have no life, but I can die. What am I?", "battery"),
            ("What five-letter word becomes shorter when you add two letters to it?", "short"),
            ("You see a house with two doors. One leads to certain death, one to freedom. Two guards: one always lies, one always tells the truth. You can ask one question. What do you ask?", "what would the other guard say"),
            ("A man walks into a restaurant and orders albatross soup. He takes one sip, goes home, and kills himself. Why?", "he survived a shipwreck by eating his partner who died, and the soup confirmed it was not real albatross"),
        ]
        pools = {1: pool_easy, 2: pool_normal, 3: pool_hard}
        question, answer = random.choice(pools[difficulty])
        def _riddle_check(user_input, ans):
            u = user_input.strip().lower()
            return u == ans or any(word in u for word in ans.split() if len(word) > 3)
        return _ModalLauncherView(**kw,
            prompt=f"🧩 **Riddle:**\n\n*{question}*",
            label="Your answer",
            answer=answer,
            check_fn=_riddle_check,
            colour=discord.Colour.purple())

    # ── flood ─────────────────────────────────────────────────────────────────
    if key == "flood":
        return _FloodView(**kw)

    # ── lights_out ───────────────────────────────────────────────────────────
    if key == "lights_out":
        return _LightsOutView(**kw)

    # ── sliding_puzzle ───────────────────────────────────────────────────────
    if key == "sliding_puzzle":
        return _SlidingPuzzleView(**kw)

    # ── eight_ball / tarot removed — available as /8ball and /tarot slash commands in fun.py ──

    # ── unscramble fallthrough already handled above ─────────────────────────

    # ── Unknown — fallback to a simple display ───────────────────────────────
    return _InfoView(**kw, content=f"Game **{name}** is coming soon! 🚧", won=False)


# ─────────────────────────────────────────────────────────────────────────────
# GAME CATEGORIES & KEY → DISPLAY NAME MAP
# ─────────────────────────────────────────────────────────────────────────────

_HUB_CATEGORIES: dict[str, list[tuple[str, str, str]]] = {
    "🧠 Knowledge": [
        ("trivia",        "Trivia",        "True or False — answer in one click. *(+coins)*"),
        ("emoji_quiz",    "Emoji Quiz",    "Guess what the emoji represents."),
        ("capitals",      "Capitals",      "Name the capital of a country."),
        ("month_quiz",    "Month Quiz",    "Calendar knowledge questions."),
        ("weekday_quiz",  "Weekday Quiz",  "Day-of-the-week questions."),
        ("labelling",     "Labelling",     "Label the emoji group correctly."),
    ],
    "🔢 Numbers": [
        ("quick_math",        "Quick Math",     "Solve a quick arithmetic problem."),
        ("sequence_complete", "Sequence",       "Complete the number sequence."),
        ("math_race",         "Math Race",      "Answer 3 math problems in a row."),
        ("binary_guess",      "Binary Guess",   "Guess 0 or 1 — 50/50 challenge."),
        ("number_chain",      "Number Chain",   "Continue the counting chain (5 rounds)."),
        ("stones",            "Stones",         "Nim game — take stones, last loses."),
    ],
    "📝 Words": [
        ("hangman",          "Hangman",          "Classic letter-by-letter hangman."),
        ("wordle",           "Wordle",           "Guess the 5-letter word in up to 7 tries."),
        ("unscramble",       "Unscramble",       "Unscramble a jumbled word."),
        ("spelling_bee",     "Spelling Bee",     "Spell the given word correctly."),
        ("scramble_sentence","Scramble Sentence","Unscramble the mixed-up sentence."),
        ("text_twist",       "Text Twist",       "Make a new word from the given letters."),
        ("word_chain",       "Word Chain",       "Add a word starting with the last letter."),
    ],
    "✍️ Language": [
        ("reverse_word", "Reverse Word", "Pick the word written backwards."),
        ("flip_words",   "Flip Words",   "Pick the sentence with reversed word order."),
        ("palindrome",   "Palindrome",   "Is the word a palindrome? Yes or No."),
        ("count_vowels", "Count Vowels", "Count the vowels in a word."),
        ("synonym",      "Synonym",      "Pick a synonym for the shown word."),
        ("antonym",      "Antonym",      "Pick an antonym for the shown word."),
    ],
    "⚡ Speed": [
        ("reaction_time", "Reaction",   "Click GO! as fast as possible."),
        ("quick_draw",    "Quick Draw", "Click the shown letter fast."),
        ("typing_race",   "Type Race",  "Type a sentence exactly."),
        ("tap_count",     "Tap Count",  "Tap the button exactly N times."),
        ("bubble_pop",    "Bubble Pop", "Pop the correct colored bubble."),
    ],
    "🎲 Luck": [
        ("coinflip",     "Coin Flip",    "Heads or tails — 50/50."),
        ("roll",         "Dice Roll",    "Guess the range of the dice roll."),
        ("guess_number", "Guess Number", "Guess the secret number 1–12."),
        ("pick_a_card",  "Pick a Card",  "Guess the suit of the drawn card."),
        ("higher_lower", "Higher/Lower", "Higher, lower, or equal?"),
        ("predict",      "Predict",      "Let the bot tell your fortune."),
        ("color_guess",  "Color Guess",  "Guess which colour was secretly picked."),
    ],
    "🖥️ Memory": [
        ("memory",       "Memory",       "Remember and recreate the emoji sequence."),
        ("emoji_memory", "Emoji Memory", "Recall a longer 6-emoji sequence."),
        ("simon_says",   "Simon Says",   "Repeat the colour sequence in order."),
    ],
    "🧩 Puzzle": [
        ("find_pair",       "Find Pair",       "Spot the matching pair."),
        ("odd_one_out",     "Odd One Out",     "Identify the item that doesn't belong."),
        ("riddle",          "Riddle",          "Solve a brain-teasing riddle."),
        ("treasure_hunt",   "Treasure Hunt",   "Find the hidden treasure word."),
        ("rps",             "Rock Paper Scissors", "Classic RPS against the bot."),
        ("flood",           "Flood",           "Flood-fill the 5×5 board from top-left."),
        ("lights_out",      "Lights Out",      "Toggle lights off — clicking affects neighbours."),
        ("sliding_puzzle",  "Sliding Puzzle",  "Slide tiles into order 1–N."),
        ("choose",          "Choose",          "Let the bot make a choice for you."),
    ],
    "🎉 Fun": [
        ("mimic",       "Mimic",       "Repeat back exactly what you see."),
        ("short_story", "Short Story", "Write a mini story from a prompt word."),
        ("guess_the_emoji", "Guess Emoji",   "Name what the emoji represents."),
        ("emoji_quiz",      "Emoji Quiz",    "Another round of emoji guessing."),
    ],
}

# Map key → display name for the factory
_KEY_TO_NAME: dict[str, str] = {
    key: name
    for games in _HUB_CATEGORIES.values()
    for key, name, _ in games
}



# ─────────────────────────────────────────────────────────────────────────────
# SIMON SAYS
# ─────────────────────────────────────────────────────────────────────────────

class _SimonSaysView(_BaseGameView):
    """Classic Simon memory game.
    Each round a new colour is appended to the sequence.
    The sequence is shown briefly, then hidden — player must repeat it from memory.
    One mistake ends the game.
    """

    _COLORS = [
        ("\U0001f534", "Red"),
        ("\U0001f535", "Blue"),
        ("\U0001f7e2", "Green"),
        ("\U0001f7e1", "Yellow"),
        ("\U0001f7e3", "Purple"),
        ("\U0001f7e0", "Orange"),
    ]

    def __init__(self, cog, user, key, name, category, page, difficulty: int = 2):
        super().__init__(cog, user, key, name, category, page, difficulty=difficulty)
        pool_size       = {0: 4, 1: 3, 2: 4, 3: 5}[difficulty]
        self._show_secs = {0: 2.0, 1: 3.0, 2: 2.0, 3: 1.5}[difficulty]
        self._win_at    = {0: 9999, 1: 10, 2: 20, 3: 30}[difficulty]  # 9999 = endless
        self._pool      = self._COLORS[:pool_size]
        self._sequence: list[tuple[str, str]] = []
        self._input_step = 0
        self._phase      = "show"   # "show" | "input"
        self._interaction_ref = None
        self._dead = False
        # Build the first round immediately (before set_interaction_ref is called)
        self._grow_sequence()
        self._build_show()

    def set_interaction_ref(self, interaction: discord.Interaction) -> None:
        self._interaction_ref = interaction
        # Now that we have the ref, kick off the hide-timer for the first round
        asyncio.create_task(self._switch_to_input_task())

    # ── build helpers ────────────────────────────────────────────────────────

    def _build_show(self) -> None:
        """Display the full sequence so the player can memorise it."""
        self.clear_items()
        diff_tag = self.DIFF_LABEL.get(self.difficulty, "")
        seq_str  = "  ".join(e for e, _ in self._sequence)
        round_n  = len(self._sequence)
        endless  = self.difficulty == 0
        subtitle = f"Best so far: **Round {round_n}** ♾️" if endless else f"Win at round **{self._win_at}**"
        self.add_item(discord.ui.Container(
            discord.ui.TextDisplay(
                f"## \U0001f3ae Simon Says {diff_tag} — Round {round_n}\n"
                f"{subtitle}\n\n"
                f"**Memorise the sequence!**\n\n"
                f"{seq_str}\n\n"
                f"⏳ Disappears in **{self._show_secs:.0f}s**\u2026"
            ),
            accent_colour=discord.Colour.gold(),
        ))

    def _build_input(self) -> None:
        """Show colour buttons for player input."""
        self.clear_items()
        diff_tag = self.DIFF_LABEL.get(self.difficulty, "")
        round_n  = len(self._sequence)
        endless  = self.difficulty == 0
        subtitle = f"Best so far: **Round {round_n}** ♾️" if endless else f"Win at round **{self._win_at}**"
        done     = "\u2705 " * self._input_step
        left     = "\u2b1c " * (round_n - self._input_step)
        btns = []
        for emoji_c, label in self._pool:
            btn = discord.ui.Button(
                label=label, emoji=emoji_c,
                style=discord.ButtonStyle.primary,
                custom_id=f"ss_{label}",
            )
            btn.callback = self._make_cb(emoji_c)
            btns.append(btn)
        btn_rows = [discord.ui.ActionRow(*btns[r:r+3]) for r in range(0, len(btns), 3)]
        self.add_item(discord.ui.Container(
            discord.ui.TextDisplay(
                f"## \U0001f3ae Simon Says {diff_tag} — Round {round_n}\n"
                f"{subtitle}\n\n"
                f"Repeat the sequence! Step **{self._input_step + 1}/{round_n}**\n\n"
                f"{done}{left}"
            ),
            discord.ui.Separator(),
            *btn_rows,
            accent_colour=discord.Colour.blue(),
        ))

    # ── internal logic ───────────────────────────────────────────────────────

    def _grow_sequence(self) -> None:
        self._sequence.append(random.choice(self._pool))
        self._input_step = 0
        self._phase = "show"

    async def _switch_to_input_task(self) -> None:
        await asyncio.sleep(self._show_secs)
        if self._dead or self._phase != "show":
            return
        self._phase = "input"
        self._build_input()
        try:
            if self._interaction_ref:
                await self._interaction_ref.edit_original_response(view=self)
        except Exception:
            pass

    # ── button callback ──────────────────────────────────────────────────────

    def _make_cb(self, pressed_emoji: str):
        async def cb(interaction: discord.Interaction):
            if self._phase != "input":
                await interaction.response.send_message(
                    "\u23f3 Wait for the sequence to finish first!", ephemeral=True)
                return

            need_emoji, _ = self._sequence[self._input_step]

            if pressed_emoji != need_emoji:
                self._dead = True
                reached = len(self._sequence)
                endless  = self.difficulty == 0
                fail_msg = (
                    f"\U0001f3c6 You survived **{reached} round(s)** in Endless mode! Try to beat it next time."
                    if endless else
                    f"Step {self._input_step + 1}: needed {need_emoji}, got {pressed_emoji}.\n"
                    f"You reached round **{reached}**! \u274c"
                )
                await self._finish(interaction, False, "Simon Says \u2014 Game Over!", fail_msg)
                return

            self._input_step += 1

            # Completed this round's sequence → move to next round
            if self._input_step >= len(self._sequence):
                if len(self._sequence) >= self._win_at:
                    self._dead = True
                    await self._finish(
                        interaction, True,
                        "Simon Says \u2014 Perfect!",
                        f"\U0001f38a You completed all **{self._win_at}** rounds without a mistake!",
                    )
                    return
                # store fresh interaction token for next round's hide-timer
                self._interaction_ref = interaction
                self._grow_sequence()
                self._build_show()
                asyncio.create_task(self._switch_to_input_task())
                await interaction.response.edit_message(view=self)
                return

            # Still in same round — update progress bar
            self._build_input()
            await interaction.response.edit_message(view=self)
        return cb


# ─────────────────────────────────────────────────────────────────────────────
# QUIZ RACE  (multi-round MC, used by month/weekday/emoji quiz)
# ─────────────────────────────────────────────────────────────────────────────

class _QuizRaceView(_BaseGameView):
    """Generic multi-round MC quiz. Pool = list of (question, answer, [wrongs])."""

    def __init__(self, cog, user, key, name, category, page,
                 pool: list, difficulty: int = 2):
        super().__init__(cog, user, key, name, category, page, difficulty=difficulty)
        rounds = {1: 2, 2: 3, 3: 5}[difficulty]
        self._rounds = rounds
        self._round = 0
        self._score = 0
        # sample without replacement when possible
        sample_size = min(rounds, len(pool))
        self._questions = random.sample(pool, sample_size)
        # pad with repeats if pool smaller than rounds
        while len(self._questions) < rounds:
            self._questions.append(random.choice(pool))
        self._build_question()

    def _build_question(self):
        q_text, ans, wrongs = self._questions[self._round]
        opts = [ans] + list(wrongs[:3])
        random.shuffle(opts)
        self._correct_idx = opts.index(ans)
        self._opts = opts
        self._build(q_text, opts)

    def _build(self, q_text: str, opts: list[str]):
        self.clear_items()
        diff_tag = self.DIFF_LABEL.get(self.difficulty, "")
        btns = []
        for i, opt in enumerate(opts):
            btn = discord.ui.Button(label=opt, style=discord.ButtonStyle.primary,
                                    custom_id=f"qr_{i}")
            btn.callback = self._make_cb(i)
            btns.append(btn)
        rows = [discord.ui.ActionRow(*btns[r:r+2]) for r in range(0, len(btns), 2)]
        self.add_item(discord.ui.Container(
            discord.ui.TextDisplay(
                f"## \U0001f4dd Quiz {diff_tag} \u2014 Round {self._round + 1}/{self._rounds}\n"
                f"Score: {self._score}/{self._round}\n\n"
                f"{q_text}"
            ),
            discord.ui.Separator(),
            *rows,
            accent_colour=discord.Colour.purple(),
        ))

    def _make_cb(self, idx: int):
        async def cb(interaction: discord.Interaction):
            if idx == self._correct_idx:
                self._score += 1
            self._round += 1
            if self._round >= self._rounds:
                won = self._score == self._rounds
                await self._finish(
                    interaction, won,
                    f"Quiz \u2014 {self._score}/{self._rounds}!",
                    "Perfect! \U0001f389" if won else f"Got {self._score} correct."
                )
                return
            self._build_question()
            await interaction.response.edit_message(view=self)
        return cb

# ─────────────────────────────────────────────────────────────────────────────
# HUB NAVIGATION VIEWS
# ─────────────────────────────────────────────────────────────────────────────

# ─────────────────────────────────────────────────────────────────────────────
# DIFFICULTY PICKER
# ─────────────────────────────────────────────────────────────────────────────

class _DifficultyPickerView(discord.ui.LayoutView):
    """✅ Choose difficulty before starting a game."""

    _DESCS = {
        1: "🟢 **Easy** — relaxed rules, more time, simpler questions.",
        2: "🔵 **Normal** — balanced challenge for most players.",
        3: "🔴 **Hard** — strict time limits, bigger pools, tougher content.",
    }
    _DESCS_SIMON = {
        0: "♾️ **Endless** — no round limit, play until you make a mistake!",
        1: "🟢 **Easy** — 3 colours, 3s to memorise, win at round 5.",
        2: "🔵 **Normal** — 4 colours, 2s to memorise, win at round 8.",
        3: "🔴 **Hard** — 5 colours, 1.5s to memorise, win at round 12.",
    }

    def __init__(self, cog, user, key: str, category: str, page: int = 0):
        super().__init__(timeout=60)
        self.cog = cog
        self.user = user
        self.key = key
        self.category = category
        self.page = page
        self._build()

    def _build(self):
        self.clear_items()
        name = _KEY_TO_NAME.get(self.key, self.key.replace("_", " ").title())
        is_simon = self.key == "simon_says"
        descs = self._DESCS_SIMON if is_simon else self._DESCS
        desc = "\n".join(descs.values())
        e = discord.ui.Button(label="🟢 Easy",   style=discord.ButtonStyle.success,   custom_id="diff_1")
        e.callback = self._make_cb(1)
        n = discord.ui.Button(label="🔵 Normal", style=discord.ButtonStyle.primary,   custom_id="diff_2")
        n.callback = self._make_cb(2)
        h = discord.ui.Button(label="🔴 Hard",   style=discord.ButtonStyle.danger,    custom_id="diff_3")
        h.callback = self._make_cb(3)
        b = discord.ui.Button(label="◄ Back",    style=discord.ButtonStyle.secondary, custom_id="diff_back")
        b.callback = self._back
        if is_simon:
            inf_btn = discord.ui.Button(label="♾️ Endless", style=discord.ButtonStyle.secondary, custom_id="diff_0")
            inf_btn.callback = self._make_cb(0)
            btn_rows = [
                discord.ui.ActionRow(inf_btn, e, n),
                discord.ui.ActionRow(h, b),
            ]
        else:
            btn_rows = [discord.ui.ActionRow(e, n, h, b)]
        self.add_item(discord.ui.Container(
            discord.ui.TextDisplay(f"## 🎮 {name} — Select Difficulty\n\n{desc}"),
            discord.ui.Separator(),
            *btn_rows,
            accent_colour=discord.Colour.blurple(),
        ))

    def _make_cb(self, difficulty: int):
        async def cb(interaction: discord.Interaction):
            if interaction.user.id != self.user.id:
                return await interaction.response.send_message("❌ Not yours!", ephemeral=True)
            view = get_game_view(self.cog, self.user, self.key, self.category, self.page, difficulty)
            if hasattr(view, "set_interaction_ref"):
                view.set_interaction_ref(interaction)
            # PIL-rendered games expose render_file(); pass the initial image
            if hasattr(view, "render_file"):
                await interaction.response.edit_message(view=view, attachments=[view.render_file()])
            else:
                await interaction.response.edit_message(view=view)
        return cb

    async def _back(self, interaction: discord.Interaction):
        if interaction.user.id != self.user.id:
            return await interaction.response.send_message("❌ Not yours!", ephemeral=True)
        await interaction.response.edit_message(
            view=MinigamesCategoryView(self.cog, self.user, self.category, self.page)
        )

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("❌ Not yours!", ephemeral=True)
            return False
        return True

class MinigamesHubView(discord.ui.LayoutView):
    """Main hub panel — Components V2."""

    def __init__(self, cog: "Minigames", user: discord.User | discord.Member):
        super().__init__(timeout=120)
        self.cog = cog
        self.user = user
        self._build()

    def _build(self):
        self.clear_items()
        cats = list(_HUB_CATEGORIES.keys())
        summary_lines = []
        for cat, games in _HUB_CATEGORIES.items():
            names = " • ".join(g[1] for g in games)
            summary_lines.append(f"**{cat}** — {names}")
        header = discord.ui.TextDisplay(
            "## 🎮 Minigames Hub\n"
            "Pick a **category** to browse games, then press **▶ Play** to start!\n"
            "Every win rewards **PsyCoins**.\n\n"
            + "\n".join(summary_lines)
        )
        btn_rows = []
        for row_i in range(0, len(cats), 3):
            row_cats = cats[row_i : row_i + 3]
            btns = []
            for j, cat in enumerate(row_cats):
                btn = discord.ui.Button(
                    label=cat,
                    style=discord.ButtonStyle.primary,
                    custom_id=f"hub_cat_{row_i + j}",
                )
                btn.callback = self._make_cat_callback(cat)
                btns.append(btn)
            btn_rows.append(discord.ui.ActionRow(*btns))
        self.add_item(discord.ui.Container(
            header, discord.ui.Separator(), *btn_rows,
            accent_colour=discord.Colour.blurple(),
        ))

    def _make_cat_callback(self, cat: str):
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.user.id:
                return await interaction.response.send_message("❌ Not yours!", ephemeral=True)
            view = MinigamesCategoryView(self.cog, self.user, cat)
            await interaction.response.edit_message(view=view)
        return callback

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("❌ Not yours!", ephemeral=True)
            return False
        return True

    async def on_timeout(self): self.clear_items()


class MinigamesCategoryView(discord.ui.LayoutView):
    """Games in one category — paginated 4/page. Components V2."""

    _PAGE_SIZE = 4

    def __init__(self, cog, user, category: str, page: int = 0):
        super().__init__(timeout=120)
        self.cog = cog
        self.user = user
        self.category = category
        self.page = page
        self._games = _HUB_CATEGORIES[category]
        self._build()

    def _page_games(self): return self._games[self.page * self._PAGE_SIZE:(self.page + 1) * self._PAGE_SIZE]

    @property
    def _total_pages(self): return max(1, math.ceil(len(self._games) / self._PAGE_SIZE))

    def _build(self):
        self.clear_items()
        games = self._page_games()
        lines = [f"**{name}** — {desc}" for _, name, desc in games]
        hdr = (
            f"## {self.category}\n"
            f"Page **{self.page + 1}/{self._total_pages}** — press **▶ Play** to start!\n\n"
            + "\n".join(lines)
        )
        game_rows = []
        for i in range(0, len(games), 2):
            btns = []
            for key, name, _ in games[i:i + 2]:
                btn = discord.ui.Button(
                    label=f"▶ {name}", style=discord.ButtonStyle.success,
                    custom_id=f"hub_play_{key}_{self.page}_{i}",
                )
                btn.callback = self._make_play_callback(key, name)
                btns.append(btn)
            game_rows.append(discord.ui.ActionRow(*btns))
        nav: list[discord.ui.Button] = []
        if self.page > 0:
            p = discord.ui.Button(label="◀ Prev", style=discord.ButtonStyle.secondary, custom_id="hub_prev")
            p.callback = self._prev_callback; nav.append(p)
        if self.page < self._total_pages - 1:
            n = discord.ui.Button(label="Next ▶", style=discord.ButtonStyle.secondary, custom_id="hub_next")
            n.callback = self._next_callback; nav.append(n)
        b = discord.ui.Button(label="🔙 Back to Hub", style=discord.ButtonStyle.primary, custom_id="hub_back")
        b.callback = self._back_callback; nav.append(b)
        self.add_item(discord.ui.Container(
            discord.ui.TextDisplay(hdr), discord.ui.Separator(),
            *game_rows, discord.ui.ActionRow(*nav),
            accent_colour=discord.Colour.green(),
        ))

    def _make_play_callback(self, key: str, name: str):
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.user.id:
                return await interaction.response.send_message("❌ Not yours!", ephemeral=True)
            view = _DifficultyPickerView(self.cog, self.user, key, self.category, self.page)
            await interaction.response.edit_message(view=view)
        return callback

    async def _prev_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user.id:
            return await interaction.response.send_message("❌ Not yours!", ephemeral=True)
        await interaction.response.edit_message(
            view=MinigamesCategoryView(self.cog, self.user, self.category, self.page - 1))

    async def _next_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user.id:
            return await interaction.response.send_message("❌ Not yours!", ephemeral=True)
        await interaction.response.edit_message(
            view=MinigamesCategoryView(self.cog, self.user, self.category, self.page + 1))

    async def _back_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user.id:
            return await interaction.response.send_message("❌ Not yours!", ephemeral=True)
        await interaction.response.edit_message(view=MinigamesHubView(self.cog, self.user))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("❌ Not yours!", ephemeral=True)
            return False
        return True




class Minigames(commands.Cog):
    """Minigames cog — provides the /minigames hub with in-message interactive games."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _award_win(self, ctx, game_name: str, amount: int = 5):
        """Best-effort: award `amount` PsyCoins using the Economy cog."""

        eco = cast(Any, self.bot.get_cog("Economy"))
        if eco and hasattr(eco, "add_coins"):
            try:
                res = eco.add_coins(ctx.author.id, amount, f"Win: {game_name}")
                if asyncio.iscoroutine(res):
                    await res
            except Exception:
                # don't break the game if economy fails
                pass
        # notify user
        try:
            await ctx.send(f"You received **{amount}** PsyCoins!")
        except Exception:
            pass

        # Track minigame stats in profile
        try:
            profile_cog = self.bot.get_cog("Profile")
            if profile_cog and hasattr(profile_cog, "profile_manager"):
                pm = profile_cog.profile_manager
                pm.increment_stat(ctx.author.id, 'minigames_played')
                pm.increment_stat(ctx.author.id, 'minigames_won')
        except Exception:
            pass

        # Record the win in persistent user storage if available.
        try:
            # try common import paths; prefer non-blocking execution
            record_fn = None
            try:
                from utils.user_storage import record_minigame_result as _r
                record_fn = _r
            except Exception:
                try:
                    from ..utils.user_storage import record_minigame_result as _r
                    record_fn = _r
                except Exception:
                    record_fn = None

            if record_fn:
                try:
                    await record_fn(int(ctx.author.id), game_name, 'win', int(amount), str(getattr(ctx.author, 'name', ctx.author)))
                except Exception:
                    import traceback; traceback.print_exc()
        except Exception:
            pass

    # ------------------------------------------------------------------ #
    #  /minigames slash command — interactive hub                          #
    # ------------------------------------------------------------------ #

    @app_commands.command(name="minigames", description="🎮 Open the Minigames Hub and pick a game to play!")
    async def minigames_slash(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)
        view = MinigamesHubView(self, interaction.user)
        await interaction.followup.send(view=view)
# ======================================================================
# Cog setup
# ======================================================================

async def setup(bot: commands.Bot):
    cog = Minigames(bot)

    await bot.add_cog(cog)
    
class PaginatedHelpView(discord.ui.View):
    """Paginated embed helper used by other cogs.

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
        desc_text = self.category_desc
        if desc_text:
            desc_text += "\n\n"
        desc_text += "🔘 Use the interactive buttons below to navigate!"
        embed = discord.Embed(title=f"{self.category_name} (page {self.page+1}/{len(self.pages)})",
                              description=desc_text,
                              color=discord.Color.blurple())
        for name, desc in self.pages[self.page]:
            embed.add_field(name=name, value=desc or "-", inline=False)
        embed.set_footer(text="💡 Buttons are fully functional - click to interact!")
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
                    channel = cast(discord.abc.Messageable, self.interaction.channel)
                    self.message = await channel.send(embed=self._make_embed(), view=self)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.author.id

    @discord.ui.button(label="Prev", style=discord.ButtonStyle.secondary)
    async def prev(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.page > 0:
            self.page -= 1
            await interaction.response.edit_message(embed=self._make_embed(), view=self)
        else:
            await interaction.response.defer()

    @discord.ui.button(label="Next", style=discord.ButtonStyle.secondary)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.page < len(self.pages) - 1:
            self.page += 1
            await interaction.response.edit_message(embed=self._make_embed(), view=self)
        else:
            await interaction.response.defer()

    @discord.ui.button(label="Close", style=discord.ButtonStyle.danger)
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            if self.message:
                if self.message:
                    await self.message.delete()
            else:
                if interaction.message:
                    await interaction.message.delete()
        except Exception:
            await interaction.response.defer()
