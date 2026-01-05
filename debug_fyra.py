import os
import requests
import json
import time

# --- CONFIGURATION ---
# Base URL from your PDF
BASE_URL = "https://fyra.im"
CHAT_ENDPOINT = f"{BASE_URL}/v1/chat/completions"
MODELS_ENDPOINT = f"{BASE_URL}/v1/models"

# The specific Kimi ID found in research
TARGET_MODEL = "kimi-k2-instruct-0905"
API_KEY = os.environ.get("FRY")

def debug_kimi():
    print(f"--- FYRA.IM KIMI DIAGNOSTIC ---")
    
    if not API_KEY:
        print("::error:: FRY environment variable is missing!")
        return

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    # --- STEP 1: Verify Model Existence ---
    print(f"\n[1] Checking if '{TARGET_MODEL}' is listed in API...")
    try:
        r = requests.get(MODELS_ENDPOINT, headers=headers, timeout=10)
        if r.status_code == 200:
            data = r.json()
            all_ids = [m['id'] for m in data.get('data', [])]
            
            # Search for ANY Kimi or Moonshot model
            kimi_ids = [m for m in all_ids if 'kimi' in m.lower() or 'moonshot' in m.lower()]
            
            print(f"   ✅ API Connected.")
            print(f"   📋 Kimi/Moonshot Models Found: {json.dumps(kimi_ids, indent=2)}")
            
            if TARGET_MODEL in all_ids:
                print(f"   ✅ Exact match found for '{TARGET_MODEL}'")
            elif kimi_ids:
                print(f"   ⚠️ Exact match missing. Will try found ID: '{kimi_ids[0]}'")
                # Optional: Uncomment to auto-switch
                # TARGET_MODEL = kimi_ids[0]
            else:
                print(f"   ❌ No Kimi models found. Is it hidden?")
        else:
            print(f"   ❌ Failed to list models: {r.status_code}")

    except Exception as e:
        print(f"   ❌ Connection failed: {e}")

    # --- STEP 2: Test Chat ---
    print(f"\n[2] Testing Chat with ID: '{TARGET_MODEL}'...")
    payload = {
        "model": TARGET_MODEL,
        "messages": [{"role": "user", "content": "Who created you? Reply in 1 sentence."}],
        "temperature": 0.5
    }

    try:
        r = requests.post(CHAT_ENDPOINT, headers=headers, json=payload, timeout=30)
        
        print(f"   Status Code: {r.status_code}")
        
        if r.status_code == 200:
            resp = r.json()
            if 'error' in resp:
                print(f"   ❌ API ERROR (200 OK): {resp['error']}")
            elif 'choices' in resp:
                print(f"   ✅ SUCCESS! Output: {resp['choices'][0]['message']['content']}")
            else:
                print(f"   ⚠️ Unknown format: {resp.keys()}")
        else:
            print(f"   ❌ HTTP Error: {r.text}")

    except Exception as e:
        print(f"   ❌ Request Error: {e}")

if __name__ == "__main__":
    debug_kimi()
