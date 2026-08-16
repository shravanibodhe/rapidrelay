"""
Demo script to test the end-to-end Claude extraction and heuristics pipeline on RapidRelay.
"""

import os
import sys
import json
import urllib.request
import urllib.error
from dotenv import load_dotenv

# Ensure UTF-8 output handling on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

current_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(current_dir, ".env"))

SAMPLE_HINDI_DISTRESS = {
    "text": "मदद करो! हमारे घर में पानी भर गया है, 4 लोग छत पर फंसे हैं और एक बच्चा बीमार है। पटना राजेंद्र नगर।"
}

API_URL = "http://localhost:8000/incidents"


def run_demo():
    print("=" * 70)
    print("RAPIDRELAY - EMERGENCY TRIAGE INTAKE PIPELINE DEMO")
    print("=" * 70)
    print(f"\n[1] Sending raw Hindi distress text to {API_URL}:")
    print(f"    Message: \"{SAMPLE_HINDI_DISTRESS['text']}\"\n")

    data = json.dumps(SAMPLE_HINDI_DISTRESS).encode("utf-8")
    req = urllib.request.Request(
        API_URL,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            status_code = resp.status
            body = resp.read().decode("utf-8")
            res_json = json.loads(body)
            print(f"[2] HTTP Status Code: {status_code} CREATED")
            print("\n[3] Response JSON:")
            print(json.dumps(res_json, indent=2, ensure_ascii=False))
            print("\n>>> Pipeline successfully executed with Claude Sonnet 4.5 & Heuristic Booster! <<<")
    except urllib.error.HTTPError as err:
        status_code = err.code
        body = err.read().decode("utf-8")
        print(f"[2] HTTP Status Code: {status_code}")
        try:
            err_json = json.loads(body)
            print("\n[3] Response JSON:")
            print(json.dumps(err_json, indent=2, ensure_ascii=False))
        except Exception:
            print(f"\n[3] Raw Response: {body}")
            
        if status_code == 502:
            print("\n>>> Caught expected 502 error path (Anthropic API Key not configured or upstream error) <<<")
    except urllib.error.URLError as err:
        print(f"Error: Could not connect to {API_URL}. Ensure uvicorn is running: {err}")


if __name__ == "__main__":
    run_demo()
