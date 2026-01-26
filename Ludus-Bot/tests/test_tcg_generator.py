import pytest
from cogs import psyvrse_tcg


def test_generate_card_deterministic():
    a = psyvrse_tcg.generate_card_from_seed(123456)
    b = psyvrse_tcg.generate_card_from_seed(123456)
    assert a.name == b.name
    assert a.rarity == b.rarity
    assert a.attack == b.attack


def test_create_crafted_and_inventory(tmp_path, monkeypatch):
    # use temp files by monkeypatching constants
    monkeypatch.setattr(psyvrse_tcg, 'USERS_FILE', str(tmp_path / 'users.json'))
    monkeypatch.setattr(psyvrse_tcg, 'CRAFTED_FILE', str(tmp_path / 'crafted.json'))
    monkeypatch.setattr(psyvrse_tcg, 'TRADES_FILE', str(tmp_path / 'trades.json'))
    inv = psyvrse_tcg.PsyInventory()
    cid = inv.create_crafted(psyvrse_tcg.Card(id='0', name='X', rarity='A'))
    assert cid.startswith('C')
    inv.add_card(1, cid)
    u = inv.get_user(1)
    assert cid in u['cards']