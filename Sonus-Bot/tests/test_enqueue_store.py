import importlib
import os


def test_enqueue_store_save_load_remove(tmp_path, monkeypatch):
    # point the enqueue DB to a temp file
    dbpath = tmp_path / "sonus_enqueue_test.db"
    monkeypatch.setenv('SONUS_ENQUEUE_DB', str(dbpath))

    # reload module so it picks up the env var
    import src.utils.enqueue_store as es
    importlib.reload(es)

    # save a state
    es.save_enqueue_state(999, {'items': ['one', 'two'], 'added': 0, 'total': 2})

    states = es.load_all_enqueue_states()
    assert isinstance(states, dict)
    assert 999 in states
    assert states[999]['items'] == ['one', 'two']

    # remove and verify gone
    es.remove_enqueue_state(999)
    states2 = es.load_all_enqueue_states()
    assert 999 not in states2
