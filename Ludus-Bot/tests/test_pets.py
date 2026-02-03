import os
import sys
import random
import pytest

# ensure Ludus-Bot is on path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from cogs.pets import Pets

class DummyBot:
    def get_cog(self, name):
        return None


def test_pets_multipliers(tmp_path, monkeypatch):
    bot = DummyBot()
    pets = Pets(bot)

    # inject pet data
    pets.pets_data = {
        '100': {'type': 'Cat', 'emoji': '🐱'},
        '200': {'type': 'Axolotl', 'emoji': '🦎'},
        '300': {'type': 'Dog', 'emoji': '🐶'},
        '400': {'type': 'Dragon', 'emoji': '🐉'},
    }

    assert abs(pets.get_fishing_multiplier(100) - 1.20) < 0.001
    assert abs(pets.get_fishing_multiplier(200) - 1.30) < 0.001

    assert abs(pets.get_farm_yield_multiplier(300) - 1.15) < 0.001

    # rarity boosts
    assert pets.get_rarity_multiplier(200, 'Rare') > 1.0
    assert pets.get_rarity_multiplier(100, 'Legendary') > 1.0

    # coin bonus checks
    assert pets.get_coin_bonus(400) >= 8
    assert pets.get_coin_bonus(100) >= 0

    # auto tend chance
    c = pets.get_auto_tend_chance(300)
    assert 0.0 <= c <= 1.0