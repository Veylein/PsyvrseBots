from discord import Embed


def playlist_embed(playlist):
    e = Embed(title=playlist.get("name", "Playlist"))
    for t in playlist.get("tracks", [])[:10]:
        e.add_field(name=t.get("title"), value=t.get("uri", ""), inline=False)
    return e
