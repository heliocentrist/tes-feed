#!/usr/bin/env python3
"""Generate RSS XML from feed.json"""

import json
import html
from datetime import datetime, timezone
from pathlib import Path

FEED_JSON = Path(__file__).parent / "feed.json"
OUTPUT_XML = Path(__file__).parent / "public" / "feed.xml"
OUTPUT_INDEX = Path(__file__).parent / "public" / "index.html"

def escape(s):
    return html.escape(str(s)) if s else ""

def generate_rss(data):
    items_xml = []
    # Sort by date, newest first
    sorted_items = sorted(data["items"], key=lambda x: x.get("date", ""), reverse=True)
    
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
    sorted_items = sorted(data["items"], key=lambda x: x.get("date", ""), reverse=True)
    
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
    
    subs_count = len(data.get("subscriptions", []))
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
  font-family: 'Courier New', monospace;
  background: #0a0a0a; color: #e0e0e0;
  max-width: 700px; margin: 0 auto; padding: 24px 16px;
}}
header {{ margin-bottom: 40px; border-bottom: 1px solid #222; padding-bottom: 20px; }}
h1 {{ font-size: 20px; color: #fff; letter-spacing: 2px; text-transform: uppercase; margin-bottom: 8px; }}
header p {{ font-size: 13px; color: #666; }}
header .rss-link {{ color: #f90; font-size: 12px; text-decoration: none; }}
header .rss-link:hover {{ text-decoration: underline; }}
header .stats {{ font-size: 11px; color: #444; margin-top: 8px; }}
article {{ padding: 16px 0; border-bottom: 1px solid #151515; }}
article:hover {{ background: #0f0f0f; margin: 0 -8px; padding: 16px 8px; border-radius: 4px; }}
.meta {{ font-size: 11px; color: #555; margin-bottom: 6px; text-transform: uppercase; letter-spacing: 1px; }}
.source {{ color: #666; margin-left: 8px; }}
h2 {{ font-size: 15px; font-weight: normal; line-height: 1.4; }}
h2 a {{ color: #ccc; text-decoration: none; }}
h2 a:hover {{ color: #fff; }}
.summary {{ font-size: 13px; color: #555; margin-top: 6px; line-height: 1.5; }}
</style>
</head>
<body>
<header>
  <h1>{escape(data.get('title', 'Reading List'))}</h1>
  <p>{escape(data.get('description', ''))}</p>
  <a class="rss-link" href="/feed.xml">RSS Feed</a>
  <div class="stats">{items_count} articles · {subs_count} subscriptions</div>
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
