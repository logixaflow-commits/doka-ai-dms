"""
Test API endpoints
"""
import requests
import json

# Login to get token
login_response = requests.post("http://localhost:8000/api/auth/login", json={
    "username": "admin",
    "password": "admin123"
})

print(f"Login response status: {login_response.status_code}")
if login_response.status_code == 200:
    token_data = login_response.json()
    access_token = token_data.get("access_token")
    print(f"Got access token: {access_token[:20]}...")

    # Test authenticated request
    headers = {"Authorization": f"Bearer {access_token}"}
    docs_response = requests.get("http://localhost:8000/api/documents", headers=headers)
    print(f"Documents response status: {docs_response.status_code}")
    print(f"Documents response: {docs_response.json()}")
else:
    print(f"Login failed: {login_response.text}")