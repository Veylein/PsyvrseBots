import asyncio
import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv


DEFAULT_PREFIX = "$"
MAX_TIMEOUT = timedelta(days=28)
TICKET_CREATE_ID = "psysource:ticket:create"
TICKET_CLOSE_ID = "psysource:ticket:close"
DATA_DIR = Path(__file__).parent / "data"
DATA_FILE = DATA_DIR / "moderation_data.json"
DURATION_RE = re.compile(r"(\d+)([smhdw])", re.IGNORECASE)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def truncate(text: str, limit: int = 1000) -> str:
    value = (text or "").strip()
    if len(value) <= limit:
        return value
    return f"{value[:limit]}... (truncated)"


def parse_duration(raw: str) -> Optional[timedelta]:
    if raw is None:
        return None
    text = raw.strip().lower()
    if not text:
        return None
    if text.isdigit():
        minutes = int(text)
        return timedelta(minutes=minutes) if minutes > 0 else None

    compact = text.replace(" ", "")
    matches = list(DURATION_RE.finditer(compact))
    if not matches:
        return None
    consumed = "".join(match.group(0) for match in matches)
    if consumed != compact:
        return None

    total = timedelta()
    for match in matches:
        amount = int(match.group(1))
        unit = match.group(2).lower()
        if amount <= 0:
            return None
        if unit == "s":
            total += timedelta(seconds=amount)
        elif unit == "m":
            total += timedelta(minutes=amount)
        elif unit == "h":
            total += timedelta(hours=amount)
        elif unit == "d":
            total += timedelta(days=amount)
        elif unit == "w":
            total += timedelta(weeks=amount)
        else:
            return None

    return total if total.total_seconds() > 0 else None


def parse_hex_color(raw: Optional[str]) -> Optional[discord.Color]:
    if raw is None:
        return None
    value = raw.strip().lower()
    if value.startswith("0x"):
        value = value[2:]
    if value.startswith("#"):
        value = value[1:]
    if not re.fullmatch(r"[0-9a-f]{6}", value):
        return None
    return discord.Color(int(value, 16))


def safe_channel_slug(name: str) -> str:
    lowered = re.sub(r"[^a-zA-Z0-9-]+", "-", name.lower())
    lowered = re.sub(r"-{2,}", "-", lowered).strip("-")
    return (lowered or "member")[:24]


def iso_to_unix(value: str) -> Optional[int]:
    try:
        return int(datetime.fromisoformat(value).timestamp())
    except (TypeError, ValueError):
        return None


def format_member_message(template: str, member: discord.Member) -> str:
    values = {
        "user": member.mention,
        "user_name": member.display_name,
        "server": member.guild.name,
        "member_count": member.guild.member_count or 0,
    }
    try:
        return template.format(**values)
    except Exception:
        return template


class ModerationStore:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.data = {"guilds": {}}
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            self.save()
            return
        try:
            loaded = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                self.data = loaded
            else:
                self.data = {"guilds": {}}
        except Exception:
            self.data = {"guilds": {}}
            self.save()

    def save(self) -> None:
        payload = json.dumps(self.data, indent=2)
        tmp_path = self.path.with_suffix(".tmp")
        tmp_path.write_text(payload, encoding="utf-8")
        tmp_path.replace(self.path)

    def guild(self, guild_id: int) -> dict:
        guilds = self.data.setdefault("guilds", {})
        key = str(guild_id)
        if key not in guilds or not isinstance(guilds[key], dict):
            guilds[key] = {}
        cfg = guilds[key]
        cfg.setdefault("log_channel_id", None)
        cfg.setdefault("welcome_channel_id", None)
        cfg.setdefault("goodbye_channel_id", None)
        cfg.setdefault(
            "welcome_message",
            "Welcome {user} to {server}. You are member #{member_count}.",
        )
        cfg.setdefault("goodbye_message", "{user_name} left {server}.")
        cfg.setdefault("ticket_category_id", None)
        cfg.setdefault("ticket_staff_role_id", None)
        cfg.setdefault("warns", {})
        cfg.setdefault("tickets", {"counter": 0, "open": {}})
        if not isinstance(cfg["warns"], dict):
            cfg["warns"] = {}
        if not isinstance(cfg["tickets"], dict):
            cfg["tickets"] = {"counter": 0, "open": {}}
        cfg["tickets"].setdefault("counter", 0)
        cfg["tickets"].setdefault("open", {})
        return cfg

    def add_warn(self, guild_id: int, user_id: int, moderator_id: int, reason: str) -> dict:
        cfg = self.guild(guild_id)
        warns = cfg["warns"].setdefault(str(user_id), [])
        next_id = max((int(item.get("id", 0)) for item in warns), default=0) + 1
        entry = {
            "id": next_id,
            "reason": reason,
            "moderator_id": moderator_id,
            "created_at": utc_now_iso(),
        }
        warns.append(entry)
        self.save()
        return entry

    def get_warns(self, guild_id: int, user_id: int) -> list[dict]:
        cfg = self.guild(guild_id)
        warns = cfg["warns"].get(str(user_id), [])
        if not isinstance(warns, list):
            return []
        return list(warns)

    def remove_warn(self, guild_id: int, user_id: int, warn_id: int) -> Optional[dict]:
        cfg = self.guild(guild_id)
        key = str(user_id)
        warns = cfg["warns"].get(key, [])
        if not isinstance(warns, list):
            return None
        for index, item in enumerate(warns):
            if int(item.get("id", 0)) == warn_id:
                removed = warns.pop(index)
                if not warns:
                    cfg["warns"].pop(key, None)
                self.save()
                return removed
        return None

    def clear_warns(self, guild_id: int, user_id: int) -> int:
        cfg = self.guild(guild_id)
        removed = cfg["warns"].pop(str(user_id), [])
        if removed:
            self.save()
        return len(removed)

    def peek_next_ticket_number(self, guild_id: int) -> int:
        cfg = self.guild(guild_id)
        return int(cfg["tickets"].get("counter", 0)) + 1

    def register_ticket(self, guild_id: int, channel_id: int, owner_id: int, number: int) -> None:
        cfg = self.guild(guild_id)
        tickets = cfg["tickets"]
        current = int(tickets.get("counter", 0))
        tickets["counter"] = max(current, number)
        tickets["open"][str(channel_id)] = {
            "owner_id": owner_id,
            "number": number,
            "created_at": utc_now_iso(),
        }
        self.save()

    def get_ticket(self, guild_id: int, channel_id: int) -> Optional[dict]:
        cfg = self.guild(guild_id)
        ticket = cfg["tickets"]["open"].get(str(channel_id))
        return ticket if isinstance(ticket, dict) else None

    def close_ticket(self, guild_id: int, channel_id: int) -> Optional[dict]:
        cfg = self.guild(guild_id)
        ticket = cfg["tickets"]["open"].pop(str(channel_id), None)
        if ticket is not None:
            self.save()
        return ticket

    def find_open_ticket_by_owner(self, guild_id: int, owner_id: int) -> Optional[tuple[int, dict]]:
        cfg = self.guild(guild_id)
        for channel_id, ticket in cfg["tickets"]["open"].items():
            if isinstance(ticket, dict) and int(ticket.get("owner_id", 0)) == owner_id:
                return int(channel_id), ticket
        return None


load_dotenv()
TOKEN = (
    os.getenv("DISCORD_TOKEN")
    or os.getenv("PSYVERSE_TOKEN")
    or os.getenv("PSYVRSE_TOKEN")
)
if not TOKEN:
    raise RuntimeError("Missing DISCORD_TOKEN/PSYVERSE_TOKEN/PSYVRSE_TOKEN in .env")

allowed_guild_raw = os.getenv("PSYVRSE_GUILD_ID") or os.getenv("ALLOWED_GUILD_ID")
if allowed_guild_raw and allowed_guild_raw.isdigit():
    ALLOWED_GUILD_ID = int(allowed_guild_raw)
else:
    ALLOWED_GUILD_ID = 0

PREFIX = os.getenv("BOT_PREFIX", DEFAULT_PREFIX)

store = ModerationStore(DATA_FILE)

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.message_content = True


class PsySourceBot(commands.Bot):
    async def setup_hook(self) -> None:
        self.add_view(TicketPanelView())
        self.add_view(TicketCloseView())
        if ALLOWED_GUILD_ID:
            guild_obj = discord.Object(id=ALLOWED_GUILD_ID)
            self.tree.copy_global_to(guild=guild_obj)
            synced = await self.tree.sync(guild=guild_obj)
            print(f"Synced {len(synced)} command(s) to guild {ALLOWED_GUILD_ID}.")
        else:
            synced = await self.tree.sync()
            print(f"Synced {len(synced)} global command(s).")


bot = PsySourceBot(
    command_prefix=commands.when_mentioned_or(PREFIX),
    intents=intents,
    help_command=None,
)


def is_allowed_guild(guild: Optional[discord.Guild]) -> bool:
    if guild is None:
        return False
    if ALLOWED_GUILD_ID and guild.id != ALLOWED_GUILD_ID:
        return False
    return True

    @bot.check
def mention_channel(channel_id: Optional[int]) -> str:
    if not channel_id:
        return "Not set"
    return f"<#{channel_id}>"


def mention_role(role_id: Optional[int]) -> str:
    if not role_id:
        return "Not set"
    return f"<@&{role_id}>"


def has_role(member: discord.Member, role_id: Optional[int]) -> bool:
    if not role_id:
        return False
    return any(role.id == int(role_id) for role in member.roles)


def can_target(actor: discord.Member, target: discord.Member, me: Optional[discord.Member]) -> tuple[bool, str]:
    if actor.id == target.id:
        return False, "You cannot target yourself."
    if target.id == actor.guild.owner_id:
        return False, "You cannot target the server owner."
    if actor.id != actor.guild.owner_id and actor.top_role <= target.top_role:
        return False, "Your top role must be higher than the target's top role."
    if me is not None and me.top_role <= target.top_role:
        return False, "My top role must be higher than the target's top role."
    return True, ""


async def resolve_text_channel(
    guild: discord.Guild, channel_id: Optional[int]
) -> Optional[discord.TextChannel]:
    if not channel_id:
        return None
    try:
        cid = int(channel_id)
    except (TypeError, ValueError):
        return None

    cached = guild.get_channel(cid)
    if isinstance(cached, discord.TextChannel):
        return cached

    try:
        fetched = await bot.fetch_channel(cid)
    except (discord.NotFound, discord.Forbidden, discord.HTTPException):
        return None
    return fetched if isinstance(fetched, discord.TextChannel) else None


async def send_log(
    guild: discord.Guild,
    title: str,
    description: str,
    color: discord.Color = discord.Color.blurple(),
) -> None:
    cfg = store.guild(guild.id)
    channel = await resolve_text_channel(guild, cfg.get("log_channel_id"))
    if channel is None:
        return
    embed = discord.Embed(
        title=title,
        description=truncate(description, 3900) or "No details.",
        color=color,
        timestamp=discord.utils.utcnow(),
    )
    try:
        await channel.send(embed=embed)
    except discord.HTTPException:
        return


async def reply(interaction: discord.Interaction, content: str, ephemeral: bool = True) -> None:
    if interaction.response.is_done():
        await interaction.followup.send(content, ephemeral=ephemeral)
    else:
        await interaction.response.send_message(content, ephemeral=ephemeral)


async def close_ticket_channel(interaction: discord.Interaction, reason: str) -> None:
    guild = interaction.guild
    if guild is None or not isinstance(interaction.channel, discord.TextChannel):
        await reply(interaction, "This action can only be used in a ticket channel.")
        return

    ticket = store.get_ticket(guild.id, interaction.channel.id)
    if ticket is None:
        await reply(interaction, "This channel is not an open ticket.")
        return

    member = interaction.user if isinstance(interaction.user, discord.Member) else None
    if member is None:
        await reply(interaction, "Member data not available.")
        return

    cfg = store.guild(guild.id)
    owner_id = int(ticket.get("owner_id", 0))
    staff_role_id = cfg.get("ticket_staff_role_id")
    can_close = (
        member.id == owner_id
        or member.guild_permissions.manage_channels
        or has_role(member, staff_role_id)
    )
    if not can_close:
        await reply(interaction, "Only the ticket owner or staff can close this ticket.")
        return

    store.close_ticket(guild.id, interaction.channel.id)
    await reply(interaction, "Closing ticket in 3 seconds...", ephemeral=True)
    await send_log(
        guild,
        "Ticket Closed",
        f"{member.mention} closed {interaction.channel.mention}. Reason: {reason}",
        discord.Color.orange(),
    )
    await asyncio.sleep(3)
    try:
        await interaction.channel.delete(reason=f"Ticket closed by {member} ({member.id})")
    except discord.HTTPException:
        pass


class TicketPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Create Ticket",
        style=discord.ButtonStyle.primary,
        custom_id=TICKET_CREATE_ID,
    )
    async def create_ticket(
        self,
        interaction: discord.Interaction,
        _button: discord.ui.Button,
    ) -> None:
        guild = interaction.guild
        member = interaction.user if isinstance(interaction.user, discord.Member) else None
        if guild is None or member is None:
            await reply(interaction, "This action can only be used in a server.")
            return
        if not is_allowed_guild(guild):
            await reply(interaction, "This bot is locked to Psyvrse.")
            return

        existing = store.find_open_ticket_by_owner(guild.id, member.id)
        if existing:
            existing_channel = guild.get_channel(existing[0])
            mention = (
                existing_channel.mention
                if isinstance(existing_channel, discord.TextChannel)
                else f"<#{existing[0]}>"
            )
            await reply(interaction, f"You already have an open ticket: {mention}")
            return

        cfg = store.guild(guild.id)
        number = store.peek_next_ticket_number(guild.id)
        channel_name = f"ticket-{safe_channel_slug(member.display_name)}-{number}"

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            member: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                attach_files=True,
                embed_links=True,
            ),
        }

        staff_role = None
        if cfg.get("ticket_staff_role_id"):
            staff_role = guild.get_role(int(cfg["ticket_staff_role_id"]))
        if staff_role:
            overwrites[staff_role] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                attach_files=True,
                embed_links=True,
                manage_messages=True,
            )

        me = guild.me or guild.get_member(bot.user.id if bot.user else 0)
        if me:
            overwrites[me] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                attach_files=True,
                embed_links=True,
                manage_messages=True,
                manage_channels=True,
            )

        category = None
        if cfg.get("ticket_category_id"):
            maybe_category = guild.get_channel(int(cfg["ticket_category_id"]))
            if isinstance(maybe_category, discord.CategoryChannel):
                category = maybe_category

        try:
            ticket_channel = await guild.create_text_channel(
                name=channel_name,
                overwrites=overwrites,
                category=category,
                reason=f"Ticket opened by {member} ({member.id})",
            )
        except discord.Forbidden:
            await reply(interaction, "I do not have permission to create ticket channels.")
            return
        except discord.HTTPException as exc:
            await reply(interaction, f"Failed to create ticket: {exc}")
            return

        store.register_ticket(guild.id, ticket_channel.id, member.id, number)

        embed = discord.Embed(
            title=f"Ticket #{number}",
            description="Describe your issue and a staff member will help you soon.",
            color=discord.Color.blurple(),
            timestamp=discord.utils.utcnow(),
        )
        embed.add_field(name="Opened by", value=member.mention, inline=True)
        embed.set_footer(text="Use the button below when your issue is resolved.")

        await ticket_channel.send(
            content=member.mention,
            embed=embed,
            view=TicketCloseView(),
        )
        await reply(interaction, f"Ticket created: {ticket_channel.mention}", ephemeral=True)
        await send_log(
            guild,
            "Ticket Opened",
            f"{member.mention} opened {ticket_channel.mention} (#{number}).",
            discord.Color.green(),
        )


class TicketCloseView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Close Ticket",
        style=discord.ButtonStyle.danger,
        custom_id=TICKET_CLOSE_ID,
    )
    async def close_ticket(
        self,
        interaction: discord.Interaction,
        _button: discord.ui.Button,
    ) -> None:
        await close_ticket_channel(interaction, "Closed from ticket button")


@bot.check
async def prefix_scope_check(ctx: commands.Context) -> bool:
    if ctx.guild is None:
        await ctx.send("This bot only works in servers.")
        return False
    if ALLOWED_GUILD_ID and ctx.guild.id != ALLOWED_GUILD_ID:
        return False
    return True


@bot.tree.check
async def slash_scope_check(interaction: discord.Interaction) -> bool:
    if interaction.guild is None:
        raise app_commands.CheckFailure("This command only works in servers.")
    if ALLOWED_GUILD_ID and interaction.guild_id != ALLOWED_GUILD_ID:
        raise app_commands.CheckFailure("This bot is locked to Psyvrse.")
    return True


@bot.event
async def on_ready() -> None:
    if bot.user:
        print(f"Logged in as {bot.user} ({bot.user.id})")


@bot.tree.command(name="modhelp", description="Show moderation and utility command list.")
async def modhelp(interaction: discord.Interaction) -> None:
    embed = discord.Embed(
        title="PsySource Commands",
        color=discord.Color.blurple(),
        timestamp=discord.utils.utcnow(),
    )
    embed.description = (
        "Moderation: /ban, /kick, /warn, /warns, /removewarn, /clearwarns, "
        "/mute, /unmute, /unban, /purge\n"
        "Logging and messaging: /setlog, /setwelcome, /setgoodbye, "
        "/setwelcomemsg, /setgoodbyemsg\n"
        "Tickets: /ticketpanel, /setticketcategory, /setticketstaff, /close_ticket\n"
        "Utility: /say, /embed, /serverconfig"
    )
    embed.set_footer(text=f"Prefix commands also available: {PREFIX}say and {PREFIX}embed")
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="setlog", description="Set the log channel.")
@app_commands.checks.has_permissions(manage_guild=True)
async def setlog(interaction: discord.Interaction, channel: discord.TextChannel) -> None:
    cfg = store.guild(interaction.guild_id)
    cfg["log_channel_id"] = channel.id
    store.save()
    await interaction.response.send_message(
        f"Log channel set to {channel.mention}.",
        ephemeral=True,
    )


@bot.tree.command(name="setwelcome", description="Set the welcome channel.")
@app_commands.checks.has_permissions(manage_guild=True)
async def setwelcome(interaction: discord.Interaction, channel: discord.TextChannel) -> None:
    cfg = store.guild(interaction.guild_id)
    cfg["welcome_channel_id"] = channel.id
    store.save()
    await interaction.response.send_message(
        f"Welcome channel set to {channel.mention}.",
        ephemeral=True,
    )


@bot.tree.command(name="setgoodbye", description="Set the goodbye channel.")
@app_commands.checks.has_permissions(manage_guild=True)
async def setgoodbye(interaction: discord.Interaction, channel: discord.TextChannel) -> None:
    cfg = store.guild(interaction.guild_id)
    cfg["goodbye_channel_id"] = channel.id
    store.save()
    await interaction.response.send_message(
        f"Goodbye channel set to {channel.mention}.",
        ephemeral=True,
    )


@bot.tree.command(name="setwelcomemsg", description="Set welcome message template.")
@app_commands.checks.has_permissions(manage_guild=True)
@app_commands.describe(message="Use {user}, {user_name}, {server}, {member_count}")
async def setwelcomemsg(interaction: discord.Interaction, message: str) -> None:
    cfg = store.guild(interaction.guild_id)
    cfg["welcome_message"] = message
    store.save()
    await interaction.response.send_message("Welcome message template updated.", ephemeral=True)


@bot.tree.command(name="setgoodbyemsg", description="Set goodbye message template.")
@app_commands.checks.has_permissions(manage_guild=True)
@app_commands.describe(message="Use {user}, {user_name}, {server}, {member_count}")
async def setgoodbyemsg(interaction: discord.Interaction, message: str) -> None:
    cfg = store.guild(interaction.guild_id)
    cfg["goodbye_message"] = message
    store.save()
    await interaction.response.send_message("Goodbye message template updated.", ephemeral=True)


@bot.tree.command(name="setticketcategory", description="Set ticket category (or clear it).")
@app_commands.checks.has_permissions(manage_channels=True)
async def setticketcategory(
    interaction: discord.Interaction,
    category: Optional[discord.CategoryChannel] = None,
) -> None:
    cfg = store.guild(interaction.guild_id)
    cfg["ticket_category_id"] = category.id if category else None
    store.save()
    if category:
        await interaction.response.send_message(
            f"Ticket category set to **{category.name}**.",
            ephemeral=True,
        )
    else:
        await interaction.response.send_message("Ticket category cleared.", ephemeral=True)


@bot.tree.command(name="setticketstaff", description="Set ticket staff role (or clear it).")
@app_commands.checks.has_permissions(manage_channels=True)
async def setticketstaff(
    interaction: discord.Interaction,
    role: Optional[discord.Role] = None,
) -> None:
    cfg = store.guild(interaction.guild_id)
    cfg["ticket_staff_role_id"] = role.id if role else None
    store.save()
    if role:
        await interaction.response.send_message(
            f"Ticket staff role set to {role.mention}.",
            ephemeral=True,
        )
    else:
        await interaction.response.send_message("Ticket staff role cleared.", ephemeral=True)


@bot.tree.command(name="ticketpanel", description="Send the ticket panel in a channel.")
@app_commands.checks.has_permissions(manage_channels=True)
async def ticketpanel(
    interaction: discord.Interaction,
    channel: discord.TextChannel,
    message: Optional[str] = None,
) -> None:
    panel_message = message or "Need help? Click the button below to open a private ticket."
    embed = discord.Embed(
        title="Support Tickets",
        description=panel_message,
        color=discord.Color.blurple(),
    )
    await channel.send(embed=embed, view=TicketPanelView())
    await interaction.response.send_message(
        f"Ticket panel sent in {channel.mention}.",
        ephemeral=True,
    )
    await send_log(
        interaction.guild,
        "Ticket Panel Posted",
        f"{interaction.user.mention} posted a ticket panel in {channel.mention}.",
        discord.Color.blurple(),
    )


@bot.tree.command(name="close_ticket", description="Close the current ticket channel.")
@app_commands.describe(reason="Reason for closing the ticket")
async def close_ticket(interaction: discord.Interaction, reason: str = "Closed by command") -> None:
    await close_ticket_channel(interaction, reason)


@bot.tree.command(name="ban", description="Ban a user from the server.")
@app_commands.checks.has_permissions(ban_members=True)
async def ban(
    interaction: discord.Interaction,
    user: discord.Member,
    reason: Optional[str] = None,
) -> None:
    actor = interaction.user if isinstance(interaction.user, discord.Member) else None
    if actor is None:
        await interaction.response.send_message("Member data not available.", ephemeral=True)
        return
    allowed, message = can_target(actor, user, interaction.guild.me)
    if not allowed:
        await interaction.response.send_message(message, ephemeral=True)
        return

    reason_text = reason or "No reason provided."
    try:
        await user.ban(reason=f"{reason_text} | by {actor} ({actor.id})")
    except discord.Forbidden:
        await interaction.response.send_message("I do not have permission to ban that user.", ephemeral=True)
        return
    except discord.HTTPException as exc:
        await interaction.response.send_message(f"Ban failed: {exc}", ephemeral=True)
        return

    await interaction.response.send_message(f"Banned **{user}**. Reason: {reason_text}")
    await send_log(
        interaction.guild,
        "Member Banned",
        f"{actor.mention} banned **{user}** (`{user.id}`). Reason: {reason_text}",
        discord.Color.red(),
    )


@bot.tree.command(name="kick", description="Kick a user from the server.")
@app_commands.checks.has_permissions(kick_members=True)
async def kick(
    interaction: discord.Interaction,
    user: discord.Member,
    reason: Optional[str] = None,
) -> None:
    actor = interaction.user if isinstance(interaction.user, discord.Member) else None
    if actor is None:
        await interaction.response.send_message("Member data not available.", ephemeral=True)
        return
    allowed, message = can_target(actor, user, interaction.guild.me)
    if not allowed:
        await interaction.response.send_message(message, ephemeral=True)
        return

    reason_text = reason or "No reason provided."
    try:
        await user.kick(reason=f"{reason_text} | by {actor} ({actor.id})")
    except discord.Forbidden:
        await interaction.response.send_message("I do not have permission to kick that user.", ephemeral=True)
        return
    except discord.HTTPException as exc:
        await interaction.response.send_message(f"Kick failed: {exc}", ephemeral=True)
        return

    await interaction.response.send_message(f"Kicked **{user}**. Reason: {reason_text}")
    await send_log(
        interaction.guild,
        "Member Kicked",
        f"{actor.mention} kicked **{user}** (`{user.id}`). Reason: {reason_text}",
        discord.Color.orange(),
    )


@bot.tree.command(name="warn", description="Warn a user and store it.")
@app_commands.checks.has_permissions(moderate_members=True)
async def warn(
    interaction: discord.Interaction,
    user: discord.Member,
    reason: Optional[str] = None,
) -> None:
    actor = interaction.user if isinstance(interaction.user, discord.Member) else None
    if actor is None:
        await interaction.response.send_message("Member data not available.", ephemeral=True)
        return
    allowed, message = can_target(actor, user, interaction.guild.me)
    if not allowed:
        await interaction.response.send_message(message, ephemeral=True)
        return

    reason_text = reason or "No reason provided."
    entry = store.add_warn(interaction.guild_id, user.id, actor.id, reason_text)

    try:
        await user.send(
            f"You were warned in **{interaction.guild.name}**.\n"
            f"Reason: {reason_text}\n"
            f"Warn ID: #{entry['id']}"
        )
    except discord.HTTPException:
        pass

    await interaction.response.send_message(
        f"Warned {user.mention}. Warn ID: **#{entry['id']}**. Reason: {reason_text}"
    )
    await send_log(
        interaction.guild,
        "Member Warned",
        f"{actor.mention} warned {user.mention} (`{user.id}`) as #{entry['id']}. Reason: {reason_text}",
        discord.Color.gold(),
    )


@bot.tree.command(name="warns", description="Check stored warnings for a user.")
@app_commands.checks.has_permissions(moderate_members=True)
async def warns(interaction: discord.Interaction, user: discord.Member) -> None:
    entries = store.get_warns(interaction.guild_id, user.id)
    if not entries:
        await interaction.response.send_message(
            f"{user.mention} has no warnings.",
            ephemeral=True,
        )
        return

    embed = discord.Embed(
        title=f"Warnings for {user}",
        color=discord.Color.gold(),
        timestamp=discord.utils.utcnow(),
    )
    lines = []
    for item in entries[-10:]:
        stamp = iso_to_unix(item.get("created_at"))
        when = f"<t:{stamp}:R>" if stamp else "unknown time"
        reason = truncate(item.get("reason", "No reason."), 120)
        lines.append(
            f"`#{item.get('id', '?')}` - {reason} | mod <@{item.get('moderator_id')}> | {when}"
        )

    embed.description = "\n".join(lines)
    if len(entries) > 10:
        embed.set_footer(text=f"Showing newest 10 of {len(entries)} warnings.")

    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="removewarn", description="Remove one warning by warn ID.")
@app_commands.checks.has_permissions(moderate_members=True)
async def removewarn(
    interaction: discord.Interaction,
    user: discord.Member,
    warn_id: int,
) -> None:
    removed = store.remove_warn(interaction.guild_id, user.id, warn_id)
    if removed is None:
        await interaction.response.send_message(
            f"No warning #{warn_id} found for {user.mention}.",
            ephemeral=True,
        )
        return

    await interaction.response.send_message(f"Removed warning #{warn_id} from {user.mention}.")
    await send_log(
        interaction.guild,
        "Warning Removed",
        f"{interaction.user.mention} removed warning #{warn_id} from {user.mention}.",
        discord.Color.orange(),
    )


@bot.tree.command(name="clearwarns", description="Clear all warnings for a user.")
@app_commands.checks.has_permissions(moderate_members=True)
async def clearwarns(interaction: discord.Interaction, user: discord.Member) -> None:
    count = store.clear_warns(interaction.guild_id, user.id)
    await interaction.response.send_message(
        f"Removed **{count}** warning(s) from {user.mention}.",
        ephemeral=False,
    )
    await send_log(
        interaction.guild,
        "Warnings Cleared",
        f"{interaction.user.mention} cleared {count} warning(s) for {user.mention}.",
        discord.Color.orange(),
    )


@bot.tree.command(name="mute", description="Mute (timeout) a user.")
@app_commands.checks.has_permissions(moderate_members=True)
@app_commands.describe(duration="Examples: 15m, 2h, 1d, 1h30m")
async def mute(
    interaction: discord.Interaction,
    user: discord.Member,
    duration: str,
    reason: Optional[str] = None,
) -> None:
    actor = interaction.user if isinstance(interaction.user, discord.Member) else None
    if actor is None:
        await interaction.response.send_message("Member data not available.", ephemeral=True)
        return
    allowed, message = can_target(actor, user, interaction.guild.me)
    if not allowed:
        await interaction.response.send_message(message, ephemeral=True)
        return

    delta = parse_duration(duration)
    if delta is None:
        await interaction.response.send_message(
            "Invalid duration. Use values like `15m`, `2h`, `1d`, or `1h30m`.",
            ephemeral=True,
        )
        return
    if delta > MAX_TIMEOUT:
        await interaction.response.send_message(
            "Mute duration cannot be more than 28 days.",
            ephemeral=True,
        )
        return

    reason_text = reason or "No reason provided."
    until = discord.utils.utcnow() + delta
    try:
        await user.timeout(until, reason=f"{reason_text} | by {actor} ({actor.id})")
    except discord.Forbidden:
        await interaction.response.send_message("I do not have permission to mute that user.", ephemeral=True)
        return
    except discord.HTTPException as exc:
        await interaction.response.send_message(f"Mute failed: {exc}", ephemeral=True)
        return

    await interaction.response.send_message(
        f"Muted {user.mention} until <t:{int(until.timestamp())}:F>. Reason: {reason_text}"
    )
    await send_log(
        interaction.guild,
        "Member Muted",
        (
            f"{actor.mention} muted {user.mention} (`{user.id}`) for `{duration}` "
            f"(until <t:{int(until.timestamp())}:F>). Reason: {reason_text}"
        ),
        discord.Color.orange(),
    )


@bot.tree.command(name="unmute", description="Remove timeout from a user.")
@app_commands.checks.has_permissions(moderate_members=True)
async def unmute(
    interaction: discord.Interaction,
    user: discord.Member,
    reason: Optional[str] = None,
) -> None:
    actor = interaction.user if isinstance(interaction.user, discord.Member) else None
    if actor is None:
        await interaction.response.send_message("Member data not available.", ephemeral=True)
        return
    allowed, message = can_target(actor, user, interaction.guild.me)
    if not allowed:
        await interaction.response.send_message(message, ephemeral=True)
        return

    reason_text = reason or "No reason provided."
    try:
        await user.timeout(None, reason=f"{reason_text} | by {actor} ({actor.id})")
    except discord.Forbidden:
        await interaction.response.send_message("I do not have permission to unmute that user.", ephemeral=True)
        return
    except discord.HTTPException as exc:
        await interaction.response.send_message(f"Unmute failed: {exc}", ephemeral=True)
        return

    await interaction.response.send_message(f"Unmuted {user.mention}. Reason: {reason_text}")
    await send_log(
        interaction.guild,
        "Member Unmuted",
        f"{actor.mention} unmuted {user.mention} (`{user.id}`). Reason: {reason_text}",
        discord.Color.green(),
    )


@bot.tree.command(name="unban", description="Unban a user by their user ID.")
@app_commands.checks.has_permissions(ban_members=True)
async def unban(
    interaction: discord.Interaction,
    user_id: str,
    reason: Optional[str] = None,
) -> None:
    if not user_id.isdigit():
        await interaction.response.send_message("User ID must be numeric.", ephemeral=True)
        return

    target_id = int(user_id)
    try:
        target_user = await bot.fetch_user(target_id)
    except discord.HTTPException:
        await interaction.response.send_message("Could not find that user.", ephemeral=True)
        return

    reason_text = reason or "No reason provided."
    try:
        await interaction.guild.unban(
            target_user,
            reason=f"{reason_text} | by {interaction.user} ({interaction.user.id})",
        )
    except discord.NotFound:
        await interaction.response.send_message("That user is not currently banned.", ephemeral=True)
        return
    except discord.Forbidden:
        await interaction.response.send_message("I do not have permission to unban users.", ephemeral=True)
        return
    except discord.HTTPException as exc:
        await interaction.response.send_message(f"Unban failed: {exc}", ephemeral=True)
        return

    await interaction.response.send_message(f"Unbanned **{target_user}**. Reason: {reason_text}")
    await send_log(
        interaction.guild,
        "Member Unbanned",
        f"{interaction.user.mention} unbanned **{target_user}** (`{target_user.id}`). Reason: {reason_text}",
        discord.Color.green(),
    )


@bot.tree.command(name="purge", description="Bulk delete messages.")
@app_commands.checks.has_permissions(manage_messages=True)
async def purge(
    interaction: discord.Interaction,
    amount: app_commands.Range[int, 1, 200],
    user: Optional[discord.Member] = None,
) -> None:
    channel = interaction.channel
    if not isinstance(channel, (discord.TextChannel, discord.Thread)):
        await interaction.response.send_message("This command only works in text channels.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True, thinking=True)

    def check(message: discord.Message) -> bool:
        return user is None or message.author.id == user.id

    try:
        deleted = await channel.purge(
            limit=amount,
            check=check,
            reason=f"Purge by {interaction.user} ({interaction.user.id})",
        )
    except discord.Forbidden:
        await interaction.followup.send("I do not have permission to delete messages.", ephemeral=True)
        return
    except discord.HTTPException as exc:
        await interaction.followup.send(f"Purge failed: {exc}", ephemeral=True)
        return

    target_note = f" for {user.mention}" if user else ""
    await interaction.followup.send(f"Deleted {len(deleted)} message(s){target_note}.", ephemeral=True)
    await send_log(
        interaction.guild,
        "Messages Purged",
        (
            f"{interaction.user.mention} purged {len(deleted)} message(s){target_note} "
            f"in {channel.mention}."
        ),
        discord.Color.orange(),
    )


@bot.tree.command(name="say", description="Make the bot send a message.")
@app_commands.checks.has_permissions(manage_messages=True)
async def say(
    interaction: discord.Interaction,
    message: str,
    channel: Optional[discord.TextChannel] = None,
) -> None:
    target = channel if channel else interaction.channel
    if not isinstance(target, (discord.TextChannel, discord.Thread)):
        await interaction.response.send_message("Target must be a text channel.", ephemeral=True)
        return

    try:
        await target.send(message)
    except discord.Forbidden:
        await interaction.response.send_message("I cannot send messages there.", ephemeral=True)
        return
    except discord.HTTPException as exc:
        await interaction.response.send_message(f"Send failed: {exc}", ephemeral=True)
        return

    await interaction.response.send_message("Message sent.", ephemeral=True)
    await send_log(
        interaction.guild,
        "Say Command",
        f"{interaction.user.mention} used /say in {target.mention}.",
        discord.Color.blurple(),
    )


@bot.tree.command(name="embed", description="Send a custom embed.")
@app_commands.checks.has_permissions(manage_messages=True)
@app_commands.describe(color="Optional hex color, example: #3498db")
async def embed(
    interaction: discord.Interaction,
    title: str,
    description: str,
    color: Optional[str] = None,
    channel: Optional[discord.TextChannel] = None,
) -> None:
    embed_color = parse_hex_color(color) if color else discord.Color.blurple()
    if color and embed_color is None:
        await interaction.response.send_message(
            "Invalid color format. Use a hex value like `#3498db`.",
            ephemeral=True,
        )
        return

    target = channel if channel else interaction.channel
    if not isinstance(target, (discord.TextChannel, discord.Thread)):
        await interaction.response.send_message("Target must be a text channel.", ephemeral=True)
        return

    payload = discord.Embed(
        title=title,
        description=description,
        color=embed_color,
        timestamp=discord.utils.utcnow(),
    )
    payload.set_footer(text=f"Posted by {interaction.user}")

    try:
        await target.send(embed=payload)
    except discord.Forbidden:
        await interaction.response.send_message("I cannot send embeds there.", ephemeral=True)
        return
    except discord.HTTPException as exc:
        await interaction.response.send_message(f"Embed send failed: {exc}", ephemeral=True)
        return

    await interaction.response.send_message("Embed sent.", ephemeral=True)
    await send_log(
        interaction.guild,
        "Embed Command",
        f"{interaction.user.mention} used /embed in {target.mention}.",
        discord.Color.blurple(),
    )


@bot.tree.command(name="serverconfig", description="Show current PsySource configuration.")
@app_commands.checks.has_permissions(manage_guild=True)
async def serverconfig(interaction: discord.Interaction) -> None:
    cfg = store.guild(interaction.guild_id)
    embed = discord.Embed(
        title="PsySource Server Config",
        color=discord.Color.blurple(),
        timestamp=discord.utils.utcnow(),
    )
    embed.add_field(name="Log Channel", value=mention_channel(cfg.get("log_channel_id")), inline=False)
    embed.add_field(name="Welcome Channel", value=mention_channel(cfg.get("welcome_channel_id")), inline=False)
    embed.add_field(name="Goodbye Channel", value=mention_channel(cfg.get("goodbye_channel_id")), inline=False)
    embed.add_field(
        name="Ticket Category",
        value=mention_channel(cfg.get("ticket_category_id")),
        inline=False,
    )
    embed.add_field(
        name="Ticket Staff Role",
        value=mention_role(cfg.get("ticket_staff_role_id")),
        inline=False,
    )
    embed.add_field(name="Prefix", value=f"`{PREFIX}`", inline=False)
    embed.set_footer(text="Use /modhelp to view commands.")
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.command(name="say")
@commands.has_permissions(manage_messages=True)
async def prefix_say(ctx: commands.Context, *, message: str) -> None:
    try:
        await ctx.message.delete()
    except discord.HTTPException:
        pass
    await ctx.send(message)
    await send_log(
        ctx.guild,
        "Prefix Say",
        f"{ctx.author.mention} used {PREFIX}say in {ctx.channel.mention}.",
        discord.Color.blurple(),
    )


@bot.command(name="embed")
@commands.has_permissions(manage_messages=True)
async def prefix_embed(ctx: commands.Context, *, payload: str) -> None:
    parts = [part.strip() for part in payload.split("|")]
    if len(parts) < 2:
        await ctx.send(f"Usage: `{PREFIX}embed <title> | <description> | [#hexcolor]`")
        return

    title = parts[0]
    description = parts[1]
    color_raw = parts[2] if len(parts) >= 3 else None
    embed_color = parse_hex_color(color_raw) if color_raw else discord.Color.blurple()
    if color_raw and embed_color is None:
        await ctx.send("Invalid color format. Use hex like `#3498db`.")
        return

    payload_embed = discord.Embed(
        title=title,
        description=description,
        color=embed_color,
        timestamp=discord.utils.utcnow(),
    )
    payload_embed.set_footer(text=f"Posted by {ctx.author}")

    try:
        await ctx.message.delete()
    except discord.HTTPException:
        pass
    await ctx.send(embed=payload_embed)
    await send_log(
        ctx.guild,
        "Prefix Embed",
        f"{ctx.author.mention} used {PREFIX}embed in {ctx.channel.mention}.",
        discord.Color.blurple(),
    )


@bot.event
async def on_app_command_completion(
    interaction: discord.Interaction,
    command: app_commands.Command,
) -> None:
    if interaction.guild is None or not is_allowed_guild(interaction.guild):
        return
    channel = interaction.channel
    location = channel.mention if isinstance(channel, (discord.TextChannel, discord.Thread)) else "unknown"
    await send_log(
        interaction.guild,
        "Slash Command Used",
        f"{interaction.user.mention} ran `/{command.qualified_name}` in {location}.",
        discord.Color.dark_gray(),
    )


@bot.event
async def on_command_completion(ctx: commands.Context) -> None:
    if ctx.guild is None or not is_allowed_guild(ctx.guild) or ctx.command is None:
        return
    await send_log(
        ctx.guild,
        "Prefix Command Used",
        f"{ctx.author.mention} ran `{PREFIX}{ctx.command.qualified_name}` in {ctx.channel.mention}.",
        discord.Color.dark_gray(),
    )


@bot.event
async def on_member_join(member: discord.Member) -> None:
    if not is_allowed_guild(member.guild):
        return
    cfg = store.guild(member.guild.id)
    channel = await resolve_text_channel(member.guild, cfg.get("welcome_channel_id"))
    if channel is not None:
        message = format_member_message(cfg.get("welcome_message", ""), member)
        try:
            await channel.send(message)
        except discord.HTTPException:
            pass
    await send_log(
        member.guild,
        "Member Joined",
        f"{member.mention} joined the server (`{member.id}`).",
        discord.Color.green(),
    )


@bot.event
async def on_member_remove(member: discord.Member) -> None:
    if not is_allowed_guild(member.guild):
        return
    cfg = store.guild(member.guild.id)
    channel = await resolve_text_channel(member.guild, cfg.get("goodbye_channel_id"))
    if channel is not None:
        message = format_member_message(cfg.get("goodbye_message", ""), member)
        try:
            await channel.send(message)
        except discord.HTTPException:
            pass
    await send_log(
        member.guild,
        "Member Left",
        f"{member} (`{member.id}`) left the server.",
        discord.Color.orange(),
    )


@bot.event
async def on_member_ban(guild: discord.Guild, user: discord.User) -> None:
    if not is_allowed_guild(guild):
        return
    await send_log(
        guild,
        "Member Banned",
        f"{user} (`{user.id}`) was banned.",
        discord.Color.red(),
    )


@bot.event
async def on_member_unban(guild: discord.Guild, user: discord.User) -> None:
    if not is_allowed_guild(guild):
        return
    await send_log(
        guild,
        "Member Unbanned",
        f"{user} (`{user.id}`) was unbanned.",
        discord.Color.green(),
    )


@bot.event
async def on_message_delete(message: discord.Message) -> None:
    if message.guild is None or not is_allowed_guild(message.guild):
        return
    if message.author and message.author.bot:
        return
    content = truncate(message.content or "[no text]", 900)
    attachment_urls = [att.url for att in message.attachments[:3]]
    attachments = "\n".join(attachment_urls)
    attachment_line = f"\nAttachments:\n{attachments}" if attachments else ""
    author = message.author.mention if message.author else "Unknown"
    await send_log(
        message.guild,
        "Message Deleted",
        (
            f"Author: {author}\n"
            f"Channel: {message.channel.mention}\n"
            f"Content: {content}{attachment_line}"
        ),
        discord.Color.red(),
    )


@bot.event
async def on_bulk_message_delete(messages: list[discord.Message]) -> None:
    if not messages:
        return
    guild = messages[0].guild
    if guild is None or not is_allowed_guild(guild):
        return
    channel = messages[0].channel
    location = channel.mention if isinstance(channel, (discord.TextChannel, discord.Thread)) else "unknown"
    await send_log(
        guild,
        "Bulk Delete",
        f"{len(messages)} messages were deleted in {location}.",
        discord.Color.red(),
    )


@bot.event
async def on_message_edit(before: discord.Message, after: discord.Message) -> None:
    if before.guild is None or not is_allowed_guild(before.guild):
        return
    if before.author.bot:
        return
    if before.content == after.content:
        return
    await send_log(
        before.guild,
        "Message Edited",
        (
            f"Author: {before.author.mention}\n"
            f"Channel: {before.channel.mention}\n"
            f"Before: {truncate(before.content or '[no text]', 700)}\n"
            f"After: {truncate(after.content or '[no text]', 700)}"
        ),
        discord.Color.orange(),
    )


@bot.event
async def on_member_update(before: discord.Member, after: discord.Member) -> None:
    guild = after.guild
    if not is_allowed_guild(guild):
        return

    if before.nick != after.nick:
        await send_log(
            guild,
            "Nickname Changed",
            (
                f"{after.mention} changed nickname.\n"
                f"Before: {before.nick or before.name}\n"
                f"After: {after.nick or after.name}"
            ),
            discord.Color.blurple(),
        )

    if before.timed_out_until != after.timed_out_until:
        if after.timed_out_until:
            until = int(after.timed_out_until.timestamp())
            text = f"{after.mention} is timed out until <t:{until}:F>."
        else:
            text = f"{after.mention} timeout was removed."
        await send_log(guild, "Timeout Updated", text, discord.Color.orange())

    before_roles = {role.id for role in before.roles if role != guild.default_role}
    after_roles = {role.id for role in after.roles if role != guild.default_role}
    added = list(after_roles - before_roles)
    removed = list(before_roles - after_roles)
    if added or removed:
        added_text = ", ".join(f"<@&{role_id}>" for role_id in added[:10]) if added else "None"
        removed_text = ", ".join(f"<@&{role_id}>" for role_id in removed[:10]) if removed else "None"
        await send_log(
            guild,
            "Roles Updated",
            f"User: {after.mention}\nAdded: {added_text}\nRemoved: {removed_text}",
            discord.Color.blurple(),
        )


@bot.event
async def on_guild_channel_create(channel: discord.abc.GuildChannel) -> None:
    if not is_allowed_guild(channel.guild):
        return
    await send_log(
        channel.guild,
        "Channel Created",
        f"`#{channel.name}` (`{channel.id}`) was created.",
        discord.Color.green(),
    )


@bot.event
async def on_guild_channel_delete(channel: discord.abc.GuildChannel) -> None:
    if not is_allowed_guild(channel.guild):
        return
    await send_log(
        channel.guild,
        "Channel Deleted",
        f"`#{channel.name}` (`{channel.id}`) was deleted.",
        discord.Color.red(),
    )


@bot.tree.error
async def on_tree_error(interaction: discord.Interaction, error: app_commands.AppCommandError) -> None:
    if isinstance(error, app_commands.MissingPermissions):
        message = "You do not have permission to use this command."
    elif isinstance(error, app_commands.CheckFailure):
        message = str(error) or "You cannot use this command here."
    else:
        message = "Command failed. Check my permissions and try again."
        print(f"App command error: {error}")
    await reply(interaction, message, ephemeral=True)


@bot.event
async def on_command_error(ctx: commands.Context, error: commands.CommandError) -> None:
    if isinstance(error, commands.CommandNotFound):
        return
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("You do not have permission to use that command.")
        return
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"Missing argument: `{error.param.name}`.")
        return
    if isinstance(error, commands.CheckFailure):
        return
    await ctx.send("Command failed. Check my permissions and arguments.")
    print(f"Prefix command error: {error}")


if __name__ == "__main__":
    bot.run(TOKEN)
