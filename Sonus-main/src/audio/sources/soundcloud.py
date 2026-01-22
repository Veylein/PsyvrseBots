# soundcloud source adapter (stub)

class SoundCloudSource:
    def __init__(self, url: str):
        self.url = url

    async def stream(self):
        yield b""
