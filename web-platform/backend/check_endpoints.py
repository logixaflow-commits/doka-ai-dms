"""
Check available API endpoints
"""
import requests
import json

try:
    response = requests.get("http://localhost:8000/api/openapi.json")
    if response.status_code == 200:
        openapi_spec = response.json()
        paths = openapi_spec.get("paths", {})
        
        print("Available API Endpoints:")
        print("=" * 50)
        
        for path, methods in paths.items():
            print(f"\n{path}:")
            for method, details in methods.items():
                print(f"  {method.upper()}: {details.get('summary', 'No summary')}")
                
        print(f"\n\nTotal endpoints: {len(paths)}")
        
    else:
        print(f"Error: {response.status_code}")
        
except Exception as e:
    print(f"Connection error: {e}")