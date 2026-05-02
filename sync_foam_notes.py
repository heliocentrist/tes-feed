#!/usr/bin/env python3
"""Scan foam-notes ingested sources and add them to feed.json"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path

FEED_JSON = Path(__file__).parent / "feed.json"
FOAM_NOTES_SOURCES = Path("/home/claude/foam-notes/sources/ingested")

# Generic titles to skip when they're mixed with real author names
GENERIC_TITLES = {"Member of the Technical Staff", "Staff Writer", "Editor", "Contributor"}


def parse_yaml_frontmatter(text):
    """Extract YAML frontmatter from markdown text"""
    if not text.startswith("---"):
        return None
    
    end = text.find("---", 3)
    if end == -1:
        return None
    
    yaml_text = text[3:end].strip()
    data = {}
    current_key = None
    current_list = None
    
    for line in yaml_text.split("\n"):
        line = line.rstrip()
        if not line or line.startswith("#"):
            continue
        
        # Check if this is a list item
        list_match = re.match(r'^\s+-\s+(.*)$', line)
        if list_match:
            val = list_match.group(1).strip()
            if current_list is not None:
                current_list.append(val)
            continue
        else:
            # Save any accumulated list
            if current_key and current_list is not None:
                data[current_key] = current_list
                current_list = None
        
        # Simple key: value parsing
        match = re.match(r'^([a-zA-Z_][a-zA-Z0-9_]*):\s*(.*)$', line)
        if match:
            current_key, val = match.group(1), match.group(2).strip()
            
            if val == "":
                # Empty value - maybe start of a list
                data[current_key] = []
                current_list = []
            else:
                # Strip quotes
                if (val.startswith('"') and val.endswith('"')) or \
                   (val.startswith("'") and val.endswith("'")):
                    val = val[1:-1]
                
                data[current_key] = val
                current_list = None
    
    # Save final list if any
    if current_key and current_list is not None:
        data[current_key] = current_list
    
    return data


# Author roles/titles to strip (matched at end of string, spaces optional)
ROLE_PATTERNS = [
    r"Machine\s*Learning\s*Engineer",
    r"Software\s*Engineer",
    r"Research\s*Scientist",
    r"Member\s*of\s*the\s*Technical\s*Staff",
    r"Ph\.?D\.?",
    r"Dr\.?",
    r"MD",
    r"CEO",
    r"CTO",
    r"VP",
    r"Director",
    r"Manager",
    r"Lead",
    r"Senior",
    r"Junior",
    r"Staff",
    r"Principal",
    r"Fellow",
    r"Professor",
    r"Researcher",
    r"Analyst",
    r"Writer",
    r"Editor",
    r"Contributor",
]

def normalize_name(name):
    """Remove job titles from end of author names"""
    for pattern in ROLE_PATTERNS:
        # Match at end, with optional leading whitespace
        name = re.sub(rf"\s*{pattern}$", "", name, flags=re.IGNORECASE)
    return name.strip()


def extract_author(fm):
    """Extract author name(s) from frontmatter, strip wikilinks and roles"""
    author_field = fm.get("author", "")
    
    if isinstance(author_field, list):
        authors = [a.strip() for a in author_field]
    elif isinstance(author_field, str) and author_field:
        authors = [author_field.strip()]
    else:
        return ""
    
    cleaned = []
    for a in authors:
        # Strip outer quotes first (common artifact from yaml parsing)
        a = a.strip()
        if (a.startswith('"') and a.endswith('"')) or (a.startswith("'") and a.endswith("'")):
            a = a[1:-1]
        
        # Handle weird nested list artifacts like "(['jxnl'])"
        a = re.sub(r"\[+'", "", a)
        a = re.sub(r"'\]+", "", a)
        
        # Strip wikilinks
        a = re.sub(r"\[\[(.*?)\]\]", r"\1", a)  # [[Name]] -> Name
        a = re.sub(r"\[(.*?)\]\(.*?\)", r"\1", a)  # [Name](url) -> Name
        
        a = a.strip()
        
        # Strip roles
        a = normalize_name(a)
        
        # Clean up Twitter handles: @name -> name
        a = re.sub(r"^@", "", a)
        
        if a and a not in GENERIC_TITLES:
            cleaned.append(a)
    
    return ", ".join(cleaned) if cleaned else ""


def extract_description(fm, text):
    """Extract description from frontmatter or content"""
    # Get from frontmatter (handle both string and list)
    description = fm.get("description", "")
    if isinstance(description, list):
        description = " ".join(description)
    description = description.strip()
    
    if description and description != fm.get("title", ""):
        return description[:500]
    
    # Fallback: extract from content after frontmatter
    if text.startswith("---"):
        end = text.find("---", 3)
        if end != -1:
            text = text[end + 3:]
    
    for line in text.strip().split("\n"):
        line = line.strip()
        if line and not line.startswith("#") and not line.startswith("-"):
            plain = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', line)
            plain = re.sub(r'\*\*([^\*]+)\*\*', r'\1', plain)
            plain = re.sub(r'\*([^\*]+)\*', r'\1', plain)
            plain = re.sub(r'`([^`]+)`', r'\1', plain)
            return plain[:500]
    
    return ""


def parse_created_date(date_str):
    """Parse date from frontmatter, return datetime or None"""
    if not date_str:
        return None
    
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt.replace(tzinfo=timezone.utc)
    except ValueError:
        pass
    
    try:
        if "T" in date_str:
            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            return dt
    except ValueError:
        pass
    
    return None


def scan_foam_notes():
    """Scan foam-notes ingested sources and return feed items"""
    items = []
    
    if not FOAM_NOTES_SOURCES.exists():
        print(f"Foam notes sources directory not found: {FOAM_NOTES_SOURCES}")
        return items
    
    for md_file in FOAM_NOTES_SOURCES.rglob("*.md"):
        text = md_file.read_text(encoding="utf-8")
        fm = parse_yaml_frontmatter(text)
        
        if not fm:
            continue
        
        url = fm.get("source", "").strip()
        if not url or not url.startswith(("http://", "https://")):
            continue
        
        title = fm.get("title", "").strip()
        if not title:
            title = md_file.stem
        
        # Extract author
        author = extract_author(fm)
        
        # Parse date
        date_str = fm.get("created", "")
        dt = parse_created_date(date_str)
        if not dt:
            mtime = md_file.stat().st_mtime
            dt = datetime.fromtimestamp(mtime, tz=timezone.utc)
        
        date_rfc = dt.strftime("%a, %d %b %Y %H:%M:%S +0000")
        
        # Description
        description = extract_description(fm, text)
        
        items.append({
            "title": title,
            "url": url,
            "summary": description[:500],
            "date": date_rfc,
            "source": author if author else "",
            "auto": False
        })
    
    return items


def sync():
    data = json.loads(FEED_JSON.read_text())
    existing_urls = {item["url"] for item in data["items"]}
    new_count = 0
    
    foam_items = scan_foam_notes()
    print(f"Scanned foam-notes: found {len(foam_items)} sources with valid URLs")
    
    for item in foam_items:
        if item["url"] not in existing_urls:
            data["items"].append(item)
            existing_urls.add(item["url"])
            new_count += 1
            author_tag = f" ({item['source']})" if item['source'] else ""
            print(f"  + {item['title'][:60]}{author_tag}")
    
    if new_count > 0:
        FEED_JSON.write_text(json.dumps(data, indent=2, ensure_ascii=False))
        print(f"\nAdded {new_count} new items from foam-notes")
    else:
        print("\nNo new items from foam-notes")
    
    return new_count


if __name__ == "__main__":
    sync()
