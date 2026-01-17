#!/usr/bin/env python3
"""
Geopolitical Intelligence Curator
Final — two-file output (filter_feed.xml and filter_feed_overflow.xml), no cascade.
Rules enforced:
- Triple-run per batch (3 independent API calls)
- Keep articles selected in >=2 runs
- 61s delay between runs and between batch groups
- Exit immediately on any API/network/API format error
- No XML file contains more than MAX_FEED_ITEMS (100)
- First 100 -> filter_feed.xml; next up to 100 -> filter_feed_overflow.xml; extra beyond 200 dropped
"""

import os
import json
import requests
import time
import sys
import re
from xml.etree import ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

# ---------- CONFIG ----------
MAX_FEED_ITEMS = 100
URLS = [
    "https://evilgodfahim.github.io/gpd/daily_feed.xml",
    "https://evilgodfahim.github.io/daily/daily_master.xml",
"https://feeds.feedburner.com/TheAtlantic",
"https://time.com/feed/"
]
MODELS = [
    {
        "name": "gemini-3-flash",
        "display": "Gemini-2.5-Flash-Lite",
        "batch_size": 100,
        "api": "google"
    }
]
GOOGLE_API_KEY = os.environ.get("PO")
GOOGLE_API_URL = "https://generativelanguage.googleapis.com/v1beta/models"
SYSTEM_PROMPT = """You are a Geopolitical Intelligence Filter.
Return ONLY a JSON array of article IDs (integers) that are geopolitically significant.
No explanation, no text, JSON only."""
DEBUG = False

# ---------- HELPERS ----------
def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def write_feed_xml(data, filename):
    os.makedirs(os.path.dirname(filename) if os.path.dirname(filename) else ".", exist_ok=True)
    rss = ET.Element("rss", version="2.0")
    channel = ET.SubElement(rss, "channel")

    ET.SubElement(channel, "title").text = "Geopolitical Intelligence Feed"
    ET.SubElement(channel, "lastBuildDate").text = datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0600")
    ET.SubElement(channel, "link").text = "https://github.com/evilgodfahim"
    ET.SubElement(channel, "description").text = "AI-curated geopolitical news feed"

    if not data:
        item = ET.SubElement(channel, "item")
        ET.SubElement(item, "title").text = "End of Feed"
        ET.SubElement(item, "description").text = "No geopolitically significant articles found."
        ET.SubElement(item, "pubDate").text = datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0600")
    else:
        for art in data:
            item = ET.SubElement(channel, "item")
            ET.SubElement(item, "title").text = art.get('title', 'No Title')
            ET.SubElement(item, "link").text = art.get('link', '')
            ET.SubElement(item, "pubDate").text = art.get('pubDate', datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0000"))

            models_str = ", ".join(art.get('selected_by', ['Unknown']))
            category_info = art.get('category', 'Geopolitical')
            reason_info = art.get('reason', 'Geopolitically Significant')

            html_desc = f"<p><b>[{category_info}]</b></p>"
            html_desc += f"<p><i>{reason_info}</i></p>"
            html_desc += f"<p><small>Selected by: {models_str}</small></p>"
            html_desc += f"<hr/><p>{art.get('description','')}</p>"

            ET.SubElement(item, "description").text = html_desc

    tree = ET.ElementTree(rss)
    try:
        ET.indent(tree, space="  ", level=0)
    except Exception:
        pass
    tree.write(filename, encoding="utf-8", xml_declaration=True)
    print(f"   Saved {len(data)} items to {filename}", flush=True)

# ---------- FETCH ----------
def fetch_titles_only():
    all_articles = []
    seen_links = set()
    now = datetime.now(timezone.utc)
    cutoff_time = now - timedelta(hours=26)

    print(f"Time Filter: Articles after {cutoff_time.strftime('%Y-%m-%d %H:%M UTC')}", flush=True)
    headers = {'User-Agent': 'Geopolitical-Curator/1.0'}

    for url in URLS:
        print(f"Fetching: {url}", flush=True)
        try:
            r = requests.get(url, headers=headers, timeout=15)
            print(f"  Status: {r.status_code}", flush=True)
            if r.status_code != 200:
                print("  ❌ Failed to fetch feed", flush=True)
                continue

            try:
                root = ET.fromstring(r.content)
            except Exception as e:
                print(f"  ❌ XML Parse Error: {e}", flush=True)
                continue

            items = root.findall('.//item')
            print(f"  Found {len(items)} total items", flush=True)

            items_added = 0
            for item in items:
                pub_date = item.findtext('pubDate') or ""
                if not pub_date:
                    pub_date = datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0000")

                try:
                    dt = parsedate_to_datetime(pub_date)
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    else:
                        dt = dt.astimezone(timezone.utc)
                    if dt < cutoff_time:
                        continue
                except Exception:
                    pass

                link = item.findtext('link') or ""
                if not link:
                    guid = item.find('guid')
                    link = guid.text if guid is not None else ""

                if not link or link in seen_links:
                    continue

                title = (item.findtext('title') or "No Title").strip()
                desc_text = item.findtext('description') or title

                all_articles.append({
                    "id": len(all_articles),
                    "title": title,
                    "link": link,
                    "description": desc_text,
                    "pubDate": pub_date
                })
                seen_links.add(link)
                items_added += 1

            print(f"  ✅ Added {items_added} articles from this feed", flush=True)
        except Exception as e:
            print(f"  ❌ Error: {e}", flush=True)
            continue

    print(f"\nTotal Loaded: {len(all_articles)} unique headlines", flush=True)
    return all_articles

# ---------- MODEL PARSE ----------
def extract_json_from_text(text):
    try:
        return json.loads(text)
    except Exception:
        pass
    try:
        match = re.search(r'(\[[\s\d,]+\])', text, re.DOTALL)
        if match:
            return json.loads(match.group(1))
    except Exception:
        pass
    return None

def call_model(model_info, batch):
    prompt_list = [f"{a['id']}: {a['title']}" for a in batch]
    prompt_text = "\n".join(prompt_list)

    api_url = f"{GOOGLE_API_URL}/{model_info['name']}:generateContent?key={GOOGLE_API_KEY}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{
            "parts": [{
                "text": f"{SYSTEM_PROMPT}\n\n{prompt_text}"
            }]
        }],
        "generationConfig": {"temperature": 0.3}
    }

    try:
        response = requests.post(api_url, headers=headers, json=payload, timeout=90)
        if DEBUG:
            preview = response.text[:2000].replace("\n", " ")
            print(f"    [DEBUG] HTTP {response.status_code} body preview: {preview}", flush=True)

        if response.status_code == 200:
            try:
                response_data = response.json()
            except Exception as e:
                print(f"    [{model_info['display']}] Invalid JSON response: {e}", flush=True)
                sys.exit(1)

            if 'error' in response_data:
                print(f"    [{model_info['display']}] API Error: {response_data.get('error')}", flush=True)
                sys.exit(1)

            try:
                candidates = response_data.get('candidates') or response_data.get('outputs') or []
                if candidates:
                    content_text = candidates[0]['content']['parts'][0]['text'].strip()
                else:
                    content_text = response_data.get('content', '') or response_data.get('output', '')
            except Exception as e:
                print(f"    [{model_info['display']}] Response parse error: {e}", flush=True)
                sys.exit(1)

            if content_text.startswith("```"):
                content_text = content_text.replace("```json", "").replace("```", "").strip()

            parsed_data = extract_json_from_text(content_text)
            if parsed_data is not None and isinstance(parsed_data, list):
                return parsed_data
            else:
                print(f"    [{model_info['display']}] JSON parse error: model output not a JSON list", flush=True)
                if DEBUG:
                    print(f"    [DEBUG] Model output: {content_text}", flush=True)
                sys.exit(1)

        elif response.status_code == 429:
            print(f"    [{model_info['display']}] Rate Limit (429). Exiting.", flush=True)
            sys.exit(1)
        elif response.status_code >= 500:
            print(f"    [{model_info['display']}] Server Error {response.status_code}. Exiting.", flush=True)
            sys.exit(1)
        else:
            print(f"    [{model_info['display']}] HTTP Error {response.status_code}. Exiting.", flush=True)
            if DEBUG:
                print(f"    [DEBUG] HTTP body: {response.text[:1600]}", flush=True)
            sys.exit(1)

    except requests.exceptions.RequestException as e:
        print(f"    [{model_info['display']}] Network Error: {e}. Exiting.", flush=True)
        sys.exit(1)

    return []

# ---------- MAIN ----------
def main():
    print("=" * 60, flush=True)
    print("Geopolitical Intelligence Curator", flush=True)
    print("=" * 60, flush=True)

    if not GOOGLE_API_KEY:
        print("::error::PO environment variable is missing!", flush=True)
        sys.exit(1)

    articles = fetch_titles_only()
    if not articles:
        print("No articles found.", flush=True)
        write_feed_xml([], "filter_feed.xml")
        write_feed_xml([], "filter_feed_overflow.xml")
        return

    model_batches = {}
    for model_info in MODELS:
        bs = model_info['batch_size']
        model_batches[model_info['name']] = [articles[i:i + bs] for i in range(0, len(articles), bs)]

    max_batch_count = max(len(batches) for batches in model_batches.values())
    selections_map = {}

    print(f"\nProcessing {max_batch_count} Batch Groups...", flush=True)

    for batch_idx in range(max_batch_count):
        print(f"\n  Batch Group {batch_idx+1}...", flush=True)

        for model_info in MODELS:
            m_name = model_info['name']
            if batch_idx >= len(model_batches[m_name]):
                print(f"    Skipping {model_info['display']} (no batch)", flush=True)
                continue

            batch = model_batches[m_name][batch_idx]
            print(f"    Processing model {model_info['display']} batch {batch_idx+1} (size={len(batch)})", flush=True)

            for run_num in (1, 2, 3):
                print(f"    [{model_info['display']}] Run {run_num}/3 start at {now_str()}", flush=True)
                decisions = call_model(model_info, batch)

                if decisions:
                    print(f"      [{model_info['display']}] Run {run_num} selected {len(decisions)} articles", flush=True)
                    for aid in decisions:
                        if isinstance(aid, int) and 0 <= aid < len(articles):
                            if aid not in selections_map:
                                selections_map[aid] = {'runs': [], 'count': 0}
                            selections_map[aid]['runs'].append(f"Batch{batch_idx+1}-Run{run_num}")
                            selections_map[aid]['count'] += 1
                else:
                    print(f"      [{model_info['display']}] Run {run_num} returned no selections", flush=True)

                if run_num < 3:
                    print(f"      Waiting 61s before next run...", flush=True)
                    time.sleep(61)

        if batch_idx < max_batch_count - 1:
            print(f"  Waiting 61s before next batch group...", flush=True)
            time.sleep(61)

    # filter: selected in at least 2 runs
    final_articles = []
    for aid, info in selections_map.items():
        if info['count'] >= 2:
            original = articles[aid].copy()
            original['category'] = 'Geopolitical'
            original['reason'] = 'Geopolitically Significant'
            original['selected_by'] = info['runs']
            original['selection_count'] = info['count']
            final_articles.append(original)

    print(f"\n{'='*60}", flush=True)
    print(f"FILTERING: Minimum 2 selections required (out of 3 runs per batch)...", flush=True)
    print(f"{'='*60}", flush=True)
    print(f"   ✅ {len(final_articles)} articles selected 2+ times", flush=True)
    print(f"\nRESULTS:", flush=True)
    print(f"   Analyzed: {len(articles)} headlines", flush=True)
    print(f"   Selected: {len(final_articles)} geopolitically significant articles", flush=True)

    # Split into primary and single overflow (no cascade). Drop extras beyond 2*MAX_FEED_ITEMS.
    primary = final_articles[:MAX_FEED_ITEMS]
    overflow = final_articles[MAX_FEED_ITEMS:MAX_FEED_ITEMS * 2]

    write_feed_xml(primary, "filter_feed.xml")
    write_feed_xml(overflow, "filter_feed_overflow.xml")

if __name__ == "__main__":
    main()