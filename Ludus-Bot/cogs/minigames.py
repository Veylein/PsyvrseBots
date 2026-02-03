import discord
from discord.ext import commands
import random
import asyncio
import time
from typing import List


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
        eco = None
        try:
            eco = self.bot.get_cog("Economy")
        except Exception:
            eco = None
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
                # run in executor to avoid blocking the event loop
                try:
                    self.bot.loop.run_in_executor(None, record_fn, int(ctx.author.id), game_name, 'win', int(amount), str(getattr(ctx.author, 'name', ctx.author)))
                except Exception:
                    # last-resort: call synchronously (best-effort)
                    try:
                        record_fn(int(ctx.author.id), game_name, 'win', int(amount), str(getattr(ctx.author, 'name', ctx.author)))
                    except Exception:
                        pass
        except Exception:
            pass

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
        kind_id = (idx - 1) % 10
        difficulty = (idx - 1) // 10  # 0..24
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

    async def _handle_game(self, ctx: commands.Context, game_name: str):
        """Generic dispatcher that runs the chosen minigame by name."""
        # map names to simple behaviors
        name = game_name
        # basic helpers
        def rnd_word(words: List[str]):
            return random.choice(words)

        if name == "coinflip":
            choice = random.choice(("heads", "tails"))
            await ctx.send(f"I flipped a coin: **{choice}**")
            return

        if name == "roll":
            n = random.randint(1, 100)
            await ctx.send(f"You rolled: **{n}**")
            return

        if name == "guess_number":
            target = random.randint(1, 20)
            await ctx.send("I'm thinking of a number 1-20. You have 4 guesses.")
            for i in range(4):
                try:
                    msg = await self.bot.wait_for('message', timeout=25.0, check=self._author_channel_check(ctx))
                except asyncio.TimeoutError:
                    await ctx.send(f"Timed out — the number was **{target}**.")
                    return
                try:
                    guess = int(msg.content.strip())
                except Exception:
                    await ctx.send("Send a number.")
                    continue
                if guess == target:
                    await ctx.send(f"Correct! The number was **{target}**")
                    await self._award_win(ctx, name)
                    return
                await ctx.send("Too high." if guess > target else "Too low.")
            await ctx.send(f"Out of guesses — it was **{target}**")
            return

        if name == "rps":
            await ctx.send("Rock / Paper / Scissors — type your choice.")
            try:
                msg = await self.bot.wait_for('message', timeout=20.0, check=self._author_channel_check(ctx))
            except asyncio.TimeoutError:
                await ctx.send("Timed out.")
                return
            user = msg.content.lower().strip()
            choices = ("rock", "paper", "scissors")
            if user not in choices:
                await ctx.send("Use rock, paper or scissors.")
                return
            botc = random.choice(choices)
            outcome = "tie"
            if (user, botc) in (("rock", "scissors"), ("scissors", "paper"), ("paper", "rock")):
                outcome = "you win"
            elif user != botc:
                outcome = "you lose"
            await ctx.send(f"I chose **{botc}** — {outcome}.")
            if outcome == "you win":
                await self._award_win(ctx, name)
            return

        if name == "higher_lower":
            a = random.randint(1, 50)
            b = random.randint(1, 50)
            await ctx.send(f"First: **{a}**. Will the next number be higher or lower? (type higher/lower)")
            try:
                msg = await self.bot.wait_for('message', timeout=20.0, check=self._author_channel_check(ctx))
            except asyncio.TimeoutError:
                await ctx.send("Timed out.")
                return
            pick = msg.content.lower().strip()
            if pick not in ("higher", "lower"):
                await ctx.send("Reply with 'higher' or 'lower'.")
                return
            result = "higher" if b > a else "lower" if b < a else "equal"
            await ctx.send(f"Next number: **{b}** — you guessed **{pick}**. Result: **{result}**")
            return

        if name == "memory":
            emojis = ["🍎", "🍌", "🍒", "🍇", "🍉", "🍓", "🍍"]
            seq = [random.choice(emojis) for _ in range(3)]
            await ctx.send("Memorize this sequence:")
            await ctx.send(" ".join(seq))
            await asyncio.sleep(3)
            await ctx.send("Now type the sequence exactly as shown (space separated).")
            try:
                msg = await self.bot.wait_for('message', timeout=15.0, check=self._author_channel_check(ctx))
            except asyncio.TimeoutError:
                await ctx.send("Timed out.")
                return
            if msg.content.strip() == " ".join(seq):
                await ctx.send("Correct!")
                await self._award_win(ctx, name)
            else:
                await ctx.send(f"Wrong. The sequence was: {' '.join(seq)}")
            return

        if name == "reaction_time":
            await ctx.send("Get ready...")
            await asyncio.sleep(random.uniform(1.0, 3.0))
            start = time.perf_counter()
            await ctx.send("GO!")
            try:
                _ = await self.bot.wait_for('message', timeout=10.0, check=self._author_channel_check(ctx))
            except asyncio.TimeoutError:
                await ctx.send("Too slow or timed out.")
                return
            end = time.perf_counter()
            await ctx.send(f"Reaction time: {(end-start)*1000:.0f} ms")
            return

        if name == "typing_race":
            sentence = "The quick brown fox jumps over the lazy dog"
            await ctx.send(f"Type exactly: {sentence}")
            start = time.perf_counter()
            try:
                msg = await self.bot.wait_for('message', timeout=25.0, check=self._author_channel_check(ctx))
            except asyncio.TimeoutError:
                await ctx.send("Timed out.")
                return
            end = time.perf_counter()
            correct = msg.content.strip() == sentence
            await ctx.send(f"Time: {end-start:.2f}s — {'Correct' if correct else 'Incorrect'}")
            if correct:
                await self._award_win(ctx, name)
            return

        if name == "hangman":
            words = ["python", "discord", "ludus", "minigame"]
            word = rnd_word(words)
            revealed = ['_' for _ in word]
            tries = 6
            used = set()
            await ctx.send(f"Hangman: {' '.join(revealed)}")
            while tries > 0 and '_' in revealed:
                try:
                    msg = await self.bot.wait_for('message', timeout=30.0, check=self._author_channel_check(ctx))
                except asyncio.TimeoutError:
                    await ctx.send(f"Timed out. Word was **{word}**")
                    return
                guess = msg.content.lower().strip()
                if len(guess) != 1 or not guess.isalpha():
                    await ctx.send("Reply with a single letter.")
                    continue
                if guess in used:
                    await ctx.send("Already tried that.")
                    continue
                used.add(guess)
                if guess in word:
                    for i, ch in enumerate(word):
                        if ch == guess:
                            revealed[i] = guess
                    await ctx.send(' '.join(revealed))
                else:
                    tries -= 1
                    await ctx.send(f"Wrong. {tries} tries left.")
            if '_' not in revealed:
                await ctx.send(f"You win! **{word}**")
                await self._award_win(ctx, name)
            else:
                await ctx.send(f"Out of tries. Word was **{word}**")
            return

        if name == "unscramble":
            words = ["apple", "bread", "crane", "delta", "eagle"]
            word = rnd_word(words)
            scrambled = ''.join(random.sample(list(word), len(word)))
            await ctx.send(f"Unscramble: **{scrambled}**")
            try:
                msg = await self.bot.wait_for('message', timeout=20.0, check=self._author_channel_check(ctx))
            except asyncio.TimeoutError:
                await ctx.send(f"Timed out. Answer: **{word}**")
                return
            if msg.content.lower().strip() == word:
                await ctx.send("Correct!")
                await self._award_win(ctx, name)
            else:
                await ctx.send(f"No — it was **{word}**")
            return

        if name == "quick_math":
            a = random.randint(1, 12)
            b = random.randint(1, 12)
            op = random.choice(['+', '-', '*'])
            expr = f"{a}{op}{b}"
            ans = eval(expr)
            await ctx.send(f"Solve: {expr}")
            try:
                msg = await self.bot.wait_for('message', timeout=15.0, check=self._author_channel_check(ctx))
            except asyncio.TimeoutError:
                await ctx.send(f"Timed out. Answer: **{ans}**")
                return
            try:
                val = int(msg.content.strip())
            except Exception:
                await ctx.send("Send a number.")
                return
            if val == ans:
                await ctx.send("Correct!")
                await self._award_win(ctx, name)
            else:
                await ctx.send(f"Wrong — {ans}")
            return

        if name == "trivia":
            qas = [("What color is the sky on a clear day?", "blue"), ("How many legs has a spider?", "8")]
            q, a = rnd_word(qas)
            await ctx.send(q)
            try:
                msg = await self.bot.wait_for('message', timeout=20.0, check=self._author_channel_check(ctx))
            except asyncio.TimeoutError:
                await ctx.send(f"Timed out. Answer: **{a}**")
                return
            if msg.content.lower().strip() == a.lower():
                await ctx.send("Correct!")
                await self._award_win(ctx, name)
            else:
                await ctx.send(f"No — {a}")
            return

        if name == "choose":
            await ctx.send("Send options separated by commas (e.g. a,b,c)")
            try:
                msg = await self.bot.wait_for('message', timeout=25.0, check=self._author_channel_check(ctx))
            except asyncio.TimeoutError:
                await ctx.send("Timed out.")
                return
            opts = [o.strip() for o in msg.content.split(',') if o.strip()]
            if not opts:
                await ctx.send("No options provided.")
                return
            await ctx.send(f"I pick: **{random.choice(opts)}**")
            return

        # fallback generic: simple fortune
        await ctx.send(random.choice(["Nice!", "Try again.", "Nope."]))

        # micro_ prefixed games: delegate to a dedicated micro handler
        if name.startswith("micro_"):
            try:
                idx = int(name.split("_")[1])
            except Exception:
                idx = 0
            await self._micro_play(ctx, idx, 0, False, name)
            return


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
        ("emoji_recall_pro_ii_micro", "Emoji recall pro II", "micro_125"),
        ("color_master_iii_micro", "Color master III", "micro_126"),
        ("typing_reflex_pro_ii_micro", "Typing reflex pro II", "micro_127"),
        ("unscramble_expert_ii_micro", "Unscramble expert II", "micro_128"),
        ("true_false_blitz_ii_micro", "True/False blitz II", "micro_129"),
        ("find_hidden_thing_ii_micro", "Find the hidden thing II", "micro_130"),
        ("even_odd_challenge_ii_micro", "Even/Odd challenge II", "micro_131"),
        ("dice_master_iii_micro", "Dice master III", "micro_132"),
        ("rapid_arithmetic_ii_micro", "Rapid arithmetic II", "micro_133"),
        ("reverse_champion_ii_micro", "Reverse champion II", "micro_134"),
        ("emoji_memory_champion_ii_micro", "Emoji memory champion II", "micro_135"),
        ("color_chooser_pro_ii_micro", "Color chooser pro II", "micro_136"),
        ("typing_champion_ii_micro", "Typing champion II", "micro_137"),
        ("unscramble_champion_ii_micro", "Unscramble champion II", "micro_138"),
        ("trivia_blitz_master_ii_micro", "Trivia blitz master II", "micro_139"),
        ("pick_secret_item_ii_micro", "Pick-the-secret-item II", "micro_140"),
        ("parity_grandmaster_ii_micro", "Parity grandmaster II", "micro_141"),
        ("dice_grandmaster_ii_micro", "Dice grandmaster II", "micro_142"),
        ("mental_math_grand_ii_micro", "Mental math grand II", "micro_143"),
        ("reverse_grand_ii_micro", "Reverse grand II", "micro_144"),
        ("emoji_grand_recall_ii_micro", "Emoji grand recall II", "micro_145"),
        ("color_grandmaster_ii_micro", "Color grandmaster II", "micro_146"),
        ("typing_grandmaster_ii_micro", "Typing grandmaster II", "micro_147"),
        ("unscramble_grandmaster_ii_micro", "Unscramble grandmaster II", "micro_148"),
        ("ultimate_trivia_ii_micro", "Ultimate trivia II", "micro_149"),
        ("hidden_item_grand_ii_micro", "Hidden item grand challenge II", "micro_150"),
        # Next 50 micro minigames (201-250)
        ("parity_master_iv_micro", "Parity master IV", "micro_151"),
        ("dice_showoff_iii_micro", "Dice sum showoff III", "micro_152"),
        ("math_lightning_iii_micro", "Math lightning III", "micro_153"),
        ("reverse_sprint_iii_micro", "Reverse word sprint III", "micro_154"),
        ("emoji_recall_challenge_iii_micro", "Emoji recall challenge III", "micro_155"),
        ("color_conundrum_iii_micro", "Color pick conundrum III", "micro_156"),
        ("typing_reflex_iii_micro", "Typing reflex III", "micro_157"),
        ("unscramble_dash_iii_micro", "Unscramble dash III", "micro_158"),
        ("quick_tf_iii_micro", "Quick true/false III", "micro_159"),
        ("guess_object_iii_micro", "Guess the object III", "micro_160"),
        ("even_odd_rapid_iv_micro", "Even/Odd rapid IV", "micro_161"),
        ("mega_dice_sum_iii_micro", "Mega dice sum III", "micro_162"),
        ("crunch_numbers_iii_micro", "Crunch the numbers III", "micro_163"),
        ("mirror_phrase_test_iii_micro", "Mirror phrase test III", "micro_164"),
        ("emoji_memory_extreme_iii_micro", "Emoji memory extreme III", "micro_165"),
        ("color_roulette_iii_micro", "Color roulette III", "micro_166"),
        ("speed_typing_blitz_iii_micro", "Speed typing blitz III", "micro_167"),
        ("word_scramble_relay_iii_micro", "Word scramble relay III", "micro_168"),
        ("yes_no_rapidfire_iii_micro", "Yes/No rapidfire III", "micro_169"),
        ("pick_item_master_iii_micro", "Pick-the-item master III", "micro_170"),
        ("parity_blitz_iii_micro", "Parity blitz III", "micro_171"),
        ("dice_frenzy_iii_micro", "Dice frenzy III", "micro_172"),
        ("math_sprint_pro_iii_micro", "Math sprint pro III", "micro_173"),
        ("reverse_phrase_iv_micro", "Reverse the phrase IV", "micro_174"),
        ("emoji_recall_pro_iii_micro", "Emoji recall pro III", "micro_175"),
        ("color_master_iv_micro", "Color master IV", "micro_176"),
        ("typing_reflex_pro_iii_micro", "Typing reflex pro III", "micro_177"),
        ("unscramble_expert_iii_micro", "Unscramble expert III", "micro_178"),
        ("true_false_blitz_iii_micro", "True/False blitz III", "micro_179"),
        ("find_hidden_thing_iii_micro", "Find the hidden thing III", "micro_180"),
        ("even_odd_challenge_iii_micro", "Even/Odd challenge III", "micro_181"),
        ("dice_master_iv_micro", "Dice master IV", "micro_182"),
        ("rapid_arithmetic_iii_micro", "Rapid arithmetic III", "micro_183"),
        ("reverse_champion_iii_micro", "Reverse champion III", "micro_184"),
        ("emoji_memory_champion_iii_micro", "Emoji memory champion III", "micro_185"),
        ("color_chooser_pro_iii_micro", "Color chooser pro III", "micro_186"),
        ("typing_champion_iii_micro", "Typing champion III", "micro_187"),
        ("unscramble_champion_iii_micro", "Unscramble champion III", "micro_188"),
        ("trivia_blitz_master_iii_micro", "Trivia blitz master III", "micro_189"),
        ("pick_secret_item_iii_micro", "Pick-the-secret-item III", "micro_190"),
        ("parity_grandmaster_iii_micro", "Parity grandmaster III", "micro_191"),
        ("dice_grandmaster_iii_micro", "Dice grandmaster III", "micro_192"),
        ("mental_math_grand_iii_micro", "Mental math grand III", "micro_193"),
        ("reverse_grand_iii_micro", "Reverse grand III", "micro_194"),
        ("emoji_grand_recall_iii_micro", "Emoji grand recall III", "micro_195"),
        ("color_grandmaster_iii_micro", "Color grandmaster III", "micro_196"),
        ("typing_grandmaster_iii_micro", "Typing grandmaster III", "micro_197"),
        ("unscramble_grandmaster_iii_micro", "Unscramble grandmaster III", "micro_198"),
        ("ultimate_trivia_iii_micro", "Ultimate trivia III", "micro_199"),
        ("hidden_item_grand_iii_micro", "Hidden item grand challenge III", "micro_200"),
        # Final 50 micro minigames (201-250)
        ("parity_master_v_micro", "Parity master V", "micro_201"),
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
        async def _cmd_wrapper(ctx, _internal=internal):
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
            cog.add_command(cmd)
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
    async def gamelist(ctx):
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
        per_page = 12
        pages = [entries[i:i+per_page] for i in range(0, len(entries), per_page)]

        def make_embed(page_index: int):
            page = pages[page_index]
            embed = discord.Embed(title=f"🎮 Minigames (page {page_index+1}/{len(pages)})",
                                  color=discord.Color.blurple())
            for name_, brief in page:
                embed.add_field(name=name_, value=brief, inline=False)
            return embed

        view = discord.ui.View(timeout=120)
        view.page = 0
        view.author = ctx.author

        async def interaction_check(interaction: discord.Interaction) -> bool:
            return interaction.user.id == ctx.author.id

        view.interaction_check = interaction_check

        @discord.ui.button(label="Prev", style=discord.ButtonStyle.secondary)
        async def prev(button: discord.ui.Button, interaction: discord.Interaction):
            if view.page > 0:
                view.page -= 1
                await interaction.response.edit_message(embed=make_embed(view.page), view=view)
            else:
                await interaction.response.defer()

        @discord.ui.button(label="Next", style=discord.ButtonStyle.secondary)
        async def next(button: discord.ui.Button, interaction: discord.Interaction):
            if view.page < len(pages) - 1:
                view.page += 1
                await interaction.response.edit_message(embed=make_embed(view.page), view=view)
            else:
                await interaction.response.defer()

        @discord.ui.button(label="Close", style=discord.ButtonStyle.danger)
        async def close(button: discord.ui.Button, interaction: discord.Interaction):
            try:
                await interaction.message.delete()
            except Exception:
                await interaction.response.defer()

        # attach buttons
        view.add_item(prev)
        view.add_item(next)
        view.add_item(close)

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
        cog.add_command(commands.Command(gamelist, name=safe_name, help="List available minigames."))
    except Exception:
        pass

    await bot.add_cog(cog)
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


