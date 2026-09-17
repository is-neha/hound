import pyttsx3
import multiprocessing

def _speak_process(text, mute=False):
    if mute: return
    
    # Check for urgency tag
    is_urgent = False
    if "[URGENT]" in text or "URGENT" in text:
        text = text.replace("[URGENT]", "").replace("URGENT:", "").strip()
        is_urgent = True
        
    import os
    from dotenv import load_dotenv
    load_dotenv()
    
    eleven_key = os.getenv("ELEVENLABS_API_KEY")
    
    # --- TIER 1: ElevenLabs (High Quality Girl Voice) ---
    if eleven_key and eleven_key.strip():
        try:
            import requests
            import sounddevice as sd
            import numpy as np
            
            # Bella Voice ID: EXAVITQu4vr4xnSDxMaL
            # Rachel Voice ID: 21m00Tcm4TlvDq8ikWAM
            voice_id = "EXAVITQu4vr4xnSDxMaL"
            
            # turbo_v2_5 is 50% cheaper and way faster!
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}?output_format=pcm_24000"
            
            headers = {
                "xi-api-key": eleven_key,
                "Content-Type": "application/json"
            }
            
            data = {
                "text": text,
                "model_id": "eleven_turbo_v2_5" 
            }
            
            response = requests.post(url, json=data, headers=headers)
            
            if response.status_code == 200:
                # Read raw PCM bytes and convert to numpy array for sounddevice
                raw_pcm = response.content
                audio_data = np.frombuffer(raw_pcm, dtype=np.int16)
                
                # If urgent, we can artificially speed up the audio via samplerate
                playback_rate = 24000
                if is_urgent:
                    playback_rate = int(24000 * 1.25) # 25% faster
                    
                sd.play(audio_data, samplerate=playback_rate)
                sd.wait() # Block until done (required so the process doesn't exit prematurely)
                return
            else:
                print(f"[Hound]: ElevenLabs failed ({response.status_code}). Falling back to local TTS...")
        except Exception as e:
            print(f"[Hound]: ElevenLabs error ({e}). Falling back to local TTS...")
            
    # --- TIER 2: Pyttsx3 (Robotic Local Fallback) ---
    try:
        import pyttsx3
        engine = pyttsx3.init()
        
        # Try to find a female voice in local Windows registry
        voices = engine.getProperty('voices')
        for v in voices:
            if "Zira" in v.name or "female" in v.name.lower():
                engine.setProperty('voice', v.id)
                break
                
        if is_urgent:
            engine.setProperty('rate', 210)
        else:
            engine.setProperty('rate', 160)
            
        engine.say(text)
        engine.runAndWait()
    except Exception as e:
        print(f"TTS Error: {e}")

def speak(text, mute=False):
    if mute:
        return None
        
    # We run TTS in a separate process. 
    # This allows the Barge-in engine to instantly .terminate() it.
    p = multiprocessing.Process(target=_speak_process, args=(text,))
    p.start()
    return p
