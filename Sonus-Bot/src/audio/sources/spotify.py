# spotify source adapter (stub) - data-driven metadata only

class SpotifySource:
    def __init__(self, uri: str):
        self.uri = uri

    async def metadata(self):
        return {"title": "unknown", "uri": self.uri}
