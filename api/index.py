from flask import Flask, render_template, jsonify
import feedparser
from datetime import datetime, timedelta
import threading
import time

# Vercel needs this to handle the Flask app
app = Flask(__name__)

# RSS feeds of Czech news sources with custom icon URLs
RSS_FEEDS = [
    {"name": "ČT24", "url": "https://ct24.ceskatelevize.cz/rss/tema/vyber-redakce-84313", "icon": "/static/icons/ct24.png"},
    {"name": "Novinky.cz", "url": "https://www.novinky.cz/rss/v2.xml", "icon": "/static/icons/novinky.png"},
    {"name": "iDNES.cz", "url": "https://servis.idnes.cz/rss.aspx?c=zpravodaj", "icon": "/static/icons/idnes.png"},
    {"name": "Seznam Zprávy", "url": "https://www.seznamzpravy.cz/rss", "icon": "/static/icons/seznam.png"},
    {"name": "Aktuálně.cz", "url": "https://www.aktualne.cz/rss", "icon": "/static/icons/aktualne.png"},
    {"name": "Deník.cz", "url": "https://www.denik.cz/rss/zpravy.html", "icon": "/static/icons/denik.png"},
    {"name": "Blesk.cz", "url": "https://www.blesk.cz/rss", "icon": "/static/icons/blesk.png"},
    {"name": "Lidovky.cz", "url": "https://servis.lidovky.cz/rss.aspx", "icon": "/static/icons/lidovky.png"},
    {"name": "iRozhlas", "url": "https://www.irozhlas.cz/rss/irozhlas", "icon": "/static/icons/irozhlas.png"}
]

# Cache for news data
news_cache = {}
last_update = datetime.min

def fetch_news_from_feed(feed):
    """Fetches and parses a single RSS feed."""
    try:
        feed_data = feedparser.parse(feed['url'])
        articles = []

        if feed_data.entries:
            for entry in feed_data.entries[:10]:
                title = entry.title.strip() if entry.title else "Bez názvu"
                link = entry.link if entry.link else "#"
                published = None

                # Try to get published or updated date
                if hasattr(entry, 'published'):
                    try:
                        published = datetime.strptime(entry.published, "%a, %d %b %Y %H:%M:%S %z")
                    except Exception:
                        if hasattr(entry, 'published_parsed') and entry.published_parsed:
                            published = datetime.fromtimestamp(time.mktime(entry.published_parsed))
                elif hasattr(entry, 'updated'):
                    try:
                        published = datetime.strptime(entry.updated, "%a, %d %b %Y %H:%M:%S %z")
                    except Exception:
                        if hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                            published = datetime.fromtimestamp(time.mktime(entry.updated_parsed))

                articles.append({
                    "title": title,
                    "link": link,
                    "published": published
                })

        return {
            "source": feed["name"],
            "icon": feed["icon"],
            "articles": articles
        }
    except Exception as e:
        print(f"Error fetching {feed['name']}: {str(e)}")
        return {
            "source": feed["name"],
            "icon": feed["icon"],
            "articles": [
                {"title": f"Chyba při načítání zpráv: {str(e)}", "link": "#", "published": None}
            ]
        }

def calculate_time_since(published_date):
    """Calculates time difference in Czech."""
    now = datetime.now(published_date.tzinfo)
    delta = now - published_date

    if delta.days >= 365:
        years = delta.days // 365
        return f"před {years} rokem" if years == 1 else f"před {years} roky"
    elif delta.days >= 30:
        months = delta.days // 30
        return f"před {months} měsícem" if months == 1 else f"před {months} měsíci"
    elif delta.days > 0:
        return f"před {delta.days} dnem" if delta.days == 1 else f"před {delta.days} dny"
    elif delta.seconds >= 3600:
        hours = delta.seconds // 3600
        return f"před {hours} hodinou" if hours == 1 else f"před {hours} hodinami"
    elif delta.seconds >= 60:
        minutes = delta.seconds // 60
        return f"před {minutes} minutou" if minutes == 1 else f"před {minutes} minutami"
    else:
        return "před chvílí"

def update_news_cache():
    """Fetches all news and updates the cache."""
    global news_cache, last_update
    print("Updating news cache...")
    new_cache = {}

    for feed in RSS_FEEDS:
        feed_data = fetch_news_from_feed(feed)
        new_cache[feed["name"]] = feed_data

    news_cache = new_cache
    last_update = datetime.now()
    print(f"News cache updated at {last_update}")

@app.route('/')
def index():
    """Renders the main page."""
    # Vercel's build process doesn't handle static files the same way as a local dev server.
    # We must provide the full path to the template.
    return render_template('index.html')

@app.route('/api/news')
def get_news():
    """API endpoint to get cached news data."""
    global news_cache, last_update

    # --- Změna pro nasazení na Vercel ---
    # Kontrola stáří cache. Pokud je starší než 15 minut, aktualizuje se.
    if datetime.now() - last_update > timedelta(minutes=15):
        update_news_cache()
    # ------------------------------------

    formatted_news = []
    for source_name, source_data in news_cache.items():
        articles_out = []
        for article in source_data["articles"]:
            if article["published"]:
                articles_out.append({
                    "title": article["title"],
                    "link": article["link"],
                    "published": article["published"].isoformat(),
                    "age": calculate_time_since(article["published"])
                })
            else:
                articles_out.append({
                    "title": article["title"],
                    "link": article["link"],
                    "published": None,
                    "age": "?"
                })

        formatted_news.append({
            "source": source_name,
            "icon": source_data["icon"],
            "articles": articles_out
        })

    return jsonify({
        "news": formatted_news,
        "last_update": last_update.isoformat() if last_update else None
    })
