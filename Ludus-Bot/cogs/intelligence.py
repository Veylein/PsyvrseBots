import discord
from discord.ext import commands
import json
import os
import re
import random
import wikipedia
import asyncio
from fuzzywuzzy import process

class Intelligence(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.knowledge_file = os.path.join(os.path.dirname(__file__), '..', 'knowledge.json')
        self.knowledge = {}
        self.load_knowledge()

        # Morality & Ethics Responses (6th Grader Style)
        self.moral_map = {
            "cheat": "Cheating is never the answer! It's better to fail honestly than succeed by tricking others. We learn more when we do the work ourselves!",
            "steal": "Stealing is wrong because it hurts others. Imagine if someone took your favorite game! We should always respect other people's property.",
            "bully": "Bullying is totally uncool. Being kind and standing up for others is what real heroes do. If you see someone being bullied, help them out!",
            "lie": "Honesty is the best policy! Lies can grow like snowballs and get messy. Telling the truth builds trust, which is super important.",
            "copy": "Copying someone else's work isn't learning! It's better to ask for help if you're stuck.",
            "wrong": "We all make mistakes, but knowing right from wrong is a superpower. If something feels wrong in your gut, it probably is.",
            "right": "Doing the right thing feels awesome! Even when no one is looking, integrity matters."
        }

        # Gamer Reactions
        self.game_map = {
            "mario": "It's-a me, Mario! Classic! Platformers are the best.",
            "zelda": "Hyrule is amazing! have you found all the shrines yet?",
            "minecraft": "Creeper? Aww man! I love building redstone contraptions.",
            "fortnite": "Where we droppin'? Tilted Towers? Just kidding! Remember to thank the bus driver!",
            "roblox": "Oof! There are so many cool games on Roblox. Do you like tycoons or obbys?",
            "pokemon": "Gotta catch 'em all! Which starter matches your personality? I feel like a psychic type.",
            "arcade": "Pixel art and chiptunes are my jam! High scores are made to be broken.",
            "retro": "Old school games are tough! No save states back then, just pure skill."
        }

    def load_knowledge(self):
        try:
            with open(self.knowledge_file, 'r', encoding='utf-8') as f:
                self.knowledge = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.knowledge = {}

    def solve_math(self, expression):
        # Allow only safe characters for basic math
        allowed = set("0123456789.+-*/() ")
        if not set(expression).issubset(allowed):
            return None
        try:
            # Evaluate using restricted scope
            return eval(expression, {"__builtins__": None}, {})
        except:
            return None

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        is_dm = isinstance(message.channel, discord.DMChannel)
        is_mention = self.bot.user in message.mentions
        content_lower = message.content.lower().strip()
        is_heyludus = content_lower.startswith('hey ludus')

        if not (is_dm or is_mention or is_heyludus):
            return

        # Removing trigger phrases to get pure prompt
        raw_prompt = message.content
        if is_mention:
            raw_prompt = raw_prompt.replace(self.bot.user.mention, "")
        elif is_heyludus:
            # Case insensitive check for length
            if raw_prompt.lower().startswith('hey ludus'):
                raw_prompt = raw_prompt[9:] # len("hey ludus")
        
        prompt = raw_prompt.strip()
        if prompt.startswith(','):
             prompt = prompt[1:].strip()
        
        if not prompt:
            return

        prompt_lower = prompt.lower()

        async with message.channel.typing():
            # 1. Check Morality Keywords
            for k, v in self.moral_map.items():
                if k in prompt_lower:
                    await message.reply(f"🤔 **Ethics Check:** {v}", mention_author=False)
                    return

            # 2. Check Game Keywords
            for k, v in self.game_map.items():
                if k in prompt_lower:
                    await message.reply(f"🎮 {v}", mention_author=False)
                    return

            # 3. Math Helper
            # Regex to find something that looks like a math problem: 'calculate 5+5', 'solve 10/2', 'what is 3*3'
            math_match = re.search(r'(?:calculate|solve|what is)\s+([0-9.\-+*/()\s]+)', prompt_lower)
            if math_match:
                expr = math_match.group(1)
                result = self.solve_math(expr)
                if result is not None:
                    # formatting
                    if isinstance(result, float):
                        result = round(result, 2)
                    await message.reply(f"🧮 That's easy! The answer is **{result}**. Math is fun when you get the hang of it!", mention_author=False)
                    return

            # 4. Wikipedia Knowledge (Homework Helper)
            # Triggers: 'who is', 'what is', 'tell me about', 'define'
            wiki_triggers = ["who is", "what is", "tell me about", "define", "explain"]
            is_wiki_query = any(prompt_lower.startswith(t) for t in wiki_triggers)
            
            if is_wiki_query:
                # remove the trigger to get the search term
                search_term = prompt
                for t in wiki_triggers:
                    if prompt_lower.startswith(t):
                        search_term = prompt[len(t):].strip()
                        break
                
                # Cleanup
                search_term = search_term.rstrip("?!.")
                
                try:
                    # sentences=2 ensures concise 6th-grade level summary
                    summary = wikipedia.summary(search_term, sentences=2)
                    await message.reply(f"📚 **Class Notes:** {summary}", mention_author=False)
                    return
                except wikipedia.exceptions.DisambiguationError as e:
                    options = ", ".join(e.options[:3])
                    await message.reply(f"🤔 Whoa, too many things generally match **{search_term}**! Like: {options}...", mention_author=False)
                    return
                except wikipedia.exceptions.PageError:
                    pass # Fall through to conversational defaults
                except Exception:
                    pass

            # 5. Fallback Conversation
            if "history" in prompt_lower:
                await message.reply("📜 History is fascinating! It teaches us about the past so we can build a better future.", mention_author=False)
            elif "science" in prompt_lower:
                await message.reply("🧪 Science rules! It explains the universe.", mention_author=False)
            else:
                responses = [
                    "That's super interesting! Tell me more!",
                    "I haven't learned about that in school yet, but I'll ask my teacher!",
                    "Can we talk about video games instead? Or maybe history?",
                    "Hmm, I'm pondering that...",
                    "You're pretty smart!"
                ]
                await message.reply(random.choice(responses), mention_author=False)

async def setup(bot):
    await bot.add_cog(Intelligence(bot))
