# DB models placeholder - prefer pydantic + migrations in real implementation
from pydantic import BaseModel

class Playlist(BaseModel):
    id: str
    name: str
    tracks: list[dict]
