"""
Quick test to see the full multimodal response
"""
import requests
from pathlib import Path

BASE_URL = 'http://127.0.0.1:8000'

# Login
login_resp = requests.post(f'{BASE_URL}/api/auth/login', json={'email': 'dev@gmail.com', 'password': '123456'})
token = login_resp.json().get('access_token')
headers = {'Authorization': f'Bearer {token}'}

# Get agent
agents_resp = requests.get(f'{BASE_URL}/api/agents/', headers=headers)
agent_name = agents_resp.json()[0]['name']
print(f"Using agent: {agent_name}")

# Test with image
test_image = Path('data/temp/test_multimodal.png')
with open(test_image, 'rb') as f:
    files = {'image': (test_image.name, f, 'image/png')}
    data = {'agent_name': agent_name, 'message': 'What color is this image?', 'include_explainability': 'true'}
    response = requests.post(f'{BASE_URL}/api/chat/multimodal', files=files, data=data, headers=headers, timeout=120)

result = response.json()
print('=== FULL RESPONSE ===')
print(f"Success: {result.get('success')}")
print(f"Answer: {result.get('answer')}")
print(f"Confidence: {result.get('confidence')}")
print(f"Image URL: {result.get('image_url')}")
print(f"In Domain: {result.get('in_domain')}")
