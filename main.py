import os
import json
import requests
import time
import sys
from xml.etree import ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

# --- Configuration ---
URLS = [
    "https://evilgodfahim.github.io/sci/daily_feed.xml",
    "https://evilgodfahim.github.io/fp/final.xml",
    "https://evilgodfahim.github.io/bdl/final.xml",
    "https://evilgodfahim.github.io/int/final.xml",
    "https://evilgodfahim.github.io/gpd/daily_feed.xml",
    "https://evilgodfahim.github.io/daily/daily_master.xml",
    "https://evilgodfahim.github.io/bdit/daily_feed_2.xml",
    "https://evilgodfahim.github.io/bdit/daily_feed.xml",
    "https://evilgodfahim.github.io/edit/daily_feed.xml",
"https://evilgodfahim.github.io/bint/final.xml",
"https://evilgodfahim.github.io/bdlb/final.xml",
"https://evilgodfahim.github.io/bint/final_extra.xml"  
]

# Groq Configuration - 3 Model Ensemble
MODELS = [
    {"name": "llama-3.3-70b-versatile", "display": "Llama-3.3-70B"},
    {"name": "qwen/qwen3-32b", "display": "Qwen-3-32B"},
    {"name": "openai/gpt-oss-120b", "display": "GPT-OSS-120B"}
]
GROQ_API_KEY = os.environ["GEM"]
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

SYSTEM_PROMPT = """You are a Chief Information Filter.
Your task is to select headlines with structural and lasting significance.
You do not evaluate importance by popularity, novelty, or emotion.
You evaluate how information explains or alters systems.
Judgment must rely only on linguistic structure, implied scope, and systemic consequence.
TWO INFORMATION TYPES (internal use)
STRUCTURAL
— Explains how power, institutions, economies, or long-term social/strategic forces operate or change.
EPISODIC
— Describes isolated events, individual actions, or short-lived situations without system impact.
Select only STRUCTURAL.
FOUR STRUCTURAL LENSES (exclusive)
GOVERNANCE & CONTROL
Rules, enforcement, institutional balance, authority transfer, administrative or judicial change.
ECONOMIC & RESOURCE FLOWS
Capital movement, trade structure, production capacity, fiscal or monetary direction, systemic risk.
POWER RELATIONS & STRATEGY
Strategic alignment, coercion, deterrence, security posture, long-term rivalry or cooperation.
IDEAS, ARGUMENTS & LONG-TERM TRENDS
Editorial reasoning, policy debate, scientific or technological trajectories, demographic or climate forces.
CONTEXTUAL GRAVITY RULE (KEY)
When two or more headlines show equal structural strength, favor the one that:
• Operates closer to the decision-making center of a society
• Directly affects national policy formation or institutional practice
• Originates from internal analytical or editorial discourse, not external observation
This rule applies universally, regardless of language or country.
SINGLE DECISION TEST (mandatory)
Ask only:
"Does this headline clarify how a system functions or how its future direction is being shaped, in a way that remains relevant after time passes?"
• Yes or plausibly yes → SELECT
• No → SKIP
No secondary tests.
AUTOMATIC EXCLUSIONS
Skip always: • Crime, accidents, or scandals without institutional consequence
• Sports, entertainment, lifestyle
• Personal narratives without systemic implication
• Repetition of already-settled facts
OUTPUT SPEC (strict)
Return only a JSON array.
Each item must contain exactly: id
category (one of the four lenses)
reason (one concise sentence explaining the structural significance)
No markdown.
No commentary.
No text outside JSON.
Start with [ and end with ]."""

def save_xml(data, error_message=None):
    filename = "filtered_feed.xml"
    
    os.makedirs(os.path.dirname(filename) if os.path.dirname(filename) else ".", exist_ok=True)
    
    rss = ET.Element("rss", version="2.0")
    channel = ET.SubElement(rss, "channel")
    ET.SubElement(channel, "title").text = "Elite News Feed - 3-Model Ensemble"
    ET.SubElement(channel, "lastBuildDate").text = datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0600")
    ET.SubElement(channel, "link").text = "https://github.com/evilgodfahim"
    ET.SubElement(channel, "description").text = "AI-curated feed using Llama, Qwen, and GPT ensemble"

    if error_message:
        item = ET.SubElement(channel, "item")
        ET.SubElement(item, "title").text = "System Error"
        ET.SubElement(item, "description").text = f"Script failed: {error_message}"
        ET.SubElement(item, "pubDate").text = datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0600")
        ET.SubElement(item, "link").text = "https://github.com/evilgodfahim"
    
    elif not data:
        item = ET.SubElement(channel, "item")
        ET.SubElement(item, "title").text = "System Running - No Priority News Today"
        ET.SubElement(item, "description").text = "Curation system working. No structurally significant articles found in the last 26 hours."
        ET.SubElement(item, "pubDate").text = datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0600")
        ET.SubElement(item, "link").text = "https://github.com/evilgodfahim"
        
    else:
        for art in data:
            item = ET.SubElement(channel, "item")
            ET.SubElement(item, "title").text = art['title']
            ET.SubElement(item, "link").text = art['link']
            ET.SubElement(item, "pubDate").text = art['pubDate']
            
            # Build description with model attribution
            models_str = ", ".join(art.get('selected_by', ['Unknown']))
            category_info = art.get('category', 'News')
            reason_info = art.get('reason', 'Selected')
            
            html_desc = f"<p><b>[{category_info}]</b></p>"
            html_desc += f"<p><i>{reason_info}</i></p>"
            html_desc += f"<p><small>Selected by: {models_str}</small></p>"
            html_desc += f"<hr/><p>{art['description']}</p>"
            
            ET.SubElement(item, "description").text = html_desc

    try:
        tree = ET.ElementTree(rss)
        ET.indent(tree, space="  ", level=0)
        tree.write(filename, encoding="utf-8", xml_declaration=True)
        print(f"\nSuccessfully saved {len(data) if data else 0} priority items to {filename}", flush=True)
        
        if os.path.exists(filename):
            file_size = os.path.getsize(filename)
            print(f"File created: {filename} ({file_size} bytes)", flush=True)
            
    except Exception as e:
        print(f"::error::Failed to write XML: {e}", flush=True)
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write('<?xml version="1.0" encoding="utf-8"?>\n')
                f.write('<rss version="2.0"><channel>')
                f.write('<title>Elite News Feed - Ensemble</title>')
                f.write('<link>https://github.com/evilgodfahim</link>')
                f.write('<description>Emergency fallback feed</description>')
                f.write('<item><title>System Initialization</title>')
                f.write('<description>Feed initializing. Check back shortly.</description>')
                f.write(f'<pubDate>{datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0600")}</pubDate>')
                f.write('</item></channel></rss>')
            print(f"Created fallback XML", flush=True)
        except:
            pass

def fetch_titles_only():
    all_articles = []
    seen_links = set()
    seen_titles = set()
    now = datetime.now(timezone.utc)
    cutoff_time = now - timedelta(hours=26)
    
    print(f"Time Filter: Articles after {cutoff_time.strftime('%Y-%m-%d %H:%M UTC')}", flush=True)
    headers = {'User-Agent': 'BCS-Curator/3.0-Ensemble'}

    for url in URLS:
        try:
            r = requests.get(url, headers=headers, timeout=8)
            if r.status_code != 200: 
                continue
            
            try:
                root = ET.fromstring(r.content)
            except: 
                continue

            for item in root.findall('.//item'):
                pub_date = item.find('pubDate').text if item.find('pubDate') is not None else ""
                if not pub_date: 
                    continue
                
                try:
                    dt = parsedate_to_datetime(pub_date)
                    if dt.tzinfo is None: 
                        dt = dt.replace(tzinfo=timezone.utc)
                    else: 
                        dt = dt.astimezone(timezone.utc)
                    if dt < cutoff_time: 
                        continue
                except: 
                    continue

                link = item.find('link').text or ""
                if not link or link in seen_links: 
                    continue
                
                title = item.find('title').text or "No Title"
                title = title.strip()
                
                title_normalized = title.lower().strip()
                if title_normalized in seen_titles:
                    continue
                
                seen_links.add(link)
                seen_titles.add(title_normalized)
                
                desc = item.find('description')
                desc_text = desc.text if desc is not None else ""

                all_articles.append({
                    "id": len(all_articles),
                    "title": title,
                    "link": link,
                    "description": desc_text or title,
                    "pubDate": pub_date
                })

        except Exception:
            continue

    print(f"Loaded {len(all_articles)} unique headlines (deduped)", flush=True)
    return all_articles

def call_model(model_info, batch):
    prompt_list = [f"{a['id']}: {a['title']}" for a in batch]
    prompt_text = "\n".join(prompt_list)

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": model_info["name"],
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt_text}
        ],
        "temperature": 0.3,
        "max_tokens": 3000
    }

    try:
        response = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content'].strip()
            
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()
            
            try:
                parsed = json.loads(content)
                
                if isinstance(parsed, dict):
                    if 'error' in parsed:
                        print(f"    [{model_info['display']}] Model returned error", flush=True)
                        return []
                    
                    for key in ['selections', 'articles', 'results', 'selected', 'data']:
                        if key in parsed and isinstance(parsed[key], list):
                            return parsed[key]
                    
                    return []
                    
                elif isinstance(parsed, list):
                    return parsed
                else:
                    return []
                    
            except json.JSONDecodeError:
                print(f"    [{model_info['display']}] JSON parse error", flush=True)
                return []
        
        elif response.status_code == 429:
            print(f"    [{model_info['display']}] Rate limit (429)", flush=True)
            return []
        
        elif response.status_code >= 500:
            print(f"    [{model_info['display']}] Server Error {response.status_code}", flush=True)
            return []
        
        else:
            print(f"    [{model_info['display']}] API Error {response.status_code}", flush=True)
            return []

    except requests.exceptions.Timeout:
        print(f"    [{model_info['display']}] Timeout", flush=True)
        return []
        
    except Exception as e:
        print(f"    [{model_info['display']}] Error: {str(e)[:60]}", flush=True)
        return []

def main():
    print("=" * 70, flush=True)
    print("Elite News Curator - 3-Model Ensemble", flush=True)
    print("Models: Llama-3.3-70B | Qwen-3-32B | GPT-OSS-120B", flush=True)
    print("=" * 70, flush=True)
    
    if not os.path.exists("filtered_feed.xml"):
        print("First run detected - creating initial XML file...", flush=True)
        save_xml([], error_message=None)
    
    try:
        articles = fetch_titles_only()
        
        if not articles:
            print("No articles found in source feeds", flush=True)
            save_xml([])
            print("\nScript completed successfully (no articles to process)", flush=True)
            return

        BATCH_SIZE = 150
        batches = [articles[i:i + BATCH_SIZE] for i in range(0, len(articles), BATCH_SIZE)]
        
        MAX_BATCHES = 10
        if len(batches) > MAX_BATCHES:
            print(f"Found {len(batches)} batches, limiting to {MAX_BATCHES}", flush=True)
            batches = batches[:MAX_BATCHES]
            articles_to_process = articles[:MAX_BATCHES * BATCH_SIZE]
        else:
            articles_to_process = articles
        
        # Dictionary to track selections: {article_id: {models: [], decisions: []}}
        selections_map = {}
        
        print(f"\nProcessing {len(batches)} batches (size={BATCH_SIZE}) with 3-model ensemble...", flush=True)
        print(f"Strategy: Union - keep all unique selections from any model\n", flush=True)

        batches_processed = 0
        
        for i, batch in enumerate(batches):
            print(f"  Batch {i+1}/{len(batches)} ({len(batch)} articles)...", flush=True)
            
            # Call all 3 models
            for model_info in MODELS:
                print(f"    [{model_info['display']}] Processing...", flush=True)
                decisions = call_model(model_info, batch)
                print(f"    [{model_info['display']}] Selected {len(decisions)} articles", flush=True)
                
                # Store decisions
                for d in decisions:
                    article_id = d.get('id')
                    if article_id not in selections_map:
                        selections_map[article_id] = {
                            'models': [],
                            'decisions': []
                        }
                    selections_map[article_id]['models'].append(model_info['display'])
                    selections_map[article_id]['decisions'].append(d)
                
                # Small delay between models
                time.sleep(2)
            
            batches_processed += 1
            
            # Delay between batches
            if i < len(batches) - 1:
                print(f"    Waiting 5 seconds before next batch...", flush=True)
                time.sleep(5)

        # Build final article list with deduplication
        final_articles = []
        seen_links = set()
        seen_titles = set()
        
        print(f"\nMerging selections from all models...", flush=True)
        
        for article_id, selection_info in selections_map.items():
            # Find original article
            original = next((x for x in articles_to_process if x["id"] == article_id), None)
            if not original:
                continue
            
            # Deduplicate
            link = original['link']
            title_normalized = original['title'].lower().strip()
            
            if link in seen_links or title_normalized in seen_titles:
                continue
            
            seen_links.add(link)
            seen_titles.add(title_normalized)
            
            # Use first model's decision for category/reason, but track all models
            first_decision = selection_info['decisions'][0]
            
            original['category'] = first_decision.get('category', 'Priority')
            original['reason'] = first_decision.get('reason', 'Structural significance')
            original['selected_by'] = selection_info['models']
            
            final_articles.append(original)
        
        # Statistics
        total_selections = len(selections_map)
        unique_articles = len(final_articles)
        duplicates_removed = total_selections - unique_articles
        selection_rate = (unique_articles * 100 // len(articles_to_process)) if articles_to_process else 0
        
        # Model agreement statistics
        model_counts = {}
        for art in final_articles:
            count = len(art['selected_by'])
            model_counts[count] = model_counts.get(count, 0) + 1
        
        print(f"\nRESULTS:", flush=True)
        print(f"   Total articles available: {len(articles)}", flush=True)
        print(f"   Articles analyzed: {len(articles_to_process)}", flush=True)
        print(f"   Total selections (all models): {total_selections}", flush=True)
        print(f"   Unique articles selected: {unique_articles} ({selection_rate}% of analyzed)", flush=True)
        if duplicates_removed > 0:
            print(f"   Duplicates removed: {duplicates_removed}", flush=True)
        
        print(f"\n   Model Agreement:", flush=True)
        for count in sorted(model_counts.keys(), reverse=True):
            print(f"      {count} model(s): {model_counts[count]} articles", flush=True)
        
        print(f"\n   Batches processed: {batches_processed}/{MAX_BATCHES}", flush=True)
        print(f"   Total API calls: ~{batches_processed * 3} ({batches_processed} batches × 3 models)", flush=True)
        print(f"   Daily quota used: ~{batches_processed * 3}/14400 requests", flush=True)
        
        save_xml(final_articles)
        print("\nScript completed successfully!", flush=True)

    except KeyError as e:
        error_msg = f"Configuration error: {e}. Check if GEM environment variable is set."
        print(f"::error::{error_msg}", flush=True)
        save_xml([], error_message=error_msg)
        print("\nScript completed with configuration error (XML file created)", flush=True)
        sys.exit(0)
        
    except requests.exceptions.RequestException as e:
        error_msg = f"Network error: {str(e)[:100]}"
        print(f"::error::{error_msg}", flush=True)
        save_xml([], error_message=error_msg)
        print("\nScript completed with network error (XML file created)", flush=True)
        sys.exit(0)
        
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)[:100]}"
        print(f"::error::{error_msg}", flush=True)
        save_xml([], error_message=error_msg)
        print("\nScript completed with error (XML file created)", flush=True)
        sys.exit(0)

if __name__ == "__main__":
    main()