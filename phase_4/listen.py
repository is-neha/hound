import speech_recognition as sr
import sounddevice as sd
import numpy as np
from tts import speak
from llm import query_llm
import time
import os

def transcribe_audio(r, audio_data):
    """Transcribes audio using Groq Whisper if key exists, else falls back to Google."""
    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key:
        try:
            from openai import OpenAI
            import tempfile
            
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_wav:
                temp_wav.write(audio_data.get_wav_data())
                temp_path = temp_wav.name
                
            client = OpenAI(api_key=groq_key, base_url="https://api.groq.com/openai/v1")
            with open(temp_path, "rb") as audio_file:
                transcription = client.audio.transcriptions.create(
                    model="whisper-large-v3-turbo",
                    file=audio_file,
                    response_format="text"
                )
            
            os.remove(temp_path)
            return transcription.strip()
        except Exception as e:
            print(f"[Hound]: Groq STT failed ({e}), falling back to local Whisper...")
            
    # Fallback 1: Local Whisper (base.en)
    try:
        # This requires `pip install openai-whisper`
        return r.recognize_whisper(audio_data, model="base.en")
    except ImportError:
        print("[Hound]: openai-whisper not installed. Falling back to Google...")
    except Exception as e:
        print(f"[Hound]: Local Whisper failed ({e}). Falling back to Google...")
        
    # Fallback 2: Google
    return r.recognize_google(audio_data)

def listen_for_barge_in(audio_process):
    """Listens for the kill-switch phrase while audio is playing, or Ctrl+P/P key press."""
    r = sr.Recognizer()
    fs = 16000
    import msvcrt
    
    while audio_process is not None and audio_process.is_alive():
        # Check keyboard first
        if msvcrt.kbhit():
            key = msvcrt.getch()
            # Ctrl+P is \x10, 'p' is b'p', 'P' is b'P'
            if key in [b'p', b'P', b'\x10']:
                print("\n[Hound]: TTS stopped via keyboard (Ctrl+P).")
                audio_process.terminate()
                return True
                
        try:
            # We record in 1.5 second bursts for barge-in
            rec = sd.rec(int(1.5 * fs), samplerate=fs, channels=1, dtype='int16')
            sd.wait()
            audio = sr.AudioData(rec.tobytes(), fs, 2)
            # Use fallback for barge-in since it's just checking simple keywords rapidly
            text = r.recognize_google(audio).lower()
            
            if any(phrase in text for phrase in ["shut up", "stop", "listen"]):
                print("\n[Barge-In Detected!]: How rude. Dropping to text mode. Killing audio.")
                audio_process.terminate()
                return True
        except (sr.UnknownValueError, sr.RequestError):
            continue
        except Exception:
            continue
    return False

def record_until_silence(fs=16000, silence_duration=0.9):
    """Dynamically records audio until the user stops speaking for 900ms."""
    chunk_duration = 0.1 # 100ms chunks
    chunk_samples = int(fs * chunk_duration)
    audio_data = []
    has_spoken = False
    silence_timer = 0.0
    
    # Use a streaming input so we can continuously read chunks
    with sd.InputStream(samplerate=fs, channels=1, dtype='float32') as stream:
        # 1. Auto-calibrate background noise (listen for 0.5s before speaking)
        bg_rms = []
        for _ in range(5):
            chunk, _ = stream.read(chunk_samples)
            bg_rms.append(np.sqrt(np.mean(chunk**2)))
        
        # Threshold is 3x the average background noise, with a minimum floor
        threshold = np.mean(bg_rms) * 3.0
        threshold = max(0.005, threshold)
        
        print("\n[Hound]: Listening...")
        
        while True:
            chunk, _ = stream.read(chunk_samples)
            audio_data.append(chunk)
            rms = np.sqrt(np.mean(chunk**2))
            
            if rms > threshold:
                has_spoken = True
                silence_timer = 0.0 # User is speaking, reset silence timer
            elif has_spoken:
                silence_timer += chunk_duration # User paused, increment timer
                
            # If they paused for 900ms, stop recording immediately!
            if has_spoken and silence_timer >= silence_duration:
                break
                
            # Failsafe: Timeout if no speech detected for 10 seconds
            if not has_spoken and (len(audio_data) * chunk_duration) > 10.0:
                return None
                
    # Convert float32 array into int16 bytes for the SpeechRecognizer
    audio_np = np.concatenate(audio_data)
    audio_int16 = np.int16(audio_np * 32767)
    return audio_int16.tobytes()

def trigger_reminders():
    import datetime
    from database import get_all_opportunities, mark_as_reminded
    ops = get_all_opportunities()
    today_str = datetime.date.today().isoformat()
    
    print("\n" + "-"*40)
    print(" ALL TRACKED OPPORTUNITIES ")
    print("-"*40)
    for o in ops:
        print(f"- {o['title']}")
        print(f"  Link: {o['link']}\n")
    print("-"*40 + "\n")
    
    unreminded = [o for o in ops if o.get('last_reminded_date') != today_str]
    
    if not unreminded:
        return False # No new updates
        
    top_3 = unreminded[:3]
    answer = f"You have {len(unreminded)} new updates. I have printed the full list to your terminal. The top three are: "
    for i, o in enumerate(top_3):
        answer += f"Number {i+1}, {o['title']}. "
        mark_as_reminded(o['id'], today_str) # Mark it as reminded today!
        
    print(f"[Hound]: {answer}")
    from tts import speak
    audio_process = speak(answer)
    listen_for_barge_in(audio_process)
    
    if audio_process and audio_process.is_alive():
        audio_process.join()
    return True

def listen_and_respond():
    r = sr.Recognizer()
    fs = 16000
    
    raw_audio_bytes = record_until_silence(fs=fs, silence_duration=0.9)
    if not raw_audio_bytes:
        return True # Loop continues if timeout
        
    print("[Hound]: Processing audio...")
    try:
        audio = sr.AudioData(raw_audio_bytes, fs, 2)
        text = transcribe_audio(r, audio)
        print(f"You said: \"{text}\"")
        
        if text.lower() in ["shut up", "stop", "exit", "quit", "sleep"]:
            print("[Hound]: Exiting voice mode.")
            return False
            
        # Intercept "reminder" or "remind" command
        if "remind" in text.lower() or "reminder" in text.lower():
            if not trigger_reminders():
                answer = "You have no new updates right now. Everything has been covered for today."
                print(f"[Hound]: {answer}")
                p = speak(answer)
                listen_for_barge_in(p)
                if p and p.is_alive(): p.join()
            return True

        # Intercept dynamic timers
        if "set reminder for" in text.lower() or "set a reminder for" in text.lower():
            import re
            import threading
            
            match = re.search(r'(\d+)\s*(minute|min|second|sec|hour|hr)', text.lower())
            if match:
                val = int(match.group(1))
                unit = match.group(2)
                secs = val
                if 'min' in unit: secs = val * 60
                elif 'hour' in unit or 'hr' in unit: secs = val * 3600
                
                def timer_done():
                    print(f"\n\n[Hound]: 🚨 BEEP! Your {val} {unit} reminder is up! 🚨\n> ", end="")
                    p = speak(f"[URGENT] Reminder! Your {val} {unit} timer is up!")
                    if p: p.join()
                    
                threading.Timer(secs, timer_done).start()
                
                answer = f"Timer set for {val} {unit}."
                print(f"[Hound]: {answer}")
                audio_process = speak(answer)
                listen_for_barge_in(audio_process)
                return True

        print("[Hound]: Thinking...")
        answer = query_llm(text)
        print(f"[Hound]: {answer}")
        
        audio_process = speak(answer)
        listen_for_barge_in(audio_process)
        
        if audio_process and audio_process.is_alive():
            audio_process.join()
            
        return True
        
    except sr.UnknownValueError:
        return True
    except sr.RequestError as e:
        print(f"[Hound]: API Error: {e}")
        return True
    except Exception as e:
        print(f"[Hound]: Error: {e}")
        return True

def start_voice_loop():
    print("--- Voice Copilot Activated ---")
    active = True
    while active:
        active = listen_and_respond()
        time.sleep(0.5)

if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    start_voice_loop()
