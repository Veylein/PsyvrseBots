# Audio effects pipeline placeholders. All effects must be data-driven.

class Effect:
    def apply(self, pcm_bytes: bytes) -> bytes:
        # transform PCM; override in concrete effect implementations
        return pcm_bytes
