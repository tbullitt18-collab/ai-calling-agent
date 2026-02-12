"""
Check Twilio Debugger Logs for errors.
"""
import os
from twilio.rest import Client
from dotenv import load_dotenv

def check_errors():
    load_dotenv()
    sid = os.getenv("TWILIO_ACCOUNT_SID")
    token = os.getenv("TWILIO_AUTH_TOKEN")
    
    client = Client(sid, token)
    
    print("Checking recently failed calls...")
    calls = client.calls.list(status='failed', limit=10)
    for call in calls:
        print(f"FAILED CALL: SID={call.sid}, To={call.to}, Date={call.date_created}")
        
    print("\nChecking Twilio Alerts (Debugger)...")
    alerts = client.monitor.alerts.list(limit=5)
    for alert in alerts:
        print(f"ALERT: Date={alert.date_created}, Error={alert.error_code}, Msg={alert.alert_text}, URL={alert.request_url}")

if __name__ == "__main__":
    check_errors()
