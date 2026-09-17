import time
from database import get_all_opportunities
from tts import speak

def check_deadlines():
    print("Checking for upcoming deadlines...")
    opportunities = get_all_opportunities()
    
    alert_messages = []
    for opp in opportunities:
        # In a real app, parse the deadline date. Here we do a simple check.
        title = opp.get("title", "Unknown")
        deadline = opp.get("deadline", "Unknown")
        
        if deadline != "Unknown":
            # For demonstration, we alert on all tasks
            alert_messages.append(f"Reminder: {title} deadline is approaching.")
    
    if alert_messages:
        full_alert = " You have upcoming deadlines. " + " ".join(alert_messages)
        print(f"\n[Daemon]: {full_alert}")
        speak(full_alert)
    else:
        print("[Daemon]: No immediate deadlines found.")

def run_daemon():
    print("Starting Hound Background Daemon... (Press Ctrl+C to stop)")
    try:
        while True:
            check_deadlines()
            # Sleep for 1 hour (3600 seconds), shortened to 30s for testing
            time.sleep(30)
    except KeyboardInterrupt:
        print("Daemon stopped.")

if __name__ == "__main__":
    run_daemon()
