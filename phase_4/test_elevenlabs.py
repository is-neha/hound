import os
import requests
import sounddevice as sd
import numpy as np
from dotenv import load_dotenv

# Load the .env file
load_dotenv()

eleven_key = os.getenv("ELEVENLABS_API_KEY")

if not eleven_key or eleven_key.strip() == "":
    print("❌ ERROR: ELEVENLABS_API_KEY is missing or empty in your .env file!")
    exit(1)

print(f"✅ Key found: {eleven_key[:5]}...{eleven_key[-4:]}")

voice_id = "EXAVITQu4vr4xnSDxMaL" # Bella
url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}?output_format=pcm_24000"

headers = {
    "xi-api-key": eleven_key,
    "Content-Type": "application/json"
}

data = {
    "text": "Hello! This is a successful test of the Eleven Labs API.",
    "model_id": "eleven_turbo_v2_5" 
}

print("🎙️ Requesting audio from ElevenLabs...")
try:
    response = requests.post(url, json=data, headers=headers)
    
    if response.status_code == 200:
        print("✅ API Success! Playing audio...")
        raw_pcm = response.content
        audio_data = np.frombuffer(raw_pcm, dtype=np.int16)
        sd.play(audio_data, samplerate=24000)
        sd.wait()
        print("🎵 Audio playback complete.")
    else:
        print(f"❌ API ERROR: Status Code {response.status_code}")
        print(f"🔍 Exact Reason: {response.text}")
        
except Exception as e:
    print(f"❌ NETWORK ERROR: {e}")
