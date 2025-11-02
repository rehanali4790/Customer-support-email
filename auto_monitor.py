import requests
import time
from datetime import datetime

BASE_URL = "http://localhost:5000"

print("🤖 Email Agent Monitor - Running every 2 minutes")
print("Press Ctrl+C to stop\n")

while True:
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] Checking for emails...")
    
    # Fetch and process emails
    try:
        r = requests.post(
            f"{BASE_URL}/api/v1/email/batch-process",
            json={"limit": 20},
            timeout=60
        )
        result = r.json()
        print(f"  ✅ Processed: {result.get('processed', 0)}")
        print(f"  📤 Auto-sent: {result.get('sent', 0)}")
        print(f"  ⏳ Needs approval: {result.get('requires_review', 0)}")
    except Exception as e:
        print(f"  ❌ Error: {e}")
    
    # Check for approvals
    # try:
    #     r = requests.post(f"{BASE_URL}/api/v1/approvals/check")
    #     result = r.json()
    #     if result.get('processed', 0) > 0:
    #         print(f"  ✅ Approvals processed: {result.get('approved', 0)}")
    #         print(f"  📧 Sent to customers: {result.get('sent', 0)}")
    # except Exception as e:
    #     print(f"  ❌ Approval check error: {e}")
    
    print("\n💤 Waiting 2 minutes...\n")
    time.sleep(120)  # 2 minutes