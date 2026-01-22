def is_valid_uri(uri: str) -> bool:
    return uri.startswith("http") or uri.startswith("spotify:")
