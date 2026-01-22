import sqlite3

TEMPLATES = {
    'memes': [
        'Share your best meme of the week!',
        'Post a wholesome meme to make someone smile.',
        'Which meme format needs a comeback?'
    ],
    'music': [
        'What song are you vibing to right now?',
        'Share a song recommendation for the group.',
        'What artist deserves more recognition?'
    ],
    'gaming': [
        'What game are you playing currently?',
        'Share a proud gaming moment from this month.',
        'Which upcoming release are you hyped for?'
    ],
    'art': [
        'Show a piece of art you made recently.',
        'What colors are you loving right now?',
        'Share a quick sketch or wallpaper you made.'
    ],
    'tech': [
        'What small coding tip saved you recently?',
        'Share a tiny project you finished this week.',
        'Which tool do you recommend for productivity?'
    ],
    'food': [
        'Post a photo of your meal!',
        'Sweet or savory — what did you pick?',
        'Share a quick recipe for busy nights.'
    ],
}

def seed():
    conn = sqlite3.connect('eventus.db')
    c = conn.cursor()
    for cat, texts in TEMPLATES.items():
        for t in texts:
            c.execute("INSERT INTO topic_templates (guild_id, category, template_text) VALUES (?, ?, ?)", (None, cat, t))
    conn.commit()
    conn.close()

if __name__ == '__main__':
    seed()
