import Parser from "rss-parser";

const parser = new Parser({
  headers: { 
    'User-Agent': 'Mozilla/5.0 (compatible; Zpravy360Bot/1.0; +https://zpravy360.vercel.app)',
    'Accept': 'application/rss+xml,application/xml'
  }
});

const RSS_FEEDS = [
  { name: "ČT24", url: "https://ct24.ceskatelevize.cz/rss/tema/vyber-redakce-84313", icon: "/static/icons/ct24.png" },
  { name: "Novinky.cz", url: "https://www.novinky.cz/rss/v2.xml", icon: "/static/icons/novinky.png" },
  { name: "iDNES.cz", url: "https://servis.idnes.cz/rss.aspx?c=zpravodaj", icon: "/static/icons/idnes.png" },
  { name: "Seznam Zprávy", url: "https://www.seznamzpravy.cz/rss", icon: "/static/icons/seznam.png" },
  { name: "Aktuálně.cz", url: "https://www.aktualne.cz/rss", icon: "/static/icons/aktualne.png" },
  { name: "Deník.cz", url: "https://www.denik.cz/rss/zpravy.html", icon: "/static/icons/denik.png" },
  { name: "Blesk.cz", url: "https://www.blesk.cz/rss", icon: "/static/icons/blesk.png" },
  { name: "Lidovky.cz", url: "https://servis.lidovky.cz/rss.aspx", icon: "/static/icons/lidovky.png" },
  { name: "iRozhlas", url: "https://www.irozhlas.cz/rss/irozhlas", icon: "/static/icons/irozhlas.png" }
];

let newsCache = {};
let lastUpdate = null;

function calculateTimeSince(publishedDate) {
  const now = new Date();
  const deltaMs = now - publishedDate;
  const deltaSec = Math.floor(deltaMs / 1000);
  const deltaMin = Math.floor(deltaSec / 60);
  const deltaHours = Math.floor(deltaMin / 60);
  const deltaDays = Math.floor(deltaHours / 24);

  if (deltaDays >= 365) {
    const years = Math.floor(deltaDays / 365);
    return `před ${years} ${years === 1 ? "rokem" : "roky"}`;
  } else if (deltaDays >= 30) {
    const months = Math.floor(deltaDays / 30);
    return `před ${months} ${months === 1 ? "měsícem" : "měsíci"}`;
  } else if (deltaDays > 0) {
    return `před ${deltaDays} ${deltaDays === 1 ? "dnem" : "dny"}`;
  } else if (deltaHours > 0) {
    return `před ${deltaHours} ${deltaHours === 1 ? "hodinou" : "hodinami"}`;
  } else if (deltaMin > 0) {
    return `před ${deltaMin} ${deltaMin === 1 ? "minutou" : "minutami"}`;
  } else {
    return "před chvílí";
  }
}

async function fetchNewsFromFeed(feed) {
  try {
    const feedData = await parser.parseURL(feed.url);
    const articles = feedData.items.slice(0, 10).map(item => {
      const published = item.isoDate ? new Date(item.isoDate) : null;
      return {
        title: item.title || "Bez názvu",
        link: item.link || "#",
        published: published ? published.toISOString() : null,
        age: published ? calculateTimeSince(published) : "?"
      };
    });

    return {
      source: feed.name,
      icon: feed.icon,
      articles
    };
  } catch (err) {
    return {
      source: feed.name,
      icon: feed.icon,
      articles: [
        { title: `Chyba při načítání zpráv: ${err.message}`, link: "#", published: null, age: "?" }
      ]
    };
  }
}

async function updateNewsCache() {
  const newCache = {};
  for (const feed of RSS_FEEDS) {
    newCache[feed.name] = await fetchNewsFromFeed(feed);
  }
  newsCache = newCache;
  lastUpdate = new Date();
}

export default async function handler(req, res) {
  if (!lastUpdate || (Date.now() - lastUpdate.getTime()) > 15 * 60 * 1000) {
    await updateNewsCache();
  }

  const formattedNews = Object.values(newsCache);
  res.status(200).json({
    news: formattedNews,
    last_update: lastUpdate ? lastUpdate.toISOString() : null
  });
}
