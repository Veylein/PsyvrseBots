import discord
from discord.ext import commands
from discord import app_commands
import json
import os

_STARBOARD_DATA_DIR = os.getenv("RENDER_DISK_PATH", "data")
if not os.access(_STARBOARD_DATA_DIR, os.W_OK):
    _STARBOARD_DATA_DIR = os.path.join(os.getcwd(), "data")
os.makedirs(_STARBOARD_DATA_DIR, exist_ok=True)
STARBOARD_FILE = os.path.join(_STARBOARD_DATA_DIR, "starboard.json")


def load_starboards():
    if not os.path.exists(STARBOARD_FILE):
        with open(STARBOARD_FILE, "w") as f:
            json.dump({"boards": {}, "posted_messages": {}}, f, indent=4)
    with open(STARBOARD_FILE) as f:
        data = json.load(f)
    data.setdefault("boards", {})
    data.setdefault("posted_messages", {})
    return data


def save_starboards(data):
    tmp = STARBOARD_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=4)
    os.replace(tmp, STARBOARD_FILE)


# ─── Visual helpers ───────────────────────────────────────────────────────────

def _star_color(count: int, needed: int) -> discord.Color:
    """Color scales from gold → orange → red based on how 'hot' the post is."""
    ratio = count / max(needed, 1)
    if ratio < 1.5:
        return discord.Color.from_rgb(255, 204, 0)   # gold
    elif ratio < 2.5:
        return discord.Color.from_rgb(255, 140, 0)   # orange
    else:
        return discord.Color.from_rgb(255, 60, 0)    # red-orange


def _star_icon(count: int, needed: int) -> str:
    """Emoji that scales with popularity."""
    ratio = count / max(needed, 1)
    if ratio >= 3:
        return "🌟"
    elif ratio >= 2:
        return "⭐"
    else:
        return "✨"


# ─── Slash command group ──────────────────────────────────────────────────────

class StarboardGroup(app_commands.Group):
    def __init__(self, cog: "Starboard"):
        super().__init__(name="starboard", description="Manage server starboards")
        self.cog = cog

    # /starboard create
    @app_commands.command(name="create", description="Create a new starboard channel")
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(
        emoji="Reaction emoji to track (e.g. ⭐)",
        channel="Channel where starred messages will be posted",
        amount="Number of reactions required",
        allow_self_star="Allow users to star their own messages (default: off)"
    )
    async def create(
        self,
        interaction: discord.Interaction,
        emoji: str,
        channel: discord.TextChannel,
        amount: int,
        allow_self_star: bool = False
    ):
        await interaction.response.defer(ephemeral=True)
        guild_id = str(interaction.guild_id)
        boards = self.cog.data["boards"].setdefault(guild_id, {})

        if emoji in boards:
            return await interaction.followup.send(
                f"❌ A starboard for `{emoji}` already exists.", ephemeral=True
            )
        if len(boards) >= 5:
            return await interaction.followup.send(
                "❌ Maximum **5** starboards per server.", ephemeral=True
            )
        if amount < 1:
            return await interaction.followup.send(
                "❌ Amount must be at least **1**.", ephemeral=True
            )

        boards[emoji] = {
            "channel": channel.id,
            "amount": amount,
            "self_star": allow_self_star
        }
        save_starboards(self.cog.data)

        embed = discord.Embed(
            title="✅ Starboard Created",
            color=discord.Color.green(),
            description=(
                f"**Emoji:** {emoji}\n"
                f"**Channel:** {channel.mention}\n"
                f"**Threshold:** {amount} reactions\n"
                f"**Self-star:** {'✅ allowed' if allow_self_star else '❌ blocked'}"
            )
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

    # /starboard edit
    @app_commands.command(name="edit", description="Edit a starboard's settings")
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(
        emoji="Emoji of the starboard to edit",
        amount="New reaction threshold",
        channel="New output channel",
        allow_self_star="Toggle self-starring"
    )
    async def edit(
        self,
        interaction: discord.Interaction,
        emoji: str,
        amount: int = None,
        channel: discord.TextChannel = None,
        allow_self_star: bool = None
    ):
        await interaction.response.defer(ephemeral=True)
        guild_id = str(interaction.guild_id)
        boards = self.cog.data["boards"].get(guild_id, {})

        if emoji not in boards:
            return await interaction.followup.send(
                f"❌ No starboard found for `{emoji}`.", ephemeral=True
            )

        board = boards[emoji]
        if amount is not None:
            board["amount"] = amount
        if channel is not None:
            board["channel"] = channel.id
        if allow_self_star is not None:
            board["self_star"] = allow_self_star

        save_starboards(self.cog.data)
        ch = interaction.guild.get_channel(board["channel"])
        embed = discord.Embed(
            title="✏️ Starboard Updated",
            color=discord.Color.blurple(),
            description=(
                f"**Emoji:** {emoji}\n"
                f"**Channel:** {ch.mention if ch else '`(deleted)`'}\n"
                f"**Threshold:** {board['amount']} reactions\n"
                f"**Self-star:** {'✅ allowed' if board.get('self_star') else '❌ blocked'}"
            )
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

    # /starboard remove
    @app_commands.command(name="remove", description="Delete a starboard")
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(emoji="Emoji of the starboard to remove")
    async def remove(self, interaction: discord.Interaction, emoji: str):
        await interaction.response.defer(ephemeral=True)
        guild_id = str(interaction.guild_id)
        boards = self.cog.data["boards"].get(guild_id, {})

        if emoji not in boards:
            return await interaction.followup.send(
                f"❌ No starboard found for `{emoji}`.", ephemeral=True
            )

        del boards[emoji]
        save_starboards(self.cog.data)
        await interaction.followup.send(
            f"🗑️ Removed the `{emoji}` starboard.", ephemeral=True
        )

    # /starboard list
    @app_commands.command(name="list", description="Show all active starboards on this server")
    async def list_boards(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild_id = str(interaction.guild_id)
        boards = self.cog.data["boards"].get(guild_id, {})

        if not boards:
            return await interaction.followup.send(
                "No starboards configured on this server.", ephemeral=True
            )

        embed = discord.Embed(title="⭐ Active Starboards", color=discord.Color.gold())
        for emo, cfg in boards.items():
            ch = interaction.guild.get_channel(cfg["channel"])
            embed.add_field(
                name=emo,
                value=(
                    f"Channel: {ch.mention if ch else '`(deleted)`'}\n"
                    f"Threshold: **{cfg['amount']}** reactions\n"
                    f"Self-star: {'✅' if cfg.get('self_star') else '❌'}"
                ),
                inline=True
            )
        await interaction.followup.send(embed=embed, ephemeral=True)


# ─── Cog ─────────────────────────────────────────────────────────────────────

class Starboard(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.data = load_starboards()
        self._group = StarboardGroup(self)
        bot.tree.add_command(self._group)

    def cog_unload(self):
        self.bot.tree.remove_command(self._group.name)

    # ── Prefix commands (backwards compat) ───────────────────────────────────

    @commands.group(name="starboard", invoke_without_command=True)
    async def sb_prefix(self, ctx: commands.Context):
        await ctx.send(
            "Subcommands: `create <emoji> <#channel> <amount>` · "
            "`edit <emoji> <amount>` · `remove <emoji>` · `list`"
        )

    @sb_prefix.command(name="create")
    @commands.has_permissions(manage_guild=True)
    async def sb_create(self, ctx, emoji: str, channel: discord.TextChannel, amount: int):
        guild_id = str(ctx.guild.id)
        boards = self.data["boards"].setdefault(guild_id, {})
        if emoji in boards:
            return await ctx.send(f"❌ Starboard for `{emoji}` already exists.")
        if len(boards) >= 5:
            return await ctx.send("❌ Max 5 starboards per server.")
        boards[emoji] = {"channel": channel.id, "amount": amount, "self_star": False}
        save_starboards(self.data)
        await ctx.send(f"⭐ Created `{emoji}` starboard in {channel.mention} (needs **{amount}** reactions).")

    @sb_prefix.command(name="edit")
    @commands.has_permissions(manage_guild=True)
    async def sb_edit(self, ctx, emoji: str, amount: int):
        guild_id = str(ctx.guild.id)
        boards = self.data["boards"].get(guild_id, {})
        if emoji not in boards:
            return await ctx.send(f"❌ No starboard for `{emoji}`.")
        boards[emoji]["amount"] = amount
        save_starboards(self.data)
        await ctx.send(f"✏️ `{emoji}` starboard updated → **{amount}** reactions.")

    @sb_prefix.command(name="remove")
    @commands.has_permissions(manage_guild=True)
    async def sb_remove(self, ctx, emoji: str):
        guild_id = str(ctx.guild.id)
        boards = self.data["boards"].get(guild_id, {})
        if emoji not in boards:
            return await ctx.send(f"❌ No starboard for `{emoji}`.")
        del boards[emoji]
        save_starboards(self.data)
        await ctx.send(f"🗑️ Removed `{emoji}` starboard.")

    @sb_prefix.command(name="list")
    async def sb_list(self, ctx):
        guild_id = str(ctx.guild.id)
        boards = self.data["boards"].get(guild_id, {})
        if not boards:
            return await ctx.send("No starboards configured.")
        lines = [
            f"{emo} → {ctx.guild.get_channel(cfg['channel']).mention if ctx.guild.get_channel(cfg['channel']) else '`deleted`'}"
            f" · **{cfg['amount']}** reactions · self-star {'✅' if cfg.get('self_star') else '❌'}"
            for emo, cfg in boards.items()
        ]
        await ctx.send("**⭐ Starboards:**\n" + "\n".join(lines))

    # ── Embed builder ─────────────────────────────────────────────────────────

    def _build_embed(
        self,
        message: discord.Message,
        emoji: str,
        count: int,
        needed: int
    ) -> discord.Embed:
        embed = discord.Embed(
            color=_star_color(count, needed),
            timestamp=message.created_at
        )
        embed.set_author(
            name=message.author.display_name,
            icon_url=message.author.display_avatar.url
        )

        # Message content
        if message.content:
            embed.description = message.content

        # Attachments — first image in big slot, rest as link fields
        image_set = False
        for att in message.attachments:
            if not image_set and att.content_type and att.content_type.startswith("image/"):
                embed.set_image(url=att.url)
                image_set = True
            else:
                embed.add_field(
                    name="📎 Attachment",
                    value=f"[{att.filename}]({att.url})",
                    inline=False
                )

        # Embed previews (link unfurls)
        if not image_set and message.embeds:
            orig = message.embeds[0]
            if orig.image and orig.image.url:
                embed.set_image(url=orig.image.url)
                image_set = True
            elif orig.thumbnail and orig.thumbnail.url:
                embed.set_image(url=orig.thumbnail.url)
                image_set = True
            if not message.content and orig.description:
                embed.description = orig.description

        # Reply context
        ref = message.reference
        if ref and ref.resolved and isinstance(ref.resolved, discord.Message):
            preview = (ref.resolved.content or "*no text*")[:100]
            if len(ref.resolved.content or "") > 100:
                preview += "…"
            embed.add_field(
                name=f"↩️ Replying to {ref.resolved.author.display_name}",
                value=preview,
                inline=False
            )

        # Navigation row
        embed.add_field(name="", value=f"[Jump to message]({message.jump_url})", inline=True)
        embed.add_field(name="", value=message.channel.mention, inline=True)
        embed.set_footer(text=f"{_star_icon(count, needed)} {count}  ·  #{message.channel.name}")

        return embed

    # ── Reaction events (raw = works on uncached/old messages) ───────────────

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        await self._process_reaction(payload)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        await self._process_reaction(payload)

    async def _process_reaction(self, payload: discord.RawReactionActionEvent):
        if not payload.guild_id:
            return

        guild_id = str(payload.guild_id)
        boards = self.data["boards"].get(guild_id, {})
        emoji = str(payload.emoji)

        if emoji not in boards:
            return

        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return

        board = boards[emoji]
        needed = board["amount"]
        sb_channel = guild.get_channel(board["channel"])
        if not sb_channel:
            return

        src_channel = guild.get_channel(payload.channel_id)
        if not src_channel:
            return

        try:
            message = await src_channel.fetch_message(payload.message_id)
        except (discord.NotFound, discord.Forbidden):
            return

        # Ignore bots and messages inside the starboard channel itself
        if message.author.bot or src_channel.id == sb_channel.id:
            return

        # Self-star guard (only block on ADD)
        if (
            not board.get("self_star", False)
            and getattr(payload, "event_type", None) == "REACTION_ADD"
            and payload.user_id == message.author.id
        ):
            return

        # Count current reactions
        count = 0
        for r in message.reactions:
            if str(r.emoji) == emoji:
                count = r.count
                break

        message_key = f"{guild_id}_{message.id}_{emoji}"
        star_icon = _star_icon(count, needed)
        header = f"{star_icon} **{count}** — {src_channel.mention}"

        # Below threshold → remove existing post if any
        if count < needed:
            stored = self.data["posted_messages"].get(message_key)
            if stored:
                try:
                    old = await sb_channel.fetch_message(stored)
                    await old.delete()
                except Exception:
                    pass
                del self.data["posted_messages"][message_key]
                save_starboards(self.data)
            return

        embed = self._build_embed(message, emoji, count, needed)

        # Update existing post
        stored = self.data["posted_messages"].get(message_key)
        if stored:
            try:
                sb_msg = await sb_channel.fetch_message(stored)
                await sb_msg.edit(content=header, embed=embed)
                save_starboards(self.data)
                return
            except discord.NotFound:
                del self.data["posted_messages"][message_key]
            except Exception as e:
                print(f"[Starboard] Failed to update: {e}")
                return

        # Create new post
        try:
            sb_msg = await sb_channel.send(content=header, embed=embed)
            self.data["posted_messages"][message_key] = sb_msg.id
            save_starboards(self.data)
        except Exception as e:
            print(f"[Starboard] Error posting: {e}")


async def setup(bot):
    await bot.add_cog(Starboard(bot))
