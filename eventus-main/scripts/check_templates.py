import sqlite3
conn = sqlite3.connect('eventus.db')
c = conn.cursor()
c.execute('SELECT COUNT(*) FROM topic_templates')
print('Templates:', c.fetchone()[0])
conn.close()
