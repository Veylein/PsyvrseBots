# youtube source adapter (stub)

class YouTubeSource:
    def __init__(self, url: str):
        self.url = url

    async def stream(self):
        # return async iterator of pcm chunks
        yield b""
