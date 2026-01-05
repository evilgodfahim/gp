import os
import requests
import json
import time

# --- CONFIGURATION ---
# The specific endpoint for Fyra (verify if they need /v1/ or not in their docs)
API_URL = "https://api.fyra.im/v1/chat/completions" 

# The key from your environment (FRY)
API_KEY = os.environ.get("FRY")

# The model name you want to test. 
# Try "deepseek-chat", "deepseek-v3", or "DeepSeek-V3.1" one by one.
MODEL_NAME = "deepseek-chat" 

def test_fyra():
    print(f"--- DIAGNOSTIC START ---")
    print(f"Target URL: {API_URL}")
    print(f"Target Model: {MODEL_NAME}")
    
    if not API_KEY:
        print("::error:: FRY environment variable is missing!")
        return

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "user", "content": "Say 'Hello World' and nothing else."}
        ],
        "temperature": 0.1
    }

    print("\nSending request...")
    start_time = time.time()
    
    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
        elapsed = time.time() - start_time
        
        print(f"\n--- RESPONSE METADATA ---")
        print(f"Status Code: {response.status_code}")
        print(f"Time Taken:  {elapsed:.2f}s")
        
        print(f"\n--- RAW RESPONSE TEXT ---")
        # This is where you see the real error message
        print(response.text)
        
        print(f"\n--- JSON PARSING CHECK ---")
        try:
            data = response.json()
            print("✅ JSON Decode Successful")
            
            if 'choices' in data:
                print(f"Content: {data['choices'][0]['message']['content']}")
            elif 'error' in data:
                print("❌ API Returned Error Object:")
                print(json.dumps(data['error'], indent=2))
            else:
                print("⚠️ Unknown JSON Structure. Keys found:", list(data.keys()))
                
        except json.JSONDecodeError:
            print("❌ Failed to decode JSON (Response might be HTML or empty)")

    except Exception as e:
        print(f"❌ Connection Failed: {e}")

if __name__ == "__main__":
    test_fyra()
