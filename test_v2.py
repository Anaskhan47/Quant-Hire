import urllib.request
import json

data = json.dumps({
    "resume": "Skills: Python, Java. Experience: 3 years. Lead developer on personal projects.",
    "job_description": "Skills: Python, Go. Experience: 5 years. Required skill: Go."
}).encode('utf-8')

req = urllib.request.Request("http://127.0.0.1:8000/v2/predict", data=data, headers={'Content-Type': 'application/json'})

try:
    with urllib.request.urlopen(req) as response:
        print("STATUS:", response.status)
        result = json.loads(response.read().decode('utf-8'))
        print(json.dumps(result, indent=2))
except Exception as e:
    print("ERROR:", e)
    if hasattr(e, 'read'):
        print(e.read().decode('utf-8'))
