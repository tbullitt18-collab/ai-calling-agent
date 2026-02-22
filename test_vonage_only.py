from dotenv import load_dotenv
import os
import requests

def test_vonage():
    load_dotenv()
    print("TEST_VONAGE_START")
    key = os.getenv("VONAGE_API_KEY")
    secret = os.getenv("VONAGE_API_SECRET")
    
    if not key or not secret:
        print("MISSING_CREDENTIALS")
        return

    try:
        resp = requests.get(
            "https://rest.nexmo.com/account/get-balance",
            params={"api_key": key, "api_secret": secret},
            timeout=10
        )
        if resp.status_code == 200:
            print(f"SUCCESS Balance: {resp.json().get('value')}")
        else:
            print(f"FAILED {resp.status_code}")
    except Exception as e:
        print(f"ERROR {e}")
    print("TEST_VONAGE_END")

if __name__ == "__main__":
    test_vonage()
