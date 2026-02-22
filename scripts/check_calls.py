"""Check recent Vonage call status."""
import jwt, time, uuid, requests, json

with open('./private.key', 'r') as f:
    private_key = f.read()

app_id = 'bed9794a-0f5b-4e51-a32c-3b751f5f292a'
token = jwt.encode({
    'application_id': app_id,
    'iat': int(time.time()),
    'jti': str(uuid.uuid4()),
    'exp': int(time.time()) + 3600
}, private_key, algorithm='RS256')

r = requests.get('https://api.nexmo.com/v1/calls',
    headers={'Authorization': f'Bearer {token}'},
    timeout=10)

data = r.json()
calls = data.get('_embedded', {}).get('calls', [])
print(f"Total calls: {data.get('count', 0)}")
for c in calls[:5]:
    to_num = c.get('to', {}).get('number', '?')
    status = c.get('status', '?')
    direction = c.get('direction', '?')
    uid = c.get('uuid', '?')[:16]
    print(f"  {uid}.. | to={to_num} | status={status} | dir={direction}")
