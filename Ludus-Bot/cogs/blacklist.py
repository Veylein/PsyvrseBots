import discord
from discord.ext import commands
import json
import os


_DATA_DIR = os.getenv("RENDER_DISK_PATH", ".")
BLACKLIST_FILE = os.path.join(_DATA_DIR, "blacklist.json")


def _load() -> dict:
    if os.path.exists(BLACKLIST_FILE):
        with open(BLACKLIST_FILE, "r") as f:
            return json.load(f)
    data = {"users": [], "servers": []}
    _save(data)
    return data


def _save(data: dict):
    tmp = BLACKLIST_FILE + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        os.replace(tmp, BLACKLIST_FILE)
    except Exception as e:
        print(f"[Blacklist] Save error: {e}")
        try:
            os.remove(tmp)
        except OSError:
            pass


# ── Modals ────────────────────────────────────────────────────────────────────

class _InputModal(discord.ui.Modal):
    target_id = discord.ui.TextInput(
        label="Enter ID",
        placeholder="User ID or Server ID\u2026",
        min_length=15,
        max_length=22,
    )

    def __init__(self, title: str, action: str, cog):
        super().__init__(title=title)
        self._action = action
        self._cog = cog

    async def on_submit(self, interaction: discord.Interaction):
        raw = self.target_id.value.strip()
        if not raw.isdigit():
            await interaction.response.send_message("\u274c ID must be a number.", ephemeral=True)
            return

        target = int(raw)
        data = _load()
        owner_ids = getattr(self._cog.bot, "owner_ids", set())

        if self._action == "ban_user":
            if target in owner_ids:
                return await interaction.response.send_message("\u274c Cannot blacklist a bot owner.", ephemeral=True)
            if target in data["users"]:
                return await interaction.response.send_message(f"\u274c User `{target}` is already blacklisted.", ephemeral=True)
            data["users"].append(target)
            _save(data)
            try:
                u = await self._cog.bot.fetch_user(target)
                label = f"**{u}** (`{target}`)"
            except Exception:
                label = f"`{target}`"
            embed = discord.Embed(title="\U0001f6ab User Blacklisted", description=f"{label} cannot use the bot.", color=discord.Color.red())

        elif self._action == "ban_server":
            if target in data["servers"]:
                return await interaction.response.send_message(f"\u274c Server `{target}` is already blacklisted.", ephemeral=True)
            data["servers"].append(target)
            _save(data)
            g = self._cog.bot.get_guild(target)
            label = f"**{g.name}** (`{target}`)" if g else f"`{target}`"
            embed = discord.Embed(title="\U0001f6ab Server Blacklisted", description=f"{label} has been blocked.", color=discord.Color.red())

        elif self._action == "unban_user":
            if target not in data["users"]:
                return await interaction.response.send_message(f"\u274c User `{target}` is not blacklisted.", ephemeral=True)
            data["users"].remove(target)
            _save(data)
            try:
                u = await self._cog.bot.fetch_user(target)
                label = f"**{u}** (`{target}`)"
            except Exception:
                label = f"`{target}`"
            embed = discord.Embed(title="\u2705 User Un-blacklisted", description=f"{label} can use the bot again.", color=discord.Color.green())

        elif self._action == "unban_server":
            if target not in data["servers"]:
                return await interaction.response.send_message(f"\u274c Server `{target}` is not blacklisted.", ephemeral=True)
            data["servers"].remove(target)
            _save(data)
            g = self._cog.bot.get_guild(target)
            label = f"**{g.name}** (`{target}`)" if g else f"`{target}`"
            embed = discord.Embed(title="\u2705 Server Un-blacklisted", description=f"{label} can use the bot again.", color=discord.Color.green())

        else:
            embed = discord.Embed(title="\u274c Unknown action", color=discord.Color.red())

        await interaction.response.send_message(embed=embed, ephemeral=True)
        # refresh the dashboard
        await interaction.message.edit(embed=_build_overview_embed(), view=BlacklistView(self._cog))


# ── View ───────────────────────────────────────────────────────────────────────

def _build_overview_embed() -> discord.Embed:
    data = _load()
    embed = discord.Embed(
        title="\U0001f6ab Blacklist Manager",
        color=discord.Color.red(),
        description="Use the buttons below to manage who can use the bot."
    )

    # Users
    users = data["users"]
    if users:
        lines = [f"\u2022 `{uid}`" for uid in users[:15]]
        if len(users) > 15:
            lines.append(f"\u2026 and {len(users) - 15} more")
        embed.add_field(name=f"\U0001f465 Blacklisted Users ({len(users)})", value="\n".join(lines), inline=True)
    else:
        embed.add_field(name="\U0001f465 Blacklisted Users (0)", value="*None*", inline=True)

    # Servers
    servers = data["servers"]
    if servers:
        lines = [f"\u2022 `{sid}`" for sid in servers[:15]]
        if len(servers) > 15:
            lines.append(f"\u2026 and {len(servers) - 15} more")
        embed.add_field(name=f"\U0001f3f0 Blacklisted Servers ({len(servers)})", value="\n".join(lines), inline=True)
    else:
        embed.add_field(name="\U0001f3f0 Blacklisted Servers (0)", value="*None*", inline=True)

    return embed


class BlacklistView(discord.ui.View):
    def __init__(self, cog):
        super().__init__(timeout=120)
        self._cog = cog

    @discord.ui.button(label="\U0001f6ab Blacklist User", style=discord.ButtonStyle.danger, row=0)
    async def ban_user(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(_InputModal("Blacklist User", "ban_user", self._cog))

    @discord.ui.button(label="\U0001f3f0 Blacklist Server", style=discord.ButtonStyle.danger, row=0)
    async def ban_server(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(_InputModal("Blacklist Server", "ban_server", self._cog))

    @discord.ui.button(label="\u2705 Unblacklist User", style=discord.ButtonStyle.success, row=1)
    async def unban_user(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(_InputModal("Unblacklist User", "unban_user", self._cog))

    @discord.ui.button(label="\u2705 Unblacklist Server", style=discord.ButtonStyle.success, row=1)
    async def unban_server(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(_InputModal("Unblacklist Server", "unban_server", self._cog))

    @discord.ui.button(label="\U0001f504 Refresh", style=discord.ButtonStyle.secondary, row=2)
    async def refresh(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=_build_overview_embed(), view=BlacklistView(self._cog))


# ── Cog ───────────────────────────────────────────────────────────────────────

class Blacklist(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @property
    def owner_ids(self):
        return getattr(self.bot, "owner_ids", set())

    def is_blacklisted(self, user_id: int = None, guild_id: int = None) -> bool:
        data = _load()
        if user_id and user_id in data["users"]:
            return True
        if guild_id and guild_id in data["servers"]:
            return True
        return False

    def _is_admin(self, ctx) -> bool:
        if ctx.author.id in self.owner_ids:
            return True
        if ctx.guild and ctx.author.guild_permissions.administrator:
            return True
        return False

    @commands.command(name="blacklist", aliases=["bl"])
    async def blacklist_cmd(self, ctx):
        """Open the Blacklist Manager UI (Admins only)."""
        if not self._is_admin(ctx):
            return await ctx.send("\u274c You need to be an administrator to use this command.", delete_after=5)
        embed = _build_overview_embed()
        await ctx.send(embed=embed, view=BlacklistView(self))

    # ── Enforcement ───────────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_command(self, ctx):
        if ctx.author.id in self.owner_ids:
            return
        data = _load()
        if ctx.author.id in data["users"]:
            await ctx.send("\U0001f6ab You are blacklisted from using this bot.")
            raise commands.CheckFailure("User is blacklisted")
        if ctx.guild and ctx.guild.id in data["servers"]:
            await ctx.send("\U0001f6ab This server is blacklisted from using this bot.")
            raise commands.CheckFailure("Server is blacklisted")

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.type != discord.InteractionType.application_command:
            return
        if interaction.user.id in self.owner_ids:
            return
        data = _load()
        if interaction.user.id in data["users"]:
            try:
                await interaction.response.send_message("\U0001f6ab You are blacklisted from using this bot.", ephemeral=True)
            except Exception:
                pass
            return
        if interaction.guild and interaction.guild.id in data["servers"]:
            try:
                await interaction.response.send_message("\U0001f6ab This server is blacklisted from using this bot.", ephemeral=True)
            except Exception:
                pass


async def setup(bot):
    await bot.add_cog(Blacklist(bot))