import time
import os
import multiprocessing
import sounddevice as sd
import numpy as np

def run_wake_word():
    try:
        from openwakeword.model import Model
    except ImportError:
        print("openwakeword not installed. Please run: pip install openwakeword")
        return
        
    print("[Wake] Loading Wake Word Engine...")
    oww_model = Model(wakeword_models=["hey_jarvis", "alexa"], inference_framework="tflite")
    
    print("========================================")
    print(" 🎙️ OFFLINE LISTENING (Say 'Alexa') 🎙️ ")
    print("========================================")

    fs = 16000
    chunk_size = 1280
    
    while True:
        wake_detected = False
        
        # 1. Listen for Wake Word
        # We use a context manager, but BREAK immediately on detection to unlock the mic!
        try:
            with sd.InputStream(samplerate=fs, channels=1, dtype='int16', blocksize=chunk_size) as stream:
                while True:
                    audio_chunk, overflow = stream.read(chunk_size)
                    audio_np = np.frombuffer(audio_chunk, dtype=np.int16)
                    
                    prediction = oww_model.predict(audio_np)
                    
                    for mdl in oww_model.prediction_buffer.keys():
                        if oww_model.prediction_buffer[mdl][-1] > 0.5:
                            print(f"\n[Wake] '{mdl}' detected!")
                            wake_detected = True
                            break
                            
                    if wake_detected:
                        break # Break inner loop
        except Exception as e:
            print(f"[Wake] Audio error: {e}")
            time.sleep(2)
            continue
            
        # 2. Start Live Session
        if wake_detected:
            # At this point, the `with sd.InputStream` is fully closed and mic is unlocked.
            print("[Wake] Mic unlocked. Passing control to Gemini Live...")
            try:
                from live_session import start_session
                start_session()
            except Exception as e:
                print(f"[Wake] Live session crashed: {e}. Recovering...")
                
            print("[Wake] Session over. Resuming offline listening...")
            time.sleep(1) # Brief pause before grabbing mic again

if __name__ == "__main__":
    multiprocessing.freeze_support()
    run_wake_word()
