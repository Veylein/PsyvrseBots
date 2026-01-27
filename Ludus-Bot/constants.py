# Stałe używane w uno
# Ten plik jest importowany przez main.py i inne moduły aby uniknąć circular imports

# UNO Back Emoji - będzie zaktualizowane przez main.py po załadowaniu emoji
UNO_BACK_EMOJI = "<:uno_back:1446933469476159559>"

# Funkcja do aktualizacji emoji (wywoływana przez main.py)
def set_uno_back_emoji(emoji_str):
    global UNO_BACK_EMOJI
    UNO_BACK_EMOJI = emoji_str
