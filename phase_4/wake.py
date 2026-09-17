import os
import time
import numpy as np
import sounddevice as sd
from openwakeword.model import Model
from listen import listen_and_respond
from tts import speak

def run_wake_word_engine():
    print("[Hound]: Loading wake-word engine (OpenWakeWord)...")
    # Using the completely free, local OpenWakeWord engine. 
    # We load multiple built-in models so you can use any of them!
    oww_model = Model(
        wakeword_models=["hey_jarvis", "alexa", "hey_mycroft", "timer"], 
        inference_framework="onnx"
    )

    print("\n" + "="*60)
    print(" 24/7 Wake-Word Engine Active (NO API KEY REQUIRED) ")
    print(" Say 'Hey Jarvis', 'Alexa', or 'Hey Mycroft' to wake Hound up!")
    print("="*60 + "\n")

    fs = 16000
    chunk_samples = 1280

    from datetime import datetime
    from dotenv import load_dotenv
    load_dotenv()
    
    PROACTIVE_TIME = os.getenv("PROACTIVE_TIME", "22:00")
    last_proactive_date = None

    while True:
        with sd.InputStream(samplerate=fs, channels=1, dtype='int16') as stream:
            wake_detected = False
            proactive_trigger = False
            while True:
                try:
                    # 1. Check time for Proactive Wakeup
                    now = datetime.now()
                    if now.strftime("%H:%M") == PROACTIVE_TIME and last_proactive_date != now.date():
                        wake_detected = True
                        proactive_trigger = True
                        last_proactive_date = now.date()
                        break
                        
                    # 2. Check microphone for Wake Word
                    audio, _ = stream.read(chunk_samples)
                    audio_data = audio.flatten()
                    
                    prediction = oww_model.predict(audio_data)
                    
                    for mdl in oww_model.prediction_buffer.keys():
                        if prediction[mdl] > 0.5:
                            wake_detected = True
                            oww_model.reset()
                            break
                            
                    if wake_detected:
                        break # Break out of inner loop to release microphone lock
                        
                except KeyboardInterrupt:
                    print("Stopping wake-word engine...")
                    return
                except Exception as e:
                    print(f"Error in background loop: {e}")
                    time.sleep(1)
                    
        # Now the `with` block has exited, and the microphone is FULLY RELEASED.
        if wake_detected:
            if proactive_trigger:
                print("\n[Proactive Wakeup Triggered!]")
                p = speak("Excuse me, I have some daily updates for you.")
                if p: p.join()
            else:
                print("\n[Wake Word Detected!]")
                p = speak("Yes?")
                if p: p.join()
                
            # Trigger reminders immediately upon waking!
            from listen import trigger_reminders, listen_and_respond
            trigger_reminders()
            
            # Handoff to Phase 3 conversational loop
            print("--- Voice Copilot Activated ---")
            active = True
            while active:
                active = listen_and_respond()
            
            print(f"\n[Hound]: Going back to sleep. Say 'Hey Jarvis' to wake me, or I will wake you at {PROACTIVE_TIME}.")

if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    run_wake_word_engine()
