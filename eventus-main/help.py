import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, button

class HelpCog(commands.Cog):
    """Custom help command: lists available commands with parameters and detailed help."""

    def __init__(self, bot):
        self.bot = bot
        # lightweight examples map for common commands
        self.examples = {
            'topic': 'E!topic 2  # generate a topic and ping top 2 contributors',
            'set_topic_channel': 'E!set_topic_channel #general',
            'enable_topics': 'E!enable_topics',
            'disable_topics': 'E!disable_topics',
            'set_topic_ping': 'E!set_topic_ping 3',
            'add_ping': 'E!add_ping #channel 60 3',
            'list_pings': 'E!list_pings',
            'remove_ping': 'E!remove_ping 42',
            'announce_template': 'E!announce_template my-template',
            'add_template': 'E!add_template my-template | Title | Body with {mentions}',
            'list_templates': 'E!list_templates',
            'remove_template': 'E!remove_template my-template',
            'copy_template': 'E!copy_template global-template',
            'edit_template': 'E!edit_template my-template',
            'polish_template': 'E!polish_template my-template',
            'aip': 'E!aip @member',
            'server_stats': 'E!server_stats',
            'list_topic_categories': 'E!list_topic_categories',
            'list_category_topics': 'E!list_category_topics memes',
            'add_category_topic': 'E!add_category_topic memes "Share your best meme of the week!"',
        }

    def format_signature(self, command):
        # discord.py provides a signature attribute for hybrid commands
        sig = getattr(command, 'signature', None)
        if sig:
            return str(sig)
        # fallback to listing parameters with clearer angle/round bracket style
        params = []
        for name, param in getattr(command, 'clean_params', {}).items():
            if param.default is param.empty:
                params.append(f"<{name}>")
            else:
                params.append(f"[{name}]")
        return ' '.join(params)

    @commands.hybrid_command(name='help', description='Show help for commands. Optionally pass a command name for details.')
    async def help(self, ctx, *, command_name: str = None):
        """When called without args, lists commands the caller can run. When given a command name, show detailed usage."""
        prefix = getattr(ctx, 'prefix', None) or 'E!'
        # detect if caller is an owner: check bot owner or optional OWNER_IDS env var
        is_owner = False
        try:
            is_owner = await self.bot.is_owner(ctx.author)
        except Exception:
            is_owner = False
        if not is_owner:
            # allow custom owner list via env OWNER_IDS (comma separated)
            import os
            owner_env = os.getenv('OWNER_IDS')
            if owner_env:
                try:
                    ids = {int(x.strip()) for x in owner_env.split(',') if x.strip()}
                    if getattr(ctx.author, 'id', None) in ids:
                        is_owner = True
                except Exception:
                    pass

        if command_name:
            cmd = self.bot.get_command(command_name)
            if not cmd:
                # try partial match
                matches = [c for c in self.bot.commands if c.name == command_name or command_name in c.aliases]
                cmd = matches[0] if matches else None
            if not cmd:
                msg = f"No command named '{command_name}' found."
                if hasattr(ctx, 'respond'):
                    await ctx.respond(msg, ephemeral=True)
                else:
                    await ctx.send(msg)
                return

            sig = self.format_signature(cmd)
            desc = cmd.help or cmd.description or ''
            aliases = ', '.join(cmd.aliases) if cmd.aliases else 'None'
            cog_name = cmd.cog_name or 'General'
            embed = discord.Embed(title=f"Help — {cmd.name}", color=discord.Color.blue())
            embed.add_field(name="Usage", value=f"{prefix}{cmd.name} {sig}".strip(), inline=False)
            embed.add_field(name="Description", value=desc or 'No description provided.', inline=False)
            embed.add_field(name="Aliases", value=aliases, inline=True)
            embed.add_field(name="Cog", value=cog_name, inline=True)
            # find examples from command attribute or examples map
            example_text = None
            try:
                example_text = getattr(cmd.callback, 'examples', None)
            except Exception:
                example_text = None
            if not example_text:
                example_text = self.examples.get(cmd.name)
            if example_text:
                embed.add_field(name="Example", value=example_text, inline=False)
            if hasattr(ctx, 'respond'):
                await ctx.respond(embed=embed, ephemeral=True)
            else:
                await ctx.send(embed=embed)
            return

        # Build list of commands. If caller is owner, include owner-only commands too.
        lines = []
        for cmd in sorted(self.bot.commands, key=lambda c: (c.cog_name or '', c.name)):
            # Skip hidden commands
            if getattr(cmd, 'hidden', False):
                continue
            # Owner: include all commands; otherwise check can_run
            if not is_owner:
                try:
                    allowed = await cmd.can_run(ctx)
                except Exception:
                    allowed = False
                if not allowed:
                    continue
            sig = self.format_signature(cmd)
            brief = cmd.short_doc or cmd.help or cmd.description or ''
            cog_label = cmd.cog_name or 'General'
            lines.append((cog_label, f"**{prefix}{cmd.name} {sig}** — {brief}"))

        # Group lines by cog for readability
        grouped = {}
        for cog, text in lines:
            grouped.setdefault(cog, []).append(text)

        # Prepend a friendly overview / how-it-works
        overview = (
            "Eventus is an activity & events bot. Key features:\n"
            "• Auto-generated discussion topics and `/topic` command.\n"
            "• Create events with RSVP buttons, event roles, and channels.\n"
            "• Announcement templates (create, edit, preview, copy).\n"
            "• Activity tracking, rewards, and periodic pings for top contributors.\n"
            "• LLM-powered polishing when `OPENAI_API_KEY` is configured.\n\n"
            "Usage examples:\n"
            f"`{prefix}topic 2` — generate a topic and ping top 2 contributors.\n"
            f"`{prefix}set_topic_channel #general` — set auto-topic channel.\n"
            f"`{prefix}announce_template my-template` — use an announcement template.\n"
            "Owner-only: use `E!help <command>` to see detailed usage for a command.\n"
        )

        # Build paginated embeds grouped by cog (one page per cog to keep things simple)
        pages = []
        # first page: overview
        first = discord.Embed(title="Eventus — Help & Overview", color=discord.Color.green())
        first.add_field(name="Overview", value=overview, inline=False)
        pages.append(first)

        for cog, items in grouped.items():
            e = discord.Embed(title=f"{cog} Commands", color=discord.Color.blue())
            e.description = "\n".join(items)
            pages.append(e)

        # Send first page with interactive paginator if possible
        class HelpPaginator(View):
            def __init__(self, pages, author_id):
                super().__init__(timeout=120)
                self.pages = pages
                self.index = 0
                self.author_id = author_id

            async def interaction_check(self, interaction: discord.Interaction) -> bool:
                # allow only the original requester to use the controls (owners can use all)
                if interaction.user.id == self.author_id:
                    return True
                # allow bot owners
                try:
                    if await self._bot.is_owner(interaction.user):
                        return True
                except Exception:
                    pass
                await interaction.response.send_message("You cannot control this paginator.", ephemeral=True)
                return False

            @property
            def _bot(self):
                return ctx.bot

            async def update_message(self, interaction: discord.Interaction):
                await interaction.response.edit_message(embed=self.pages[self.index], view=self)

            @button(label="Prev", style=discord.ButtonStyle.secondary)
            async def prev(self, interaction: discord.Interaction, button: discord.ui.Button):
                self.index = (self.index - 1) % len(self.pages)
                await self.update_message(interaction)

            @button(label="Next", style=discord.ButtonStyle.primary)
            async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
                self.index = (self.index + 1) % len(self.pages)
                await self.update_message(interaction)

        paginator = HelpPaginator(pages, getattr(ctx.author, 'id', None))

        # Attach an examples footer on detailed view send
        if hasattr(ctx, 'respond'):
            try:
                await ctx.respond(embed=pages[0], view=paginator, ephemeral=True)
            except Exception:
                # fallback to non-ephemeral
                await ctx.send(embed=pages[0], view=paginator)
        else:
            await ctx.send(embed=pages[0], view=paginator)

        if not lines:
            msg = "No commands available for you in this context."
            if hasattr(ctx, 'respond'):
                await ctx.respond(msg, ephemeral=True)
            else:
                await ctx.send(msg)
            return

        # Create paginated embed if long
        chunk_size = 10
        chunks = [lines[i:i+chunk_size] for i in range(0, len(lines), chunk_size)]
        for i, chunk in enumerate(chunks):
            embed = discord.Embed(title="Eventus Commands", color=discord.Color.green())
            embed.description = "\n".join(chunk)
            embed.set_footer(text=f"Page {i+1}/{len(chunks)} — use E!help <command> for details")
            if hasattr(ctx, 'respond'):
                # ephemeral for slash commands
                await ctx.respond(embed=embed, ephemeral=True)
            else:
                await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(HelpCog(bot))
