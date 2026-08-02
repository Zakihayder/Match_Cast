"""Test: hit the highlights API endpoints for a completed match."""
import urllib.request
import json
import sys
import time

base = "http://127.0.0.1:8000/api"

# 1. Check pipeline status
print("=== Pipeline Status ===")
resp = urllib.request.urlopen(f"{base}/highlights/pipeline-status")
status = json.loads(resp.read())
for k, v in status.items():
    print(f"  {k}: {v}")

# 2. Find a completed match
resp = urllib.request.urlopen(f"{base}/matches/")
matches = json.loads(resp.read())
completed = [m for m in matches if m.get("status") == "completed"]
if not completed:
    print("No completed matches.")
    sys.exit(1)

match_id = completed[0]["match_id"]
print(f"\n=== Testing with match: {match_id} ===")

# 3. Check highlight status (should be not_started)
resp = urllib.request.urlopen(f"{base}/highlights/{match_id}/status")
hl_status = json.loads(resp.read())
print(f"Initial status: {hl_status['phase']}")

# 4. Trigger generation
print("\nTriggering highlight generation...")
req = urllib.request.Request(
    f"{base}/highlights/{match_id}/generate",
    data=b"",
    method="POST",
)
resp = urllib.request.urlopen(req)
trigger = json.loads(resp.read())
print(f"Trigger result: {trigger['status']} - {trigger['message']}")

# 5. Poll for completion
print("\nPolling progress...")
for i in range(30):
    time.sleep(2)
    resp = urllib.request.urlopen(f"{base}/highlights/{match_id}/status")
    hl_status = json.loads(resp.read())
    phase = hl_status["phase"]
    progress = int(hl_status.get("progress", 0) * 100)
    msg = hl_status.get("message", "")
    print(f"  [{progress:3d}%] {phase}: {msg}")
    if phase in ("complete", "failed"):
        break

# 6. Results
print(f"\n=== Result ===")
print(f"  Phase: {hl_status['phase']}")
print(f"  Commentary mode: {hl_status.get('commentary_mode', 'n/a')}")
print(f"  TTS mode: {hl_status.get('tts_mode', 'n/a')}")
print(f"  Events: {hl_status.get('event_count', 0)}")
print(f"  Reel available: {hl_status.get('reel_available', False)}")
if hl_status.get("error"):
    print(f"  Error/note: {hl_status['error']}")

# 7. Check commentary
try:
    resp = urllib.request.urlopen(f"{base}/highlights/{match_id}/commentary")
    data = json.loads(resp.read())
    commentary = data.get("commentary", [])
    print(f"\n=== Commentary ({len(commentary)} lines) ===")
    for line in commentary[:5]:
        ts = line.get("timestamp", 0)
        m = int(ts // 60)
        s = int(ts % 60)
        print(f"  [{m:02d}:{s:02d}] [{line.get('event_type', '')}] {line.get('text', '')[:80]}")
    if len(commentary) > 5:
        print(f"  ... and {len(commentary) - 5} more lines")
except Exception as e:
    print(f"  Commentary not available: {e}")

print("\n[OK] Highlights test complete.")
