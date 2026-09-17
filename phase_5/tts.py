import pyttsx3
import multiprocessing

def _speak_process(text, mute=False):
    if mute:
        return
        
    import os
    import requests
    import numpy as np
    import sounddevice as sd
    
    elevenlabs_key = os.getenv("ELEVENLABS_API_KEY")
    if elevenlabs_key:
        try:
            # Bella (Female voice)
            voice_id = "EXAVITQu4vr4xnSDxMaL"
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}?output_format=pcm_24000"
            headers = {
                "xi-api-key": elevenlabs_key,
                "Content-Type": "application/json"
            }
            
            clean_text = text
            if "[URGENT]" in text or "URGENT" in text:
                clean_text = text.replace("[URGENT]", "").replace("URGENT:", "").strip()
                
            data = {
                "text": clean_text,
                "model_id": "eleven_turbo_v2_5", # Ultra-fast model
            }
            
            response = requests.post(url, json=data, headers=headers)
            if response.status_code == 200:
                audio_data = np.frombuffer(response.content, dtype=np.int16)
                sd.play(audio_data, samplerate=24000)
                sd.wait()
                return
            else:
                print(f"\n[Hound]: ElevenLabs error {response.status_code}. Falling back to robotic voice.")
        except Exception as e:
            print(f"\n[Hound]: ElevenLabs failed ({e}). Falling back to robotic voice.")

    # Fallback to robotic pyttsx3
    try:
        import pyttsx3
        engine = pyttsx3.init()
        
        # Check for urgency tag
        if "[URGENT]" in text or "URGENT" in text:
            text = text.replace("[URGENT]", "").replace("URGENT:", "").strip()
            # Make the voice speak much faster and slightly frantic
            engine.setProperty('rate', 210) 
        else:
            # Normal conversational speed
            engine.setProperty('rate', 160)
            
        engine.say(text)
        engine.runAndWait()
    except Exception as e:
        print(f"TTS Error: {e}")

def stream_speak_worker(text_queue, mute=False):
    if mute:
        return
        
    import queue
    import threading
    import numpy as np
    import requests
    import sounddevice as sd
    from dotenv import load_dotenv
    import os
    
    load_dotenv()
    eleven_key = os.getenv("ELEVENLABS_API_KEY")
    
    audio_queue = queue.Queue()
    
    def fetcher_thread():
        while True:
            sentence = text_queue.get()
            if sentence is None:
                audio_queue.put(None)
                break
                
            if not eleven_key:
                # Local fallback
                audio_queue.put(("local", sentence))
                continue
                
            # ElevenLabs Fetch
            voice_id = "EXAVITQu4vr4xnSDxMaL"
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}?output_format=pcm_24000"
            headers = {"xi-api-key": eleven_key, "Content-Type": "application/json"}
            data = {"text": sentence, "model_id": "eleven_turbo_v2_5"}
            
            try:
                resp = requests.post(url, json=data, headers=headers)
                if resp.status_code == 200:
                    pcm = resp.content
                    audio_data = np.frombuffer(pcm, dtype=np.int16)
                    audio_queue.put(("pcm", audio_data))
                else:
                    audio_queue.put(("local", sentence))
            except Exception:
                audio_queue.put(("local", sentence))
                
    def player_thread():
        engine = None
        while True:
            item = audio_queue.get()
            if item is None:
                break
                
            mode, data = item
            if mode == "pcm":
                sd.play(data, samplerate=24000)
                sd.wait()
            elif mode == "local":
                if engine is None:
                    import pyttsx3
                    engine = pyttsx3.init()
                    voices = engine.getProperty('voices')
                    for v in voices:
                        if "Zira" in v.name or "female" in v.name.lower():
                            engine.setProperty('voice', v.id)
                            break
                    engine.setProperty('rate', 160)
                engine.say(data)
                engine.runAndWait()
                
    f_thread = threading.Thread(target=fetcher_thread, daemon=True)
    p_thread = threading.Thread(target=player_thread, daemon=True)
    
    f_thread.start()
    p_thread.start()
    
    f_thread.join()
    p_thread.join()

def speak(text, mute=False):
    if mute:
        return None
        
    # We run TTS in a separate process. 
    # This allows the Barge-in engine to instantly .terminate() it.
    p = multiprocessing.Process(target=_speak_process, args=(text, mute))
    p.start()
    return p
