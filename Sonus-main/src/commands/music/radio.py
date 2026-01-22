import asyncio
import logging
from pathlib import Path
from typing import Dict, Optional

import discord
from discord import Embed

from src.utils.loaders import ROOT, load_json
from src.commands.music.play import _ensure_vc_connected, _create_player_with_probe


RADIOS_PATH = ROOT / "data" / "radios"
_RADIO_CACHE: Dict[str, Dict] = {}
logger = logging.getLogger(__name__)


def _load_radios() -> Dict[str, Dict]:
    global _RADIO_CACHE
    if _RADIO_CACHE:
        return _RADIO_CACHE
    radios: Dict[str, Dict] = {}
    if RADIOS_PATH.exists():
        for p in RADIOS_PATH.glob("*.json"):
            try:
                data = load_json(f"data/radios/{p.name}")
                if data.get("id"):
                    radios[data["id"].lower()] = data
            except FileNotFoundError:
                logger.debug("Radio file missing: %s", p)
            except Exception as exc:
                logger.debug("Failed to load radio file %s: %s", p, exc)
    _RADIO_CACHE = radios
    return radios


def _find_radio(name: str) -> Optional[Dict]:
    radios = _load_radios()
    if not name:
        return None
    key = name.lower().strip()
    if key in radios:
        return radios[key]
    # fallback: match by title
    for r in radios.values():
        if r.get("name", "").lower() == key:
            return r
    return None


def register(bot):
    @bot.command(name="radio")
    async def _radio(ctx, action: str = "list", *, name: str = ""):
        """Prefix: S!radio list|play <name> — quick ambient/lofi radios."""
        action = (action or "").lower()
        guild = ctx.guild

        if action == "list":
            radios = _load_radios()
            if not radios:
                await ctx.send("No radios available.")
                return
            desc = "\n".join(f"• **{r.get('name', rid)}** — `{rid}`" for rid, r in radios.items())
            await ctx.send(embed=Embed(title="Radios", description=desc, color=0x4CC9F0))
            return

        if action != "play":
            await ctx.send("Usage: `S!radio list` or `S!radio play <name>`")
            return

        if guild is None:
            await ctx.send("Playback is only available in a guild.")
            return

        radio = _find_radio(name)
        if not radio:
            await ctx.send("Unknown radio. Try `S!radio list`.")
            return

        preferred = None
        try:
            voice_state = getattr(ctx.author, "voice", None)
            channel = getattr(voice_state, "channel", None)
            if channel:
                preferred = channel.id
        except Exception:
            preferred = None

        vc = guild.voice_client
        if not vc or not getattr(vc, "is_connected", lambda: False)():
            vc = await _ensure_vc_connected(bot, guild, preferred_channel_id=preferred)
        if not vc:
            await ctx.send("Could not join a voice channel.")
            return

        # stop current playback to start continuous radio
        try:
            if vc.is_playing() or vc.is_paused():
                vc.stop()
        except Exception:
            logger.debug("Failed to stop existing playback before starting radio", exc_info=True)

        ffmpeg_options = {
            "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
            "options": "-vn",
        }

        try:
            player = await _create_player_with_probe(radio["source"], ffmpeg_options, timeout=8.0)
            track = {
                "title": radio.get("name") or radio.get("id"),
                "source": radio.get("source"),
                "type": "radio",
                "started_at": asyncio.get_running_loop().time(),
            }
            try:
                setattr(bot, "sonus_now_playing", track)
            except Exception:
                pass
            vc.play(player)
            await ctx.send(embed=Embed(title="Tuned in", description=track["title"], color=0x1DB954))
        except Exception as exc:
            await ctx.send(embed=Embed(title="Radio Error", description=str(exc), color=0xE63946))
