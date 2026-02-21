import discord
from discord.ext import commands
from discord import app_commands
import random
import asyncio
import time
from typing import Any, cast

class Minigames(commands.Cog):
    """A large collection of small prefix minigames (first 50).

    Commands are registered programmatically in `setup` so they are
    standard prefix commands (not slash commands). Each command is a
    simple, self-contained interaction intended to be stable and safe.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.active = {}
        self._registered_games = []
    def _author_channel_check(self, ctx):
        return lambda m: m.author == ctx.author and m.channel == ctx.channel

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
                # now it's async, so we use create_task to not block
                try:
                    asyncio.create_task(record_fn(int(ctx.author.id), game_name, 'win', int(amount), str(getattr(ctx.author, 'name', ctx.author))))
                except Exception:
                    pass
        except Exception:
            pass

    async def _handle_game(self, ctx, internal: str) -> None:
        """Entry point for every named minigame command and hub-launched games."""
        try:
            from utils.user_storage import touch_user as _touch
            asyncio.create_task(_touch(int(ctx.author.id), getattr(ctx.author, "name", None)))
        except Exception:
            pass

        # micro_N → delegate to _micro_play
        if internal.startswith("micro_"):
            try:
                idx = int(internal.split("_", 1)[1])
            except Exception:
                idx = 1
            await self._micro_play(ctx, idx, 0, False, internal)
            return

        # ── helpers ────────────────────────────────────────────────────
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel

        async def wait(timeout=15.0):
            try:
                return await self.bot.wait_for("message", check=check, timeout=timeout)
            except asyncio.TimeoutError:
                return None

        n = internal  # short alias for game name in _award_win calls

        # ── GUESS NUMBER ───────────────────────────────────────────────
        if internal == "guess_number":
            secret = random.randint(1, 20)
            await ctx.send("🔢 I'm thinking of a number between **1 and 20**. Guess it!")
            msg = await wait(20.0)
            if not msg:
                return await ctx.send(f"⏱️ Time's up! It was **{secret}**.")
            try:
                if int(msg.content.strip()) == secret:
                    await ctx.send("✅ Correct!")
                    await self._award_win(ctx, n)
                else:
                    await ctx.send(f"❌ Nope — it was **{secret}**.")
            except ValueError:
                await ctx.send("Send a number.")
            return

        # ── HIGHER / LOWER ─────────────────────────────────────────────
        if internal == "higher_lower":
            a = random.randint(1, 100)
            b = random.randint(1, 100)
            await ctx.send(f"🔢 First number: **{a}**. Will the next number be `higher` or `lower`?")
            msg = await wait(10.0)
            if not msg:
                return await ctx.send(f"⏱️ Time's up! Next was **{b}**.")
            ans = msg.content.lower().strip()
            correct = (b > a and ans in ("higher", "h")) or (b < a and ans in ("lower", "l")) or (b == a and ans in ("equal", "same"))
            if b == a:
                await ctx.send(f"They were equal! ({b})")
            elif correct:
                await ctx.send(f"✅ Correct! Next was **{b}**.")
                await self._award_win(ctx, n)
            else:
                await ctx.send(f"❌ Wrong! Next was **{b}**.")
            return

        # ── BINARY GUESS ───────────────────────────────────────────────
        if internal == "binary_guess":
            pick = random.choice([0, 1])
            await ctx.send("🔢 I picked **0** or **1** — which is it?")
            msg = await wait(8.0)
            if not msg:
                return await ctx.send(f"⏱️ It was **{pick}**.")
            try:
                if int(msg.content.strip()) == pick:
                    await ctx.send("✅ Correct!")
                    await self._award_win(ctx, n)
                else:
                    await ctx.send(f"❌ Nope — it was **{pick}**.")
            except ValueError:
                await ctx.send("Send 0 or 1.")
            return

        # ── STONES (Nim) ───────────────────────────────────────────────
        if internal == "stones":
            pile = random.randint(7, 15)
            await ctx.send(f"🪨 There are **{pile}** stones. Take 1, 2, or 3. The one who takes the last stone **loses**. You go first!")
            while pile > 0:
                msg = await wait(15.0)
                if not msg:
                    return await ctx.send("⏱️ Time's up!")
                try:
                    take = int(msg.content.strip())
                    if take not in (1, 2, 3) or take > pile:
                        await ctx.send("Take 1, 2, or 3 stones.")
                        continue
                    pile -= take
                    if pile == 0:
                        await ctx.send("You took the last stone — you **lose**! 😈")
                        return
                    # Bot plays: avoid leaving multiples of 4
                    bot_take = pile % 4 or random.randint(1, min(3, pile))
                    bot_take = max(1, min(bot_take, min(3, pile)))
                    pile -= bot_take
                    if pile == 0:
                        await ctx.send(f"Bot takes **{bot_take}**. No stones left — bot loses! 🎉")
                        await self._award_win(ctx, n)
                        return
                    await ctx.send(f"Bot takes **{bot_take}**. Stones left: **{pile}**. Your turn (1-3):")
                except ValueError:
                    await ctx.send("Send a number.")
            return

        # ── ROLL ───────────────────────────────────────────────────────
        if internal == "roll":
            result = random.randint(1, 100)
            await ctx.send("🎲 Guess my dice roll (1–100)!")
            msg = await wait(12.0)
            if not msg:
                return await ctx.send(f"⏱️ It was **{result}**.")
            try:
                guess = int(msg.content.strip())
                diff = abs(guess - result)
                if diff == 0:
                    await ctx.send(f"✅ Exact! It was **{result}**!")
                    await self._award_win(ctx, n)
                elif diff <= 5:
                    await ctx.send(f"😮 So close! It was **{result}** (you guessed {guess}).")
                else:
                    await ctx.send(f"❌ It was **{result}** (you guessed {guess}).")
            except ValueError:
                await ctx.send("Send a number.")
            return

        # ── COINFLIP ───────────────────────────────────────────────────
        if internal == "coinflip":
            result = random.choice(["heads", "tails"])
            await ctx.send("🪙 Heads or tails?")
            msg = await wait(8.0)
            if not msg:
                return await ctx.send(f"⏱️ It was **{result}**.")
            if msg.content.lower().strip() in (result, result[0]):
                await ctx.send(f"✅ **{result.capitalize()}** — correct!")
                await self._award_win(ctx, n)
            else:
                await ctx.send(f"❌ It was **{result}**.")
            return

        # ── QUICK MATH ─────────────────────────────────────────────────
        if internal == "quick_math":
            a, b = random.randint(1, 20), random.randint(1, 20)
            op = random.choice(["+", "-", "*"])
            ans = eval(f"{a}{op}{b}")
            await ctx.send(f"🧮 Solve: **{a} {op} {b}**")
            msg = await wait(8.0)
            if not msg:
                return await ctx.send(f"⏱️ Answer: **{ans}**.")
            try:
                if int(msg.content.strip()) == ans:
                    await ctx.send("✅ Correct!")
                    await self._award_win(ctx, n)
                else:
                    await ctx.send(f"❌ Answer was **{ans}**.")
            except ValueError:
                await ctx.send("Send a number.")
            return

        # ── COUNT VOWELS ───────────────────────────────────────────────
        if internal == "count_vowels":
            words = ["strawberry", "programming", "encyclopedia", "mystery", "beautiful", "rhythm"]
            word = random.choice(words)
            vowels = sum(1 for c in word if c in "aeiou")
            await ctx.send(f"🔤 How many vowels are in **{word}**?")
            msg = await wait(10.0)
            if not msg:
                return await ctx.send(f"⏱️ It had **{vowels}** vowels.")
            try:
                if int(msg.content.strip()) == vowels:
                    await ctx.send(f"✅ Correct — **{vowels}** vowels!")
                    await self._award_win(ctx, n)
                else:
                    await ctx.send(f"❌ It had **{vowels}** vowels.")
            except ValueError:
                await ctx.send("Send a number.")
            return

        # ── MATH RACE ──────────────────────────────────────────────────
        if internal == "math_race":
            score = 0
            await ctx.send("🏁 Math Race! Solve **3 problems** as fast as you can.")
            for _ in range(3):
                a, b = random.randint(1, 15), random.randint(1, 15)
                op = random.choice(["+", "-"])
                ans = eval(f"{a}{op}{b}")
                await ctx.send(f"**{a} {op} {b} = ?**")
                msg = await wait(7.0)
                if not msg:
                    await ctx.send(f"⏱️ Too slow! Answer was **{ans}**.")
                    continue
                try:
                    if int(msg.content.strip()) == ans:
                        score += 1
                        await ctx.send("✅")
                    else:
                        await ctx.send(f"❌ ({ans})")
                except ValueError:
                    await ctx.send(f"❌ ({ans})")
            await ctx.send(f"Race over! You got **{score}/3**.")
            if score == 3:
                await self._award_win(ctx, n)
            return

        # ── REVERSE WORD ───────────────────────────────────────────────
        if internal == "reverse_word":
            pool = ["python", "discord", "banana", "keyboard", "dragon", "puzzle", "castle"]
            word = random.choice(pool)
            await ctx.send(f"🔤 Type **{word}** backwards:")
            msg = await wait(12.0)
            if not msg:
                return await ctx.send(f"⏱️ Answer: **{word[::-1]}**.")
            if msg.content.strip().lower() == word[::-1]:
                await ctx.send("✅ Correct!")
                await self._award_win(ctx, n)
            else:
                await ctx.send(f"❌ It was **{word[::-1]}**.")
            return

        # ── PALINDROME ─────────────────────────────────────────────────
        if internal == "palindrome":
            pool = [("racecar", True), ("hello", False), ("level", True), ("world", False), ("civic", True), ("python", False), ("madam", True)]
            word, is_p = random.choice(pool)
            await ctx.send(f"🔤 Is **{word}** a palindrome? (yes/no)")
            msg = await wait(8.0)
            if not msg:
                return await ctx.send(f"⏱️ It {'was' if is_p else 'was not'} a palindrome.")
            ans = msg.content.lower().strip()
            if (is_p and ans in ("yes", "y")) or (not is_p and ans in ("no", "n")):
                await ctx.send("✅ Correct!")
                await self._award_win(ctx, n)
            else:
                await ctx.send(f"❌ It {'was' if is_p else 'was not'} a palindrome.")
            return

        # ── MIMIC ──────────────────────────────────────────────────────
        if internal == "mimic":
            phrases = ["The quick brown fox", "Hello world!", "1 2 3 go", "Discord is fun", "Ludus Bot rocks"]
            phrase = random.choice(phrases)
            await ctx.send(f"🦜 Type this exactly:\n`{phrase}`")
            msg = await wait(15.0)
            if not msg:
                return await ctx.send("⏱️ Time's up!")
            if msg.content == phrase:
                await ctx.send("✅ Perfect copy!")
                await self._award_win(ctx, n)
            else:
                await ctx.send(f"❌ Expected exactly: `{phrase}`")
            return

        # ── WORD CHAIN ─────────────────────────────────────────────────
        if internal == "word_chain":
            start_words = ["apple", "eagle", "elephant", "orange", "umbrella"]
            word = random.choice(start_words)
            await ctx.send(f"🔗 Word Chain! I say **{word}**. Give a word starting with **{word[-1].upper()}** (10s).")
            msg = await wait(10.0)
            if not msg:
                return await ctx.send("⏱️ Time's up!")
            reply = msg.content.strip().lower()
            if reply and reply[0] == word[-1]:
                await ctx.send(f"✅ **{reply}** — good chain!")
                await self._award_win(ctx, n)
            else:
                await ctx.send(f"❌ Must start with **{word[-1].upper()}**.")
            return

        # ── MEMORY / EMOJI MEMORY ──────────────────────────────────────
        if internal in ("memory", "emoji_memory"):
            emojis = ["🍎", "🍌", "🍒", "🍇", "🍉", "🍓", "🍍", "🍑", "🥝", "🍋"]
            length = 4 if internal == "memory" else 6
            seq = [random.choice(emojis) for _ in range(length)]
            await ctx.send(f"🧠 Memorize this sequence ({length} emojis):")
            await ctx.send(" ".join(seq))
            await asyncio.sleep(3.0)
            await ctx.send("Now type the sequence (space-separated, 15s):")
            msg = await wait(15.0)
            if not msg:
                return await ctx.send(f"⏱️ It was: **{' '.join(seq)}**")
            if msg.content.strip() == " ".join(seq):
                await ctx.send("✅ Perfect memory!")
                await self._award_win(ctx, n)
            else:
                await ctx.send(f"❌ Sequence was: **{' '.join(seq)}**")
            return

        # ── EMOJI QUIZ / GUESS THE EMOJI ───────────────────────────────
        if internal in ("emoji_quiz", "guess_the_emoji"):
            pool = [("🍕", "pizza"), ("🐶", "dog"), ("🚀", "rocket"), ("🌍", "earth"),
                    ("🎸", "guitar"), ("⚽", "soccer"), ("🦁", "lion"), ("🌈", "rainbow")]
            emoji, answer = random.choice(pool)
            await ctx.send(f"🤔 What does {emoji} represent? (one word)")
            msg = await wait(10.0)
            if not msg:
                return await ctx.send(f"⏱️ It was **{answer}**.")
            if msg.content.lower().strip() == answer:
                await ctx.send("✅ Correct!")
                await self._award_win(ctx, n)
            else:
                await ctx.send(f"❌ It was **{answer}**.")
            return

        # ── RPS ────────────────────────────────────────────────────────
        if internal == "rps":
            choices = ["rock", "paper", "scissors"]
            bot_pick = random.choice(choices)
            await ctx.send("✂️ Rock, paper, or scissors?")
            msg = await wait(8.0)
            if not msg:
                return await ctx.send(f"⏱️ I picked **{bot_pick}**.")
            player = msg.content.lower().strip()
            if player not in choices:
                return await ctx.send(f"Pick rock, paper, or scissors. I had **{bot_pick}**.")
            wins = {"rock": "scissors", "paper": "rock", "scissors": "paper"}
            if player == bot_pick:
                await ctx.send(f"🤝 Tie! We both picked **{bot_pick}**.")
            elif wins[player] == bot_pick:
                await ctx.send(f"✅ **{player}** beats **{bot_pick}** — you win!")
                await self._award_win(ctx, n)
            else:
                await ctx.send(f"❌ **{bot_pick}** beats **{player}** — you lose!")
            return

        # ── MATCH COLORS ───────────────────────────────────────────────
        if internal == "match_colors":
            colors = ["🔴 red", "🔵 blue", "🟢 green", "🟡 yellow", "🟣 purple"]
            shown = random.sample(colors, 4)
            target = random.choice(shown)
            color_name = target.split()[1]
            await ctx.send(f"🎨 Which emoji matches **{color_name}**?\n" + " | ".join(shown))
            msg = await wait(8.0)
            if not msg:
                return await ctx.send(f"⏱️ It was {target}.")
            if color_name in msg.content.lower():
                await ctx.send("✅ Correct!")
                await self._award_win(ctx, n)
            else:
                await ctx.send(f"❌ It was **{color_name}**.")
            return

        # ── PREDICT ────────────────────────────────────────────────────
        if internal == "predict":
            fortunes = ["🌟 Great things await you!", "⚡ Stay alert today.", "🍀 Luck is on your side.",
                        "🌧️ Patience will be rewarded.", "🔥 Take a bold step forward.", "🌈 Good news is coming."]
            await ctx.send(f"🔮 Your fortune: {random.choice(fortunes)}")
            await self._award_win(ctx, n)
            return

        # ── REACTION TIME ──────────────────────────────────────────────
        if internal == "reaction_time":
            delay = random.uniform(2.0, 5.0)
            await ctx.send("⚡ Wait for it…")
            await asyncio.sleep(delay)
            await ctx.send("**GO!** Type `go` as fast as you can!")
            start = time.perf_counter()
            msg = await wait(5.0)
            if not msg:
                return await ctx.send("⏱️ Too slow!")
            elapsed = time.perf_counter() - start
            if msg.content.lower().strip() == "go":
                await ctx.send(f"⚡ Reaction time: **{elapsed:.3f}s**!")
                if elapsed < 1.5:
                    await self._award_win(ctx, n)
            else:
                await ctx.send("Type `go` not something else!")
            return

        # ── TYPING RACE ────────────────────────────────────────────────
        if internal == "typing_race":
            sentences = ["The quick brown fox jumps over the lazy dog",
                         "Discord bots are fun to build",
                         "Minigames are a great way to pass time",
                         "Python is an amazing programming language"]
            sentence = random.choice(sentences)
            await ctx.send(f"⌨️ Type this exactly:\n`{sentence}`")
            start = time.perf_counter()
            msg = await wait(30.0)
            if not msg:
                return await ctx.send("⏱️ Time's up!")
            elapsed = time.perf_counter() - start
            if msg.content.strip() == sentence:
                await ctx.send(f"✅ Done in **{elapsed:.2f}s**!")
                await self._award_win(ctx, n)
            else:
                await ctx.send("❌ That wasn't exact. Try again!")
            return

        # ── QUICK DRAW ─────────────────────────────────────────────────
        if internal == "quick_draw":
            char = random.choice("ASDFJKL")
            await ctx.send(f"🔫 Type **{char}** as fast as you can!")
            start = time.perf_counter()
            msg = await wait(3.0)
            if not msg:
                return await ctx.send("⏱️ Too slow!")
            elapsed = time.perf_counter() - start
            if msg.content.strip().upper() == char:
                await ctx.send(f"✅ {elapsed:.3f}s!")
                if elapsed < 1.5:
                    await self._award_win(ctx, n)
            else:
                await ctx.send(f"❌ Wrong key! Needed **{char}**.")
            return

        # ── HANGMAN ────────────────────────────────────────────────────
        if internal == "hangman":
            pool = ["python", "discord", "hangman", "castle", "wizard", "dragon", "puzzle", "button"]
            word = random.choice(pool)
            guessed = set()
            lives = 6
            await ctx.send(f"🎯 Hangman! Guess letters. Word: `{''.join(c if c in guessed else '_' for c in word)}` — {lives} lives.")
            while lives > 0:
                msg = await wait(20.0)
                if not msg:
                    return await ctx.send(f"⏱️ Word was **{word}**.")
                letter = msg.content.lower().strip()
                if len(letter) != 1 or not letter.isalpha():
                    await ctx.send("Single letter only.")
                    continue
                if letter in guessed:
                    await ctx.send(f"Already guessed **{letter}**.")
                    continue
                guessed.add(letter)
                if letter in word:
                    display = ''.join(c if c in guessed else '_' for c in word)
                    if '_' not in display:
                        await ctx.send(f"✅ Solved: **{word}**!")
                        await self._award_win(ctx, n)
                        return
                    await ctx.send(f"✅ `{display}` — {lives} lives left.")
                else:
                    lives -= 1
                    await ctx.send(f"❌ No **{letter}**. `{''.join(c if c in guessed else '_' for c in word)}` — {lives} lives left.")
            await ctx.send(f"💀 Game over! Word was **{word}**.")
            return

        # ── UNSCRAMBLE ─────────────────────────────────────────────────
        if internal == "unscramble":
            pool = ["python", "discord", "castle", "wizard", "dragon", "puzzle", "button", "frozen"]
            word = random.choice(pool)
            scrambled = word
            while scrambled == word:
                scrambled = ''.join(random.sample(word, len(word)))
            await ctx.send(f"🔀 Unscramble: **{scrambled}**")
            msg = await wait(15.0)
            if not msg:
                return await ctx.send(f"⏱️ It was **{word}**.")
            if msg.content.lower().strip() == word:
                await ctx.send("✅ Correct!")
                await self._award_win(ctx, n)
            else:
                await ctx.send(f"❌ It was **{word}**.")
            return

        # ── SPELLING BEE ───────────────────────────────────────────────
        if internal == "spelling_bee":
            pool = [("necessary", "necessary"), ("rhythm", "rhythm"), ("occurrence", "occurrence"),
                    ("accommodate", "accommodate"), ("embarrass", "embarrass"), ("liaison", "liaison")]
            word, correct = random.choice(pool)
            await ctx.send(f"🐝 Spell this word: **{word}**")
            msg = await wait(15.0)
            if not msg:
                return await ctx.send(f"⏱️ Correct spelling: **{correct}**.")
            if msg.content.strip() == correct:
                await ctx.send("✅ Correctly spelled!")
                await self._award_win(ctx, n)
            else:
                await ctx.send(f"❌ Correct spelling: **{correct}**.")
            return

        # ── SCRAMBLE SENTENCE ──────────────────────────────────────────
        if internal == "scramble_sentence":
            sentences = ["cats love napping", "dogs chase their tails", "birds fly south in winter", "fish swim in schools"]
            sentence = random.choice(sentences)
            words = sentence.split()
            shuffled = words[:]
            while shuffled == words:
                random.shuffle(shuffled)
            await ctx.send(f"🔀 Unscramble: **{' '.join(shuffled)}**")
            msg = await wait(20.0)
            if not msg:
                return await ctx.send(f"⏱️ It was: **{sentence}**.")
            if msg.content.lower().strip() == sentence:
                await ctx.send("✅ Correct!")
                await self._award_win(ctx, n)
            else:
                await ctx.send(f"❌ It was: **{sentence}**.")
            return

        # ── TEXT TWIST ─────────────────────────────────────────────────
        if internal == "text_twist":
            pool = ["listen", "silent", "enlist", "tinsel", "inlets"]  # anagram groups
            word = "listen"
            anagrams = ["silent", "enlist", "tinsel", "inlets"]
            letters = sorted(word)
            random.shuffle(letters)
            await ctx.send(f"🔤 Make a word using ALL these letters: **{' '.join(letters)}**")
            msg = await wait(20.0)
            if not msg:
                return await ctx.send(f"⏱️ Some valid words: **{', '.join(anagrams[:3])}**.")
            guess = msg.content.lower().strip()
            if sorted(guess) == sorted(word) and len(guess) == len(word):
                await ctx.send(f"✅ **{guess}** — valid!")
                await self._award_win(ctx, n)
            else:
                await ctx.send(f"❌ Must use all {len(word)} letters. E.g. **{anagrams[0]}**.")
            return

        # ── FIRST LETTER ───────────────────────────────────────────────
        if internal == "first_letter":
            pool = [("elephant", "e"), ("umbrella", "u"), ("dragon", "d"), ("python", "p"), ("castle", "c")]
            word, letter = random.choice(pool)
            await ctx.send(f"🔤 What is the **first letter** of `{word}`?")
            msg = await wait(8.0)
            if not msg:
                return await ctx.send(f"⏱️ It was **{letter}**.")
            if msg.content.lower().strip() == letter:
                await ctx.send("✅ Correct!")
                await self._award_win(ctx, n)
            else:
                await ctx.send(f"❌ It was **{letter}**.")
            return

        # ── LAST LETTER ────────────────────────────────────────────────
        if internal == "last_letter":
            pool = [("elephant", "t"), ("umbrella", "a"), ("dragon", "n"), ("python", "n"), ("castle", "e")]
            word, letter = random.choice(pool)
            await ctx.send(f"🔤 What is the **last letter** of `{word}`?")
            msg = await wait(8.0)
            if not msg:
                return await ctx.send(f"⏱️ It was **{letter}**.")
            if msg.content.lower().strip() == letter:
                await ctx.send("✅ Correct!")
                await self._award_win(ctx, n)
            else:
                await ctx.send(f"❌ It was **{letter}**.")
            return

        # ── TRIVIA ─────────────────────────────────────────────────────
        if internal == "trivia":
            pool = [
                ("The sky is blue.", True), ("Fish can climb trees.", False),
                ("Water freezes at 0°C.", True), ("The sun is a planet.", False),
                ("Cats are mammals.", True), ("Diamonds are made of gold.", False),
                ("Humans have 206 bones.", True), ("The moon is made of cheese.", False),
            ]
            statement, answer = random.choice(pool)
            await ctx.send(f"❓ True or false: **{statement}** (yes/no)")
            msg = await wait(10.0)
            if not msg:
                return await ctx.send(f"⏱️ It was **{'true' if answer else 'false'}**.")
            ans = msg.content.lower().strip()
            if (answer and ans in ("yes", "y", "true")) or (not answer and ans in ("no", "n", "false")):
                await ctx.send("✅ Correct!")
                await self._award_win(ctx, n)
            else:
                await ctx.send(f"❌ It was **{'true' if answer else 'false'}**.")
            return

        # ── CAPITALS ───────────────────────────────────────────────────
        if internal == "capitals":
            pool = [("France", "Paris"), ("Japan", "Tokyo"), ("Brazil", "Brasília"),
                    ("Australia", "Canberra"), ("Germany", "Berlin"), ("Canada", "Ottawa"),
                    ("Egypt", "Cairo"), ("Argentina", "Buenos Aires")]
            country, capital = random.choice(pool)
            await ctx.send(f"🌍 What is the capital of **{country}**?")
            msg = await wait(12.0)
            if not msg:
                return await ctx.send(f"⏱️ The capital is **{capital}**.")
            if msg.content.strip().lower() == capital.lower():
                await ctx.send("✅ Correct!")
                await self._award_win(ctx, n)
            else:
                await ctx.send(f"❌ The capital is **{capital}**.")
            return

        # ── SYNONYM ────────────────────────────────────────────────────
        if internal == "synonym":
            pool = [("happy", ["joyful", "glad", "cheerful", "pleased"]),
                    ("fast", ["quick", "swift", "rapid", "speedy"]),
                    ("big", ["large", "huge", "enormous", "giant"]),
                    ("sad", ["unhappy", "miserable", "sorrowful", "gloomy"])]
            word, synonyms = random.choice(pool)
            await ctx.send(f"📖 Give a synonym for **{word}**:")
            msg = await wait(12.0)
            if not msg:
                return await ctx.send(f"⏱️ Some synonyms: **{', '.join(synonyms)}**.")
            if msg.content.lower().strip() in synonyms:
                await ctx.send("✅ Correct synonym!")
                await self._award_win(ctx, n)
            else:
                await ctx.send(f"❌ Some synonyms: **{', '.join(synonyms)}**.")
            return

        # ── ANTONYM ────────────────────────────────────────────────────
        if internal == "antonym":
            pool = [("happy", ["sad", "unhappy", "miserable"]),
                    ("fast", ["slow", "sluggish"]),
                    ("big", ["small", "tiny", "little"]),
                    ("hot", ["cold", "cool", "chilly"])]
            word, antonyms = random.choice(pool)
            await ctx.send(f"📖 Give an antonym (opposite) of **{word}**:")
            msg = await wait(12.0)
            if not msg:
                return await ctx.send(f"⏱️ Some antonyms: **{', '.join(antonyms)}**.")
            if msg.content.lower().strip() in antonyms:
                await ctx.send("✅ Correct antonym!")
                await self._award_win(ctx, n)
            else:
                await ctx.send(f"❌ Some antonyms: **{', '.join(antonyms)}**.")
            return

        # ── MONTH QUIZ ─────────────────────────────────────────────────
        if internal == "month_quiz":
            pool = [("How many days does February have in a non-leap year?", "28"),
                    ("Which month is the 7th month of the year?", "july"),
                    ("How many months have 31 days?", "7"),
                    ("Which month comes after March?", "april")]
            q, a = random.choice(pool)
            await ctx.send(f"📅 {q}")
            msg = await wait(10.0)
            if not msg:
                return await ctx.send(f"⏱️ Answer: **{a}**.")
            if msg.content.lower().strip() == a:
                await ctx.send("✅ Correct!")
                await self._award_win(ctx, n)
            else:
                await ctx.send(f"❌ Answer: **{a}**.")
            return

        # ── WEEKDAY QUIZ ───────────────────────────────────────────────
        if internal == "weekday_quiz":
            pool = [("How many days are in a week?", "7"),
                    ("What day comes after Wednesday?", "thursday"),
                    ("What is the first day of the week (US)?", "sunday"),
                    ("What day comes before Friday?", "thursday")]
            q, a = random.choice(pool)
            await ctx.send(f"📅 {q}")
            msg = await wait(10.0)
            if not msg:
                return await ctx.send(f"⏱️ Answer: **{a}**.")
            if msg.content.lower().strip() == a:
                await ctx.send("✅ Correct!")
                await self._award_win(ctx, n)
            else:
                await ctx.send(f"❌ Answer: **{a}**.")
            return

        # ── SHORT STORY ────────────────────────────────────────────────
        if internal == "short_story":
            prompts = ["adventure", "mystery", "robot", "dragon", "space", "wizard"]
            prompt_word = random.choice(prompts)
            await ctx.send(f"📝 Write a **one-sentence** story using the word **{prompt_word}** (30s):")
            msg = await wait(30.0)
            if not msg:
                return await ctx.send("⏱️ Time's up!")
            if prompt_word in msg.content.lower():
                await ctx.send(f"✅ Great story! Here it is:\n> {msg.content}")
                await self._award_win(ctx, n)
            else:
                await ctx.send(f"❌ Story must contain the word **{prompt_word}**.")
            return

        # ── CHOOSE ─────────────────────────────────────────────────────
        if internal == "choose":
            options = ["pizza", "tacos", "sushi", "burgers", "pasta"]
            pick = random.choice(options)
            await ctx.send(f"🎲 I'll pick from: {', '.join(options)}. Which one will I choose?")
            msg = await wait(8.0)
            if not msg:
                return await ctx.send(f"⏱️ I picked **{pick}**.")
            if msg.content.lower().strip() == pick:
                await ctx.send(f"✅ Correct — **{pick}**!")
                await self._award_win(ctx, n)
            else:
                await ctx.send(f"❌ I picked **{pick}**.")
            return

        # ── TREASURE HUNT ──────────────────────────────────────────────
        if internal == "treasure_hunt":
            words = ["chest", "gold", "map", "island", "compass", "ship", "anchor"]
            hidden = random.choice(words)
            hints = [w for w in words if w != hidden]
            random.shuffle(hints)
            await ctx.send(f"🗺️ The treasure word is hidden among these: **{', '.join(hints[:4] + [hidden])}**. Which is the real treasure? (starts with `{hidden[0]}`)")
            msg = await wait(10.0)
            if not msg:
                return await ctx.send(f"⏱️ Treasure was **{hidden}**.")
            if msg.content.lower().strip() == hidden:
                await ctx.send("✅ Treasure found!")
                await self._award_win(ctx, n)
            else:
                await ctx.send(f"❌ Treasure was **{hidden}**.")
            return

        # ── LABELLING ──────────────────────────────────────────────────
        if internal == "labelling":
            categories = [
                ("🍎🍌🍒🍇", "fruits"),
                ("🐶🐱🐭🐹", "animals"),
                ("🚗🚕🚙🚌", "vehicles"),
                ("⚽🏀🏈⚾", "sports balls"),
            ]
            emojis, label = random.choice(categories)
            await ctx.send(f"🏷️ What category do these belong to?\n{emojis}")
            msg = await wait(10.0)
            if not msg:
                return await ctx.send(f"⏱️ Category: **{label}**.")
            if label.lower() in msg.content.lower():
                await ctx.send("✅ Correct!")
                await self._award_win(ctx, n)
            else:
                await ctx.send(f"❌ Category: **{label}**.")
            return

        # ── FIND PAIR ──────────────────────────────────────────────────
        if internal == "find_pair":
            pool = ["apple", "banana", "cherry"]
            items = pool * 2
            random.shuffle(items)
            displayed = [f"{i+1}:{v}" for i, v in enumerate(items)]
            await ctx.send(f"🔍 Find a matching pair! Items: **{', '.join(displayed)}**\nType a word that appears twice:")
            msg = await wait(15.0)
            if not msg:
                return await ctx.send("⏱️ Time's up! All words appear twice.")
            guess = msg.content.lower().strip()
            if guess in pool:
                await ctx.send(f"✅ **{guess}** appears twice — correct!")
                await self._award_win(ctx, n)
            else:
                await ctx.send(f"❌ Any of {', '.join(pool)} would work.")
            return

        # ── ODD ONE OUT ────────────────────────────────────────────────
        if internal == "odd_one_out":
            groups = [
                (["cat", "dog", "fish", "car"], "car"),
                (["red", "blue", "green", "piano"], "piano"),
                (["apple", "banana", "laptop", "cherry"], "laptop"),
                (["run", "jump", "swim", "table"], "table"),
            ]
            items, odd = random.choice(groups)
            random.shuffle(items)
            await ctx.send(f"🔍 Odd one out: **{', '.join(items)}**")
            msg = await wait(10.0)
            if not msg:
                return await ctx.send(f"⏱️ Odd one out was **{odd}**.")
            if msg.content.lower().strip() == odd:
                await ctx.send("✅ Correct!")
                await self._award_win(ctx, n)
            else:
                await ctx.send(f"❌ Odd one out was **{odd}**.")
            return

        # ── SEQUENCE COMPLETE ──────────────────────────────────────────
        if internal == "sequence_complete":
            start = random.randint(1, 10)
            step = random.randint(2, 5)
            seq = [start + step * i for i in range(4)]
            nxt = seq[-1] + step
            await ctx.send(f"🔢 Complete the sequence: **{', '.join(map(str, seq))}, ?**")
            msg = await wait(12.0)
            if not msg:
                return await ctx.send(f"⏱️ Next was **{nxt}** (step +{step}).")
            try:
                if int(msg.content.strip()) == nxt:
                    await ctx.send(f"✅ Correct — step was +{step}!")
                    await self._award_win(ctx, n)
                else:
                    await ctx.send(f"❌ Next was **{nxt}** (step +{step}).")
            except ValueError:
                await ctx.send("Send a number.")
            return

        # ── TAP COUNT ──────────────────────────────────────────────────
        if internal == "tap_count":
            target = random.randint(3, 7)
            await ctx.send(f"👆 React with 👆 exactly **{target}** times on the next message!")
            msg_obj = await ctx.send("React here! 👇")
            await msg_obj.add_reaction("👆")
            await asyncio.sleep(12.0)
            try:
                updated = await ctx.channel.fetch_message(msg_obj.id)
                count = next((r.count - 1 for r in updated.reactions if str(r.emoji) == "👆"), 0)
                if count == target:
                    await ctx.send(f"✅ {count} taps — correct!")
                    await self._award_win(ctx, n)
                else:
                    await ctx.send(f"❌ You tapped {count} times, needed {target}.")
            except Exception:
                await ctx.send("Could not count reactions.")
            return

        # ── BUBBLE POP ─────────────────────────────────────────────────
        if internal == "bubble_pop":
            colors = {"🟢": "green", "🔵": "blue", "🟡": "yellow", "🔴": "red"}
            emoji, color = random.choice(list(colors.items()))
            await ctx.send(f"💥 Pop the **{color}** bubble! Type its color:")
            msg = await wait(8.0)
            if not msg:
                return await ctx.send(f"⏱️ It was **{color}**. {emoji} Pop!")
            if msg.content.lower().strip() == color:
                await ctx.send(f"💥 Pop! **{emoji}** popped!")
                await self._award_win(ctx, n)
            else:
                await ctx.send(f"❌ It was **{color}**. {emoji}")
            return

        # ── PICK A CARD ────────────────────────────────────────────────
        if internal == "pick_a_card":
            suits = ["♠️ Spades", "♥️ Hearts", "♦️ Diamonds", "♣️ Clubs"]
            ranks = ["2","3","4","5","6","7","8","9","10","Jack","Queen","King","Ace"]
            card = f"{random.choice(ranks)} of {random.choice(suits)}"
            suit_options = [s.split()[1] for s in suits]
            await ctx.send(f"🃏 I drew a card. What **suit** is it? ({' / '.join(suit_options)})")
            msg = await wait(10.0)
            actual_suit = card.split(" of ")[1].split()[1]
            if not msg:
                return await ctx.send(f"⏱️ Card was **{card}**.")
            if msg.content.strip().lower() == actual_suit.lower():
                await ctx.send(f"✅ Correct — it was **{card}**!")
                await self._award_win(ctx, n)
            else:
                await ctx.send(f"❌ Card was **{card}**.")
            return

        # ── NUMBER CHAIN ───────────────────────────────────────────────
        if internal == "number_chain":
            await ctx.send("🔢 I'll say a number, you add the step and say the next. **Step is +3**. I start with **1** — what's next?")
            current = 1
            step = 3
            for _ in range(5):
                expected = current + step
                msg = await wait(8.0)
                if not msg:
                    return await ctx.send(f"⏱️ Next was **{expected}**.")
                try:
                    if int(msg.content.strip()) == expected:
                        current = expected
                        if _ == 4:
                            await ctx.send(f"✅ Full chain complete!")
                            await self._award_win(ctx, n)
                        else:
                            await ctx.send(f"✅ Next (+{step}):")
                    else:
                        return await ctx.send(f"❌ Expected **{expected}** (you had {current}, +{step}).")
                except ValueError:
                    return await ctx.send("Send a number.")
            return

        # ── COLOR GUESS ────────────────────────────────────────────────
        if internal == "color_guess":
            colors = ["red", "blue", "green", "yellow", "purple", "orange"]
            picked = random.choice(colors)
            sample = random.sample(colors, 4)
            if picked not in sample:
                sample[0] = picked
                random.shuffle(sample)
            await ctx.send(f"🎨 I'm thinking of a color. Options: **{', '.join(sample)}**. Which is it?")
            msg = await wait(8.0)
            if not msg:
                return await ctx.send(f"⏱️ It was **{picked}**.")
            if msg.content.lower().strip() == picked:
                await ctx.send("✅ Correct!")
                await self._award_win(ctx, n)
            else:
                await ctx.send(f"❌ It was **{picked}**.")
            return

        # ── FLIP WORDS ─────────────────────────────────────────────────
        if internal == "flip_words":
            sentences = ["the cat sat", "I love pizza", "sky is blue", "dogs are loyal", "code never lies"]
            sentence = random.choice(sentences)
            flipped = " ".join(reversed(sentence.split()))
            await ctx.send(f"🔄 Reverse the word order: **{sentence}**")
            msg = await wait(12.0)
            if not msg:
                return await ctx.send(f"⏱️ Answer: **{flipped}**.")
            if msg.content.lower().strip() == flipped.lower():
                await ctx.send("✅ Correct!")
                await self._award_win(ctx, n)
            else:
                await ctx.send(f"❌ Answer: **{flipped}**.")
            return

        # ── GUESS THE EMOJI (duplicate key handled above) ──────────────

        # ── FAST TYPE MICRO (hub only) ─────────────────────────────────
        if internal == "fast_type_micro":
            char = random.choice("ASDFJKL;")
            await ctx.send(f"⚡ Type **{char}** FAST!")
            start = time.perf_counter()
            msg = await wait(3.0)
            if not msg:
                return await ctx.send("⏱️ Too slow!")
            elapsed = time.perf_counter() - start
            if msg.content.strip().upper() == char.upper():
                await ctx.send(f"⚡ {elapsed:.3f}s!")
                if elapsed < 2.0:
                    await self._award_win(ctx, n)
            else:
                await ctx.send(f"❌ Needed **{char}**.")
            return

        # ── Unknown named game → micro fallback ───────────────────────
        await self._micro_play(ctx, 1, 0, False, internal)

    async def _micro_play(self, ctx, kind: int, variant: int, is_advanced: bool, name: str):
        """Handle micro games by index.

        The first parameter is the micro index (1..250). We map indices
        to one of ten small kinds and vary difficulty by index range.
        """
        # normalize inputs: treat `kind` as the micro index (legacy callers)
        try:
            idx = int(kind)
        except Exception:
            idx = 1
        kind_id = (idx - 1) % 20
        difficulty = (idx - 1) // 20  # 0..12
        adv = is_advanced or (difficulty > 0)

        async def wait_for_reply(timeout: float):
            try:
                msg = await self.bot.wait_for('message', timeout=timeout, check=self._author_channel_check(ctx))
                return msg
            except asyncio.TimeoutError:
                return None

        # KIND 0: parity / even-odd
        if kind_id == 0:
            n = random.randint(1, 20 + difficulty)
            await ctx.send(f"I thought of a number between 1 and {20 + difficulty}. Is it even or odd?")
            msg = await wait_for_reply(8.0 if not adv else 6.0)
            if not msg:
                await ctx.send(f"Timed out. It was **{n}**.")
                return
            ans = "even" if n % 2 == 0 else "odd"
            if msg.content.lower().strip() in (ans, ans[0]):
                await ctx.send("Correct!")
                await self._award_win(ctx, name)
            else:
                await ctx.send(f"No — it was **{ans}** ({n}).")
            return

        # KIND 1: dice sum (2..6*rolls)
        if kind_id == 1:
            rolls = 2 + (difficulty % 3)
            dice = [random.randint(1, 6) for _ in range(rolls)]
            total = sum(dice)
            await ctx.send(f"I rolled {rolls} dice. Guess the total sum (1..{6*rolls}).")
            msg = await wait_for_reply(10.0 if not adv else 8.0)
            if not msg:
                await ctx.send(f"Timed out. It was **{total}** ({', '.join(map(str,dice))}).")
                return
            try:
                guess = int(msg.content.strip())
            except Exception:
                await ctx.send("Send a number.")
                return
            if guess == total:
                await ctx.send("Spot on!")
                await self._award_win(ctx, name)
            else:
                await ctx.send(f"No — it was **{total}**")
            return

        # KIND 2: quick math
        if kind_id == 2:
            a = random.randint(1, 10 + difficulty)
            b = random.randint(1, 10 + difficulty)
            op = random.choice(['+', '-', '*'])
            expr = f"{a}{op}{b}"
            ans = eval(expr)
            await ctx.send(f"Solve quickly: {expr}")
            msg = await wait_for_reply(8.0 if not adv else 6.0)
            if not msg:
                await ctx.send(f"Timed out. Answer: **{ans}**")
                return
            try:
                if int(msg.content.strip()) == ans:
                    await ctx.send("Correct!")
                    await self._award_win(ctx, name)
                else:
                    await ctx.send(f"Wrong — {ans}")
            except Exception:
                await ctx.send("Send a number.")
            return

        # KIND 3: reverse word
        if kind_id == 3:
            pool = ["apple", "bread", "crane", "delta", "python", "ludus"]
            word = random.choice(pool)
            to_type = word[::-1]
            await ctx.send(f"Type the reverse of: **{word}**")
            msg = await wait_for_reply(10.0 if not adv else 8.0)
            if not msg:
                await ctx.send(f"Timed out. Answer: **{to_type}**")
                return
            if msg.content.strip() == to_type:
                await ctx.send("Correct!")
                await self._award_win(ctx, name)
            else:
                await ctx.send(f"No — it was **{to_type}**")
            return

        # KIND 4: emoji memory
        if kind_id == 4:
            emojis = ["🍎","🍌","🍒","🍇","🍉","🍓","🍍","🍑"]
            length = 3 + (difficulty % 3)
            seq = [random.choice(emojis) for _ in range(length)]
            await ctx.send("Memorize:")
            await ctx.send(" ".join(seq))
            await asyncio.sleep(1 + (0 if not adv else 1))
            await ctx.send("Now type the sequence exactly (space separated).")
            msg = await wait_for_reply(10.0 if not adv else 8.0)
            if not msg:
                await ctx.send(f"Timed out. Answer: **{' '.join(seq)}**")
                return
            if msg.content.strip() == " ".join(seq):
                await ctx.send("Correct!")
                await self._award_win(ctx, name)
            else:
                await ctx.send(f"Wrong — {' '.join(seq)}")
            return

        # KIND 5: color pick (guess which color was chosen)
        if kind_id == 5:
            colors = ["red","blue","green","yellow","purple","orange"]
            picked = random.choice(colors)
            opts = random.sample(colors, k=4) if len(colors) >= 4 else colors
            if picked not in opts:
                opts[0] = picked
                random.shuffle(opts)
            await ctx.send("Which color did I pick? Options: " + ", ".join(opts))
            msg = await wait_for_reply(8.0 if not adv else 6.0)
            if not msg:
                await ctx.send(f"Timed out. It was **{picked}**")
                return
            if msg.content.lower().strip() == picked:
                await ctx.send("Correct!")
                await self._award_win(ctx, name)
            else:
                await ctx.send(f"No — it was **{picked}**")
            return

        # KIND 6: fast type a character
        if kind_id == 6:
            ch = random.choice('asdfjkl;')
            await ctx.send(f"Type this character as fast as you can: **{ch}**")
            start = time.perf_counter()
            msg = await wait_for_reply(4.0 if not adv else 3.0)
            if not msg:
                await ctx.send("Too slow or timed out.")
                return
            elapsed = time.perf_counter() - start
            if msg.content.strip() == ch and elapsed <= (1.5 if not adv else 1.0):
                await ctx.send(f"Nice — {elapsed:.2f}s")
                await self._award_win(ctx, name)
            else:
                await ctx.send(f"No — you sent '{msg.content.strip()}' in {elapsed:.2f}s")
            return

        # KIND 7: unscramble
        if kind_id == 7:
            pool = ["game","word","friend","apple","music","quick"]
            w = random.choice(pool)
            scrambled = ''.join(random.sample(list(w), len(w)))
            await ctx.send(f"Unscramble: **{scrambled}**")
            msg = await wait_for_reply(12.0 if not adv else 10.0)
            if not msg:
                await ctx.send(f"Timed out. Answer: **{w}**")
                return
            if msg.content.lower().strip() == w:
                await ctx.send("Correct!")
                await self._award_win(ctx, name)
            else:
                await ctx.send(f"No — it was **{w}**")
            return

        # KIND 8: yes/no trivia (simple)
        if kind_id == 8:
            pool = [("Is the sky blue?","yes"),("Do cats bark?","no"),("Is water wet?","yes"),("Is fire cold?","no")]
            q,a = random.choice(pool)
            await ctx.send(q)
            msg = await wait_for_reply(10.0 if not adv else 8.0)
            if not msg:
                await ctx.send(f"Timed out. Answer: **{a}**")
                return
            if msg.content.lower().strip() in (a, a[0]):
                await ctx.send("Correct!")
                await self._award_win(ctx, name)
            else:
                await ctx.send(f"No — {a}")
            return

        # KIND 9: pick item from list
        if kind_id == 9:
            pools = [["apple","bread","crane","delta"], ["red","blue","green","yellow"], ["dog","cat","fox","owl"]]
            items = pools[difficulty % len(pools)]
            picked = random.choice(items)
            await ctx.send("Guess the item I picked: " + ", ".join(items))
            msg = await wait_for_reply(10.0 if not adv else 8.0)
            if not msg:
                await ctx.send(f"Timed out. It was **{picked}**")
                return
            if msg.content.lower().strip() == picked:
                await ctx.send("Correct!")
                await self._award_win(ctx, name)
            else:
                await ctx.send(f"No — it was **{picked}**")
            return

        # KIND 10: find pair
        if kind_id == 10:
            items = ["apple", "banana", "cherry", "apple", "banana", "cherry"]
            random.shuffle(items)
            await ctx.send(f"Find the matching pair: {', '.join(items)}")

            def check(m):
                return m.author == ctx.author and m.channel == ctx.channel

            try:
                msg = await self.bot.wait_for("message", check=check, timeout=15.0)
                if msg.content.lower() in items and items.count(msg.content.lower()) > 1:
                    await ctx.send("Correct! You found a pair.")
                    await self._award_win(ctx, "find_pair")
                else:
                    await ctx.send("Wrong! No matching pair found.")
            except asyncio.TimeoutError:
                await ctx.send("You ran out of time!")
            return

        # KIND 11: odd one out
        if kind_id == 11:
            items = ["cat", "dog", "fish", "car"]
            odd_one = "car"
            random.shuffle(items)
            await ctx.send(f"Identify the odd one out: {', '.join(items)}")

            def check(m):
                return m.author == ctx.author and m.channel == ctx.channel

            try:
                msg = await self.bot.wait_for("message", check=check, timeout=15.0)
                if msg.content.lower() == odd_one:
                    await ctx.send("Correct! You found the odd one out.")
                    await self._award_win(ctx, "odd_one_out")
                else:
                    await ctx.send(f"Wrong! The odd one out was {odd_one}.")
            except asyncio.TimeoutError:
                await ctx.send(f"You ran out of time! The odd one out was {odd_one}.")
            return

        # KIND 12: sequence complete
        if kind_id == 12:
            sequence = [random.randint(1, 10) for _ in range(4)]
            next_number = sequence[-1] + (sequence[-1] - sequence[-2])
            await ctx.send(f"Complete the sequence: {', '.join(map(str, sequence))}, ?")

            def check(m):
                return m.author == ctx.author and m.channel == ctx.channel

            try:
                msg = await self.bot.wait_for("message", check=check, timeout=15.0)
                if int(msg.content) == next_number:
                    await ctx.send("Correct! You completed the sequence.")
                    await self._award_win(ctx, "sequence_complete")
                else:
                    await ctx.send(f"Wrong! The next number was {next_number}.")
            except asyncio.TimeoutError:
                await ctx.send(f"You ran out of time! The next number was {next_number}.")
            return

        # KIND 13: tap count
        if kind_id == 13:
            await ctx.send("Tap the reaction as many times as you can in 10 seconds!")
            message = await ctx.send("Start tapping! 🖱️")
            await message.add_reaction("🖱️")

            def reaction_check(reaction, user):
                return user == ctx.author and str(reaction.emoji) == "🖱️"

            reaction_count = 0
            try:
                while True:
                    reaction, user = await self.bot.wait_for("reaction_add", check=reaction_check, timeout=10.0)
                    reaction_count += 1
            except asyncio.TimeoutError:
                await ctx.send(f"Time's up! You tapped {reaction_count} times.")
            return

        # KIND 14: bubble pop
        if kind_id == 14:
            bubbles = ["🟢", "🔵", "🟡", "🔴"]
            await ctx.send(f"Pop the bubbles by typing their colors: {', '.join(bubbles)}")

            def color_check(m):
                return m.author == ctx.author and m.channel == ctx.channel and m.content.lower() in ["green", "blue", "yellow", "red"]

            try:
                msg = await self.bot.wait_for("message", check=color_check, timeout=15.0)
                await ctx.send("Pop! You popped a bubble.")
                await self._award_win(ctx, "bubble_pop")
            except asyncio.TimeoutError:
                await ctx.send("You ran out of time! The bubbles floated away.")
            return

        # KIND 15: quick draw
        if kind_id == 15:
            char = random.choice(["A", "B", "C", "D", "E"])
            await ctx.send(f"Type this character as fast as you can: **{char}**")

            def check(m):
                return m.author == ctx.author and m.channel == ctx.channel and m.content == char

            start_time = time.perf_counter()
            try:
                msg = await self.bot.wait_for("message", check=check, timeout=10.0)
                reaction_time = time.perf_counter() - start_time
                await ctx.send(f"You typed it in {reaction_time:.2f} seconds! Well done.")
                await self._award_win(ctx, "quick_draw")
            except asyncio.TimeoutError:
                await ctx.send("You didn't type the character in time!")
            return

        # KIND 16: number chain
        if kind_id == 16:
            await ctx.send("Start the number chain! Say a number.")

            def check(m):
                return m.author == ctx.author and m.channel == ctx.channel and m.content.isdigit()

            try:
                msg = await self.bot.wait_for("message", check=check, timeout=30.0)
                next_number = int(msg.content) + 1
                await ctx.send(f"Great! Now say the next number: {next_number}.")
            except asyncio.TimeoutError:
                await ctx.send("You took too long to respond!")
            return

        # KIND 17: color guess
        if kind_id == 17:
            colors = ["red", "blue", "green", "yellow"]
            correct_color = random.choice(colors)
            await ctx.send(f"Guess the color I'm thinking of: {', '.join(colors)}")

            def author_check(m):
                return m.author == ctx.author and m.channel == ctx.channel and m.content.lower() in colors

            try:
                msg = await self.bot.wait_for("message", check=author_check, timeout=15.0)
                if msg.content.lower() == correct_color:
                    await ctx.send("Correct! You guessed the color.")
                    await self._award_win(ctx, "color_guess")
                else:
                    await ctx.send(f"Wrong! The correct color was {correct_color}.")
            except asyncio.TimeoutError:
                await ctx.send(f"You ran out of time! The correct color was {correct_color}.")
            return

        # KIND 18: flip words
        if kind_id == 18:
            sentence = "The quick brown fox"
            flipped = " ".join(reversed(sentence.split()))
            await ctx.send(f"Flip the order of these words: **{sentence}**")

            def check(m):
                return m.author == ctx.author and m.channel == ctx.channel

            try:
                msg = await self.bot.wait_for("message", check=check, timeout=15.0)
                if msg.content == flipped:
                    await ctx.send("Correct! You flipped the words.")
                    await self._award_win(ctx, "flip_words")
                else:
                    await ctx.send(f"Wrong! The correct order was: {flipped}.")
            except asyncio.TimeoutError:
                await ctx.send(f"You ran out of time! The correct order was: {flipped}")
            return

        # KIND 19: pick a card
        if kind_id == 19:
            suits = ["Hearts", "Diamonds", "Clubs", "Spades"]
            ranks = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "Jack", "Queen", "King", "Ace"]
            card = f"{random.choice(ranks)} of {random.choice(suits)}"
            await ctx.send("I picked a card. Guess what it is!")

            def check(m):
                return m.author == ctx.author and m.channel == ctx.channel

            try:
                msg = await self.bot.wait_for("message", check=check, timeout=30.0)
                if msg.content.lower() == card.lower():
                    await ctx.send("Correct! You guessed the card.")
                    await self._award_win(ctx, "pick_a_card")
                else:
                    await ctx.send(f"Wrong! The card was {card}.")
            except asyncio.TimeoutError:
                await ctx.send(f"You ran out of time! The card was {card}.")
            return

        # Unknown kind — silent fallback
        await ctx.send("🎮 Game not found. Try another one!")

    # ------------------------------------------------------------------ #
    #  /minigames slash command — interactive hub                          #
    # ------------------------------------------------------------------ #

    @app_commands.command(name="minigames", description="🎮 Open the Minigames Hub and pick a game to play!")
    async def minigames_slash(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)
        view = MinigamesHubView(self, interaction.user)
        await interaction.followup.send(view=view)

    async def _hub_play(self, interaction: discord.Interaction, game_key: str):
        """Run a minigame from the hub using a fake ctx-like object."""
        try:
            from utils.user_storage import touch_user as _touch
            asyncio.create_task(_touch(int(interaction.user.id), str(interaction.user)))
        except Exception:
            pass

        # Build a lightweight ctx proxy so existing _award_win / wait_for logic works
        ctx = _HubCtx(self.bot, interaction)
        await self._handle_game(ctx, game_key)


# ======================================================================
# Hub Views — used by the /minigames slash command
# ======================================================================

# All named base games grouped by category.
# Each entry: (command_key, display_name, short_description)
# Views page through them 4 at a time (leaving room for nav buttons).
_HUB_CATEGORIES: dict[str, list[tuple[str, str, str]]] = {
    "🧠 Knowledge": [
        ("trivia",        "Trivia",        "Answer a yes/no trivia question."),
        ("emoji_quiz",    "Emoji Quiz",    "Guess what the emoji means."),
        ("capitals",      "Capitals",      "Name the capital of a country."),
        ("month_quiz",    "Month Quiz",    "Which month has X?"),
        ("weekday_quiz",  "Weekday Quiz",  "Which weekday is X?"),
        ("first_letter",  "First Letter",  "Give the first letter of a word."),
        ("last_letter",   "Last Letter",   "Give the last letter of a word."),
        ("guess_the_emoji","Guess Emoji",  "Guess the meaning of an emoji sequence."),
    ],
    "🔢 Numbers": [
        ("quick_math",        "Quick Math",     "Solve a quick arithmetic problem."),
        ("sequence_complete", "Sequence",       "Complete the number sequence."),
        ("math_race",         "Math Race",      "Answer several math problems fast."),
        ("binary_guess",      "Binary Guess",   "Guess 0 or 1 — binary challenge."),
        ("number_chain",      "Number Chain",   "Continue the counting chain."),
        ("stones",            "Stones",         "Remove stones (mini Nim game)."),
    ],
    "📝 Words": [
        ("hangman",          "Hangman",          "Classic hangman."),
        ("unscramble",       "Unscramble",       "Unscramble a jumbled word."),
        ("spelling_bee",     "Spelling Bee",     "Spell the given word correctly."),
        ("scramble_sentence","Scramble Sentence","Unscramble the mixed-up sentence."),
        ("text_twist",       "Text Twist",       "Make a new word from the given letters."),
        ("word_chain",       "Word Chain",       "Add a word starting with the last letter."),
    ],
    "✍️ Language": [
        ("reverse_word", "Reverse Word", "Type the word backwards."),
        ("flip_words",   "Flip Words",   "Reverse the word order in a sentence."),
        ("palindrome",   "Palindrome",   "Is the word a palindrome?"),
        ("count_vowels", "Count Vowels", "Count the vowels in a word."),
        ("synonym",      "Synonym",      "Give a synonym for the shown word."),
        ("antonym",      "Antonym",      "Give an antonym for the shown word."),
    ],
    "⚡ Speed": [
        ("reaction_time", "Reaction",   "Test your reaction speed."),
        ("quick_draw",    "Quick Draw", "Type a character as fast as you can."),
        ("typing_race",   "Type Race",  "Type a sentence quickly."),
        ("tap_count",     "Tap Count",  "Count taps quickly."),
        ("bubble_pop",    "Bubble Pop", "Pop virtual bubbles."),
        ("fast_type_micro","Fast Type", "Type the shown character as fast as possible."),
    ],
    "🎲 Luck": [
        ("coinflip",     "Coin Flip",    "Heads or tails — 50/50 chance."),
        ("roll",         "Dice Roll",    "Guess the dice total."),
        ("guess_number", "Guess Number", "Guess the secret number 1–20."),
        ("pick_a_card",  "Pick a Card",  "Guess the randomly drawn card."),
        ("higher_lower", "Higher/Lower", "Predict whether next number is higher or lower."),
        ("predict",      "Predict",      "Let the bot tell your fortune."),
    ],
    "🖼️ Memory": [
        ("memory",       "Memory",       "Remember and repeat the emoji sequence."),
        ("emoji_memory", "Emoji Memory", "Recall a longer emoji sequence."),
        ("match_colors", "Match Colors", "Quickly pick the matching color."),
        ("color_guess",  "Color Guess",  "Guess which color was secretly picked."),
    ],
    "🧩 Puzzle": [
        ("find_pair",     "Find Pair",     "Spot the matching pair in a list."),
        ("odd_one_out",   "Odd One Out",   "Identify the item that doesn't belong."),
        ("treasure_hunt", "Treasure Hunt", "Find the hidden treasure word."),
        ("labelling",     "Labelling",     "Label items correctly under time pressure."),
        ("choose",        "Choose",        "Have the bot pick an option for you."),
        ("binary_guess",  "Binary Guess",  "0 or 1 — which did the bot pick?"),
    ],
    "🎭 Fun": [
        ("rps",         "Rock Paper Scissors", "Classic RPS against the bot."),
        ("mimic",       "Mimic",               "Repeat back exactly what you send."),
        ("short_story", "Short Story",         "Create a mini story from a word."),
    ],
}


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


class MinigamesHubView(discord.ui.LayoutView):
    """Main hub — Components V2."""

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
            "Pick a **category** to browse, then press **▶ Play** to start!\n"
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
                return await interaction.response.send_message(
                    "❌ This panel isn't yours!", ephemeral=True)
            view = MinigamesCategoryView(self.cog, self.user, cat)
            await interaction.response.edit_message(view=view)
        return callback

    async def on_timeout(self): self.clear_items()


class MinigamesCategoryView(discord.ui.LayoutView):
    """Games in one category — paginated 4/page. Components V2."""
    _PAGE_SIZE = 4

    def __init__(self, cog, user, category: str, page: int = 0):
        super().__init__(timeout=120)
        self.cog = cog; self.user = user
        self.category = category; self.page = page
        self._games = _HUB_CATEGORIES[category]
        self._build()

    def _page_games(self): return self._games[self.page*self._PAGE_SIZE:(self.page+1)*self._PAGE_SIZE]

    @property
    def _total_pages(self):
        import math; return max(1, math.ceil(len(self._games)/self._PAGE_SIZE))

    def _build(self):
        self.clear_items()
        games = self._page_games()
        lines = [f"**{name}** — {desc}" for _, name, desc in games]
        hdr = (
            f"## {self.category}\n"
            f"Page **{self.page+1}/{self._total_pages}** — press **▶ Play** to start!\n\n"
            + "\n".join(lines)
        )
        game_rows = []
        for i in range(0, len(games), 2):
            btns = []
            for key, name, _ in games[i:i+2]:
                btn = discord.ui.Button(
                    label=f"▶ {name}", style=discord.ButtonStyle.success,
                    custom_id=f"hub_play_{key}_{self.page}_{i}",
                )
                btn.callback = self._make_play_callback(key, name)
                btns.append(btn)
            game_rows.append(discord.ui.ActionRow(*btns))
        nav: list[discord.ui.Button] = []
        if self.page > 0:
            p = discord.ui.Button(label="◄ Prev", style=discord.ButtonStyle.secondary, custom_id="hub_prev")
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
                return await interaction.response.send_message(
                    "❌ This panel isn't yours!", ephemeral=True)
            rv = _PlayingView(self.cog, self.user, key, name, self.category, self.page)
            await interaction.response.edit_message(view=rv)
            asyncio.create_task(self._run_game(interaction, key, name, rv))
        return callback

    async def _prev_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user.id:
            return await interaction.response.send_message("❌ Not yours!", ephemeral=True)
        await interaction.response.edit_message(
            view=MinigamesCategoryView(self.cog, self.user, self.category, self.page-1))

    async def _next_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user.id:
            return await interaction.response.send_message("❌ Not yours!", ephemeral=True)
        await interaction.response.edit_message(
            view=MinigamesCategoryView(self.cog, self.user, self.category, self.page+1))

    async def _run_game(self, interaction, key, name, view):
        await self.cog._hub_play(interaction, key)
        try:
            dv = _PlayingView(self.cog, self.user, key, name, self.category, self.page)
            dv.enable_buttons()
            await interaction.edit_original_response(view=dv)
        except Exception: pass

    async def _back_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user.id:
            return await interaction.response.send_message("❌ Not yours!", ephemeral=True)
        await interaction.response.edit_message(view=MinigamesHubView(self.cog, self.user))


class _PlayingView(discord.ui.LayoutView):
    """While/after a game. Components V2."""

    def __init__(self, cog, user, key, name, category, page=0):
        super().__init__(timeout=180)
        self.cog = cog; self.user = user
        self.key = key; self.name = name
        self.category = category; self.page = page
        self._finished = False; self._build()

    def enable_buttons(self): self._finished = True; self._build()

    def _build(self):
        self.clear_items()
        if self._finished:
            txt = discord.ui.TextDisplay(f"## ✅ {self.name} — Finished!\nGame complete! What next?")
            col = discord.Colour.blurple()
        else:
            txt = discord.ui.TextDisplay(
                f"## 🎮 Playing: {self.name}\n**Starting…**\n\n"
                "Reply with your answer when prompted!\n*Buttons activate when done.*"
            )
            col = discord.Colour.gold()
        pa = discord.ui.Button(label='🔄 Play Again',style=discord.ButtonStyle.success,custom_id='play_again',disabled=not self._finished)
        pa.callback = self._play_again_callback
        bk = discord.ui.Button(label='◄ Back',style=discord.ButtonStyle.secondary,custom_id='back_to_cat',disabled=not self._finished)
        bk.callback = self._back_callback
        hb = discord.ui.Button(label='🏠 Hub',style=discord.ButtonStyle.primary,custom_id='go_hub',disabled=not self._finished)
        hb.callback = self._hub_callback
        self.add_item(discord.ui.Container(
            txt, discord.ui.Separator(), discord.ui.ActionRow(pa, bk, hb),
            accent_colour=col,
        ))

    async def _play_again_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user.id:
            return await interaction.response.send_message("❌ Not your game!", ephemeral=True)
        nv = _PlayingView(self.cog, self.user, self.key, self.name, self.category, self.page)
        await interaction.response.edit_message(view=nv)
        asyncio.create_task(MinigamesCategoryView(self.cog, self.user, self.category, self.page)._run_game(interaction, self.key, self.name, nv))

    async def _back_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user.id:
            return await interaction.response.send_message("❌ Not your game!", ephemeral=True)
        await interaction.response.edit_message(view=MinigamesCategoryView(self.cog, self.user, self.category, self.page))

    async def _hub_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user.id:
            return await interaction.response.send_message("❌ Not your game!", ephemeral=True)
        await interaction.response.edit_message(view=MinigamesHubView(self.cog, self.user))



# ======================================================================
# Cog setup
# ======================================================================

async def setup(bot: commands.Bot):
    cog = Minigames(bot)

    # Define 50 simple minigame command names and short helps
    games = [
        ("coinflip", "Flip a coin."),
        ("roll", "Roll a number 1-100."),
        ("guess_number", "Guess a number 1-20."),
        ("rps", "Play rock-paper-scissors."),
        ("higher_lower", "Predict higher or lower."),
        ("memory", "Simple memory sequence."),
        ("reaction_time", "Test your reaction time."),
        ("typing_race", "Type a sentence quickly."),
        ("hangman", "Play a short hangman."),
        ("unscramble", "Unscramble a word."),
        ("quick_math", "Solve a quick math problem."),
        ("trivia", "Answer a trivia question."),
        ("choose", "Have the bot pick an option for you."),
        ("emoji_quiz", "Guess what the emoji means."),
        ("spelling_bee", "Spell the shown word."),
        ("capitals", "Name the capital of a country."),
        ("palindrome", "Check if a word is palindrome."),
        ("reverse_word", "Reverse the provided word."),
        ("count_vowels", "Count vowels in a word."),
        ("scramble_sentence", "Scramble the sentence words."),
        ("predict", "Short fortune/prognosis."),
        ("stones", "Remove stones (tiny nim)."),
        ("match_colors", "Quick choose matching color."),
        ("emoji_memory", "Remember emoji sequence."),
        ("text_twist", "Make a word from letters."),
        ("short_story", "Create a mini story from a word."),
        ("mimic", "Repeat back what you send."),
        ("word_chain", "Add a word that starts with the last letter."),
        ("synonym", "Give a synonym for a word."),
        ("antonym", "Give an antonym for a word."),
        ("find_pair", "Find matching pair among items."),
        ("odd_one_out", "Identify the odd item."),
        ("sequence_complete", "Complete the number sequence."),
        ("tap_count", "Count taps quickly."),
        ("bubble_pop", "Pop virtual bubbles (count)."),
        ("quick_draw", "Type a given character fast."),
        ("number_chain", "Continue the counting chain."),
        ("color_guess", "Guess the color rule."),
        ("flip_words", "Flip the order of words."),
        ("pick_a_card", "Pick a random card."),
        ("treasure_hunt", "Find the hidden treasure word."),
        ("labelling", "Label items quickly."),
        ("math_race", "Answer multiple math quickly."),
        ("guess_the_emoji", "Guess meaning of emoji sequence."),
        ("binary_guess", "Guess 0 or 1 challenge."),
        ("month_quiz", "Which month has X?"),
        ("weekday_quiz", "Which weekday is X?"),
        ("first_letter", "Provide the first letter of a word."),
        ("last_letter", "Provide the last letter of a word."),
        # Next 50 micro minigames (51-100) with descriptive names
        ("parity_guess_micro", "Parity guess (even/odd)", "micro_1"),
        ("dice_sum_micro", "Dice sum guess", "micro_2"),
        ("quick_mental_math_micro", "Quick mental math", "micro_3"),
        ("reverse_word_micro", "Reverse the word", "micro_4"),
        ("emoji_memory_micro", "Emoji memory challenge", "micro_5"),
        ("color_guess_micro", "Guess the color", "micro_6"),
        ("fast_type_micro", "Type the character fast", "micro_7"),
        ("mini_unscramble_micro", "Mini unscramble", "micro_8"),
        ("yes_no_trivia_micro", "Yes/no trivia", "micro_9"),
        ("guess_picked_item_micro", "Guess the picked item", "micro_10"),
        ("parity_variant_micro", "Parity guess (variant)", "micro_11"),
        ("dice_sum_more_micro", "Dice sum guess (more dice)", "micro_12"),
        ("quick_math_harder_micro", "Quick mental math (harder)", "micro_13"),
        ("reverse_word_challenge_micro", "Reverse the word (challenge)", "micro_14"),
        ("emoji_memory_long_micro", "Emoji memory (longer)", "micro_15"),
        ("color_pick_hard_micro", "Color pick (hard)", "micro_16"),
        ("fast_type_faster_micro", "Type the character (faster)", "micro_17"),
        ("unscramble_short_micro", "Unscramble (short)", "micro_18"),
        ("yes_no_pool_micro", "Yes/no trivia (pool)", "micro_19"),
        ("guess_picked_pool_micro", "Guess the picked item (pool)", "micro_20"),
        ("parity_puzzle_micro", "Parity puzzle", "micro_21"),
        ("dice_sum_challenge_micro", "Dice sum challenge", "micro_22"),
        ("timed_math_sprint_micro", "Timed math sprint", "micro_23"),
        ("mirror_word_micro", "Mirror word test", "micro_24"),
        ("emoji_speedrun_micro", "Emoji memory speedrun", "micro_25"),
        ("color_guess_expert_micro", "Color guess - expert", "micro_26"),
        ("char_typing_blitz_micro", "Character typing blitz", "micro_27"),
        ("unscramble_quick_micro", "Unscramble quick round", "micro_28"),
        ("true_false_pop_micro", "True/False pop quiz", "micro_29"),
        ("pick_item_mini_micro", "Pick-the-item mini-game", "micro_30"),
        ("even_odd_rapid_micro", "Even/Odd rapid", "micro_31"),
        ("multi_dice_sum_micro", "Multi-dice sum guess", "micro_32"),
        ("math_minute_micro", "Math minute", "micro_33"),
        ("reverse_phrase_micro", "Reverse phrase", "micro_34"),
        ("emoji_recall_micro", "Emoji recall test", "micro_35"),
        ("color_chooser_micro", "Color chooser", "micro_36"),
        ("speed_typing_micro", "Speed typing test", "micro_37"),
        ("mini_word_scramble_micro", "Mini-word scramble", "micro_38"),
        ("binary_yes_no_micro", "Binary yes/no quiz", "micro_39"),
        ("item_guess_micro", "Item guessing game", "micro_40"),
        ("parity_extreme_micro", "Parity extreme", "micro_41"),
        ("dice_master_micro", "Dice master", "micro_42"),
        ("rapid_math_micro", "Rapid math", "micro_43"),
        ("reverse_challenge_micro", "Reverse challenge", "micro_44"),
        ("emoji_memory_master_micro", "Emoji memory master", "micro_45"),
        ("color_master_micro", "Color master", "micro_46"),
        ("typing_master_micro", "Typing master", "micro_47"),
        ("unscramble_master_micro", "Unscramble master", "micro_48"),
        ("trivia_quickfire_micro", "Trivia quickfire", "micro_49"),
        ("pick_hidden_item_micro", "Pick the hidden item", "micro_50"),
        # Next 50 micro minigames (101-150)
        ("parity_master_ii_micro", "Parity master II", "micro_51"),
        ("dice_sum_showoff_micro", "Dice sum showoff", "micro_52"),
        ("math_lightning_micro", "Math lightning", "micro_53"),
        ("reverse_sprint_micro", "Reverse word sprint", "micro_54"),
        ("emoji_recall_challenge_micro", "Emoji recall challenge", "micro_55"),
        ("color_conundrum_micro", "Color pick conundrum", "micro_56"),
        ("typing_reflex_micro", "Typing reflex", "micro_57"),
        ("unscramble_dash_micro", "Unscramble dash", "micro_58"),
        ("quick_true_false_micro", "Quick true/false", "micro_59"),
        ("guess_object_micro", "Guess the object", "micro_60"),
        ("even_odd_rapid_ii_micro", "Even/Odd rapid II", "micro_61"),
        ("mega_dice_sum_micro", "Mega dice sum", "micro_62"),
        ("crunch_numbers_micro", "Crunch the numbers", "micro_63"),
        ("mirror_phrase_test_micro", "Mirror phrase test", "micro_64"),
        ("emoji_memory_extreme_micro", "Emoji memory extreme", "micro_65"),
        ("color_roulette_micro", "Color roulette", "micro_66"),
        ("speed_typing_blitz_micro", "Speed typing blitz", "micro_67"),
        ("word_scramble_relay_micro", "Word scramble relay", "micro_68"),
        ("yes_no_rapidfire_micro", "Yes/No rapidfire", "micro_69"),
        ("pick_item_master_micro", "Pick-the-item master", "micro_70"),
        ("parity_blitz_micro", "Parity blitz", "micro_71"),
        ("dice_frenzy_micro", "Dice frenzy", "micro_72"),
        ("math_sprint_pro_micro", "Math sprint pro", "micro_73"),
        ("reverse_phrase_ii_micro", "Reverse the phrase II", "micro_74"),
        ("emoji_recall_pro_micro", "Emoji recall pro", "micro_75"),
        ("color_master_ii_micro", "Color master II", "micro_76"),
        ("typing_reflex_pro_micro", "Typing reflex pro", "micro_77"),
        ("unscramble_expert_micro", "Unscramble expert", "micro_78"),
        ("true_false_blitz_micro", "True/False blitz", "micro_79"),
        ("find_hidden_thing_micro", "Find the hidden thing", "micro_80"),
        ("even_odd_challenge_micro", "Even/Odd challenge", "micro_81"),
        ("dice_master_ii_micro", "Dice master II", "micro_82"),
        ("rapid_arithmetic_micro", "Rapid arithmetic", "micro_83"),
        ("reverse_champion_micro", "Reverse champion", "micro_84"),
        ("emoji_memory_champion_micro", "Emoji memory champion", "micro_85"),
        ("color_chooser_pro_micro", "Color chooser pro", "micro_86"),
        ("typing_champion_micro", "Typing champion", "micro_87"),
        ("unscramble_champion_micro", "Unscramble champion", "micro_88"),
        ("trivia_blitz_master_micro", "Trivia blitz master", "micro_89"),
        ("pick_secret_item_micro", "Pick-the-secret-item", "micro_90"),
        ("parity_grandmaster_micro", "Parity grandmaster", "micro_91"),
        ("dice_grandmaster_micro", "Dice grandmaster", "micro_92"),
        ("mental_math_grand_micro", "Mental math grand", "micro_93"),
        ("reverse_grand_micro", "Reverse grand", "micro_94"),
        ("emoji_grand_recall_micro", "Emoji grand recall", "micro_95"),
        ("color_grandmaster_micro", "Color grandmaster", "micro_96"),
        ("typing_grandmaster_micro", "Typing grandmaster", "micro_97"),
        ("unscramble_grandmaster_micro", "Unscramble grandmaster", "micro_98"),
        ("ultimate_trivia_micro", "Ultimate trivia", "micro_99"),
        ("hidden_item_grand_micro", "Hidden item grand challenge", "micro_100"),
        # Next 50 micro minigames (151-200)
        ("parity_master_iii_micro", "Parity master III", "micro_101"),
        ("dice_showoff_ii_micro", "Dice sum showoff II", "micro_102"),
        ("math_lightning_ii_micro", "Math lightning II", "micro_103"),
        ("reverse_sprint_ii_micro", "Reverse word sprint II", "micro_104"),
        ("emoji_recall_challenge_ii_micro", "Emoji recall challenge II", "micro_105"),
        ("color_conundrum_ii_micro", "Color pick conundrum II", "micro_106"),
        ("typing_reflex_ii_micro", "Typing reflex II", "micro_107"),
        ("unscramble_dash_ii_micro", "Unscramble dash II", "micro_108"),
        ("quick_tf_ii_micro", "Quick true/false II", "micro_109"),
        ("guess_object_ii_micro", "Guess the object II", "micro_110"),
        ("even_odd_rapid_iii_micro", "Even/Odd rapid III", "micro_111"),
        ("mega_dice_sum_ii_micro", "Mega dice sum II", "micro_112"),
        ("crunch_numbers_ii_micro", "Crunch the numbers II", "micro_113"),
        ("mirror_phrase_test_ii_micro", "Mirror phrase test II", "micro_114"),
        ("emoji_memory_extreme_ii_micro", "Emoji memory extreme II", "micro_115"),
        ("color_roulette_ii_micro", "Color roulette II", "micro_116"),
        ("speed_typing_blitz_ii_micro", "Speed typing blitz II", "micro_117"),
        ("word_scramble_relay_ii_micro", "Word scramble relay II", "micro_118"),
        ("yes_no_rapidfire_ii_micro", "Yes/No rapidfire II", "micro_119"),
        ("pick_item_master_ii_micro", "Pick-the-item master II", "micro_120"),
        ("parity_blitz_ii_micro", "Parity blitz II", "micro_121"),
        ("dice_frenzy_ii_micro", "Dice frenzy II", "micro_122"),
        ("math_sprint_pro_ii_micro", "Math sprint pro II", "micro_123"),
        ("reverse_phrase_iii_micro", "Reverse the phrase III", "micro_124"),
        ("emoji_recall_pro_iii_micro", "Emoji recall pro III", "micro_125"),
        ("color_master_iii_micro", "Color master III", "micro_126"),
        ("typing_reflex_pro_ii_micro", "Typing reflex pro II", "micro_127"),
        ("unscramble_expert_ii_micro", "Unscramble expert II", "micro_128"),
        ("true_false_blitz_ii_micro", "True/False blitz II", "micro_129"),
        ("find_hidden_thing_ii_micro", "Find the hidden thing II", "micro_130"),
        ("even_odd_challenge_ii_micro", "Even/Odd challenge II", "micro_131"),
        ("dice_master_iii_micro", "Dice master III", "micro_132"),
        ("rapid_arithmetic_ii_micro", "Rapid arithmetic II", "micro_133"),
        ("reverse_champion_ii_micro", "Reverse champion II", "micro_134"),
        ("emoji_memory_champion_iii_micro", "Emoji memory champion III", "micro_135"),
        ("color_chooser_pro_iii_micro", "Color chooser pro III", "micro_136"),
        ("typing_champion_iii_micro", "Typing champion III", "micro_137"),
        ("unscramble_champion_iii_micro", "Unscramble champion III", "micro_138"),
        ("trivia_blitz_master_iii_micro", "Trivia blitz master III", "micro_139"),
        ("pick_secret_item_iii_micro", "Pick-the-secret-item III", "micro_140"),
        ("parity_grandmaster_iii_micro", "Parity grandmaster III", "micro_141"),
        ("dice_grandmaster_iii_micro", "Dice grandmaster III", "micro_142"),
        ("mental_math_grand_iii_micro", "Mental math grand III", "micro_143"),
        ("reverse_grand_iii_micro", "Reverse grand III", "micro_144"),
        ("emoji_grand_recall_iii_micro", "Emoji grand recall III", "micro_145"),
        ("color_grandmaster_iii_micro", "Color grandmaster III", "micro_146"),
        ("typing_grandmaster_iii_micro", "Typing grandmaster III", "micro_147"),
        ("unscramble_grandmaster_iii_micro", "Unscramble grandmaster III", "micro_148"),
        ("ultimate_trivia_iii_micro", "Ultimate trivia III", "micro_199"),
        ("hidden_item_grand_iii_micro", "Hidden item grand challenge III", "micro_200"),
        # Final 50 micro minigames (201-250)
        ("parity_master_iv_micro", "Parity master IV", "micro_201"),
        ("dice_showoff_iv_micro", "Dice sum showoff IV", "micro_202"),
        ("math_lightning_iv_micro", "Math lightning IV", "micro_203"),
        ("reverse_sprint_iv_micro", "Reverse word sprint IV", "micro_204"),
        ("emoji_recall_challenge_iv_micro", "Emoji recall challenge IV", "micro_205"),
        ("color_conundrum_iv_micro", "Color pick conundrum IV", "micro_206"),
        ("typing_reflex_iv_micro", "Typing reflex IV", "micro_207"),
        ("unscramble_dash_iv_micro", "Unscramble dash IV", "micro_208"),
        ("quick_tf_iv_micro", "Quick true/false IV", "micro_209"),
        ("guess_object_iv_micro", "Guess the object IV", "micro_210"),
        ("even_odd_rapid_v_micro", "Even/Odd rapid V", "micro_211"),
        ("mega_dice_sum_iv_micro", "Mega dice sum IV", "micro_212"),
        ("crunch_numbers_iv_micro", "Crunch the numbers IV", "micro_213"),
        ("mirror_phrase_test_iv_micro", "Mirror phrase test IV", "micro_214"),
        ("emoji_memory_extreme_iv_micro", "Emoji memory extreme IV", "micro_215"),
        ("color_roulette_iv_micro", "Color roulette IV", "micro_216"),
        ("speed_typing_blitz_iv_micro", "Speed typing blitz IV", "micro_217"),
        ("word_scramble_relay_iv_micro", "Word scramble relay IV", "micro_218"),
        ("yes_no_rapidfire_iv_micro", "Yes/No rapidfire IV", "micro_219"),
        ("pick_item_master_iv_micro", "Pick-the-item master IV", "micro_220"),
        ("parity_blitz_iv_micro", "Parity blitz IV", "micro_221"),
        ("dice_frenzy_iv_micro", "Dice frenzy IV", "micro_222"),
        ("math_sprint_pro_iv_micro", "Math sprint pro IV", "micro_223"),
        ("reverse_phrase_v_micro", "Reverse the phrase V", "micro_224"),
        ("emoji_recall_pro_iv_micro", "Emoji recall pro IV", "micro_225"),
        ("color_master_v_micro", "Color master V", "micro_226"),
        ("typing_reflex_pro_iv_micro", "Typing reflex pro IV", "micro_227"),
        ("unscramble_expert_iv_micro", "Unscramble expert IV", "micro_228"),
        ("true_false_blitz_iv_micro", "True/False blitz IV", "micro_229"),
        ("find_hidden_thing_iv_micro", "Find the hidden thing IV", "micro_230"),
        ("even_odd_challenge_iv_micro", "Even/Odd challenge IV", "micro_231"),
        ("dice_master_v_micro", "Dice master V", "micro_232"),
        ("rapid_arithmetic_iv_micro", "Rapid arithmetic IV", "micro_233"),
        ("reverse_champion_iv_micro", "Reverse champion IV", "micro_234"),
        ("emoji_memory_champion_iv_micro", "Emoji memory champion IV", "micro_235"),
        ("color_chooser_pro_iv_micro", "Color chooser pro IV", "micro_236"),
        ("typing_champion_iv_micro", "Typing champion IV", "micro_237"),
        ("unscramble_champion_iv_micro", "Unscramble champion IV", "micro_238"),
        ("trivia_blitz_master_iv_micro", "Trivia blitz master IV", "micro_239"),
        ("pick_secret_item_iv_micro", "Pick-the-secret-item IV", "micro_240"),
        ("parity_grandmaster_iv_micro", "Parity grandmaster IV", "micro_241"),
        ("dice_grandmaster_iv_micro", "Dice grandmaster IV", "micro_242"),
        ("mental_math_grand_iv_micro", "Mental math grand IV", "micro_243"),
        ("reverse_grand_iv_micro", "Reverse grand IV", "micro_244"),
        ("emoji_grand_recall_iv_micro", "Emoji grand recall IV", "micro_245"),
        ("color_grandmaster_iv_micro", "Color grandmaster IV", "micro_246"),
        ("typing_grandmaster_iv_micro", "Typing grandmaster IV", "micro_247"),
        ("unscramble_grandmaster_iv_micro", "Unscramble grandmaster IV", "micro_248"),
        ("ultimate_trivia_iv_micro", "Ultimate trivia IV", "micro_249"),
        ("hidden_item_grand_iv_micro", "Hidden item grand challenge IV", "micro_250"),
    ]

    # collect existing names to avoid collisions
    existing = set()
    for c in bot.commands:
        existing.add(c.name)
        for a in getattr(c, 'aliases', ()): 
            existing.add(a)

    # register each game as a prefix command bound to the cog
    # allow entries of the form (cmd_name, help) or (cmd_name, help, internal_name)
    for entry in games:
        if len(entry) == 2:
            name, help_text = entry
            internal = name
        else:
            name, help_text, internal = entry
        # capture internal name correctly in closure
        async def _cmd_wrapper(ctx, *args, _internal=internal):
            await cog._handle_game(ctx, _internal)

        # avoid collisions: if it exists, prefix with mg_
        safe_name = name
        if safe_name in existing:
            base = f"mg_{name}"
            safe_name = base
            i = 1
            while safe_name in existing:
                safe_name = f"{base}_{i}"
                i += 1
        # if this entry maps to an internal micro_N name, try to register that as an alias
        aliases = []
        try:
            if internal != name and internal not in existing:
                aliases.append(internal)
        except NameError:
            # entries without explicit internal name will skip aliasing
            pass

        cmd = commands.Command(_cmd_wrapper, name=safe_name, help=help_text, aliases=aliases)
        try:
            # Some discord.py versions don't provide Cog.add_command; add to bot
            # and attach the cog reference to the Command so Cog.get_commands()
            # will include it.
            bot.add_command(cmd)
            # Don't set cmd._cog to avoid self parameter injection
            # record registered names to avoid future collisions
            existing.add(safe_name)
            for a in aliases:
                existing.add(a)
            try:
                cog._registered_games.append((safe_name, help_text))
            except Exception:
                pass
        except Exception:
            # ignore and continue
            pass

    # Add a gamelist command to this cog
    async def gamelist(ctx, *args):
        cmds = [c for c in cog.get_commands() if isinstance(c, commands.Command)]
        entries = []
        if cmds:
            entries = [(c.name, c.help or "-") for c in sorted(cmds, key=lambda x: x.name)]
        else:
            # fallback to the cog's registered list (populated during setup)
            try:
                reg = getattr(cog, '_registered_games', None)
                if reg:
                    entries = list(reg)
            except Exception:
                entries = []
        if not entries:
            await ctx.send("No minigames available.")
            return
        per_page = 10
        pages = [entries[i:i+per_page] for i in range(0, len(entries), per_page)]

        def make_embed(page_index: int):
            page = pages[page_index]
            embed = discord.Embed(title=f"🎮 Minigames (page {page_index+1}/{len(pages)})",
                                  description="",
                                  color=discord.Color.blurple())
            for name_, brief in page:
                embed.add_field(name=name_, value=brief, inline=False)
            embed.set_footer(text="💡 Tip: Click Prev/Next to browse, Close to dismiss")
            return embed

        class GamelistView(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=120)
                self.page = 0
                self.author = ctx.author

            async def interaction_check(self, interaction: discord.Interaction) -> bool:
                return interaction.user.id == self.author.id

            @discord.ui.button(label="Prev", style=discord.ButtonStyle.secondary)
            async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                if self.page > 0:
                    self.page -= 1
                    await interaction.response.edit_message(embed=make_embed(self.page), view=self)
                else:
                    await interaction.response.defer()

            @discord.ui.button(label="Next", style=discord.ButtonStyle.secondary)
            async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                if self.page < len(pages) - 1:
                    self.page += 1
                    await interaction.response.edit_message(embed=make_embed(self.page), view=self)
                else:
                    await interaction.response.defer()

            @discord.ui.button(label="Close", style=discord.ButtonStyle.danger)
            async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                try:
                    if interaction.message:
                        await interaction.message.delete()
                except Exception:
                    await interaction.response.defer()

        view = GamelistView()
        await ctx.send(embed=make_embed(0), view=view)

    # register gamelist avoiding collision
    safe_name = "gamelist"
    if safe_name in existing:
        safe_name = "mg_gamelist"
        i = 1
        while safe_name in existing:
            safe_name = f"mg_gamelist_{i}"
            i += 1
    try:
        cmd = commands.Command(gamelist, name=safe_name, help="List available minigames.")
        bot.add_command(cmd)
        # Don't set cmd._cog to avoid self parameter injection
    except Exception:
        pass

    await bot.add_cog(cog)
    
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
