import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

AUDIT_LOG = Path(__file__).resolve().parents[2] / "data" / "audit.log"
CHANNEL_ID = 1462019773755035731


async def _safe_send(bot, content: str):
    try:
        ch = bot.get_channel(CHANNEL_ID)
        if ch:
            await ch.send(content)
    except Exception:
        # Do not raise from audit logging
        return


async def log_action(bot, actor_id: int, action: str, details: Optional[Dict[str, Any]] = None):
    """Append an audit record to disk and post a short message to the audit channel.

    This is best-effort and never raises.
    """
    try:
        record = {
            "time": datetime.utcnow().isoformat() + "Z",
            "actor_id": actor_id,
            "action": action,
            "details": details or {},
        }

        # ensure directory
        AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
        with AUDIT_LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

        # send a minimal message to the configured channel
        if bot is not None:
            short = f"[AUDIT] <@{actor_id}> performed `{action}`"
            if details:
                # keep message short
                short += f": { {k: details[k] for k in list(details)[:3]} }"
            # schedule send without blocking
            try:
                # if inside an event loop, create task
                loop = asyncio.get_running_loop()
                loop.create_task(_safe_send(bot, short))
            except RuntimeError:
                # no running loop; fire-and-forget via asyncio
                asyncio.ensure_future(_safe_send(bot, short))
    except Exception:
        # swallow any error; auditing must not break owner flows
        return
