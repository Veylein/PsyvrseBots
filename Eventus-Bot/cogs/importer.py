import json
import asyncio
from datetime import datetime

import discord
from discord import app_commands
from discord.ui import View, button
from discord.ext import commands

from .. import db_async


class Importer(commands.Cog):
    """Admin importer for Eventus exports. Supports prefix and slash variants.

    - Prefix: `!import_stats [--apply]` with an attached JSON file
    - Slash: `/import_stats attachment:<file> apply:<bool>`
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _process_import(self, data: dict, apply_changes: bool):
        total_actions = []

        users = data.get("users") or []
        for u in users:
            user_id = u.get("user_id") or u.get("id")
            if user_id is None:
                continue
            score = u.get("activity_score", 0)
            last_active = u.get("last_active")
            # Use upsert: increment activity_score and keep latest last_active
            total_actions.append(("upsert_user", user_id))
            if apply_changes:
                if db_async.DATABASE_URL and db_async.asyncpg:
                    sql = (
                        "INSERT INTO users (user_id, activity_score, last_active) VALUES ($1,$2,$3) "
                        "ON CONFLICT (user_id) DO UPDATE SET activity_score = users.activity_score + EXCLUDED.activity_score, "
                        "last_active = CASE WHEN COALESCE(EXCLUDED.last_active, '') > COALESCE(users.last_active, '') THEN EXCLUDED.last_active ELSE users.last_active END"
                    )
                    await db_async.execute(sql, (user_id, score, last_active))
                else:
                    sql = (
                        "INSERT INTO users (user_id, activity_score, last_active) VALUES (?,?,?) "
                        "ON CONFLICT(user_id) DO UPDATE SET activity_score = activity_score + excluded.activity_score, "
                        "last_active = CASE WHEN COALESCE(excluded.last_active, '') > COALESCE(last_active, '') THEN excluded.last_active ELSE last_active END"
                    )
                    await db_async.execute(sql, (user_id, score, last_active), commit=True)

        messages = data.get("messages") or []
        for m in messages:
            mid = m.get("message_id") or m.get("id")
            if mid is None:
                continue
            total_actions.append(("upsert_message", mid))
            if apply_changes:
                if db_async.DATABASE_URL and db_async.asyncpg:
                    sql = (
                        "INSERT INTO messages (message_id, user_id, guild_id, channel_id, content, created_at) VALUES ($1,$2,$3,$4,$5,$6) "
                        "ON CONFLICT (message_id) DO NOTHING"
                    )
                    await db_async.execute(sql, (
                        mid,
                        m.get("user_id"),
                        m.get("guild_id"),
                        m.get("channel_id"),
                        m.get("content"),
                        m.get("created_at"),
                    ))
                else:
                    sql = (
                        "INSERT OR IGNORE INTO messages (message_id, user_id, guild_id, channel_id, content, created_at) "
                        "VALUES (?,?,?,?,?,?)"
                    )
                    await db_async.execute(sql, (
                        mid,
                        m.get("user_id"),
                        m.get("guild_id"),
                        m.get("channel_id"),
                        m.get("content"),
                        m.get("created_at"),
                    ), commit=True)

        pings = data.get("pings") or []
        rewards = data.get("rewards") or []

        async def _insert_generic(table, items, key_field):
            for it in items:
                key = it.get(key_field)
                if key is None:
                    continue
                total_actions.append(("upsert_" + table, key))
                if not apply_changes:
                    continue
                cols = list(it.keys())
                vals = tuple(it[c] for c in cols)
                if db_async.DATABASE_URL and db_async.asyncpg:
                    placeholders = ",".join([f"${i+1}" for i in range(len(cols))])
                    set_clause = ",".join([f"{c} = EXCLUDED.{c}" for c in cols if c != key_field]) or f"{key_field} = EXCLUDED.{key_field}"
                    sql = f"INSERT INTO {table} ({','.join(cols)}) VALUES ({placeholders}) ON CONFLICT ({key_field}) DO UPDATE SET {set_clause}"
                    try:
                        await db_async.execute(sql, vals)
                    except Exception:
                        continue
                else:
                    placeholders = ",".join(["?" for _ in cols])
                    # sqlite uses `excluded` in DO UPDATE
                    set_clause = ",".join([f"{c} = excluded.{c}" for c in cols if c != key_field]) or f"{key_field} = excluded.{key_field}"
                    sql = f"INSERT INTO {table} ({','.join(cols)}) VALUES ({placeholders}) ON CONFLICT({key_field}) DO UPDATE SET {set_clause}"
                    try:
                        await db_async.execute(sql, vals, commit=True)
                    except Exception:
                        continue

        await _insert_generic("pings", pings, "ping_id")
        await _insert_generic("rewards", rewards, "reward_id")

        # Build summary
        summary = {}
        for a in total_actions:
            summary[a[0]] = summary.get(a[0], 0) + 1

        lines = [f"Dry-run: {not apply_changes}", "Planned actions:"]
        for k, v in summary.items():
            lines.append(f" - {k}: {v}")
        return lines

    @commands.command(name="import_stats")
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def import_stats(self, ctx: commands.Context, *, flags: str = ""):
        apply_flag = "--apply" in flags.split()
        if not ctx.message.attachments:
            await ctx.send("Please attach the export JSON file to this message.")
            return
        attachment = ctx.message.attachments[0]
        await ctx.trigger_typing()
        try:
            raw = await attachment.read()
            data = json.loads(raw.decode("utf-8"))
        except Exception as e:
            await ctx.send(f"Failed to read or parse attachment: {e}")
            return

        # Always show a dry-run preview first
        preview_lines = await self._process_import(data, False)
        preview_text = "\n".join(preview_lines)
        preview_msg = await ctx.send(f"Import preview (dry-run):\n{preview_text}\n\nReact with ✅ to apply these changes, or ❌ to cancel. (60s)")
        try:
            await preview_msg.add_reaction("✅")
            await preview_msg.add_reaction("❌")
        except Exception:
            pass

        def _check(reaction, user):
            return (
                user == ctx.author
                and reaction.message.id == preview_msg.id
                and str(reaction.emoji) in ("✅", "❌")
            )

        try:
            reaction, user = await self.bot.wait_for("reaction_add", timeout=60.0, check=_check)
        except asyncio.TimeoutError:
            await ctx.send("Timed out — no changes applied.")
            return

        if str(reaction.emoji) == "✅":
            applied_lines = await self._process_import(data, True)
            await ctx.send("Applied changes:\n" + "\n".join(applied_lines))
        else:
            await ctx.send("Import cancelled — no changes applied.")

    @app_commands.command(name="import_stats")
    @app_commands.describe(attachment="Export JSON file", apply="Apply changes")
    async def import_stats_slash(self, interaction: discord.Interaction, attachment: discord.Attachment, apply: bool = False):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Administrator permissions required.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        try:
            raw = await attachment.read()
            data = json.loads(raw.decode("utf-8"))
        except Exception as e:
            await interaction.followup.send(f"Failed to read or parse attachment: {e}")
            return

        # Show preview and require confirmation via buttons
        preview_lines = await self._process_import(data, False)
        preview_text = "\n".join(preview_lines)
        if len(preview_text) > 1500:
            preview_text = preview_text[:1500] + "\n...truncated"

        class ConfirmView(View):
            def __init__(self, cog, payload, timeout=60):
                super().__init__(timeout=timeout)
                self.cog = cog
                self.payload = payload

            @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)
            async def confirm(self, interaction2: discord.Interaction, button: discord.ui.Button):
                if not interaction2.user.guild_permissions.administrator:
                    await interaction2.response.send_message("Administrator permissions required.", ephemeral=True)
                    return
                await interaction2.response.defer(ephemeral=True)
                lines = await self.cog._process_import(self.payload, True)
                await interaction2.followup.send("Applied changes:\n" + "\n".join(lines), ephemeral=True)
                for child in self.children:
                    child.disabled = True
                try:
                    await interaction2.message.edit(view=self)
                except Exception:
                    pass

            @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red)
            async def cancel(self, interaction2: discord.Interaction, button: discord.ui.Button):
                for child in self.children:
                    child.disabled = True
                try:
                    await interaction2.response.edit_message(content="Import cancelled — no changes applied.", view=self)
                except Exception:
                    await interaction2.response.send_message("Import cancelled.", ephemeral=True)

        view = ConfirmView(self, data)
        await interaction.followup.send(f"Import preview (dry-run):\n{preview_text}\n\nClick Confirm to apply these changes.", ephemeral=True, view=view)


async def setup(bot: commands.Bot):
    cog = Importer(bot)
    await bot.add_cog(cog)
    # Register app command in the cog's tree
    try:
        bot.tree.add_command(cog.import_stats_slash)
    except Exception:
        pass
