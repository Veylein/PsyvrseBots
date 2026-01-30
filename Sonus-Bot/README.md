# Sonus-Bot

Sonus is a Discord music bot focused on reliable playback across YouTube, SoundCloud, Spotify (via yt-dlp), and streaming radios.

This README documents quick setup, recommended environment variables and optional features added by recent improvements.

## Quick start (development)

1. Create and activate a Python venv

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Install dependencies

```powershell
pip install -r requirements.txt
```

3. Create a `.env` file in the `Sonus-Bot` folder (or set env vars in your host). Example values:

```
DISCORD_TOKEN=your_token_here
GUILD_ID=123456789012345678  # optional development guild to sync to
YTDL_COOKIEFILE=path/to/yt-dlp/cookies.txt  # optional
SONUS_YTDL_CACHE_DB=sonus_ytdl_cache.db  # optional persistent cache
SONUS_QUEUE_DB=sonus_queues.db  # optional persistent queue storage
```

4. Run tests (recommended before running the bot):

```powershell
python -m pytest Sonus-Bot/tests -q
```

5. Start the bot

```powershell
setx PYTHONPATH .
python Sonus-Bot/main.py
```

Or run via your process manager/container with the environment variables set.

## Optional features and env vars

- `YTDL_COOKIEFILE` / `YTDL_COOKIES`: path to a cookie file for yt-dlp when playing restricted YouTube content.
- `SONUS_YTDL_CACHE_DB`: when set, enables a shelve-backed persistent cache for yt-dlp extraction results (reduces repeated network calls).
- `SONUS_QUEUE_DB`: when set to a writable path, per-guild queue contents are persisted across restarts; the bot attempts to resume queued playback on startup.
 - `SONUS_QUEUE_DB`: when set to a writable path, per-guild queue contents are persisted across restarts; the bot attempts to resume queued playback on startup.
 - `SONUS_RESUME_ON_STARTUP`: when set to `1`, `true`, or `yes`, the bot will attempt to resume any persisted enqueue jobs (long-running playlist/album enqueues) on startup. This is optional and disabled by default to avoid unexpected background tasks during deploys.
- `SONUS_PLAYLIST_LIMIT`: maximum number of tracks to enqueue when playing a playlist/album (default 100).
- `SONUS_PROBE_CACHE_TTL` / `SONUS_YTDL_CACHE_TTL`: TTLs for probe and ytdl caches and related size env vars.

## Admin commands (in-bot)

- `ytdl_cache_stats` / `/ytdl-cache-stats`: show yt-dlp cache stats.
- `ytdl_cache_clear` / `/ytdl-cache-clear`: clear persistent yt-dlp cache.

## Notes and troubleshooting

- `ffmpeg` must be installed and available on PATH for playback to work. The bot logs an FFmpeg diagnostic at startup.
- Spotify API integration is not enabled by default; yt-dlp often extracts Spotify page info but for production-grade metadata consider adding Spotify API credentials.
- If you run multiple bot workers, the in-process caches (yt-dlp and probe caches) are per-process only. For multi-worker deployments consider using Redis or a shared DB for cache and queue persistence.

## Contributing

Run tests and follow existing code style. Open an issue or PR for major changes.
