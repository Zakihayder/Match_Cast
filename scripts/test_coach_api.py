"""Quick test: hit the AI Coach API endpoint for a completed match."""
import urllib.request
import json
import sys

base = "http://127.0.0.1:8000/api"

# Find a completed match
matches_resp = urllib.request.urlopen(f"{base}/matches/")
matches = json.loads(matches_resp.read())
completed = [m for m in matches if m.get("status") == "completed"]

if not completed:
    print("No completed matches found. Upload and process a video first.")
    sys.exit(1)

match_id = completed[0]["match_id"]
print(f"Testing with match: {match_id}")

# Hit the coach endpoint
coach_resp = urllib.request.urlopen(f"{base}/coach/{match_id}/coach")
data = json.loads(coach_resp.read())

print(f"\nMode: {data['mode']}")
print(f"Recommendations: {len(data['recommendations'])}")
print(f"Performance Scores: {data['performance_scores']}")
print()

for i, rec in enumerate(data["recommendations"], 1):
    cat = rec.get("category", "?")
    pri = rec.get("priority", "?")
    print(f"  {i}. [{cat}/{pri}] {rec['title']}")
    print(f"     {rec['body'][:100]}...")
    print(f"     Citation: {rec['citation']}")
    print()

# Also test the status endpoint
status_resp = urllib.request.urlopen(f"{base}/coach/status")
status = json.loads(status_resp.read())
print(f"Coach Status: {status}")
print("\n[OK] AI Coach API test PASSED")
