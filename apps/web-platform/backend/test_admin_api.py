"""
Test admin API with authentication
"""
import requests
import json

# Login first
login_response = requests.post("http://localhost:8000/api/auth/login", json={
    "username": "admin",
    "password": "admin123"
})

if login_response.status_code == 200:
    token_data = login_response.json()
    access_token = token_data.get("access_token")
    print(f"Got access token: {access_token[:20]}...")

    # Test admin stats
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # Admin stats
    stats_response = requests.get("http://localhost:8000/api/admin/stats", headers=headers)
    print(f"\nAdmin stats response: {stats_response.status_code}")
    if stats_response.status_code == 200:
        print(f"Stats data: {json.dumps(stats_response.json(), indent=2)}")
    else:
        print(f"Error: {stats_response.text}")

    # Documents list
    docs_response = requests.get("http://localhost:8000/api/documents", headers=headers)
    print(f"\nDocuments response: {docs_response.status_code}")
    if docs_response.status_code == 200:
        docs_data = docs_response.json()
        print(f"Documents count: {docs_data.get('total', 0)}")
        print(f"Recent docs: {docs_data.get('items', [])[:3]}")
    else:
        print(f"Error: {docs_response.text}")

else:
    print(f"Login failed: {login_response.text}")