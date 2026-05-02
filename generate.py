#!/usr/bin/env python3
"""Generate RSS XML from feed.json"""

import json
import html
from datetime import datetime, timezone
from pathlib import Path
from email.utils import parsedate_to_datetime


def parse_date(date_str):
    """Parse various date formats into datetime, return epoch 0 on failure"""
    if not date_str:
        return datetime(1970, 1, 1, tzinfo=timezone.utc)
    try:
        return parsedate_to_datetime(date_str)
    except Exception:
        pass
    for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(date_str, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except Exception:
            continue
    return datetime(1970, 1, 1, tzinfo=timezone.utc)

FEED_JSON = Path(__file__).parent / "feed.json"
OUTPUT_XML = Path(__file__).parent / "public" / "feed.xml"
OUTPUT_INDEX = Path(__file__).parent / "public" / "index.html"

def escape(s):
    return html.escape(str(s)) if s else ""

def generate_rss(data):
    items_xml = []
    # Sort by date, newest first
    sorted_items = sorted(data["items"], key=lambda x: parse_date(x.get("date", "")), reverse=True)

    for item in sorted_items[:200]:  # Cap at 200 items
        desc = item.get("summary", item.get("description", ""))
        source = item.get("source", "")
        source_tag = f"<source>{escape(source)}</source>" if source else ""

        items_xml.append(f"""    <item>
      <title>{escape(item.get('title', 'Untitled'))}</title>
      <link>{escape(item.get('url', ''))}</link>
      <description><![CDATA[{desc}]]></description>
      <pubDate>{item.get('date', '')}</pubDate>
      <guid isPermaLink="true">{escape(item.get('url', ''))}</guid>
      {source_tag}
    </item>""")

    now = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>{escape(data.get('title', 'Reading List'))}</title>
    <link>{escape(data.get('siteUrl', ''))}</link>
    <description>{escape(data.get('description', ''))}</description>
    <lastBuildDate>{now}</lastBuildDate>
    <atom:link href="{escape(data.get('siteUrl', ''))}/feed.xml" rel="self" type="application/rss+xml"/>
{chr(10).join(items_xml)}
  </channel>
</rss>"""

def generate_html(data):
    sorted_items = sorted(data["items"], key=lambda x: parse_date(x.get("date", "")), reverse=True)

    items_html = []
    for item in sorted_items[:200]:
        title = escape(item.get("title", "Untitled"))
        url = escape(item.get("url", ""))
        summary = item.get("summary", "")
        date = item.get("date", "")
        source = escape(item.get("source", ""))

        # Parse and format date
        try:
            dt = datetime.strptime(date, "%a, %d %b %Y %H:%M:%S %z")
            date_display = dt.strftime("%b %d, %Y")
        except:
            date_display = date[:10] if date else ""

        source_html = f'<span class="source">{source}</span>' if source else ""
        summary_html = f'<p class="summary">{escape(summary[:300])}</p>' if summary else ""

        items_html.append(f"""
      <article>
        <div class="meta">{date_display} {source_html}</div>
        <h2><a href="{url}" target="_blank" rel="noopener">{title}</a></h2>
        {summary_html}
      </article>""")

    # Removed: subscriptions no longer used
    items_count = len(data.get("items", []))

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{escape(data.get('title', 'Reading List'))}</title>
<link rel="alternate" type="application/rss+xml" title="{escape(data.get('title', ''))}" href="/feed.xml">
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: #fafafa; color: #1a1a1a;
  max-width: 720px; margin: 0 auto; padding: 24px 16px;
  line-height: 1.6;
}}
header {{ margin-bottom: 32px; padding-bottom: 20px; }}
h1 {{ font-size: 28px; font-weight: 600; color: #1a1a1a; margin-bottom: 6px; }}
header p {{ font-size: 15px; color: #555; margin-bottom: 16px; }}
header .rss-link {{
  display: inline-block; padding: 6px 16px;
  background: #2a2a2a; color: #fff;
  font-size: 13px; border-radius: 6px;
  text-decoration: none; letter-spacing: 0.5px;
}}
header .rss-link:hover {{ background: #444; }}
header .stats {{ font-size: 13px; color: #888; margin-top: 12px; }}
article {{
  padding: 20px 0 24px;
  border-bottom: 1px solid #e8e8e8;
  transition: background 0.15s;
}}
article:hover {{ background: #f5f5f5; margin: 0 -12px; padding: 20px 12px 24px; border-radius: 8px; }}
.meta {{ font-size: 12px; color: #888; margin-bottom: 6px; }}
.meta .source {{ color: #555; font-weight: 500; }}
h2 {{ font-size: 17px; font-weight: 500; line-height: 1.45; }}
h2 a {{ color: #1a1a1a; text-decoration: none; }}
h2 a:hover {{ color: #0066cc; }}
.summary {{ font-size: 14px; color: #555; margin-top: 8px; line-height: 1.6; }}
</style>
</head>
<body>
<header>
  <h1>{escape(data.get('title', 'Reading List'))}</h1>
  <p>{escape(data.get('description', ''))}</p>
  <a class="rss-link" href="/feed.xml">RSS Feed</a>
  <div class="stats">{items_count} articles</div>
</header>
<main>
{''.join(items_html)}
</main>
</body>
</html>"""

def main():
    data = json.loads(FEED_JSON.read_text())

    OUTPUT_XML.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_XML.write_text(generate_rss(data))
    OUTPUT_INDEX.write_text(generate_html(data))

    print(f"Generated feed.xml ({len(data['items'])} items) and index.html")

if __name__ == "__main__":
    main()
