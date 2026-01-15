import os
import json
import requests
import time
import sys
import re
from xml.etree import ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

# --- Configuration ---
MAX_FEED_ITEMS = 100

URLS = [
    "https://evilgodfahim.github.io/gpd/daily_feed.xml",
    "https://evilgodfahim.github.io/daily/daily_master.xml"
]

MODELS = [
    {
        "name": "gemini-2.5-flash-lite",
        "display": "Gemini-2.5-Flash-Lite",
        "batch_size": 100,
        "api": "google"
    }
]

# API Key and URL
GOOGLE_API_KEY = os.environ.get("PO")
GOOGLE_API_URL = "https://generativelanguage.googleapis.com/v1beta/models"

# --- SYSTEM PROMPT ---
SYSTEM_PROMPT = """You are a Geopolitical Intelligence Filter.
Your singular task is to identify headlines with significant geopolitical implications.

GEOPOLITICAL SIGNIFICANCE CRITERIA:
Select ONLY headlines that meet these standards:

1. INTERSTATE RELATIONS & POWER DYNAMICS
- Diplomatic initiatives, alliances, treaties, or major bilateral/multilateral agreements
- Strategic partnerships or deteriorating relations between nations
- Summit meetings, state visits, or high-level diplomatic engagements with substantive outcomes
- International sanctions, embargoes, or trade restrictions with political motivations

2. MILITARY & SECURITY DEVELOPMENTS
- Military operations, deployments, or strategic repositioning
- Defense agreements, arms sales, or military cooperation pacts
- Security threats, terrorism, or insurgencies with cross-border implications
- Nuclear proliferation, weapons programs, or strategic deterrence developments

3. REGIONAL STABILITY & CONFLICT
- Armed conflicts, civil wars, or insurgencies affecting regional balance
- Peace negotiations, ceasefires, or conflict resolution efforts
- Territorial disputes or sovereignty challenges
- Refugee crises or mass migrations with geopolitical consequences

4. GLOBAL GOVERNANCE & INSTITUTIONS
- UN Security Council actions, resolutions, or vetoes
- Major decisions by international organizations (NATO, EU, ASEAN, AU, etc.)
- International law developments, tribunals, or sanctions regimes
- Global coordination on transnational issues (pandemics, climate with geopolitical angle)

5. STRATEGIC RESOURCES & ECONOMIC STATECRAFT
- Energy security developments (pipelines, sanctions, OPEC decisions)
- Critical infrastructure or supply chain shifts with strategic implications
- Economic coercion, debt diplomacy, or geoeconomic competition
- Trade wars, tariffs, or economic blocs with clear political objectives

6. GREAT POWER COMPETITION
- US-China-Russia strategic rivalry developments
- Belt and Road Initiative or competing infrastructure projects
- Technology competition with national security implications (semiconductors, AI, 5G)
- Space programs or cyber operations with strategic significance

7. REGIME CHANGE & POLITICAL TRANSITIONS
- Coups, revolutions, or major political upheavals
- Elections in strategically important nations with geopolitical consequences
- Leadership transitions in major powers or pivotal regional states
- Authoritarian consolidation or democratic backsliding with regional impact

AUTOMATIC EXCLUSIONS:
NEVER select:
- Domestic politics without clear international ramifications
- Economic news unless it involves geoeconomic statecraft
- Crime, accidents, natural disasters (unless triggering international response)
- Cultural, sports, or entertainment content
- Technology or business news (unless strategic/security dimension)
- Individual scandals or personalities (unless affecting state power)
- Social issues, protests, or movements (unless threatening regime stability or borders)

DECISION TEST:
For each headline, ask:
"Does this directly affect the balance of power between nations, regional stability, or strategic interests of major powers?"
- YES → SELECT
- NO or UNCLEAR → SKIP

OUTPUT FORMAT:
Return ONLY a JSON array of selected article IDs.
Example: [0, 5, 12, 23]
No markdown. No commentary. No explanation."""

def save_xml(data, filename, error_message=None):
    os.makedirs(os.path.dirname(filename) if os.path.dirname(filename) else ".", exist_ok=True)

    rss = ET.Element("rss", version="2.0")
    channel = ET.SubElement(rss, "channel")

    ET.SubElement(channel, "title").text = "Geopolitical Intelligence Feed"
    ET.SubElement(channel, "lastBuildDate").text = datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0600")
    ET.SubElement(channel, "link").text = "https://github.com/evilgodfahim"
    ET.SubElement(channel, "description").text = "AI-curated geopolitical news feed"

    if error_message:
        item = ET.SubElement(channel, "item")
        ET.SubElement(item, "title").text = "System Error"
        ET.SubElement(item, "description").text = f"Script failed: {error_message}"
        ET.SubElement(item, "pubDate").text = datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0600")
    elif not data:
        item = ET.SubElement(channel, "item")
        ET.SubElement(item, "title").text = "End of Feed"
        ET.SubElement(item, "description").text = "No geopolitically significant articles found."
        ET.SubElement(item, "pubDate").text = datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0600")
    else:
        for art in data:
            item = ET.SubElement(channel, "item")
            ET.SubElement(item, "title").text = art['title']
            ET.SubElement(item, "link").text = art['link']
            ET.SubElement(item, "pubDate").text = art['pubDate']

            models_str = ", ".join(art.get('selected_by', ['Unknown']))
            category_info = art.get('category', 'Geopolitical')
            reason_info = art.get('reason', 'Geopolitically Significant')

            html_desc = f"<p><b>[{category_info}]</b></p>"
            html_desc += f"<p><i>{reason_info}</i></p>"
            html_desc += f"<p><small>Selected by: {models_str}</small></p>"
            html_desc += f"<hr/><p>{art['description']}</p>"

            ET.SubElement(item, "description").text = html_desc

    try:
        tree = ET.ElementTree(rss)
        ET.indent(tree, space="  ", level=0)
        tree.write(filename, encoding="utf-8", xml_declaration=True)
        print(f"   Saved {len(data) if data else 0} items to {filename}", flush=True)
    except Exception as e:
        print(f"::error::Failed to write XML {filename}: {e}", flush=True)

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
                print(f"  ❌ Failed to fetch feed", flush=True)
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
                pub_date = item.find('pubDate').text if item.find('pubDate') is not None else ""
                
                if not pub_date:
                    # If no pubDate, include it anyway
                    pub_date = datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0000")

                # Try to parse date, but don't skip if it fails
                try:
                    dt = parsedate_to_datetime(pub_date)
                    if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
                    else: dt = dt.astimezone(timezone.utc)
                    if dt < cutoff_time: continue
                except:
                    pass  # Include articles with unparseable dates

                link = item.find('link').text or ""
                if not link:
                    guid = item.find('guid')
                    link = guid.text if guid is not None else ""

                if not link or link in seen_links: continue

                title = item.find('title').text or "No Title"
                title = title.strip()
                seen_links.add(link)

                desc = item.find('description')
                desc_text = desc.text if desc is not None else ""

                all_articles.append({
                    "id": len(all_articles),
                    "title": title,
                    "link": link,
                    "description": desc_text or title,
                    "pubDate": pub_date
                })
                items_added += 1
                
            print(f"  ✅ Added {items_added} articles from this feed", flush=True)
            
        except Exception as e:
            print(f"  ❌ Error: {e}", flush=True)
            continue

    print(f"\nTotal Loaded: {len(all_articles)} unique headlines", flush=True)
    return all_articles

def extract_json_from_text(text):
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    try:
        match = re.search(r'(\[[\d,\s]*\])', text, re.DOTALL)
        if match:
            return json.loads(match.group(1))
    except json.JSONDecodeError:
        pass
    return None

def call_model(model_info, batch):
    prompt_list = [f"{a['id']}: {a['title']}" for a in batch]
    prompt_text = "\n".join(prompt_list)

    api_url = f"{GOOGLE_API_URL}/{model_info['name']}:generateContent?key={GOOGLE_API_KEY}"
    headers = {
        "Content-Type": "application/json"
    }
    payload = {
        "contents": [{
            "parts": [{
                "text": f"{SYSTEM_PROMPT}\n\n{prompt_text}"
            }]
        }],
        "generationConfig": {
            "temperature": 0.3
        }
    }

    try:
        response = requests.post(api_url, headers=headers, json=payload, timeout=90)

        if response.status_code == 200:
            try:
                response_data = response.json()

                if 'error' in response_data:
                    print(f"    [{model_info['display']}] API Error: {response_data.get('error', 'Unknown error')}", flush=True)
                    sys.exit(1)

                content = response_data['candidates'][0]['content']['parts'][0]['text'].strip()

            except (KeyError, IndexError) as e:
                print(f"    [{model_info['display']}] Response parse error: {e}", flush=True)
                sys.exit(1)

            if content.startswith("```"):
                content = content.replace("```json", "").replace("```", "").strip()

            parsed_data = extract_json_from_text(content)
            if parsed_data is not None and isinstance(parsed_data, list):
                return parsed_data
            else:
                print(f"    [{model_info['display']}] JSON parse error", flush=True)
                sys.exit(1)

        elif response.status_code == 429:
            print(f"    [{model_info['display']}] Rate Limit (429). Exiting.", flush=True)
            sys.exit(1)

        elif response.status_code >= 500:
            print(f"    [{model_info['display']}] Server Error {response.status_code}. Exiting.", flush=True)
            sys.exit(1)

        else:
            print(f"    [{model_info['display']}] HTTP Error {response.status_code}. Exiting.", flush=True)
            sys.exit(1)

    except requests.exceptions.RequestException as e:
        print(f"    [{model_info['display']}] Network Error: {e}. Exiting.", flush=True)
        sys.exit(1)

    return []

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
        save_xml([], "geopolitical_feed.xml")
        return

    model_batches = {}
    for model_info in MODELS:
        bs = model_info['batch_size']
        model_batches[model_info['name']] = [articles[i:i + bs] for i in range(0, len(articles), bs)]

    max_batch_count = max(len(batches) for batches in model_batches.values())
    selections_map = {}

    print(f"\nProcessing {max_batch_count} Batch Groups...", flush=True)

    for batch_idx in range(max_batch_count):
        print(f"  Batch Group {batch_idx+1}...", flush=True)

        for model_info in MODELS:
            m_name = model_info['name']
            if batch_idx >= len(model_batches[m_name]): continue

            decisions = call_model(model_info, model_batches[m_name][batch_idx])

            if decisions:
                print(f"    [{model_info['display']}] Selected {len(decisions)} articles", flush=True)
                for aid in decisions:
                    if isinstance(aid, int) and aid < len(articles):
                        if aid not in selections_map:
                            selections_map[aid] = {'models': [], 'count': 0}
                        selections_map[aid]['models'].append(model_info['display'])
                        selections_map[aid]['count'] += 1
            else:
                print(f"    [{model_info['display']}] No selections", flush=True)

            time.sleep(20)

        time.sleep(61)

    final_articles = []
    print(f"\n{'='*60}", flush=True)
    print(f"FILTERING: Minimum 2 selections required (out of 3 runs per batch)...", flush=True)
    print(f"{'='*60}", flush=True)
    
    for aid, info in selections_map.items():
        if info['count'] >= 2:  # Must be selected at least 2 times out of 3 runs
            original = articles[aid].copy()
            original['category'] = 'Geopolitical'
            original['reason'] = 'Geopolitically Significant'
            original['selected_by'] = info['runs']
            original['selection_count'] = info['count']
            final_articles.append(original)

    print(f"   ✅ {len(final_articles)} articles selected 2+ times from {len(selections_map)} total selections", flush=True)

    print(f"\nRESULTS:", flush=True)
    print(f"   Analyzed: {len(articles)} headlines", flush=True)
    print(f"   Selected: {len(final_articles)} geopolitically significant articles", flush=True)

    save_xml(final_articles[:MAX_FEED_ITEMS], "geopolitical_feed.xml")

if __name__ == "__main__":
    main()