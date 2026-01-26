import discord
from discord.ext import commands, tasks
from discord import ui
import datetime
import random
from .. import db_async as db
from .. import llm
from .. import ui_theme

class EventOS(commands.Cog):
    EVENT_TEMPLATES = {
        'gaming': {'title': 'Game Night', 'description': 'Join us for a night of gaming!'},
        'study': {'title': 'Study Session', 'description': 'Collaborative study time.'},
        'movie': {'title': 'Movie Night', 'description': 'Watch a movie together!'}
    }

    @commands.command(name="event_template")
    async def event_template_cmd(self, ctx, template: str):
        """Create an event from a template."""
        perms = ctx.author.guild_permissions
        if not (perms.manage_guild or perms.manage_events or perms.create_events):
            await ctx.send("You need 'Create Events', 'Manage Events', or 'Manage Server' permission.")
            return
        t = self.EVENT_TEMPLATES.get(template)
        if not t:
            await ctx.send(f"Template not found. Available: {', '.join(self.EVENT_TEMPLATES.keys())}")
            return
        await self.create_event(ctx, t['title'], description=t['description'])
    
        @commands.slash_command(name="event_template", description="Create an event from a template.")
        async def event_template_slash(self, interaction: discord.Interaction, template: str):
            perms = interaction.user.guild_permissions if hasattr(interaction.user, 'guild_permissions') else None
            if not perms or not (perms.manage_guild or perms.manage_events or perms.create_events):
                await interaction.response.send_message("You need 'Create Events', 'Manage Events', or 'Manage Server' permission.", ephemeral=True)
                return
            t = self.EVENT_TEMPLATES.get(template)
            if not t:
                await interaction.response.send_message(f"Template not found. Available: {', '.join(self.EVENT_TEMPLATES.keys())}", ephemeral=True)
                return
            await self.create_event(interaction, t['title'], description=t['description'])

    @commands.command(name="event_embed")
    async def event_embed_cmd(self, ctx, title: str, description: str, color: str = "blue"):
        """Interactive embed builder for events."""
        perms = ctx.author.guild_permissions
        if not (perms.manage_guild or perms.manage_events or perms.create_events):
            await ctx.send("You need 'Create Events', 'Manage Events', or 'Manage Server' permission.")
            return
        color_map = {"blue": 3447003, "green": 3066993, "red": 15158332, "purple": 10181046}
        embed = discord.Embed(title=title, description=description, color=color_map.get(color, 3447003))
        await ctx.send(embed=embed)

    @commands.command(name="remind_rsvp")
    async def remind_rsvp_cmd(self, ctx, event_id: int):
        """Send RSVP reminders to users who haven't RSVPed."""
        perms = ctx.author.guild_permissions
        if not (perms.manage_guild or perms.manage_events):
            await ctx.send("You need 'Manage Events' or 'Manage Server' permission.")
            return
        row = await db.fetchone("SELECT rsvp_list FROM events WHERE event_id = ?", (event_id,))
        if not row:
            await ctx.send("Event not found.")
            return
        rsvped = row['rsvp_list'].split(',') if row and row['rsvp_list'] else []
        users = await db.fetchall("SELECT user_id FROM users")
        all_users = [str(u['user_id']) for u in users]
        not_rsvped = [uid for uid in all_users if uid not in rsvped]
        sent = 0
        for uid in not_rsvped:
            member = ctx.guild.get_member(int(uid))
            if member:
                try:
                    await member.send(f"Reminder: RSVP for event {event_id}!")
                    sent += 1
                except:
                    pass
        await ctx.send(f"Reminders sent to {sent} users.")

    @commands.command(name="assign_event_role")
    async def assign_event_role_cmd(self, ctx, event_id: int, role: discord.Role):
        """Assign a role to all event attendees."""
        perms = ctx.author.guild_permissions
        if not (perms.manage_guild or perms.manage_events):
            await ctx.send("You need 'Manage Events' or 'Manage Server' permission.")
            return
        row = await db.fetchone("SELECT rsvp_list FROM events WHERE event_id = ?", (event_id,))
        rsvped = row['rsvp_list'].split(',') if row and row['rsvp_list'] else []
        for uid in rsvped:
            member = ctx.guild.get_member(int(uid))
            if member:
                try:
                    await member.add_roles(role)
                except:
                    pass
        await ctx.send(f"Role assigned to {len(rsvped)} attendees.")

    @commands.command(name="find_free_time")
    async def find_free_time_cmd(self, ctx):
        """Suggest best time for events based on user activity."""
        perms = ctx.author.guild_permissions
        if not (perms.manage_guild or perms.manage_events):
            await ctx.send("You need 'Manage Events' or 'Manage Server' permission.")
            return
        rows = await db.fetchall("SELECT last_active FROM users")
        times = [u['last_active'] for u in rows if u['last_active']]
        # Demo: suggest time with least activity (random)
        import random
        best_time = random.choice(["18:00", "20:00", "21:00", "19:00"])
        await ctx.send(f"Suggested best time for event: {best_time}")

    @commands.command(name="create_event_thread")
    async def create_event_thread_cmd(self, ctx, event_id: int):
        """Create a thread for an event."""
        perms = ctx.author.guild_permissions
        if not (perms.manage_guild or perms.manage_events):
            await ctx.send("You need 'Manage Events' or 'Manage Server' permission.")
            return
        thread = await ctx.channel.create_thread(name=f"Event {event_id} Discussion")
        await ctx.send(f"Thread created: {thread.mention}")

    @commands.command(name="setprefix")
    @commands.has_permissions(manage_guild=True)
    async def setprefix_cmd(self, ctx, prefix: str):
        """Change the bot prefix for this server."""
        from eventus_render_mega import set_guild_prefix
        set_guild_prefix(ctx.guild.id, prefix)
        await ctx.send(f"Prefix updated to `{prefix}`.")
    def __init__(self, bot):
        self.bot = bot

    def get_db(self):
        # legacy sync getter — prefer async DB helper
        raise RuntimeError("Use async DB helper via db_async")


class RSVPView(ui.View):
    def __init__(self, cog, event_id: int):
        super().__init__(timeout=None)
        self.cog = cog
        self.event_id = event_id

    async def update_rsvp_store(self, user_id: int, add: bool):
        row = await db.fetchone("SELECT rsvp_list FROM events WHERE event_id = ?", (self.event_id,))
        rsvped = row['rsvp_list'].split(',') if row and row['rsvp_list'] else []
        if add:
            if str(user_id) not in rsvped:
                rsvped.append(str(user_id))
        else:
            rsvped = [u for u in rsvped if u != str(user_id)]
        await db.execute("UPDATE events SET rsvp_list = ? WHERE event_id = ?", (','.join(rsvped), self.event_id), commit=True)

    @ui.button(label="RSVP ✅", style=discord.ButtonStyle.success, custom_id="rsvp_yes")
    async def rsvp(self, interaction: discord.Interaction, button: ui.Button):
        await self.update_rsvp_store(interaction.user.id, True)
        await interaction.response.send_message(content="You have RSVPed ✅", ephemeral=True)

    @ui.button(label="Cancel RSVP ❌", style=discord.ButtonStyle.danger, custom_id="rsvp_no")
    async def cancel(self, interaction: discord.Interaction, button: ui.Button):
        await self.update_rsvp_store(interaction.user.id, False)
        await interaction.response.send_message(content="Your RSVP has been removed ❌", ephemeral=True)

    @commands.command(name="create_event")
    async def create_event(self, ctx, title: str, *, description: str):
        """Create an event with RSVP, recurrence, and reminders."""
        # Permission: must have 'create_event' or 'manage_events' or 'manage_guild'
        perms = ctx.author.guild_permissions
        if not (perms.manage_guild or perms.manage_events or perms.create_events):
            await ctx.send("You need 'Create Events', 'Manage Events', or 'Manage Server' permission to create events.")
            return
        # insert event
        recurrence = 'none'
        if 'weekly' in description.lower():
            recurrence = 'weekly'
        start_time = None
        end_time = None
        # insert event (async)
        await db.execute("INSERT INTO events (title, description, creator_id, start_time, end_time, rsvp_list, recurring) VALUES (?, ?, ?, ?, ?, ?, ?)",
                 (title, description, ctx.author.id, start_time, end_time, "", recurrence), commit=True)
        last = await db.fetchone("SELECT event_id FROM events ORDER BY event_id DESC LIMIT 1")
        event_id = last['event_id'] if last else None

        # Create an event-specific role for announcements (optional)
        event_role = None
        try:
            if ctx.guild.me.guild_permissions.manage_roles:
                role_name = f"Event-{event_id}"
                event_role = discord.utils.get(ctx.guild.roles, name=role_name)
                if not event_role:
                    event_role = await ctx.guild.create_role(name=role_name, mentionable=True)
                    # store role id in events table by extending schema (optional)
        except Exception:
            event_role = None

        # Optionally create a dedicated channel for the event
        event_channel = None
        try:
            if ctx.guild.me.guild_permissions.manage_channels:
                ch_name = f"event-{event_id}"
                existing = discord.utils.get(ctx.guild.text_channels, name=ch_name)
                if not existing:
                    event_channel = await ctx.guild.create_text_channel(ch_name, topic=f"Discussion for event {event_id}")
                else:
                    event_channel = existing
        except Exception:
            event_channel = None

        # finalize DB with created channel/role ids if available
        if event_channel or event_role:
            await db.execute("UPDATE events SET start_time = ?, end_time = ?, rsvp_list = ?, recurring = ?, channel_id = ?, event_role_id = ? WHERE event_id = ?",
                             (start_time, end_time, "", recurrence, event_channel.id if event_channel else None, event_role.id if event_role else None, event_id), commit=True)

        embed = discord.Embed(title=f"📅 Event: {title}", description=description, color=discord.Color.blue())
        footer = f"Event ID: {event_id} | Recurrence: {recurrence}"
        if event_channel:
            footer += f" | Channel: {event_channel.name}"
        embed.set_footer(text=footer)

        view = RSVPView(self, event_id)
        if event_role:
            announce = f"{event_role.mention} \n"
        else:
            announce = ""
        msg = await ctx.send(content=announce, embed=embed, view=view)
        # persist message id for persistent view re-registration
        try:
            await db.execute("UPDATE events SET message_id = ? WHERE event_id = ?", (msg.id, event_id), commit=True)
        except Exception:
            pass
        await ctx.send(f"Event created! Use `{ctx.prefix}rsvp {event_id}` or the buttons to RSVP.")

    @commands.command(name="rsvp")
    async def rsvp_event(self, ctx, event_id: int):
        """RSVP to an event."""
        row = await db.fetchone("SELECT rsvp_list, archived FROM events WHERE event_id = ?", (event_id,))
        if not row:
            await ctx.send("Event not found.")
            return
        if row['archived']:
            await ctx.send("This event is archived.")
            return
        rsvp_list = row['rsvp_list'].split(',') if row['rsvp_list'] else []
        user_id = str(ctx.author.id)
        if user_id in rsvp_list:
            await ctx.send("You already RSVPed.")
            return
        rsvp_list.append(user_id)
        await db.execute("UPDATE events SET rsvp_list = ? WHERE event_id = ?", (','.join(rsvp_list), event_id), commit=True)
        await ctx.send(f"{ctx.author.mention} RSVPed to event {event_id}!")

    @commands.command(name="pick_winner")
    @commands.has_permissions(manage_guild=True)
    async def pick_winner(self, ctx, event_id: int, *, role_name: str = None, ttl_days: int = 0):
        """Pick a random winner from RSVPs and optionally create/assign a winner role."""
        row = await db.fetchone("SELECT rsvp_list, title FROM events WHERE event_id = ?", (event_id,))
        if not row:
            await ctx.send("Event not found.")
            return
        rsvped = row['rsvp_list'].split(',') if row and row['rsvp_list'] else []
        if not rsvped:
            await ctx.send("No RSVPs to pick from.")
            return
        winner_id = int(random.choice(rsvped))
        member = ctx.guild.get_member(winner_id)
        if not member:
            await ctx.send("Winner not in guild or could not be found.")
            return
        # create winner role if requested
        winner_role = None
        try:
            if role_name and ctx.guild.me.guild_permissions.manage_roles:
                winner_role = discord.utils.get(ctx.guild.roles, name=role_name)
                if not winner_role:
                    winner_role = await ctx.guild.create_role(name=role_name, mentionable=True)
                await member.add_roles(winner_role)
                # persist winner role and expiry if ttl provided
                if ttl_days > 0:
                    expire = (datetime.datetime.utcnow() + datetime.timedelta(days=ttl_days)).isoformat()
                    await db.execute("UPDATE events SET winner_role_id = ?, winner_expires = ? WHERE event_id = ?", (winner_role.id, expire, event_id), commit=True)
        except Exception:
            winner_role = None
        
        msg = f"🎉 Congratulations {member.mention}! You were selected as the winner for event {event_id}."
        if winner_role:
            msg += f" You have been given the role {winner_role.name}."
        await ctx.send(msg)

    @commands.Cog.listener()
    async def on_ready(self):
        # ensure cleanup task is started after bot ready
        try:
            self.cleanup_winner_roles.start()
        except Exception:
            pass
        # re-register persistent RSVP views for active events (if message_id stored)
        try:
            rows = await db.fetchall("SELECT event_id, channel_id, message_id FROM events WHERE message_id IS NOT NULL AND archived = 0")
            for r in rows:
                event_id = r['event_id']
                ch_id = r['channel_id']
                msg_id = r['message_id']
                try:
                    channel = self.bot.get_channel(ch_id)
                    if not channel:
                        continue
                    try:
                        await channel.fetch_message(msg_id)
                        self.bot.add_view(RSVPView(self, event_id), message_id=msg_id)
                    except Exception:
                        continue
                except Exception:
                    continue
        except Exception:
            pass

    @commands.Cog.listener()
    async def cog_unload(self):
        try:
            self.cleanup_winner_roles.cancel()
        except Exception:
            pass

    @tasks.loop(hours=24)
    async def cleanup_winner_roles(self):
        # remove winner roles whose expiry has passed
        now = datetime.datetime.utcnow().isoformat()
        rows = await db.fetchall("SELECT event_id, winner_role_id, winner_expires FROM events WHERE winner_role_id IS NOT NULL AND winner_expires IS NOT NULL AND winner_expires <= ?", (now,))
        for r in rows:
            event_id = r['event_id']
            role_id = r['winner_role_id']
            # find role and remove from members; then clear DB fields
            for guild in self.bot.guilds:
                role = guild.get_role(role_id)
                if role:
                    # remove role from all members who have it
                    for member in list(role.members):
                        try:
                            await member.remove_roles(role)
                        except Exception:
                            pass
                    # optionally delete the role
                    try:
                        await role.delete(reason=f"Winner role TTL expired for event {event_id}")
                    except Exception:
                        pass
            await db.execute("UPDATE events SET winner_role_id = NULL, winner_expires = NULL WHERE event_id = ?", (event_id,), commit=True)

    @commands.command(name="archive_event")
    async def archive_event(self, ctx, event_id: int):
        """Archive an event (manage_events or owner only)."""
        perms = ctx.author.guild_permissions
        if not (perms.manage_events or perms.manage_guild or ctx.author.id in [1300838678280671264, 1382187068373074001, 1311394031640776716, 1310134550566797352]):
            await ctx.send("You need 'Manage Events', 'Manage Server', or be an owner to archive events.")
            return
        await db.execute("UPDATE events SET archived = 1 WHERE event_id = ?", (event_id,), commit=True)
        await ctx.send(f"Event {event_id} archived.")

    @commands.command(name="add_template")
    @commands.has_permissions(manage_guild=True)
    async def add_template(self, ctx, name: str, *, content: str):
        """Add an announcement template for this guild. Placeholders: {event_id}, {title}, {channel}, {role_mention}"""
        await db.execute("INSERT INTO announcement_templates (guild_id, name, content, created_at) VALUES (?, ?, ?, ?)", (ctx.guild.id, name, content, datetime.datetime.utcnow().isoformat()), commit=True)
        await ctx.send(f"Template '{name}' added.")

    @commands.command(name="list_templates")
    async def list_templates(self, ctx):
        rows = await db.fetchall("SELECT template_id, name, created_at FROM announcement_templates WHERE guild_id = ? OR guild_id IS NULL ORDER BY created_at DESC", (ctx.guild.id,))
        if not rows:
            await ctx.send("No templates found for this server.")
            return
        msg = "Announcement Templates:\n"
        for r in rows:
            msg += f"- {r['template_id']}: {r['name']} (created {r['created_at']})\n"
        await ctx.send(msg)

    @commands.command(name="remove_template")
    @commands.has_permissions(manage_guild=True)
    async def remove_template(self, ctx, template_id: int):
        await db.execute("DELETE FROM announcement_templates WHERE template_id = ? AND guild_id = ?", (template_id, ctx.guild.id), commit=True)
        await ctx.send(f"Template {template_id} removed.")

    @commands.command(name="copy_template")
    @commands.has_permissions(manage_guild=True)
    async def copy_template(self, ctx, template_id: int, *, new_name: str = None):
        """Copy a global template (guild_id=NULL) into this guild for editing/usage."""
        row = await db.fetchone("SELECT name, content FROM announcement_templates WHERE template_id = ? AND guild_id IS NULL", (template_id,))
        if not row:
            await ctx.send("Global template not found.")
            return
        name = new_name.strip() if new_name else row['name']
        await db.execute("INSERT INTO announcement_templates (guild_id, name, content, created_at) VALUES (?, ?, ?, ?)", (ctx.guild.id, name, row['content'], datetime.datetime.utcnow().isoformat()), commit=True)
        await ctx.send(f"Template '{name}' copied to this server. Use `list_templates` to view and `preview_template` to preview.")

    class TemplateEditModal(ui.Modal):
        def __init__(self, template_id: int, initial_name: str = '', initial_content: str = ''):
            super().__init__(title="Edit Announcement Template")
            self.template_id = template_id
            self.name = ui.TextInput(label="Template Name", style=discord.TextStyle.short, max_length=100, default=initial_name)
            self.content = ui.TextInput(label="Template Content", style=discord.TextStyle.long, max_length=4000, default=initial_content)
            self.add_item(self.name)
            self.add_item(self.content)

        async def on_submit(self, interaction: discord.Interaction):
            # Ask for confirmation before saving edits
            class ConfirmView(ui.View):
                def __init__(self, modal):
                    super().__init__(timeout=120)
                    self.modal = modal

                @ui.button(label="Confirm", style=discord.ButtonStyle.success)
                async def confirm(self, button_interaction: discord.Interaction, button: ui.Button):
                    try:
                        await db.execute("UPDATE announcement_templates SET name = ?, content = ? WHERE template_id = ? AND guild_id = ?",
                                         (self.modal.name.value, self.modal.content.value, self.modal.template_id, button_interaction.guild.id), commit=True)
                        await button_interaction.response.edit_message(content="Template updated.", view=None)
                    except Exception:
                        await button_interaction.response.edit_message(content="Failed to update template.", view=None)

                @ui.button(label="Cancel", style=discord.ButtonStyle.danger)
                async def cancel(self, button_interaction: discord.Interaction, button: ui.Button):
                    await button_interaction.response.edit_message(content="Update canceled.", view=None)

            # show confirmation with a preview of the new values
            preview = f"**Name:** {self.name.value}\n\n**Content (preview):**\n{(self.content.value[:1500] + '...') if len(self.content.value) > 1500 else self.content.value}"
            await interaction.response.send_message(content="Please confirm the template update:\n\n" + preview, view=ConfirmView(self), ephemeral=True)

    @commands.command(name="edit_template")
    @commands.has_permissions(manage_guild=True)
    async def edit_template(self, ctx, template_id: int):
        """Open an interactive editor for a guild template (must be guild-specific)."""
        # Only allow editing guild-specific templates. If template is global, ask user to copy it first.
        row = await db.fetchone("SELECT template_id, name, content, guild_id FROM announcement_templates WHERE template_id = ?", (template_id,))
        if not row:
            await ctx.send("Template not found.")
            return
        if row['guild_id'] is None or row['guild_id'] != ctx.guild.id:
            await ctx.send("This is a global template. Use `copy_template` to copy it into your server before editing.")
            return
        # Send a small view with Preview and Edit buttons. Preview shows ephemeral embed; Edit opens the modal.
        class TemplateEditorView(ui.View):
            def __init__(self, outer, template_id, name, content):
                super().__init__(timeout=300)
                self.outer = outer
                self.template_id = template_id
                self.name = name
                self.content = content

            @ui.button(label="Preview", style=discord.ButtonStyle.primary)
            async def preview_button(self, interaction: discord.Interaction, button: ui.Button):
                # render current content as embed (ephemeral)
                embed = self.outer._render_template_embed(self.content, {'title': self.name, 'event_id': ''}, ctx.channel, '')
                if embed:
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                else:
                    await interaction.response.send_message(self.content[:1900] or 'Empty template', ephemeral=True)

            @ui.button(label="Edit", style=discord.ButtonStyle.secondary)
            async def edit_button(self, interaction: discord.Interaction, button: ui.Button):
                modal = self.outer.TemplateEditModal(self.template_id, initial_name=self.name or '', initial_content=self.content or '')
                await interaction.response.send_modal(modal)

            @ui.button(label="Help", style=discord.ButtonStyle.secondary)
            async def help_button(self, interaction: discord.Interaction, button: ui.Button):
                help_text = (
                    "Placeholders available:\n"
                    "- {event_id} — event numeric id\n"
                    "- {title} — event title\n"
                    "- {channel} — event channel mention\n"
                    "- {role_mention} — event role mention\n\n"
                    "Embed-style template example:\n"
                    "title: 🎮 Game Night Tonight!\n"
                    "description: Join us in {channel} for casual play. RSVP with {event_id}.\n"
                    "color: purple\n"
                    "footer: Hosted by Eventus\n\n"
                    "Use `preview_template` to preview with an event context."
                )
                await interaction.response.send_message(help_text, ephemeral=True)

        view = TemplateEditorView(self, template_id, row['name'] or '', row['content'] or '')
        await ctx.send(f"Editing template {template_id}: {row['name']}", view=view)

    @commands.command(name="announce_template")
    @commands.has_permissions(manage_guild=True)
    async def announce_template(self, ctx, template_id: int, event_id: int):
        row = await db.fetchone("SELECT content FROM announcement_templates WHERE template_id = ? AND (guild_id = ? OR guild_id IS NULL)", (template_id, ctx.guild.id))
        if not row:
            await ctx.send("Template not found.")
            return
        ev = await db.fetchone("SELECT title, channel_id, event_role_id FROM events WHERE event_id = ?", (event_id,))
        if not ev:
            await ctx.send("Event not found.")
            return
        content = row['content']
        channel = self.bot.get_channel(ev['channel_id']) if ev['channel_id'] else ctx.channel
        role_mention = ""
        if ev['event_role_id']:
            role = ctx.guild.get_role(ev['event_role_id'])
            if role:
                role_mention = role.mention
        # If admin requested polishing via LLM marker {polish}, expand using LLM
        try:
            if '{polish}' in content and llm.OPENAI_API_KEY:
                polished = await llm.polish_text(content.replace('{polish}', ''), tone='engaging and concise')
                if polished:
                    content = polished
        except Exception:
            pass
        # Render as embed if template contains embed-like keys
        try:
            embed = self._render_template_embed(content, ev, channel, role_mention)
            if embed:
                await channel.send(embed=embed)
                return
        except Exception:
            pass
        final = content.replace('{event_id}', str(event_id)).replace('{title}', ev['title'] or '')
        final = final.replace('{channel}', channel.mention if channel else '').replace('{role_mention}', role_mention)
        await channel.send(final)

    @commands.command(name="polish_template")
    @commands.has_permissions(manage_guild=True)
    async def polish_template(self, ctx, template_id: int):
        """Use the configured LLM to rewrite a template to be more polished. Creates a copied template in the guild."""
        if not llm.OPENAI_API_KEY:
            await ctx.send("LLM integration not configured (OPENAI_API_KEY missing).")
            return
        row = await db.fetchone("SELECT content, name FROM announcement_templates WHERE template_id = ?", (template_id,))
        if not row:
            await ctx.send("Template not found.")
            return
        polished = await llm.polish_text(row['content'], tone='engaging, concise, professional')
        if not polished:
            await ctx.send("LLM failed to produce a polished version.")
            return
        # insert as new guild-specific template
        new_name = f"{row['name']} (polished)"
        await db.execute("INSERT INTO announcement_templates (guild_id, name, content, created_at) VALUES (?, ?, ?, ?)", (ctx.guild.id, new_name, polished, datetime.datetime.utcnow().isoformat()), commit=True)
        await ctx.send(f"Polished template created as '{new_name}'. Use `list_templates` to view.")

    def _render_template_embed(self, content: str, ev_row: dict, channel, role_mention: str):
        # Simple parser: lines like "title: ...", "description: ...", "color: ...", "footer: ..."
        lines = [l.strip() for l in content.splitlines() if l.strip()]
        embed_kwargs = {}
        other_lines = []
        for ln in lines:
            if ln.lower().startswith('title:'):
                embed_kwargs['title'] = ln.split(':', 1)[1].strip()
            elif ln.lower().startswith('description:'):
                embed_kwargs['description'] = ln.split(':', 1)[1].strip()
            elif ln.lower().startswith('color:'):
                embed_kwargs['color'] = ln.split(':', 1)[1].strip()
            elif ln.lower().startswith('footer:'):
                embed_kwargs['footer'] = ln.split(':', 1)[1].strip()
            elif ln.lower().startswith('thumbnail:'):
                embed_kwargs['thumbnail'] = ln.split(':', 1)[1].strip()
            elif ln.lower().startswith('image:'):
                embed_kwargs['image'] = ln.split(':', 1)[1].strip()
            else:
                other_lines.append(ln)
        # If no embed fields detected, return None
        if not any(k in embed_kwargs for k in ('title','description','color','footer','thumbnail','image')):
            return None
        # Replace placeholders
        event_title = ev_row['title'] if ev_row and 'title' in ev_row else ''
        def repl(s: str):
            return s.replace('{event_id}', str(ev_row.get('event_id','')) if ev_row else '')\
                    .replace('{title}', event_title or '')\
                    .replace('{channel}', channel.mention if channel else '')\
                    .replace('{role_mention}', role_mention)

        title = repl(embed_kwargs.get('title',''))
        desc = repl(embed_kwargs.get('description',''))
        color = embed_kwargs.get('color','')
        footer = repl(embed_kwargs.get('footer',''))
        # Use polished theme builder
        embed = ui_theme.polished_embed(title, desc, color_name=color, image_url=(repl(embed_kwargs['image']) if 'image' in embed_kwargs else None), thumbnail_url=(repl(embed_kwargs['thumbnail']) if 'thumbnail' in embed_kwargs else None), footer=footer)
        # Add any remaining freeform lines as a field
        if other_lines:
            embed.add_field(name="Details", value='\n'.join(other_lines)[:1024], inline=False)
        return embed

    def _color_from_name(self, name: str):
        if not name:
            return discord.Color.blue()
        name = name.lower()
        mapping = {
            'blue': discord.Color.blue(),
            'green': discord.Color.green(),
            'red': discord.Color.red(),
            'purple': discord.Color.purple(),
            'orange': discord.Color.orange(),
            'gold': discord.Color.gold(),
            'teal': discord.Color.teal()
        }
        return mapping.get(name, discord.Color.blue())

    @commands.command(name="preview_template")
    @commands.has_permissions(manage_guild=True)
    async def preview_template(self, ctx, template_id: int, event_id: int = None):
        """Preview a template with optional event context (renders embed if template uses embed keys)."""
        row = await db.fetchone("SELECT content FROM announcement_templates WHERE template_id = ? AND (guild_id = ? OR guild_id IS NULL)", (template_id, ctx.guild.id))
        if not row:
            await ctx.send("Template not found.")
            return
        content = row['content']
        ev = None
        channel = ctx.channel
        role_mention = ''
        if event_id:
            ev = await db.fetchone("SELECT event_id, title, channel_id, event_role_id FROM events WHERE event_id = ?", (event_id,))
            if ev:
                channel = self.bot.get_channel(ev['channel_id']) if ev['channel_id'] else ctx.channel
                if ev['event_role_id']:
                    role = ctx.guild.get_role(ev['event_role_id'])
                    if role:
                        role_mention = role.mention
        try:
            embed = self._render_template_embed(content, ev or {}, channel, role_mention)
            if embed:
                await ctx.send(embed=embed)
                return
        except Exception:
            pass
        # fallback text preview
        final = content.replace('{event_id}', str(event_id) if event_id else '').replace('{title}', ev['title'] if ev and ev['title'] else '')
        final = final.replace('{channel}', channel.mention if channel else '').replace('{role_mention}', role_mention)
        await ctx.send(final)

async def setup(bot):
    await bot.add_cog(EventOS(bot))
