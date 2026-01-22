import sqlite3
import os
from datetime import datetime

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DB_PATH = os.path.join(ROOT, 'eventus.db')

templates = [
    (
        None,
        'Game Night (Polished)',
        '''title: 🎮 Game Night Tonight!
description: Join us in {channel} for casual play and voice chat. RSVP using `{event_id}` and bring your favorite game!
color: purple
footer: Hosted by Eventus — see you there!
thumbnail: https://i.imgur.com/8Km9tLL.png
''',
        datetime.utcnow().isoformat()
    ),
    (
        None,
        'Study Session (Focus)',
        '''title: 📚 Study Session — Focus & Accountability
description: Quiet study session in {channel}. Bring goals and a Pomodoro timer. Role: {role_mention}
color: blue
footer: Tips: 25/5 Pomodoro intervals — stay focused!
''',
        datetime.utcnow().isoformat()
    ),
    (
        None,
        'Movie Night (Screening)',
        '''title: 🎬 Movie Night Screening
description: Grab snacks and join {channel} at showtime. RSVP with `{event_id}` to save your spot.
color: teal
image: https://i.imgur.com/3GvwNBf.png
footer: Popcorn provided (virtually) — come hang!
''',
        datetime.utcnow().isoformat()
    )
]

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()
for g_id, name, content, created in templates:
    c.execute("INSERT INTO announcement_templates (guild_id, name, content, created_at) VALUES (?, ?, ?, ?)", (g_id, name, content, created))
conn.commit()
print(f"Inserted {len(templates)} example templates (guild_id=NULL).")
conn.close()
