import requests
from PIL import Image
import io

# Create a simple dummy image
img = Image.new('RGB', (100, 100), color='blue')
img_byte_arr = io.BytesIO()
img.save(img_byte_arr, format='PNG')
img_byte_arr.seek(0)

# Try login first
print("Attempting login...")
auth_res = requests.post('http://127.0.0.1:5000/api/auth/login', json={
    'email': 'test@example.com',
    'password': 'password123'
})
print("Login status:", auth_res.status_code)
print("Login body:", auth_res.json())

token = auth_res.json().get('token')

if not token:
    print("Login failed, attempting registration...")
    auth_res = requests.post('http://127.0.0.1:5000/api/auth/register', json={
        'name': 'Test User',
        'email': 'test@example.com',
        'password': 'password123'
    })
    print("Register status:", auth_res.status_code)
    print("Register body:", auth_res.json())
    token = auth_res.json().get('token')

if not token:
    print("Could not obtain token!")
    exit(1)

print("Using token:", token)

# Upload the dummy image
files = {'file': ('test.png', img_byte_arr, 'image/png')}
headers = {'Authorization': f'Bearer {token}'}
upload_res = requests.post('http://127.0.0.1:5000/api/upload', files=files, headers=headers)

print("Upload response status:", upload_res.status_code)
print("Upload response body:", upload_res.text)
