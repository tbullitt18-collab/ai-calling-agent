"""
Rain Check v2.0 Route Verification Script
Tests the new Voice Cloning and Scheduling API endpoints.
"""

import requests
import json
import os

BASE_URL = "http://localhost:5000"

def test_health():
    print("\n[1] Testing Health Endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/")
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    except Exception as e:
        print(f"Error: {e}")

def test_list_voices():
    print("\n[2] Testing List Voices...")
    try:
        response = requests.get(f"{BASE_URL}/voices/")
        print(f"Status: {response.status_code}")
        voices = response.json()
        print(f"Total Voices found: {len(voices)}")
        if voices:
            print(f"First Voice: {voices[0].get('name')} ({voices[0].get('voice_id')})")
    except Exception as e:
        print(f"Error: {e}")

def test_scheduler_validation():
    print("\n[3] Testing Scheduler (Input Validation)...")
    payload = {"to_number": "+1234567890", "time": "06:00"}
    try:
        response = requests.post(f"{BASE_URL}/session/schedule", json=payload)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    print("=== Rain Check v2.0 API Verification ===")
    test_health()
    test_list_voices()
    test_scheduler_validation()
    print("\nVerification Complete.")
