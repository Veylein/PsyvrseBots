"""
cogs/leaderboard.py
-------------------
Leaderboard system for Ludus-Bot.

• /leaderboard  – Components V2 interactive dropdown (LayoutView, mining.py pattern)
• L!synclb      – Force re-sync stats from data files (owner only)
• L!lbconsent   – Toggle global visibility for this server (admin only)

Data sources (aggregated per guild on on_ready / synclb):
  economy.json        → balance, total_earned, total_spent
  fishing_data.json   → total_catches
  profiles.json       → xp, level, minigames_played, minigames_won,
                        commands_used, messages_sent, pets_owned
  gambling_stats.json → total_games, total_won
  game_stats.json     → total_games, games_won
  leaderboard_stats.json → counting_peak, gtn_wins, tod_uses
"""

import discord
from discord.ext import commands
from discord import app_commands
import json
import os
from typing import Dict, List, Tuple
import discord.ui


# ─── helpers ──────────────────────────────────────────────────────────────────

def _load_json(path: str) -> dict:
    """Safely load a JSON file; return {} on any error."""
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {}


def _save_json(path: str, data: dict):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=4)


MEDALS = ["🥇", "🥈", "🥉"]

def _medal(idx: int) -> str:
    return MEDALS[idx - 1] if idx <= 3 else f"**{idx}.**"


# ─── dropdown categories ───────────────────────────────────────────────────────

LB_CATEGORIES: List[Tuple[str, str, str]] = [
    # Server (local)
    ("🏆 Server – Coins",        "s_coins",      "Richest users on this server"),
    ("🎣 Server – Fishing",      "s_fishing",    "Most fish caught on this server"),
    ("⛏️ Server – Mining",       "s_mining",     "Most blocks mined on this server"),
    ("🌾 Server – Farming",      "s_farming",    "Most crops harvested on this server"),
    ("🎮 Server – Minigames",    "s_minigames",  "Most minigames played on this server"),
    ("🎲 Server – Gambling",     "s_gambling",   "Most gambling games played on this server"),
    ("⚔️ Server – Duels",        "s_duels",      "Most duels won on this server"),
    ("📜 Server – Quests",       "s_quests",     "Most quests completed on this server"),
    ("❤️ Server – Reputation",   "s_reputation", "Most reputation received on this server"),
    ("⭐ Server – Level / XP",   "s_xp",         "Highest XP on this server"),
    ("🔥 Server – Daily Streak", "s_streak",     "Longest daily reward streak on this server"),
    # Global (all servers, per-user)
    ("🌍 Global – Coins",        "g_coins",      "Richest users across all servers"),
    ("🌍 Global – Fishing",      "g_fishing",    "Most fish caught across all servers"),
    ("🌍 Global – Mining",       "g_mining",     "Most blocks mined across all servers"),
    ("🌍 Global – Farming",      "g_farming",    "Most crops harvested across all servers"),
    ("🌍 Global – Minigames",    "g_minigames",  "Most minigames played across all servers"),
    ("🌍 Global – Gambling",     "g_gambling",   "Most gambling games played across all servers"),
    ("🌍 Global – Duels",        "g_duels",      "Most duels won across all servers"),
    ("🌍 Global – Quests",       "g_quests",     "Most quests completed across all servers"),
    ("🌍 Global – Level / XP",   "g_xp",         "Highest XP across all servers"),
    ("🌍 Global – Reputation",    "g_reputation", "Highest reputation across all servers"),
]


# ─── LayoutView ───────────────────────────────────────────────────────────────

class LeaderboardView(discord.ui.LayoutView):
    def __init__(self, cog: "Leaderboard", guild: discord.Guild, text: str = None):
        super().__init__(timeout=120)
        self.cog = cog
        self.guild = guild
        self.show_global = cog._consented(guild.id) if guild else False
        self._build_ui(text if text is not None else self._home_text())

    def _home_text(self) -> str:
        parts = [
            "# 🏆 Leaderboard",
            "Pick a category from the dropdown below.",
            "**🏆 Server** (this server only):",
            "Coins · Fishing · Mining · Farming · Minigames",
            "Gambling · Duels · Quests · Reputation · Level/XP · Daily Streak",
        ]
        if self.show_global:
            parts += [
                "**🌍 Global** (top users across all servers):",
                "Coins · Fishing · Mining · Farming · Minigames",
                "Gambling · Duels · Quests · Level/XP",
            ]
        else:
            parts.append("-# Global leaderboards are hidden on this server.")
        parts.append("-# Menu expires after 2 minutes of inactivity.")
        return "\n".join(parts)

    def _build_ui(self, text: str):
        categories = [
            (label, value, desc) for label, value, desc in LB_CATEGORIES
            if self.show_global or not value.startswith("g_")
        ]
        options = [
            discord.SelectOption(label=label, value=value, description=desc)
            for label, value, desc in categories
        ]
        select = discord.ui.Select(
            placeholder="📋 Choose a leaderboard…",
            options=options,
            min_values=1,
            max_values=1,
        )
        select.callback = self._on_select

        home_btn = discord.ui.Button(label="🏠 Home", style=discord.ButtonStyle.secondary)
        home_btn.callback = self._on_home

        container = discord.ui.Container(
            discord.ui.TextDisplay(text),
            discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
            discord.ui.ActionRow(select),
            discord.ui.ActionRow(home_btn),
            accent_color=discord.Color.gold(),
        )
        self.add_item(container)

    async def _on_home(self, interaction: discord.Interaction):
        self.clear_items()
        self._build_ui(self._home_text())
        await interaction.response.edit_message(view=self)

    async def _on_select(self, interaction: discord.Interaction):
        value = interaction.data["values"][0]
        try:
            text = await self.cog.build_page(value, interaction.guild)
        except Exception as e:
            text = f"❌ Error: {e}"
        self.clear_items()
        self._build_ui(text)
        await interaction.response.edit_message(view=self)


# ─── cog ──────────────────────────────────────────────────────────────────────

class Leaderboard(commands.Cog):
    """Leaderboard cog – server + global stats, Components V2 UI."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        data_dir = os.getenv("RENDER_DISK_PATH", "./data")
        if not os.access(data_dir, os.W_OK):
            data_dir = os.path.join(os.getcwd(), "data")
        os.makedirs(data_dir, exist_ok=True)
        self.data_dir = data_dir

        # global_lb.json  – per-guild aggregated stats (filled by sync_stats)
        self._lb_path      = os.path.join(data_dir, "global_leaderboard.json")
        # global_consent.json – which guilds opted into global ranking
        self._consent_path = os.path.join(data_dir, "global_consent.json")

        self._lb: Dict      = _load_json(self._lb_path)
        self._consent: Dict = _load_json(self._consent_path)

    # ── lifecycle ─────────────────────────────────────────────────────
    @commands.Cog.listener()
    async def on_ready(self):
        await self.sync_stats()

    # ── internal helpers ──────────────────────────────────────────────
    def _save(self):
        _save_json(self._lb_path, self._lb)

    def _guild_data(self, guild_id: int, name: str = "") -> dict:
        gid = str(guild_id)
        if gid not in self._lb:
            self._lb[gid] = {
                "server_name":     name,
                "total_coins":     0,
                "fish_caught":     0,
                "minigames_played":0,
                "minigames_won":   0,
                "gambling_games":  0,
                "gambling_wins":   0,
                "commands_used":   0,
                "total_xp":        0,
            }
        if name:
            self._lb[gid]["server_name"] = name
        return self._lb[gid]

    def _consented(self, guild_id: int) -> bool:
        return self._consent.get(str(guild_id), {}).get("enabled", False)

    # ── sync ──────────────────────────────────────────────────────────
    async def sync_stats(self):
        """Read all data files and aggregate per-guild stats."""
        print("[Leaderboard] Syncing stats from data files…")

        eco     = _load_json(os.path.join(self.data_dir, "economy.json"))
        fish    = _load_json(os.path.join(self.data_dir, "fishing_data.json"))
        prof    = _load_json(os.path.join(self.data_dir, "profiles.json"))
        gamble  = _load_json(os.path.join(self.data_dir, "gambling_stats.json"))
        gstats  = _load_json(os.path.join(self.data_dir, "game_stats.json"))

        for guild in self.bot.guilds:
            gid = str(guild.id)
            # Ensure member cache is populated
            if not guild.chunked:
                try:
                    await guild.chunk(cache=True)
                except Exception:
                    pass
            members = {str(m.id) for m in guild.members}

            # coins
            coins = 0
            for uid, d in eco.items():
                if uid.isdigit() and uid in members and isinstance(d, dict):
                    coins += d.get("balance", 0)

            # fishing – total_catches is the int; fish_caught is a dict
            fish_total = 0
            for uid, d in fish.items():
                if uid.isdigit() and uid in members and isinstance(d, dict):
                    val = d.get("total_catches", 0)
                    fish_total += val if isinstance(val, int) else 0

            # profiles – xp, minigames, commands
            xp = mg_played = mg_won = cmds = 0
            for uid, d in prof.items():
                if uid.isdigit() and uid in members and isinstance(d, dict):
                    xp        += d.get("xp", d.get("total_xp", 0))
                    mg_played += d.get("minigames_played", 0)
                    mg_won    += d.get("minigames_won", 0)
                    cmds      += d.get("commands_used", 0)

            # game_stats (also has minigame totals)
            for uid, d in gstats.items():
                if uid.isdigit() and uid in members and isinstance(d, dict):
                    mg_played += d.get("total_games", 0)
                    mg_won    += d.get("games_won", 0)

            # gambling
            g_games = g_wins = 0
            for uid, d in gamble.items():
                if uid.isdigit() and uid in members and isinstance(d, dict):
                    g_games += d.get("total_games", 0)
                    g_wins  += d.get("total_won", 0)

            gdata = self._guild_data(guild.id, guild.name)
            gdata.update({
                "server_name":      guild.name,
                "total_coins":      coins,
                "fish_caught":      fish_total,
                "minigames_played": mg_played,
                "minigames_won":    mg_won,
                "gambling_games":   g_games,
                "gambling_wins":    g_wins,
                "commands_used":    cmds,
                "total_xp":         xp,
                "last_synced":      discord.utils.utcnow().isoformat(),
            })

        self._save()
        print(f"[Leaderboard] Sync done – {len(self.bot.guilds)} guild(s).")

    # ── page builders ─────────────────────────────────────────────────

    async def build_page(self, category: str, guild: discord.Guild) -> str:
        """Return markdown text for a given category + guild."""

        # ── Server (local) pages ──────────────────────────────────────
        if category == "s_coins":
            return await self._local_from_eco(guild)

        if category == "s_fishing":
            return await self._local_from_file(
                guild, "fishing_data.json", "total_catches",
                "🎣 Fishing – " + guild.name, "fish")

        if category == "s_minigames":
            return await self._local_from_profile(
                guild, "minigames_played", "🎮 Minigames – " + guild.name, "games")

        if category == "s_xp":
            return await self._local_from_profile(
                guild, "xp", "⭐ Level/XP – " + guild.name, "XP")

        if category == "s_mining":
            return await self._local_from_profile(
                guild, "mining_total_mined", "⛏️ Mining – " + guild.name, "blocks")

        if category == "s_farming":
            return await self._local_from_profile(
                guild, "farming_total_harvested", "🌾 Farming – " + guild.name, "crops")

        if category == "s_gambling":
            return await self._local_from_file(
                guild, "gambling_stats.json", "total_games",
                "🎲 Gambling – " + guild.name, "games")

        if category == "s_duels":
            return await self._local_from_profile(
                guild, "duels_won", "⚔️ Duels – " + guild.name, "wins")

        if category == "s_quests":
            return await self._local_from_profile(
                guild, "quests_completed", "📜 Quests – " + guild.name, "quests")

        if category == "s_reputation":
            return await self._local_from_file(
                guild, "reputation.json", "total_rep",
                "❤️ Reputation – " + guild.name, "rep")

        if category == "s_streak":
            return await self._local_from_profile(
                guild, "daily_longest_streak", "🔥 Daily Streak – " + guild.name, "days")

        # ── Global pages (per-user, all servers) ──────────────────────
        if category == "g_coins":
            return await self._global_users(
                "economy.json", "balance", "💰 Global – Coins", "🪙")
        if category == "g_fishing":
            return await self._global_users(
                "fishing_data.json", "total_catches", "🎣 Global – Fishing", "fish")
        if category == "g_mining":
            return await self._global_users(
                "profiles.json", "mining_total_mined", "⛏️ Global – Mining", "blocks")
        if category == "g_farming":
            return await self._global_users(
                "profiles.json", "farming_total_harvested", "🌾 Global – Farming", "crops")
        if category == "g_minigames":
            return await self._global_users(
                "profiles.json", "minigames_played", "🎮 Global – Minigames", "games")
        if category == "g_gambling":
            return await self._global_users(
                "gambling_stats.json", "total_games", "🎲 Global – Gambling", "games")
        if category == "g_duels":
            return await self._global_users(
                "profiles.json", "duels_won", "⚔️ Global – Duels", "wins")
        if category == "g_quests":
            return await self._global_users(
                "profiles.json", "quests_completed", "📜 Global – Quests", "quests")
        if category == "g_xp":
            return await self._global_users(
                "profiles.json", "xp", "⭐ Global – Level/XP", "XP")
        if category == "g_reputation":
            return await self._global_users(
                "reputation.json", "total_rep", "❤️ Global – Reputation", "rep")

        return "❓ Unknown category."

    # ── local helpers ─────────────────────────────────────────────────

    async def _local_from_eco(self, guild: discord.Guild) -> str:
        title = f"# 💰 Coins – {guild.name}\n"
        eco = _load_json(os.path.join(self.data_dir, "economy.json"))
        if not guild.chunked:
            try:
                await guild.chunk(cache=True)
            except Exception:
                pass
        members = {str(m.id): m for m in guild.members}
        entries = []
        for uid, d in eco.items():
            if not uid.isdigit() or not isinstance(d, dict):
                continue
            if members and uid not in members:
                continue
            bal = d.get("balance", 0)
            name = members[uid].display_name if uid in members else d.get("username", f"User {uid}")
            entries.append((name, bal))
        entries.sort(key=lambda x: x[1], reverse=True)
        if not entries:
            return title + "*No data yet.*"
        lines = [title]
        for i, (name, val) in enumerate(entries[:10], 1):
            lines.append(f"{_medal(i)} {name} — {val:,} 🪙")
        return "\n".join(lines)

    async def _local_from_file(self, guild: discord.Guild, filename: str,
                                stat_key: str, title: str, unit: str) -> str:
        header = f"# {title}\n"
        data = _load_json(os.path.join(self.data_dir, filename))
        if not guild.chunked:
            try:
                await guild.chunk(cache=True)
            except Exception:
                pass
        members = {str(m.id): m for m in guild.members}
        entries = []
        for uid, d in data.items():
            if not uid.isdigit() or not isinstance(d, dict):
                continue
            if members and uid not in members:
                continue
            val = d.get(stat_key, 0)
            if not isinstance(val, (int, float)):
                val = 0
            if val > 0:
                name = members[uid].display_name if uid in members else f"User {uid}"
                entries.append((name, val))
        entries.sort(key=lambda x: x[1], reverse=True)
        if not entries:
            return header + "*No data yet.*"
        lines = [header]
        for i, (name, val) in enumerate(entries[:10], 1):
            lines.append(f"{_medal(i)} {name} — {int(val):,} {unit}")
        return "\n".join(lines)

    async def _local_from_profile(self, guild: discord.Guild, stat_key: str,
                                   title: str, unit: str) -> str:
        header = f"# {title}\n"
        prof = _load_json(os.path.join(self.data_dir, "profiles.json"))
        if not guild.chunked:
            try:
                await guild.chunk(cache=True)
            except Exception:
                pass
        members = {str(m.id): m for m in guild.members}
        entries = []
        for uid, d in prof.items():
            if not uid.isdigit() or not isinstance(d, dict):
                continue
            if members and uid not in members:
                continue
            val = d.get(stat_key, 0)
            if not isinstance(val, (int, float)):
                val = 0
            if val > 0:
                name = members[uid].display_name if uid in members else f"User {uid}"
                entries.append((name, val))
        entries.sort(key=lambda x: x[1], reverse=True)
        if not entries:
            return header + "*No data yet.*"
        lines = [header]
        for i, (name, val) in enumerate(entries[:10], 1):
            lines.append(f"{_medal(i)} {name} — {int(val):,} {unit}")
        return "\n".join(lines)

    # ── global helpers ────────────────────────────────────────────────

    async def _global_users(self, filename: str, stat_key: str,
                             title: str, unit: str) -> str:
        """Top users across ALL servers — no guild filter.
        Name resolution: economy.json cache → bot.get_user() → 'User {id}'."""
        header = f"# {title}\n"
        data   = _load_json(os.path.join(self.data_dir, filename))
        # Build username cache from economy.json (most reliably has display names)
        eco    = _load_json(os.path.join(self.data_dir, "economy.json"))
        name_cache: Dict[str, str] = {
            uid: d.get("username", f"User {uid}")
            for uid, d in eco.items()
            if uid.isdigit() and isinstance(d, dict)
        }

        entries = []
        for uid, d in data.items():
            if not uid.isdigit() or not isinstance(d, dict):
                continue
            val = d.get(stat_key, 0)
            if not isinstance(val, (int, float)) or val <= 0:
                continue
            if uid in name_cache:
                name = name_cache[uid]
            else:
                user = self.bot.get_user(int(uid))
                name = user.display_name if user else f"User {uid}"
            entries.append((name, int(val)))

        entries.sort(key=lambda x: x[1], reverse=True)
        if not entries:
            return header + "*No data yet.*"
        lines = [header]
        for i, (name, val) in enumerate(entries[:10], 1):
            lines.append(f"{_medal(i)} {name} — {val:,} {unit}")
        return "\n".join(lines)

    # ── slash command ─────────────────────────────────────────────────

    @app_commands.command(name="leaderboard", description="Browse server and global leaderboards")
    async def leaderboard_slash(self, interaction: discord.Interaction):
        view = LeaderboardView(self, interaction.guild)
        await interaction.response.send_message(view=view)

    # ── prefix commands ───────────────────────────────────────────────

    @commands.command(name="synclb")
    @commands.is_owner()
    async def synclb_cmd(self, ctx):
        """Force re-sync leaderboard stats from data files (owner only)."""
        msg = await ctx.send("🔄 Syncing…")
        await self.sync_stats()
        await msg.edit(content="✅ Leaderboard stats re-synced from all data files.")

    @commands.command(name="lbconsent")
    @commands.has_permissions(administrator=True)
    async def lbconsent_cmd(self, ctx, toggle: str):
        """Toggle this server's global leaderboard visibility.
        Usage: L!lbconsent on / off"""
        toggle = toggle.lower()
        if toggle not in ("on", "off", "enable", "disable"):
            await ctx.send("Usage: `L!lbconsent on` or `L!lbconsent off`")
            return
        enabled = toggle in ("on", "enable")
        gid = str(ctx.guild.id)
        self._consent[gid] = {
            "enabled":      enabled,
            "set_by":       ctx.author.id,
            "set_at":       discord.utils.utcnow().isoformat(),
        }
        _save_json(self._consent_path, self._consent)
        if enabled:
            await ctx.send("✅ Global leaderboard **enabled** for this server. "
                           "Your server will appear in cross-server rankings.")
        else:
            await ctx.send("❌ Global leaderboard **disabled**. "
                           "Your server won't appear in cross-server rankings.")


async def setup(bot: commands.Bot):
    await bot.add_cog(Leaderboard(bot))

