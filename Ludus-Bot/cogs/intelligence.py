import discord
from discord.ext import commands
import json
import os
from fuzzywuzzy import process
from googletrans import Translator, LANGUAGES

import asyncio

class Intelligence(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.knowledge_file = os.path.join(os.path.dirname(__file__), '..', 'knowledge.json')
        self.knowledge = {}
        self.load_knowledge()
        self.translator = Translator()

    def load_knowledge(self):
        try:
            with open(self.knowledge_file, 'r', encoding='utf-8') as f:
                self.knowledge = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.knowledge = {
                "greetings": ["hello", "hi", "hey", "yo", "sup"],
                "farewells": ["bye", "goodbye", "see you", "later"],
                "knowledge": {
                    "what is your name": "My name is Ludus.",
                    "who are you": "I am Ludus, a Discord bot.",
                    "what are you": "I am a bot on Discord.",
                    "abcs": "a, b, c, d, e, f, g, h, i, j, k, l, m, n, o, p, q, r, s, t, u, v, w, x, y, z",
                    "colors": "red, orange, yellow, green, blue, indigo, violet, purple, pink, brown, black, white, gray",
                    "numbers 1 to 10": "1, 2, 3, 4, 5, 6, 7, 8, 9, 10",
                    "how to use the bot": "You can use my commands by typing `L!` followed by a command name. For example, `L!help`. You can also just chat with me!",
                    "how to get currency": "You can earn currency by playing games, participating in events, and using various commands.",
                    "what are psycoins": "Psycoins are the virtual currency associated with me. You can use them to buy items, play games, and more.",
                    "what is ludus": "That's me! I'm a bot designed for fun and games.",
                    "who created you": "I was created by Psyvrse Development."
                }
            }
            self.save_knowledge()

    def save_knowledge(self):
        with open(self.knowledge_file, 'w', encoding='utf-8') as f:
            json.dump(self.knowledge, f, indent=4)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        content_lower = message.content.lower()
        is_dm = isinstance(message.channel, discord.DMChannel)
        is_mention = self.bot.user in message.mentions
        is_heyludus = content_lower.startswith('hey ludus')

        # Check if the bot is being addressed
        if not (is_dm or is_mention or is_heyludus):
            return

        # Ignore commands
        ctx = await self.bot.get_context(message)
        if ctx.valid:
            return

        content = message.content.strip()

        # Remove trigger phrases to get the actual query
        if is_mention:
            content = content.replace(self.bot.user.mention, "").strip()
        elif is_heyludus:
            content = content[len('hey ludus'):].strip()
            if content.startswith(','):
                content = content[1:].strip()

        # If after removing triggers the content is empty, do nothing.
        if not content:
            return

        # --- Language Detection and Translation ---
        try:
            detected_lang = self.translator.detect(content).lang
            if detected_lang not in LANGUAGES:
                detected_lang = 'en' # Default to english if detection is weird
        except Exception:
            detected_lang = 'en'

        original_content = content
        translated_content = content.lower()
        if detected_lang != 'en':
            try:
                translated = self.translator.translate(content, src=detected_lang, dest='en')
                translated_content = translated.text.lower()
            except Exception:
                # If translation fails, proceed with original content
                pass
        # --- End Language Detection ---

        # Check for greetings
        if translated_content in self.knowledge.get("greetings", []):
            response = f"Hello {message.author.mention}!"
            if detected_lang != 'en':
                response = self.translator.translate(response, dest=detected_lang).text
            await message.channel.send(response)
            return

        # Check for farewells
        if translated_content in self.knowledge.get("farewells", []):
            response = f"Goodbye {message.author.mention}!"
            if detected_lang != 'en':
                response = self.translator.translate(response, dest=detected_lang).text
            await message.channel.send(response)
            return

        # Check knowledge base
        result = process.extractOne(
            translated_content,
            list(self.knowledge["knowledge"].keys())
        )

        if not result:
            best_match = None
            score = 0
        else:
            best_match = result[0]
            score = result[1]

        if score > 80:
            answer = self.knowledge["knowledge"][best_match]
            if detected_lang != 'en':
                answer = self.translator.translate(answer, dest=detected_lang).text
            await message.channel.send(answer)
            return

        # Improved learning mechanism
        if '?' in original_content:
            response = "I don't have an answer for that. Would you like to teach me? If so, please tell me the answer!"
            if detected_lang != 'en':
                response = self.translator.translate(response, dest=detected_lang).text
            await message.channel.send(response)

            def check(m):
                return m.author == message.author and m.channel == message.channel and not m.content.lower().startswith('no')

            try:
                answer_msg = await self.bot.wait_for('message', timeout=60.0, check=check)
                new_answer = answer_msg.content

                # If the user taught in another language, translate the answer to english for storage
                new_answer_lang = self.translator.detect(new_answer).lang
                if new_answer_lang != 'en':
                    new_answer = self.translator.translate(new_answer, dest='en').text

                # Store the original question (in its original language)
                question_to_store = original_content.strip().rstrip('?')
                self.knowledge["knowledge"][question_to_store] = new_answer
                self.save_knowledge()

                response = f"Thank you! I've learned that '{original_content}' means '{new_answer}'."
                if detected_lang != 'en':
                    response = self.translator.translate(response, dest=detected_lang).text
                await message.channel.send(response)

            except asyncio.TimeoutError:
                response = "No problem. I won't learn that for now."
                if detected_lang != 'en':
                    response = self.translator.translate(response, dest=detected_lang).text
                await message.channel.send(response)
            return

        # Simple statement learning
        elif " is " in translated_content and len(translated_content.split(" is ")) == 2:
            parts = translated_content.split(" is ")
            subject = parts[0].strip()
            fact = parts[1].strip()
            if subject and fact:
                self.knowledge["knowledge"][subject] = fact
                self.save_knowledge()
                await message.channel.send(f"Thanks! I've learned that {subject} is {fact}.")

def setup(bot):
    bot.add_cog(Intelligence(bot))
