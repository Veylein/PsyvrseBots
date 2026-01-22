from discord import Embed


def now_playing_embed(track):
    e = Embed(title=track.get("title", "Unknown"))
    e.set_thumbnail(url=track.get("artwork"))
    e.add_field(name="Source", value=track.get("source", "N/A"))
    return e
