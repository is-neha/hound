import asyncio
import websockets
import json
import base64
import sounddevice as sd
import numpy as np
from database import get_top_urgent_alerts, mark_as_reminded
from daemon import get_api_key, read_profile

# Configuration
API_KEY = get_api_key()
HOST = "generativelanguage.googleapis.com"
URL = f"wss://{HOST}/ws/google.ai.generativelanguage.v1alpha.GenerativeService.BidiGenerateContent?key={API_KEY}"

FORMAT = 'int16'
CHANNELS = 1
RATE = 16000
CHUNK = 512

class GeminiLiveSession:
    def __init__(self):
        self.ws = None
        self.audio_in_stream = None
        self.audio_out_stream = None
        self.is_running = False

    async def send_audio(self):
        def callback(indata, frames, time, status):
            if not self.is_running or self.ws is None:
                raise sd.CallbackStop()
            
            # Convert audio to base64
            b64_data = base64.b64encode(indata.tobytes()).decode("utf-8")
            
            # We must use asyncio.run_coroutine_threadsafe to send via websocket from the audio thread
            # To keep it simpler, we just append to an asyncio queue
            try:
                self.audio_queue.put_nowait(b64_data)
            except asyncio.QueueFull:
                pass

        self.audio_queue = asyncio.Queue(maxsize=100)
        self.audio_in_stream = sd.InputStream(samplerate=RATE, channels=CHANNELS, dtype=FORMAT, blocksize=CHUNK, callback=callback)
        self.audio_in_stream.start()

        while self.is_running:
            try:
                b64_data = await asyncio.wait_for(self.audio_queue.get(), timeout=1.0)
                msg = {
                    "realtimeInput": {
                        "mediaChunks": [{
                            "mimeType": "audio/pcm;rate=16000",
                            "data": b64_data
                        }]
                    }
                }
                await self.ws.send(json.dumps(msg))
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                print(f"[Live] Send audio error: {e}")
                break

    async def receive_audio(self):
        self.audio_out_stream = sd.OutputStream(samplerate=24000, channels=1, dtype='int16')
        self.audio_out_stream.start()
        
        while self.is_running:
            try:
                # 5-second ping timeout check to prevent zombie sockets
                response = await asyncio.wait_for(self.ws.recv(), timeout=5.0)
                data = json.loads(response)
                
                # Check for Server Content (Audio)
                if "serverContent" in data:
                    parts = data["serverContent"].get("modelTurn", {}).get("parts", [])
                    for part in parts:
                        if "inlineData" in part:
                            pcm_b64 = part["inlineData"]["data"]
                            pcm_bytes = base64.b64decode(pcm_b64)
                            audio_np = np.frombuffer(pcm_bytes, dtype=np.int16)
                            self.audio_out_stream.write(audio_np)
                            
                # Check for Tool Call
                elif "toolCall" in data:
                    print("\n[Live] Tool Call Received! Updating profile...")
                    # Temporarily stop sending audio
                    self.audio_in_stream.stop()
                    
                    calls = data["toolCall"]["functionCalls"]
                    for call in calls:
                        if call["name"] == "update_profile":
                            instruction = call["args"].get("instruction", "")
                            print(f" -> Adding rule: {instruction}")
                            
                            # Atomic Profile Update
                            profile = read_profile()
                            rules = profile.get("dynamic_rules", [])
                            rules.append(instruction)
                            profile["dynamic_rules"] = rules
                            
                            import os
                            with open("profile_tmp.json", "w") as f:
                                json.dump(profile, f, indent=2)
                            os.replace("profile_tmp.json", "profile.json")
                            
                            # Send Tool Response
                            resp_msg = {
                                "toolResponse": {
                                    "functionResponses": [{
                                        "id": call["id"],
                                        "name": "update_profile",
                                        "response": {"result": "Profile successfully updated."}
                                    }]
                                }
                            }
                            await self.ws.send(json.dumps(resp_msg))
                            
                    # Resume audio
                    self.audio_in_stream.start()
                    
            except asyncio.TimeoutError:
                # If Google doesn't send anything for 5 seconds, we ping
                # Wait, Gemini Live API doesn't support manual ping frames easily via raw JSON unless client sends nothing.
                # If we get a timeout, it just means the model is silent. It's fine.
                continue
            except websockets.exceptions.ConnectionClosed:
                print("[Live] Connection closed by server.")
                break
            except Exception as e:
                print(f"[Live] Receive error: {e}")
                break

    async def run(self):
        print("\n[Live] Pulling urgent alerts from Database...")
        alerts = get_top_urgent_alerts()
        alert_text = "No urgent alerts right now."
        if alerts:
            alert_text = "Here are your urgent alerts:\n"
            for opp_id, txt in alerts:
                alert_text += f"- {txt}\n"
                mark_as_reminded(opp_id)
        
        print("[Live] Connecting to Gemini Live API...")
        profile = read_profile()
        
        setup_msg = {
            "setup": {
                "model": "models/gemini-2.5-flash-native-audio-preview-12-2025",
                "systemInstruction": {
                    "parts": [{"text": (
                        "You are Hound, a helpful Voice AI. The user just woke you up. "
                        f"Read them these alerts playfully and concisely:\n{alert_text}\n\n"
                        f"User Profile rules: {profile.get('dynamic_rules', [])}"
                    )}]
                },
                "tools": [{
                    "functionDeclarations": [{
                        "name": "update_profile",
                        "description": "If the user says they like or dislike something, call this to update their permanent memory rules.",
                        "parameters": {
                            "type": "OBJECT",
                            "properties": {
                                "instruction": {"type": "STRING", "description": "e.g. 'The user does not want hackathons'"}
                            },
                            "required": ["instruction"]
                        }
                    }]
                }]
            }
        }
        
        try:
            async with websockets.connect(URL) as ws:
                self.ws = ws
                self.is_running = True
                
                # 1. Send Setup
                await ws.send(json.dumps(setup_msg))
                # Wait for setup complete
                resp = await ws.recv()
                
                # 2. Start Full Duplex Audio
                print("========================================")
                print(" 🟢 LIVE VOICE SESSION ACTIVE. TALK! 🟢 ")
                print(" (Press Ctrl+C to close session)        ")
                print("========================================")
                
                send_task = asyncio.create_task(self.send_audio())
                recv_task = asyncio.create_task(self.receive_audio())
                
                # Enforce max 10 minute session to prevent context explosion
                done, pending = await asyncio.wait(
                    [send_task, recv_task], 
                    return_when=asyncio.FIRST_COMPLETED,
                    timeout=600 # 10 minutes
                )
                
                print("[Live] Session ended. Cleaning up...")
                self.is_running = False
                
        finally:
            self.is_running = False
            if self.audio_in_stream:
                self.audio_in_stream.stop()
                self.audio_in_stream.close()
            if self.audio_out_stream:
                self.audio_out_stream.stop()
                self.audio_out_stream.close()

def start_session():
    asyncio.run(GeminiLiveSession().run())
