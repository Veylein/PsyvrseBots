import importlib

modules = ['Pax-Bot.db_service', 'Pax-Bot.interaction_views', 'Pax-Bot.cogs.health']
for m in modules:
    try:
        importlib.import_module(m)
        print(f'Imported {m} OK')
    except Exception as e:
        print(f'FAILED {m}: {e!r}')
