import discord
from discord.ext import commands
from discord import app_commands
import json
import os


DATA_PATH = os.getenv("RENDER_DISK_PATH", "data")

BADGE_MAP = {
    "staff":                  ("\U0001f6e0\ufe0f", "Discord Staff"),
    "partner":                ("\U0001f91d", "Partnered"),
    "hypesquad":              ("\U0001f3e0", "HypeSquad Events"),
    "bug_hunter":             ("\U0001f41b", "Bug Hunter"),
    "hypesquad_bravery":      ("\U0001f525", "HypeSquad Bravery"),
    "hypesquad_brilliance":   ("\U0001f4a1", "HypeSquad Brilliance"),
    "hypesquad_balance":      ("\u2696\ufe0f", "HypeSquad Balance"),
    "early_supporter":        ("\U0001f474", "Early Supporter"),
    "bug_hunter_level_2":     ("\U0001f41e", "Bug Hunter Lv.2"),
    "verified_bot_developer": ("\U0001f916", "Verified Bot Dev"),
    "active_developer":       ("\U0001f527", "Active Developer"),
}

VERIFICATION_LABELS = {
    discord.VerificationLevel.none:    "None",
    discord.VerificationLevel.low:     "Low (email)",
    discord.VerificationLevel.medium:  "Medium (5 min)",
    discord.VerificationLevel.high:    "High (10 min)",
    discord.VerificationLevel.highest: "Highest (phone)",
}

STATUS_ICONS = {
    discord.Status.online:    "\U0001f7e2",
    discord.Status.idle:      "\U0001f7e1",
    discord.Status.dnd:       "\U0001f534",
    discord.Status.offline:   "\u26ab",
    discord.Status.invisible: "\u26ab",
}


def _load_json(path: str) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _build_serverinfo_embed(guild: discord.Guild) -> discord.Embed:
    total  = guild.member_count or len(guild.members)
    bots   = sum(1 for m in guild.members if m.bot)
    humans = total - bots
    online = sum(1 for m in guild.members if m.status != discord.Status.offline)

    text   = len(guild.text_channels)
    voice  = len(guild.voice_channels)
    cats   = len(guild.categories)
    stage  = len(guild.stage_channels)

    boost_icons = {0: "\U0001f4ca", 1: "\U0001f949", 2: "\U0001f948", 3: "\U0001f947"}
    tier = guild.premium_tier

    embed = discord.Embed(
        title=f"\U0001f4ca {guild.name}",
        color=discord.Color.blurple(),
        timestamp=discord.utils.utcnow(),
    )
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    if guild.banner:
        embed.set_image(url=guild.banner.url)

    embed.add_field(name="\U0001f194 ID",     value=f"`{guild.id}`",                                    inline=True)
    embed.add_field(name="\U0001f451 Owner",  value=guild.owner.mention if guild.owner else "Unknown",  inline=True)
    embed.add_field(
        name="\U0001f4c5 Created",
        value=f"<t:{int(guild.created_at.timestamp())}:D> (<t:{int(guild.created_at.timestamp())}:R>)",
        inline=False,
    )

    if guild.vanity_url_code:
        embed.add_field(name="\U0001f517 Vanity URL", value=f"discord.gg/{guild.vanity_url_code}", inline=True)

    embed.add_field(
        name="\U0001f465 Members",
        value=(
            f"\U0001f464 Humans: **{humans:,}**\n"
            f"\U0001f916 Bots: **{bots:,}**\n"
            f"\U0001f7e2 Online: **{online:,}**\n"
            f"\U0001f4ca Total: **{total:,}**"
        ),
        inline=True,
    )
    embed.add_field(
        name="\U0001f4fa Channels",
        value=(
            f"\U0001f4ac Text: **{text}**\n"
            f"\U0001f50a Voice: **{voice}**\n"
            f"\U0001f3a4 Stage: **{stage}**\n"
            f"\U0001f4c1 Categories: **{cats}**"
        ),
        inline=True,
    )
    embed.add_field(
        name="\U0001f3a8 Other",
        value=(
            f"\U0001f3ad Roles: **{len(guild.roles)}**\n"
            f"\U0001f600 Emojis: **{len(guild.emojis)}/{guild.emoji_limit}**\n"
            f"\U0001f4be Upload: **{guild.filesize_limit // 1048576} MB**"
        ),
        inline=True,
    )
    embed.add_field(
        name="\U0001f48e Boosts",
        value=(
            f"{boost_icons.get(tier, chr(0x1F4CA))} Level: **{tier}**\n"
            f"\U0001f680 Boosts: **{guild.premium_subscription_count}**\n"
            f"\u2728 Boosters: **{len(guild.premium_subscribers)}**"
        ),
        inline=True,
    )
    embed.add_field(
        name="\U0001f6e1\ufe0f Security",
        value=(
            f"\U0001f512 Verification: **{VERIFICATION_LABELS.get(guild.verification_level, 'Unknown')}**\n"
            f"\U0001f6e1\ufe0f 2FA Moderation: **{'Yes' if guild.mfa_level else 'No'}**\n"
            f"\U0001f51e NSFW Level: **{guild.nsfw_level.name.title()}**"
        ),
        inline=True,
    )

    if guild.features:
        feat_emojis = {
            "VERIFIED": "\u2705", "PARTNERED": "\U0001f91d", "COMMUNITY": "\U0001f3d8\ufe0f",
            "DISCOVERABLE": "\U0001f50d", "WELCOME_SCREEN_ENABLED": "\U0001f44b",
            "ANIMATED_ICON": "\U0001f3ac", "BANNER": "\U0001f3a8", "VANITY_URL": "\U0001f517",
            "INVITE_SPLASH": "\U0001f4a7", "MEMBER_VERIFICATION_GATE_ENABLED": "\U0001f6aa",
        }
        lines = [f"{feat_emojis.get(f, chr(0x2022))} {f.replace('_', ' ').title()}" for f in guild.features[:8]]
        if len(guild.features) > 8:
            lines.append(f"\u2026 and {len(guild.features) - 8} more")
        embed.add_field(name="\u2b50 Features", value="\n".join(lines), inline=False)

    return embed


def _build_userinfo_embed(member: discord.Member) -> discord.Embed:
    color = member.color if member.color != discord.Color.default() else discord.Color.blurple()

    embed = discord.Embed(
        title=f"\U0001f464 {member.display_name}",
        color=color,
        timestamp=discord.utils.utcnow(),
    )
    embed.set_thumbnail(url=member.display_avatar.url)

    embed.add_field(name="\U0001faaa Username", value=str(member),      inline=True)
    embed.add_field(name="\U0001f194 User ID",  value=f"`{member.id}`", inline=True)
    embed.add_field(name="\U0001f916 Bot",       value="Yes" if member.bot else "No", inline=True)

    embed.add_field(
        name="\U0001f4c5 Account Created",
        value=f"<t:{int(member.created_at.timestamp())}:D>\n(<t:{int(member.created_at.timestamp())}:R>)",
        inline=True,
    )
    if member.joined_at:
        embed.add_field(
            name="\U0001f4e5 Joined Server",
            value=f"<t:{int(member.joined_at.timestamp())}:D>\n(<t:{int(member.joined_at.timestamp())}:R>)",
            inline=True,
        )

    status_icon = STATUS_ICONS.get(member.status, "\u26ab")
    activity_str = "\u200b"
    if member.activity:
        act = member.activity
        if isinstance(act, discord.Spotify):
            activity_str = f"\U0001f3b5 {act.title} \u2014 {act.artist}"
        elif isinstance(act, discord.Game):
            activity_str = f"\U0001f3ae {act.name}"
        elif isinstance(act, discord.Streaming):
            activity_str = f"\U0001f4fa {act.name}"
        elif isinstance(act, discord.CustomActivity) and act.name:
            activity_str = act.name
        else:
            activity_str = getattr(act, "name", "\u200b") or "\u200b"

    embed.add_field(
        name="\U0001f4a1 Status",
        value=f"{status_icon} {member.status.name.title()}\n{activity_str}",
        inline=True,
    )

    flags  = member.public_flags
    badges = [f"{e} {lbl}" for key, (e, lbl) in BADGE_MAP.items() if getattr(flags, key, False)]
    if member.premium_since:
        badges.insert(0, f"\U0001f48e Server Booster (since <t:{int(member.premium_since.timestamp())}:D>)")
    if badges:
        embed.add_field(name="\U0001f3c5 Badges", value="\n".join(badges), inline=False)

    roles = [r for r in sorted(member.roles, key=lambda r: r.position, reverse=True) if r.name != "@everyone"]
    if roles:
        cap      = 20
        role_str = " ".join(r.mention for r in roles[:cap])
        if len(roles) > cap:
            role_str += f" \u2026 +{len(roles) - cap} more"
        embed.add_field(name=f"\U0001f3ad Roles [{len(roles)}]", value=role_str, inline=False)

    eco_path  = os.path.join(DATA_PATH, "economy.json")
    prof_path = os.path.join(DATA_PATH, "profiles.json")
    uid_str   = str(member.id)
    eco       = _load_json(eco_path).get(uid_str)
    prof      = _load_json(prof_path).get(uid_str)

    if eco or prof:
        lines = []
        if eco:
            lines.append(f"\U0001f4b0 Balance: **{eco.get('balance', 0):,}** PsyCoins")
            lines.append(f"\U0001f525 Daily Streak: **{eco.get('daily_streak', 0)}**")
            lines.append(f"\U0001f4c8 Total Earned: **{eco.get('total_earned', 0):,}**")
            if eco.get("fish_coins"):
                lines.append(f"\U0001f41f FishCoins: **{eco['fish_coins']:,}**")
            if eco.get("mine_coins"):
                lines.append(f"\u26cf\ufe0f MineCoins: **{eco['mine_coins']:,}**")
            if eco.get("farm_coins"):
                lines.append(f"\U0001f33e FarmCoins: **{eco['farm_coins']:,}**")
        if prof:
            lines.append(f"\u2b50 Level: **{prof.get('level', 1)}** (XP: {prof.get('xp', 0)})")
            lines.append(f"\U0001f3ae Games Won/Played: **{prof.get('minigames_won', 0)}/{prof.get('minigames_played', 0)}**")
        embed.add_field(name="\U0001f3ae Ludus Stats", value="\n".join(lines), inline=False)

    embed.set_footer(text=f"ID: {member.id}")
    return embed


class ServerInfo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="serverinfo", aliases=["server", "si"])
    @commands.guild_only()
    async def server_info_prefix(self, ctx):
        """\U0001f4ca Display comprehensive server statistics."""
        await ctx.send(embed=_build_serverinfo_embed(ctx.guild))

    @app_commands.command(name="serverinfo", description="Show detailed information about this server")
    @app_commands.guild_only()
    async def server_info_slash(self, interaction: discord.Interaction):
        await interaction.response.send_message(embed=_build_serverinfo_embed(interaction.guild))

    @commands.command(name="userinfo", aliases=["ui", "whois", "memberinfo"])
    @commands.guild_only()
    async def user_info_prefix(self, ctx, *, member: discord.Member = None):
        """\U0001f464 Show detailed info about a server member (defaults to yourself)."""
        target = member or ctx.author
        await ctx.send(embed=_build_userinfo_embed(target))

    @app_commands.command(name="userinfo", description="Show detailed information about a server member")
    @app_commands.guild_only()
    @app_commands.describe(member="The member to look up (defaults to yourself)")
    async def user_info_slash(self, interaction: discord.Interaction, member: discord.Member = None):
        target = member or interaction.guild.get_member(interaction.user.id)
        await interaction.response.send_message(embed=_build_userinfo_embed(target))


async def setup(bot):
    await bot.add_cog(ServerInfo(bot))