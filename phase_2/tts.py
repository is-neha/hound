import pyttsx3
import os

def speak(text, mute=False):
    if mute:
        return
        
    print("[Audio]: Speaking...")
    
    # Initialize the local Windows TTS engine
    try:
        engine = pyttsx3.init()
        # Set a slightly faster rate for a more natural feel
        engine.setProperty('rate', 180)
        engine.say(text)
        engine.runAndWait()
    except Exception as e:
        print(f"TTS Error: {e}")
