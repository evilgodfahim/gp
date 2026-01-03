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
    "https://evilgodfahim.github.io/edit/daily_feed.xml"
]

MODEL_NAME = "gemini-2.0-flash-lite"
API_KEY = os.environ["GEM"]

def save_xml(data, error_message=None):
    filename = "filtered_feed.xml"
    
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(filename) if os.path.dirname(filename) else ".", exist_ok=True)
    
    rss = ET.Element("rss", version="2.0")
    channel = ET.SubElement(rss, "channel")
    ET.SubElement(channel, "title").text = "Elite News Feed - BCS/Banking/Geopolitics"
    ET.SubElement(channel, "lastBuildDate").text = datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0600")
    ET.SubElement(channel, "link").text = "https://github.com/evilgodfahim"
    ET.SubElement(channel, "description").text = "AI-curated feed for exam prep & geopolitical advantage"

    if error_message:
        item = ET.SubElement(channel, "item")
        ET.SubElement(item, "title").text = "⚠️ System Error"
        ET.SubElement(item, "description").text = f"Script failed: {error_message}"
        ET.SubElement(item, "pubDate").text = datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0600")
        ET.SubElement(item, "link").text = "https://github.com/evilgodfahim"
    
    elif not data:
        item = ET.SubElement(channel, "item")
        ET.SubElement(item, "title").text = "✅ System Running - No Priority News Today"
        ET.SubElement(item, "description").text = "Curation system working. No exam-critical or geopolitically significant articles found in the last 24 hours."
        ET.SubElement(item, "pubDate").text = datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0600")
        ET.SubElement(item, "link").text = "https://github.com/evilgodfahim"
        
    else:
        for art in data:
            item = ET.SubElement(channel, "item")
            ET.SubElement(item, "title").text = art['title']
            ET.SubElement(item, "link").text = art['link']
            ET.SubElement(item, "pubDate").text = art['pubDate']
            html_desc = f"<p><b>📌 [{art.get('category', 'News')}]</b></p><p><i>{art.get('reason', 'Selected')}</i></p><hr/><p>{art['description']}</p>"
            ET.SubElement(item, "description").text = html_desc

    try:
        tree = ET.ElementTree(rss)
        ET.indent(tree, space="  ", level=0)
        tree.write(filename, encoding="utf-8", xml_declaration=True)
        print(f"\n💾 Successfully saved {len(data) if data else 0} priority items to {filename}", flush=True)
        
        if os.path.exists(filename):
            file_size = os.path.getsize(filename)
            print(f"✅ File created: {filename} ({file_size} bytes)", flush=True)
            
    except Exception as e:
        print(f"::error::Failed to write XML: {e}", flush=True)
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write('<?xml version="1.0" encoding="utf-8"?>\n')
                f.write('<rss version="2.0"><channel>')
                f.write('<title>BCS/Banking Exam Priority Feed</title>')
                f.write('<link>https://github.com/evilgodfahim</link>')
                f.write('<description>Emergency fallback feed</description>')
                f.write('<item><title>System Initialization</title>')
                f.write('<description>Feed initializing. Check back shortly.</description>')
                f.write(f'<pubDate>{datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0600")}</pubDate>')
                f.write('</item></channel></rss>')
            print(f"✅ Created fallback XML", flush=True)
        except:
            pass

def fetch_titles_only():
    all_articles = []
    seen_links = set()
    now = datetime.now(timezone.utc)
    cutoff_time = now - timedelta(hours=24)
    
    print(f"🕒 Time Filter: Articles after {cutoff_time.strftime('%Y-%m-%d %H:%M UTC')}", flush=True)
    headers = {'User-Agent': 'BCS-Curator/2.0'}

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
                seen_links.add(link)
                
                title = item.find('title').text or "No Title"
                title = title.strip()
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

    print(f"✅ Loaded {len(all_articles)} candidate headlines", flush=True)
    return all_articles

def call_gemini_elite(batch):
    prompt_list = [f"{a['id']}: {a['title']}" for a in batch]
    prompt_text = "\n".join(prompt_list)

    prompt = f"""You are an ELITE intelligence analyst curating news for three distinct audiences:
1. BCS (Bangladesh Civil Service) exam candidates
2. Banking job exam aspirants  
3. Geopolitical strategists & power analysts

Articles are in BANGLA (Bengali) and ENGLISH. You MUST understand both languages.

YOUR MISSION: Identify articles that provide DECISIVE COMPETITIVE ADVANTAGE - information that creates knowledge asymmetry between those who read it and those who don't.

═══════════════════════════════════════════════════════════════════

TIER 1: BCS/BANKING EXAM DOMINANCE (Highest Priority)
▸ Government policy announcements, reforms, ordinances (সরকারি নীতি, সংস্কার)
▸ Constitutional amendments, landmark Supreme Court rulings (সংবিধান, সুপ্রিম কোর্ট)
▸ Budget announcements, fiscal/monetary policy shifts (বাজেট, আর্থিক নীতি, মুদ্রানীতি)
▸ International treaties/agreements Bangladesh signed (আন্তর্জাতিক চুক্তি)
▸ High-level appointments: Secretaries, Ambassadors, BB Governor (নিয়োগ)
▸ Banking sector: Regulations, mergers, NPL policy, interest rates (ব্যাংকিং)
▸ Economic indicators: GDP growth, inflation rate, forex reserves, remittance data (জিডিপি, মুদ্রাস্ফীতি, রিজার্ভ)
▸ Mega infrastructure: Project approvals, funding, milestones (মেগা প্রকল্প)
▸ Educational reforms, exam policy changes (শিক্ষা সংস্কার)
▸ Administrative restructuring, new ministries/divisions (প্রশাসন)
▸ Trade statistics, export-import data (রপ্তানি-আমদানি)

TIER 2: GEOPOLITICAL POWER INTELLIGENCE (Critical for Strategists)
▸ Bangladesh bilateral dynamics: India, China, USA, Pakistan, Myanmar relations (ভারত, চীন)
▸ Regional alliances: ASEAN, SAARC, BIMSTEC, QUAD developments
▸ South Asian security architecture shifts
▸ Trade wars, tariff changes, economic sanctions affecting region (বাণিজ্য যুদ্ধ, শুল্ক)
▸ Energy geopolitics: LNG deals, oil agreements, renewable partnerships (এলএনজি, জ্বালানি)
▸ Defense acquisitions, military exercises, arms deals (প্রতিরক্ষা, সামরিক)
▸ Diplomatic incidents, embassy closures, ambassador recalls
▸ UN Security Council decisions on regional conflicts
▸ World Bank/IMF/ADB loan conditions or policy prescriptions
▸ Water diplomacy: Teesta, Ganges, Brahmaputra agreements (তিস্তা, গঙ্গা, ব্রহ্মপুত্র)
▸ Rohingya crisis developments with policy impact (রোহিঙ্গা)
▸ Belt & Road Initiative projects in Bangladesh/region (বিআরআই)
▸ Indo-Pacific strategy developments affecting Bangladesh

TIER 3: STRATEGIC FORESIGHT (Competitive Edge)
▸ Breakthrough scientific research with policy implications (বৈজ্ঞানিক আবিষ্কার)
▸ Climate agreements, carbon trading mechanisms (জলবায়ু চুক্তি)
▸ National cybersecurity incidents, data breach policies (সাইবার নিরাপত্তা)
▸ Major corporate mergers/bankruptcies affecting national economy
▸ Digital Bangladesh updates: e-governance, fintech regulations (ডিজিটাল বাংলাদেশ)
▸ Demographic shifts with economic impact (জনসংখ্যা)
▸ Agricultural policy changes, food security measures (কৃষি নীতি, খাদ্য নিরাপত্তা)

═══════════════════════════════════════════════════════════════════

ABSOLUTE REJECTIONS (Waste of Mental Bandwidth):
✗ Sports: Cricket/football matches, player transfers, tournament updates (ক্রিকেট, ফুটবল)
✗ Entertainment: Cinema releases, music, celebrity news, award shows (সিনেমা, গান)
✗ Crime: Local murders, robberies, accidents WITHOUT systemic policy impact (অপরাধ, দুর্ঘটনা)
✗ Human interest: Viral stories, feel-good content, personal achievements (ভাইরাল)
✗ Lifestyle: Fashion, food trends, travel, astrology (ফ্যাশন, রাশিফল)
✗ Generic editorials: Opinion pieces without NEW concrete facts

═══════════════════════════════════════════════════════════════════

EDITORIAL/OPINION FILTERING PROTOCOL:
Most newspaper editorials (সম্পাদকীয়) discuss existing issues but DON'T announce NEW policy.

SELECT editorials ONLY IF they contain:
✓ Specific NEW policy announcements or government decisions
✓ Concrete economic statistics not widely reported
✓ Confirmed international agreements or treaties
✓ Expert analysis revealing non-public strategic implications

REJECT editorials that are:
✗ Generic commentary on well-known issues
✗ Opinion/analysis without factual policy updates
✗ Rehashing of old news with new perspectives

═══════════════════════════════════════════════════════════════════

EVALUATION FRAMEWORK (Apply to EVERY article):

QUESTION 1: "Will this FACT appear in BCS/Banking exam questions next year?"
QUESTION 2: "Does this shift power balances or reveal strategic developments?"
QUESTION 3: "Will competitors have blind spots without this information?"
QUESTION 4: "Is this NEW information or rehashing old news?"

If answer to ANY question is "No" → REJECT

═══════════════════════════════════════════════════════════════════

INPUT ARTICLES (Bangla/English Mix):
{prompt_text}

OUTPUT FORMAT (JSON ONLY):
[
  {{"id": 15, "category": "Monetary Policy", "reason": "Bangladesh Bank rate cut to 8.5% - direct exam fact"}},
  {{"id": 42, "category": "Indo-Pacific Geopolitics", "reason": "BD-India defense pact signals China counterbalancing"}},
  {{"id": 73, "category": "Infrastructure", "reason": "Padma Rail Link completion date announced - exam relevant"}}
]

═══════════════════════════════════════════════════════════════════

CRITICAL INSTRUCTIONS:
• Return ONLY the JSON array, nothing else
• Be RUTHLESSLY selective: If <8% qualify, that's CORRECT
• Prioritize CONCRETE FACTS over abstract analysis
• Both Bangla and English titles must be evaluated equally
• When in doubt, ask: "Would I want to know this to outperform my competitors?"

BEGIN ANALYSIS."""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={API_KEY}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.1,  # Very low for consistent, strict filtering
            "topP": 0.8,
            "topK": 20,
            "responseMimeType": "application/json"
        }
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=50)
        
        if response.status_code == 200:
            result = response.json()
            raw_text = result['candidates'][0]['content']['parts'][0]['text']
            parsed = json.loads(raw_text)
            return parsed if isinstance(parsed, list) else []
        
        elif response.status_code == 429:
            print(f"    ❌ Rate limit (429) - Daily quota exhausted. Stopping.", flush=True)
            return []
        
        elif response.status_code >= 500:
            print(f"    ⚠️ Server Error {response.status_code} - Skipping batch", flush=True)
            return []
        
        else:
            print(f"    ❌ API Error {response.status_code} - Skipping batch", flush=True)
            return []

    except requests.exceptions.Timeout:
        print(f"    ⏱️ Timeout - Skipping batch", flush=True)
        return []
        
    except json.JSONDecodeError:
        print(f"    ⚠️ JSON parse error - Skipping batch", flush=True)
        return []
        
    except Exception as e:
        print(f"    ⚠️ Error: {str(e)[:60]} - Skipping batch", flush=True)
        return []

def main():
    print("=" * 70, flush=True)
    print("🎯 Elite News Curator - BCS/Banking/Geopolitics (Bangla/English)", flush=True)
    print("=" * 70, flush=True)
    
    if not os.path.exists("filtered_feed.xml"):
        print("📄 First run detected - creating initial XML file...", flush=True)
        save_xml([], error_message=None)
    
    try:
        articles = fetch_titles_only()
        
        if not articles:
            print("⚠️ No articles found in source feeds", flush=True)
            save_xml([])
            print("\n✅ Script completed successfully (no articles to process)", flush=True)
            return

        # Optimized batch size: Typical newspaper titles are 50-100 chars
        # With 250k TPM limit and conservative estimation:
        # - 100 articles × 75 chars avg × 2 (title+prompt) = ~15k chars ≈ 4k tokens
        # - Plus system prompt (~2k tokens) = ~6k tokens total
        # - Well under 250k TPM limit, so we can use batch size 100
        BATCH_SIZE = 100
        batches = [articles[i:i + BATCH_SIZE] for i in range(0, len(articles), BATCH_SIZE)]
        
        # With 20 RPD, process max 3 batches (300 articles) - conservative
        MAX_BATCHES = 3
        if len(batches) > MAX_BATCHES:
            print(f"⚠️ Found {len(batches)} batches, limiting to {MAX_BATCHES} to respect 20 RPD quota", flush=True)
            batches = batches[:MAX_BATCHES]
            articles_to_process = articles[:MAX_BATCHES * BATCH_SIZE]
        else:
            articles_to_process = articles
        
        selected_articles = []
        print(f"\n🚀 Processing {len(batches)} batches (size={BATCH_SIZE}) with {MODEL_NAME}...", flush=True)
        print(f"⚠️ API Limits: 10 RPM | 250k TPM | 20 RPD", flush=True)
        print(f"📊 Strategy: Process up to {len(articles_to_process)} articles, use {MAX_BATCHES}/20 quota\n", flush=True)

        quota_exhausted = False
        batches_processed = 0
        
        for i, batch in enumerate(batches):
            if quota_exhausted:
                print(f"  ⏭️  Skipping remaining batches due to quota exhaustion", flush=True)
                break
                
            print(f"  ⚡ Batch {i+1}/{len(batches)} ({len(batch)} articles)...", flush=True)
            
            decisions = call_gemini_elite(batch)
            
            if not decisions and i == 0:
                print(f"  ⚠️ First batch failed - possible quota exhaustion", flush=True)
                quota_exhausted = True
                break
            
            for d in decisions:
                try:
                    original = next((x for x in batch if x["id"] == d["id"]), None)
                    if original:
                        original['category'] = d.get('category', 'Priority')
                        original['reason'] = d.get('reason', 'Strategic importance')
                        selected_articles.append(original)
                except: 
                    continue
            
            batches_processed += 1
            print(f"    ✓ Selected {len(decisions)} from this batch", flush=True)
            
            # Wait 10 seconds between batches (10 RPM = 6 sec minimum, use 10 for safety)
            if i < len(batches) - 1:
                print(f"    ⏸️  Waiting 10 seconds (10 RPM compliance)...", flush=True)
                time.sleep(10)

        selection_rate = (len(selected_articles)*100//len(articles_to_process)) if articles_to_process else 0
        print(f"\n🎯 RESULTS:", flush=True)
        print(f"   Total articles available: {len(articles)}", flush=True)
        print(f"   Articles analyzed: {len(articles_to_process)}", flush=True)
        print(f"   Articles selected: {len(selected_articles)} ({selection_rate}% pass rate)", flush=True)
        print(f"   Batches processed: {batches_processed}/{MAX_BATCHES}", flush=True)
        print(f"   Daily API quota used: {batches_processed}/20 requests ({batches_processed*5}%)", flush=True)
        
        save_xml(selected_articles)
        print("\n✅ Script completed successfully!", flush=True)

    except KeyError as e:
        error_msg = f"Configuration error: {e}. Check if GEM environment variable is set."
        print(f"::error::{error_msg}", flush=True)
        save_xml([], error_message=error_msg)
        print("\n⚠️ Script completed with configuration error (XML file created)", flush=True)
        sys.exit(0)
        
    except requests.exceptions.RequestException as e:
        error_msg = f"Network error: {str(e)[:100]}"
        print(f"::error::{error_msg}", flush=True)
        save_xml([], error_message=error_msg)
        print("\n⚠️ Script completed with network error (XML file created)", flush=True)
        sys.exit(0)
        
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)[:100]}"
        print(f"::error::{error_msg}", flush=True)
        save_xml([], error_message=error_msg)
        print("\n⚠️ Script completed with error (XML file created)", flush=True)
        sys.exit(0)

if __name__ == "__main__":
    main()
