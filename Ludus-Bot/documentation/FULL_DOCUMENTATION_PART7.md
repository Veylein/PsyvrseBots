# 🎮 PART 7: Minigames System - Complete Documentation

> **300+ Interactive Mini-Games with Dynamic Help System**  
> minigames.py (1,070 lines) | Interactive Embeds | Pagination System  
> Full Economy Integration | 10 Game Types | Advanced Navigation

---

## 📋 TABLE OF CONTENTS

1. [Overview](#-overview)
2. [Architecture](#️-architecture)
3. [Game Categories](#-game-categories)
4. [Core Game Types (10 Kinds)](#-core-game-types-10-kinds)
5. [Help System with Interactive Buttons](#-help-system-with-interactive-buttons)
6. [Economy Integration](#-economy-integration)
7. [Command Registration System](#️-command-registration-system)
8. [PaginatedHelpView](#-paginatedhelpview)
9. [Recent Improvements (Part 7 Updates)](#-recent-improvements-part-7-updates)
10. [Statistics](#-statistics)

---

## 🎯 OVERVIEW

### System Purpose
The Minigames system provides **300+ quick, interactive mini-games** that reward players with PsyCoins. Each game is designed to be **simple, fast, and fun** with no complex setup required.

### File Structure
```
cogs/
└── minigames.py (1,070 lines)
    ├── Minigames Cog (lines 1-527)
    ├── Setup Function (lines 528-976)
    └── PaginatedHelpView (lines 989-1070)
```

### Key Features
- ✅ **300+ Mini-Games**: 50 base games + 250 micro variants
- ✅ **10 Game Types**: Parity, dice, math, reverse, emoji, color, typing, unscramble, trivia, item-picking
- ✅ **Difficulty Scaling**: 25 difficulty levels for micro-games
- ✅ **Interactive Help**: Paginated embeds with navigation buttons
- ✅ **Economy Integration**: Automatic PsyCoins rewards
- ✅ **Prefix Commands**: Traditional L! commands (not slash)
- ✅ **Anti-Collision**: Smart name handling for duplicate commands
- ✅ **User Storage**: Win tracking and statistics

---

## 🏗️ ARCHITECTURE

### Lines 1-21: Class Definition
```python
class Minigames(commands.Cog):
    """A large collection of small prefix minigames (first 50).

    Commands are registered programmatically in `setup` so they are
    standard prefix commands (not slash commands). Each command is a
    simple, self-contained interaction intended to be stable and safe.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.active = {}              # Track active games
        self._registered_games = []   # List of (name, help_text) pairs
```

**Key Properties:**
- `bot`: Discord bot instance
- `active`: Dictionary to prevent duplicate games per user
- `_registered_games`: Fallback list for command registration

---

## 🎲 GAME CATEGORIES

### Base Games (50 Total)

#### 1. Simple RNG Games (lines 286-298)
```python
if name == "coinflip":
    choice = random.choice(("heads", "tails"))
    await ctx.send(f"I flipped a coin: **{choice}**")
    return

if name == "roll":
    n = random.randint(1, 100)
    await ctx.send(f"You rolled: **{n}**")
    return
```
**Games:**
- `coinflip` - Flip a coin (heads/tails)
- `roll` - Roll 1-100
- `predict` - Random fortune

#### 2. Guessing Games (lines 300-331)
```python
if name == "guess_number":
    target = random.randint(1, 20)
    await ctx.send("I'm thinking of a number 1-20. You have 4 guesses.")
    for i in range(4):
        try:
            msg = await self.bot.wait_for('message', timeout=25.0, 
                                          check=self._author_channel_check(ctx))
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
```
**Games:**
- `guess_number` - Guess 1-20 with 4 tries
- `higher_lower` - Predict if next number is higher/lower

#### 3. Strategy Games (lines 333-365)
```python
if name == "rps":
    await ctx.send("Rock / Paper / Scissors — type your choice.")
    try:
        msg = await self.bot.wait_for('message', timeout=20.0, 
                                      check=self._author_channel_check(ctx))
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
```
**Games:**
- `rps` - Rock, Paper, Scissors

#### 4. Memory Games (lines 367-388)
```python
if name == "memory":
    emojis = ["🍎", "🍌", "🍒", "🍇", "🍉", "🍓", "🍍"]
    seq = [random.choice(emojis) for _ in range(3)]
    await ctx.send("Memorize this sequence:")
    await ctx.send(" ".join(seq))
    await asyncio.sleep(3)
    await ctx.send("Now type the sequence exactly as shown (space separated).")
    try:
        msg = await self.bot.wait_for('message', timeout=15.0, 
                                      check=self._author_channel_check(ctx))
    except asyncio.TimeoutError:
        await ctx.send("Timed out.")
        return
    if msg.content.strip() == " ".join(seq):
        await ctx.send("Correct!")
        await self._award_win(ctx, name)
    else:
        await ctx.send(f"Wrong. The sequence was: {' '.join(seq)}")
```
**Games:**
- `memory` - Remember emoji sequence
- `emoji_memory` - Enhanced memory variant
- `emoji_quiz` - Guess emoji meaning

#### 5. Speed Games (lines 390-412)
```python
if name == "reaction_time":
    await ctx.send("Get ready...")
    await asyncio.sleep(random.uniform(1.0, 3.0))
    start = time.perf_counter()
    await ctx.send("GO!")
    try:
        _ = await self.bot.wait_for('message', timeout=10.0, 
                                    check=self._author_channel_check(ctx))
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
        msg = await self.bot.wait_for('message', timeout=25.0, 
                                      check=self._author_channel_check(ctx))
    except asyncio.TimeoutError:
        await ctx.send("Timed out.")
        return
    end = time.perf_counter()
    correct = msg.content.strip() == sentence
    await ctx.send(f"Time: {end-start:.2f}s — {'Correct' if correct else 'Incorrect'}")
    if correct:
        await self._award_win(ctx, name)
```
**Games:**
- `reaction_time` - Test your reflexes
- `typing_race` - Type a sentence quickly
- `quick_draw` - Type a character fast

#### 6. Word Games (lines 414-467)
```python
if name == "hangman":
    words = ["python", "discord", "ludus", "minigame"]
    word = rnd_word(words)
    revealed = ['_' for _ in word]
    tries = 6
    used = set()
    await ctx.send(f"Hangman: {' '.join(revealed)}")
    while tries > 0 and '_' in revealed:
        try:
            msg = await self.bot.wait_for('message', timeout=30.0, 
                                          check=self._author_channel_check(ctx))
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
```
**Games:**
- `hangman` - Classic word guessing (6 tries)
- `unscramble` - Unscramble a word
- `spelling_bee` - Spell shown word
- `reverse_word` - Reverse a word
- `count_vowels` - Count vowels
- `palindrome` - Check palindromes
- `synonym` / `antonym` - Word relations
- `word_chain` - Continue word chain

#### 7. Math Games (lines 469-492)
```python
if name == "quick_math":
    a = random.randint(1, 12)
    b = random.randint(1, 12)
    op = random.choice(['+', '-', '*'])
    expr = f"{a}{op}{b}"
    ans = eval(expr)
    await ctx.send(f"Solve: {expr}")
    try:
        msg = await self.bot.wait_for('message', timeout=15.0, 
                                      check=self._author_channel_check(ctx))
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
```
**Games:**
- `quick_math` - Solve simple math
- `math_race` - Multiple math problems
- `sequence_complete` - Number patterns

#### 8. Trivia/Quiz Games (lines 494-507)
```python
if name == "trivia":
    qas = [("What color is the sky on a clear day?", "blue"), 
           ("How many legs has a spider?", "8")]
    q, a = rnd_word(qas)
    await ctx.send(q)
    try:
        msg = await self.bot.wait_for('message', timeout=20.0, 
                                      check=self._author_channel_check(ctx))
    except asyncio.TimeoutError:
        await ctx.send(f"Timed out. Answer: **{a}**")
        return
    if msg.content.lower().strip() == a.lower():
        await ctx.send("Correct!")
        await self._award_win(ctx, name)
```
**Games:**
- `trivia` - Answer trivia
- `capitals` - Name country capitals
- `month_quiz` / `weekday_quiz` - Calendar facts
- `binary_guess` - Guess 0 or 1

#### 9. Utility Games (lines 509-521)
```python
if name == "choose":
    await ctx.send("Send options separated by commas (e.g. a,b,c)")
    try:
        msg = await self.bot.wait_for('message', timeout=25.0, 
                                      check=self._author_channel_check(ctx))
    except asyncio.TimeoutError:
        await ctx.send("Timed out.")
        return
    opts = [o.strip() for o in msg.content.split(',') if o.strip()]
    if not opts:
        await ctx.send("No options provided.")
        return
    await ctx.send(f"I pick: **{random.choice(opts)}**")
```
**Games:**
- `choose` - Pick from your options
- `pick_a_card` - Random card
- `mimic` - Echo your message

#### 10. Creative Games
**Games:**
- `short_story` - Mini story from a word
- `scramble_sentence` - Scramble words
- `flip_words` - Reverse word order
- `labelling` - Label items
- `treasure_hunt` - Find treasure word

---

## 🎯 CORE GAME TYPES (10 Kinds)

The micro-game system (lines 72-278) implements **10 core game types** that are reused across 250 variants with increasing difficulty:

### KIND 0: Parity / Even-Odd (lines 92-109)
```python
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
```
**Difficulty Progression:**
- Difficulty 0-9: Numbers 1-20 to 1-29
- Difficulty 10-19: Numbers 1-30 to 1-39
- Difficulty 20-24: Numbers 1-40 to 1-44
- Advanced mode: Shorter timeout (6s instead of 8s)

**Variants:** `parity_guess_micro`, `parity_variant_micro`, `parity_puzzle_micro`, `parity_extreme_micro`, `parity_blitz_[i-iv]_micro`, `parity_master_[i-v]_micro`, `parity_grandmaster_[i-iv]_micro`, `even_odd_rapid_[i-v]_micro`, etc.

### KIND 1: Dice Sum (lines 111-130)
```python
if kind_id == 1:
    rolls = 2 + (difficulty % 3)  # 2-4 dice
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
```
**Difficulty Progression:**
- Difficulty 0-9: 2 dice
- Difficulty 10-19: 3 dice
- Difficulty 20-24: 4 dice

**Variants:** `dice_sum_micro`, `dice_sum_more_micro`, `dice_sum_challenge_micro`, `dice_frenzy_[i-iv]_micro`, `dice_master_[i-v]_micro`, `dice_grandmaster_[i-iv]_micro`, `multi_dice_sum_micro`, `mega_dice_sum_[i-iv]_micro`

### KIND 2: Quick Math (lines 132-152)
```python
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
```
**Difficulty Progression:**
- Difficulty 0: Numbers 1-10
- Difficulty 24: Numbers 1-34
- Operations: +, -, *

**Variants:** `quick_mental_math_micro`, `quick_math_harder_micro`, `timed_math_sprint_micro`, `math_minute_micro`, `rapid_math_micro`, `math_lightning_[i-iv]_micro`, `math_sprint_pro_[i-iv]_micro`, `rapid_arithmetic_[i-iv]_micro`, `crunch_numbers_[i-iv]_micro`, `mental_math_grand_[i-iv]_micro`

### KIND 3: Reverse Word (lines 154-172)
```python
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
```
**Word Pool:** 6 words of varying length

**Variants:** `reverse_word_micro`, `reverse_word_challenge_micro`, `mirror_word_micro`, `reverse_phrase_[i-v]_micro`, `reverse_challenge_micro`, `reverse_champion_[i-iv]_micro`, `reverse_grand_[i-iv]_micro`, `reverse_sprint_[i-iv]_micro`, `mirror_phrase_test_[i-iv]_micro`

### KIND 4: Emoji Memory (lines 174-196)
```python
if kind_id == 4:
    emojis = ["🍎","🍌","🍒","🍇","🍉","🍓","🍍","🍑"]
    length = 3 + (difficulty % 3)  # 3-5 emojis
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
```
**Difficulty Progression:**
- Difficulty 0-9: 3 emojis
- Difficulty 10-19: 4 emojis
- Difficulty 20-24: 5 emojis
- Advanced: Longer memorization time

**Variants:** `emoji_memory_micro`, `emoji_memory_long_micro`, `emoji_speedrun_micro`, `emoji_recall_[i-iv]_micro`, `emoji_memory_extreme_[i-iv]_micro`, `emoji_recall_pro_[i-iv]_micro`, `emoji_memory_champion_[i-iv]_micro`, `emoji_grand_recall_[i-iv]_micro`, `emoji_recall_challenge_[i-iv]_micro`

### KIND 5: Color Pick (lines 198-218)
```python
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
```
**Color Pool:** 6 colors (red, blue, green, yellow, purple, orange)

**Variants:** `color_guess_micro`, `color_pick_hard_micro`, `color_guess_expert_micro`, `color_chooser_micro`, `color_master_[i-v]_micro`, `color_grandmaster_[i-iv]_micro`, `color_conundrum_[i-iv]_micro`, `color_roulette_[i-iv]_micro`, `color_chooser_pro_[i-iv]_micro`

### KIND 6: Fast Type Character (lines 220-237)
```python
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
```
**Character Pool:** Home row keys (asdfjkl;)
**Speed Requirements:**
- Normal: < 1.5 seconds
- Advanced: < 1.0 seconds

**Variants:** `fast_type_micro`, `fast_type_faster_micro`, `char_typing_blitz_micro`, `speed_typing_[i-iv]_micro`, `typing_master_micro`, `typing_champion_[i-iv]_micro`, `typing_grandmaster_[i-iv]_micro`, `typing_reflex_[i-iv]_micro`, `speed_typing_blitz_[i-iv]_micro`, `typing_reflex_pro_[i-iv]_micro`

### KIND 7: Unscramble (lines 239-256)
```python
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
```
**Word Pool:** 6 common words

**Variants:** `mini_unscramble_micro`, `unscramble_short_micro`, `unscramble_quick_micro`, `mini_word_scramble_micro`, `unscramble_master_micro`, `unscramble_dash_[i-iv]_micro`, `unscramble_expert_[i-iv]_micro`, `unscramble_champion_[i-iv]_micro`, `unscramble_grandmaster_[i-iv]_micro`, `word_scramble_relay_[i-iv]_micro`

### KIND 8: Yes/No Trivia (lines 258-273)
```python
if kind_id == 8:
    pool = [("Is the sky blue?","yes"),
            ("Do cats bark?","no"),
            ("Is water wet?","yes"),
            ("Is fire cold?","no")]
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
```
**Question Pool:** 4 simple yes/no questions

**Variants:** `yes_no_trivia_micro`, `yes_no_pool_micro`, `true_false_pop_micro`, `binary_yes_no_micro`, `quick_true_false_micro`, `yes_no_rapidfire_[i-iv]_micro`, `true_false_blitz_[i-iv]_micro`, `quick_tf_[i-iv]_micro`, `trivia_quickfire_micro`, `trivia_blitz_master_[i-iv]_micro`, `ultimate_trivia_[i-iv]_micro`

### KIND 9: Pick Item from List (lines 275-291)
```python
if kind_id == 9:
    pools = [["apple","bread","crane","delta"], 
             ["red","blue","green","yellow"], 
             ["dog","cat","fox","owl"]]
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
```
**Item Pools:** 3 different 4-item sets that rotate by difficulty

**Variants:** `guess_picked_item_micro`, `guess_picked_pool_micro`, `pick_item_mini_micro`, `item_guess_micro`, `pick_hidden_item_micro`, `pick_item_master_[i-iv]_micro`, `pick_secret_item_[i-iv]_micro`, `find_hidden_thing_[i-iv]_micro`, `hidden_item_grand_[i-iv]_micro`, `guess_object_[i-iv]_micro`

---

## 🎨 HELP SYSTEM WITH INTERACTIVE BUTTONS

### Gamelist Command (lines 897-959)

The `gamelist` command provides an **interactive, paginated list** of all minigames with working navigation buttons:

```python
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
        embed = discord.Embed(
            title=f"🎮 Minigames (page {page_index+1}/{len(pages)})",
            description="Use the buttons below to navigate between pages. Buttons are interactive and fully functional!",
            color=discord.Color.blurple()
        )
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
                await interaction.message.delete()
            except Exception:
                await interaction.response.defer()

    view = GamelistView()
    await ctx.send(embed=make_embed(0), view=view)
```

**Key Features:**
1. **10 games per page** → ~30 pages total
2. **Interactive buttons**: Prev, Next, Close
3. **User-specific**: Only command author can interact
4. **Auto-timeout**: 120 seconds
5. **Informative embed**:
   - Title shows current page number
   - Description explains button functionality
   - Footer provides usage tips

**Integration with Help System:**
- Called by `L!gamelist` directly
- Also called by `L!help mini` in help.py

### Help.py Integration (lines 467-503 in help.py)

The help system has a special minigames handler that uses the same button pattern:

```python
if category_data.get('key') == 'mini':
    # collect commands from the Minigames cog directly (robust)
    mg_cog = self.bot.get_cog('Minigames')
    entries = []
    if mg_cog:
        try:
            reg = getattr(mg_cog, '_registered_games', None)
            if reg:
                entries = list(reg)
        except Exception:
            pass
    if not entries and mg_cog:
        try:
            cmds = mg_cog.get_commands()
            if cmds:
                entries = [(c.name, c.help or "-") for c in sorted(cmds, key=lambda x: x.name)]
        except Exception:
            pass
    if not entries:
        # last-resort: scan bot.commands for anything tagged with the Minigames cog
        cmds = [c for c in self.bot.commands if getattr(c, 'cog_name', None) == 'Minigames' and isinstance(c, commands.Command)]
        if cmds:
            entries = [(c.name, c.help or "-") for c in sorted(cmds, key=lambda x: x.name)]
        
    if not entries:
        msg = "No minigames available."
        if is_slash:
            await ctx.response.send_message(msg, ephemeral=True)
        else:
            await ctx.send(msg)
        return

    per_page = 10
    pages = [entries[i:i+per_page] for i in range(0, len(entries), per_page)]

    def make_embed(page_index: int):
        page = pages[page_index]
        desc_text = category_data.get('desc', '')
        if desc_text:
            desc_text += "\n\n"
        desc_text += "🔘 Use the interactive buttons below to navigate!"
        embed = discord.Embed(
            title=f"🎮 Minigames (page {page_index+1}/{len(pages)})",
            description=desc_text,
            color=discord.Color.blue()
        )
        for name_, brief in page:
            embed.add_field(name=name_, value=brief, inline=False)
        embed.set_footer(text="💡 Buttons are fully functional - click to interact! Prefix: L! or /")
        return embed

    class MiniPaginator(discord.ui.View):
        def __init__(self, author, timeout: int = 120):
            super().__init__(timeout=timeout)
            self.page = 0
            self.author = author

        async def interaction_check(self, interaction: discord.Interaction) -> bool:
            return interaction.user.id == self.author.id

        @discord.ui.button(label="Prev", style=discord.ButtonStyle.secondary)
        async def prev(self, interaction: discord.Interaction, button: discord.ui.Button):
            if self.page > 0:
                self.page -= 1
                await interaction.response.edit_message(embed=make_embed(self.page), view=self)
            else:
                await interaction.response.defer()

        @discord.ui.button(label="Next", style=discord.ButtonStyle.secondary)
        async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
            if self.page < len(pages) - 1:
                self.page += 1
                await interaction.response.edit_message(embed=make_embed(self.page), view=self)
            else:
                await interaction.response.defer()

        @discord.ui.button(label="Close", style=discord.ButtonStyle.danger)
        async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
            try:
                await interaction.message.delete()
            except Exception:
                await interaction.response.defer()

    view = MiniPaginator(ctx.user if is_slash else ctx.author)
    if is_slash:
        await ctx.response.send_message(embed=make_embed(0), view=view)
    else:
        await ctx.send(embed=make_embed(0), view=view)
    return
```

**Triple Fallback System:**
1. Try `_registered_games` attribute
2. Try `get_commands()` method
3. Scan `bot.commands` for cog-tagged commands

**Enhanced Features:**
- Supports both slash commands and prefix commands
- Category description integration
- Dual footer info (buttons + prefix)

---

## 💰 ECONOMY INTEGRATION

### Award Win System (lines 25-70)

Every minigame win automatically awards PsyCoins using the Economy cog:

```python
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
                self.bot.loop.run_in_executor(None, record_fn, 
                    int(ctx.author.id), game_name, 'win', 
                    int(amount), str(getattr(ctx.author, 'name', ctx.author)))
            except Exception:
                # last-resort: call synchronously (best-effort)
                try:
                    record_fn(int(ctx.author.id), game_name, 'win', 
                             int(amount), str(getattr(ctx.author, 'name', ctx.author)))
                except Exception:
                    pass
    except Exception:
        pass
```

**Features:**
1. **Safe Execution**: Never crashes game if economy fails
2. **Dual Integration**:
   - Economy cog for coin balance
   - User storage for statistics
3. **Non-Blocking**: Uses executor for user storage
4. **Fallback Handling**: Multiple try-except layers

**Statistics Tracked:**
- User ID
- Game name
- Result (win)
- Coins earned
- Username

---

## ⚙️ COMMAND REGISTRATION SYSTEM

### Setup Function (lines 528-976)

The setup function **programmatically registers 300+ commands** as prefix commands:

```python
async def setup(bot: commands.Bot):
    cog = Minigames(bot)

    # Define 50 simple minigame command names and short helps
    games = [
        ("coinflip", "Flip a coin."),
        ("roll", "Roll a number 1-100."),
        ("guess_number", "Guess a number 1-20."),
        # ... 47 more base games
        
        # Next 50 micro minigames (51-100) with descriptive names
        ("parity_guess_micro", "Parity guess (even/odd)", "micro_1"),
        ("dice_sum_micro", "Dice sum guess", "micro_2"),
        # ... 248 more micro-games
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
```

**Key Features:**

#### 1. Anti-Collision System
```python
safe_name = name
if safe_name in existing:
    base = f"mg_{name}"
    safe_name = base
    i = 1
    while safe_name in existing:
        safe_name = f"{base}_{i}"
        i += 1
```
- Checks for name conflicts
- Adds `mg_` prefix if collision
- Increments suffix (mg_game_1, mg_game_2) if still collision

#### 2. Alias Support
```python
aliases = []
try:
    if internal != name and internal not in existing:
        aliases.append(internal)
except NameError:
    pass
```
- Micro-games get aliases (e.g., `micro_1`)
- Can be called by descriptive name OR micro_N

#### 3. Wrapper Function
```python
async def _cmd_wrapper(ctx, *args, _internal=internal):
    await cog._handle_game(ctx, _internal)
```
- Captures `internal` name in closure
- Accepts `*args` for extra arguments (important for discord.py compatibility)
- Routes to `_handle_game()` dispatcher

#### 4. Fallback Registration
```python
try:
    cog._registered_games.append((safe_name, help_text))
except Exception:
    pass
```
- Keeps backup list of games
- Used when `get_commands()` fails

---

## 📚 PAGINATEDHELPVIEW

### Lines 989-1070: External Help View

A reusable paginated view class for other cogs:

```python
class PaginatedHelpView(discord.ui.View):
    """Compatibility paginator for other cogs.

    Construct with `(interaction, commands_list, category_name, category_desc)`
    where `commands_list` is a list of `(name, desc)` tuples. Callers expect
    an async `send()` method, so this class exposes `send()` which will
    deliver an initial message via the provided `interaction` and allow
    paging with buttons.
    """

    def __init__(self, interaction: discord.Interaction, commands_list, 
                 category_name: str = "Commands", category_desc: str = "", 
                 per_page: int = 10, timeout: int = 120):
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
        embed = discord.Embed(
            title=f"{self.category_name} (page {self.page+1}/{len(self.pages)})",
            description=desc_text,
            color=discord.Color.blurple()
        )
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
                    self.message = await self.interaction.channel.send(embed=self._make_embed(), view=self)

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
                await self.message.delete()
            else:
                await interaction.message.delete()
        except Exception:
            await interaction.response.defer()
```

**Usage:**
```python
from cogs.minigames import PaginatedHelpView

# In another cog:
commands_list = [("command1", "Description 1"), ("command2", "Description 2")]
view = PaginatedHelpView(interaction, commands_list, "My Category", "Category description")
await view.send()
```

**Features:**
- Triple-fallback send strategy
- User-specific interaction checks
- Configurable per_page count
- Customizable category name/description
- Enhanced embed messaging

---

## 🆕 RECENT IMPROVEMENTS (Part 7 Updates)

### February 6, 2026 Updates

#### 1. Button Parameter Order Fix
**Problem:** Button callbacks had incorrect parameter order `(self, button, interaction)`  
**Fix:** Changed to correct order `(self, interaction, button)`

**Files Updated:**
- `minigames.py` lines 933-955 (GamelistView)
- `minigames.py` lines 1045-1069 (PaginatedHelpView)
- `help.py` lines 476-500 (MiniPaginator)

**Impact:** All navigation buttons now work correctly

#### 2. Command Wrapper Argument Handling
**Problem:** `_cmd_wrapper(ctx, _internal=internal)` only accepted 1-2 arguments  
**Fix:** Changed to `_cmd_wrapper(ctx, *args, _internal=internal)`

**Location:** `minigames.py` line 854

**Impact:** Commands no longer crash with "takes X arguments but Y were given"

#### 3. Cog Attribution Removal
**Problem:** Setting `cmd._cog = cog` caused discord.py to inject `self` parameter  
**Fix:** Removed cog attribution from gamelist command

**Location:** `minigames.py` line 968

**Impact:** `gamelist` command works without AttributeError

#### 4. Enhanced Help Embeds
**Added informative descriptions:**
- "Use the buttons below to navigate between pages. Buttons are interactive and fully functional!"
- "🔘 Use the interactive buttons below to navigate!"

**Added helpful footers:**
- "💡 Tip: Click Prev/Next to browse, Close to dismiss"
- "💡 Buttons are fully functional - click to interact!"

**Impact:** Users clearly understand button functionality

#### 5. Per-Page Optimization
**Changed:** `per_page = 12` → `per_page = 10`

**Location:** `minigames.py` line 910

**Result:** 
- 25 pages → ~30 pages
- Better UX with fewer items per page

#### 6. Help System Integration
**Added:** Button descriptions to help.py minigames handler  
**Enhanced:** Description text with button instructions

**Location:** `help.py` lines 455-466

**Impact:** `L!help mini` shows same polished UI as `L!gamelist`

---

## 📊 STATISTICS

### Code Stats
- **Total Lines**: 1,070
- **Minigames Cog**: 527 lines
- **Setup Function**: 449 lines
- **PaginatedHelpView**: 94 lines

### Game Stats
- **Total Games**: 300+
  - Base games: 50
  - Micro-games: 250
- **Game Types**: 10 core kinds
- **Difficulty Levels**: 25 (0-24)
- **Commands Registered**: 300+
- **Average Game Length**: 10-30 seconds

### Help System Stats
- **Pages**: ~30 (10 games per page)
- **Buttons**: 3 (Prev, Next, Close)
- **Timeout**: 120 seconds
- **Fallback Layers**: 3 (for robustness)

### Integration Stats
- **Economy Integration**: ✅ Full
- **User Storage**: ✅ Statistics tracking
- **Help System**: ✅ Dual integration (gamelist + help.py)
- **Compatibility**: ✅ Other cogs can import PaginatedHelpView

---

## 🎯 COMMAND EXAMPLES

### Playing Games
```bash
# Base games
L!coinflip           # Flip a coin
L!roll               # Roll 1-100
L!guess_number       # Guess 1-20 (4 tries)
L!rps                # Rock Paper Scissors
L!memory             # Remember emoji sequence
L!reaction_time      # Test reflexes
L!typing_race        # Type sentence fast
L!hangman            # Classic hangman
L!quick_math         # Solve math problem
L!trivia             # Answer trivia
L!choose             # Bot picks from your options

# Micro-games (descriptive names)
L!parity_guess_micro           # Even/odd (basic)
L!dice_sum_micro               # Guess dice sum
L!emoji_memory_micro           # Remember emojis
L!fast_type_micro              # Type character fast
L!unscramble_micro             # Unscramble word

# Micro-games (numeric aliases)
L!micro_1            # Same as parity_guess_micro
L!micro_2            # Same as dice_sum_micro
L!micro_50           # Pick hidden item

# Advanced micro-games
L!parity_grandmaster_iv_micro  # Very hard even/odd
L!emoji_grand_recall_iv_micro  # Expert emoji memory
L!typing_grandmaster_iv_micro  # Pro typing challenge
```

### Viewing Game List
```bash
# Show paginated game list
L!gamelist           # Interactive embed with buttons

# Via help system
L!help mini          # Same interface, category description
```

### Navigation
```
User: L!gamelist
Bot: [Sends embed page 1/30 with Prev/Next/Close buttons]

User: [Clicks Next]
Bot: [Updates to page 2/30]

User: [Clicks Next 5 more times]
Bot: [Now on page 7/30]

User: [Clicks Prev]
Bot: [Back to page 6/30]

User: [Clicks Close]
Bot: [Deletes message]
```

---

## 🔧 TECHNICAL DETAILS

### Message Wait Pattern
```python
def _author_channel_check(self, ctx):
    return lambda m: m.author == ctx.author and m.channel == ctx.channel
```
- Ensures only command author can reply
- Checks same channel
- Used in all `wait_for('message')` calls

### Timeout Handling
```python
async def wait_for_reply(timeout: float):
    try:
        msg = await self.bot.wait_for('message', timeout=timeout, 
                                      check=self._author_channel_check(ctx))
        return msg
    except asyncio.TimeoutError:
        return None
```
- Returns None on timeout
- Each game handles None appropriately
- Typical timeouts: 6-25 seconds

### Difficulty Calculation
```python
idx = int(kind)  # micro index (1-250)
kind_id = (idx - 1) % 10      # 0-9 (game type)
difficulty = (idx - 1) // 10   # 0-24 (difficulty level)
adv = is_advanced or (difficulty > 0)
```
- Micro-games map to 10 core types
- 25 difficulty levels per type
- Advanced mode: shorter timeouts, harder targets

### Command Closure
```python
async def _cmd_wrapper(ctx, *args, _internal=internal):
    await cog._handle_game(ctx, _internal)
```
- Captures `internal` name via default parameter
- Critical: Must use `_internal=internal` not just `internal`
- Prevents "late binding" closure bugs

---

## 💡 DESIGN PATTERNS

### Pattern 1: Safe External Integration
```python
try:
    eco = self.bot.get_cog("Economy")
    if eco and hasattr(eco, "add_coins"):
        res = eco.add_coins(ctx.author.id, amount, reason)
        if asyncio.iscoroutine(res):
            await res
except Exception:
    pass  # Game continues even if economy fails
```
**Benefit:** Games never crash due to external system failures

### Pattern 2: Triple Fallback
```python
# Try method 1
if method_1_available:
    return method_1()
# Try method 2
if method_2_available:
    return method_2()
# Last resort
return method_3()
```
**Used in:**
- Gamelist command lookup
- Help system command discovery
- PaginatedHelpView send strategy

### Pattern 3: Programmatic Registration
```python
for entry in games:
    # Create command wrapper
    async def _cmd_wrapper(ctx, *args, _internal=internal):
        await cog._handle_game(ctx, _internal)
    
    # Handle name collisions
    safe_name = avoid_collision(name, existing)
    
    # Register command
    cmd = commands.Command(_cmd_wrapper, name=safe_name, ...)
    bot.add_command(cmd)
```
**Benefit:** 300+ commands with minimal code duplication

### Pattern 4: View Class Pattern
```python
class GamelistView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=120)
        self.page = 0
        self.author = ctx.author
    
    async def interaction_check(self, interaction):
        return interaction.user.id == self.author.id
    
    @discord.ui.button(label="Next", style=...)
    async def next_button(self, interaction, button):
        self.page += 1
        await interaction.response.edit_message(embed=make_embed(self.page), view=self)
```
**Benefit:** Clean button handling with proper scoping

---

## 🚀 FUTURE ENHANCEMENTS

### Potential Features
1. **Leaderboards**: Track best scores per game
2. **Daily Challenges**: Rotating featured game with bonus rewards
3. **Achievements**: Special badges for game milestones
4. **Multiplayer Variants**: Compete head-to-head
5. **Difficulty Selection**: Let users choose easy/medium/hard
6. **Custom Timeouts**: User preference for time pressure
7. **Game Categories**: Filter by type (speed/memory/math)
8. **Favorite Games**: Star games for quick access
9. **Recent Games**: Show last 5 played
10. **Win Streaks**: Track consecutive wins

### Optimization Ideas
1. **Cache game metadata** in memory
2. **Pre-generate random sequences** for emoji games
3. **Pool database queries** for user storage
4. **Lazy-load game logic** only when needed
5. **Command index** for faster lookup

---

## 🎉 CONCLUSION

The Minigames system is a **robust, extensive, and user-friendly** collection of 300+ mini-games with:

✅ **10 core game types** with 250 difficulty-scaled variants  
✅ **Interactive help system** with working pagination buttons  
✅ **Full economy integration** with automatic rewards  
✅ **Triple-fallback architecture** for maximum reliability  
✅ **User-specific controls** preventing interaction conflicts  
✅ **External compatibility** via PaginatedHelpView export  
✅ **Anti-collision system** for safe command registration  
✅ **Comprehensive error handling** that never breaks gameplay  

**Recent Part 7 updates** fixed all button functionality, improved help embeds, and enhanced user experience with clear instructions and polished UI.

---

**Last Updated**: February 6, 2026  
**Part**: 7 of 7 (Complete)  
**Total Documentation**: ~8,500 words  
**Systems Documented**: 
- Minigames Cog (527 lines)
- Setup System (449 lines)  
- PaginatedHelpView (94 lines)
- Help.py Integration (50 lines)  
**Code Analyzed**: 1,070 lines total (minigames.py)  
**Games Covered**: 300+ minigames across 10 types

---

🎮 **300+ Games. 30 Pages. Infinite Fun.** 🎮
