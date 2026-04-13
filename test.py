import urllib.request
import json

data = json.dumps({
    "resume_text": "Skills: Python, Java. Exp: 3 years. \nCandidate — Test",
    "job_description": "Skills: Python, Go. Exp: 5 years"
}).encode('utf-8')

req = urllib.request.Request("http://127.0.0.1:8003/predict", data=data, headers={'Content-Type': 'application/json'})

try:
    with urllib.request.urlopen(req) as response:
        print("STATUS:", response.status)
        print(response.read().decode('utf-8'))
except Exception as e:
    print("ERROR:", e)
    if hasattr(e, 'read'):
        print(e.read().decode('utf-8'))
