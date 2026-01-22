import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import eventus_render_mega as er

print('Initializing DB via eventus_render_mega.init_db()')
er.init_db()
print('DB init complete')
