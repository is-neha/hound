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
                    model="whisper-large-v3",
                    file=audio_file,
                    response_format="text"
                )
            
            os.remove(temp_path)
            return transcription.strip()
        except Exception as e:
            print(f"[Hound]: Groq STT failed ({e}), falling back to Google...")
            
    # Fallback
    return r.recognize_google(audio_data)

def listen_for_barge_in(audio_process):
    """Listens for the kill-switch phrase while audio is playing."""
    r = sr.Recognizer()
    fs = 16000
    while audio_process is not None and audio_process.is_alive():
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
        
        if text.lower() in ["shut up", "stop", "exit", "quit"]:
            print("[Hound]: Exiting voice mode.")
            return False
            
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
    start_voice_loop()
