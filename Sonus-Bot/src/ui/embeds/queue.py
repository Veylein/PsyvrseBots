from discord import Embed


def queue_embed(tracks):
    e = Embed(title="Queue")
    for i, t in enumerate(tracks[:10], start=1):
        e.add_field(name=f"{i}. {t.get('title')}", value=t.get('uri', ''), inline=False)
    return e
