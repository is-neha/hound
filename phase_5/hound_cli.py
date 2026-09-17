import os
import sys
import threading
import time
import multiprocessing
from prompt_toolkit import PromptSession
from prompt_toolkit.styles import Style
from prompt_toolkit.formatted_text import HTML
from rich.console import Console
from rich.markdown import Markdown
from rich.text import Text
from rich.panel import Panel

# Core Hound Modules
from llm import query_llm
from scraper import search_and_store_opportunities
from database import init_db
from tts import _speak_process
import listen  # For the STT tools

console = Console()

BANNER = """
[bold cyan]
██╗  ██╗ ██████╗ ██╗   ██╗██████╗ ██████╗ 
██║  ██║██╔═══██╗██║   ██║██╔══██╗██╔══██╗
███████║██║   ██║██║   ██║██║  ██║██║  ██║
██╔══██║██║   ██║██║   ██║██║  ██║██║  ██║
██║  ██║╚██████╔╝╚██████╔╝██████╔╝██████╔╝
╚═╝  ╚═╝ ╚═════╝  ╚═════╝ ╚═════╝ ╚═════╝ 
[/bold cyan]
[bold bright_black]Autonomous Scout Engine.  Version: v1.0[/bold bright_black]
"""

def print_hound(msg):
    console.print(f"\n[bold cyan]Hound:[/bold cyan] {msg}")

def print_user(msg):
    console.print(f"\n[bold green]> {msg}[/bold green]\n")

def trigger_voice_input():
    """Triggered when the user interrupts the bot, it opens the mic to listen."""
    console.print("[dim][Mic Open - Listening...][/dim]")
    
    # We reuse the robust record_until_silence logic from listen.py
    # But for simplicity in the CLI, we can just use the standard STT
    import speech_recognition as sr
    fs = 16000
    raw_audio_bytes = listen.record_until_silence(fs=fs, silence_duration=1.2)
    
    if not raw_audio_bytes:
        console.print("[dim]No speech detected.[/dim]")
        return
        
    console.print("[dim]Processing voice...[/dim]")
    r = sr.Recognizer()
    audio = sr.AudioData(raw_audio_bytes, fs, 2)
    text = listen.transcribe_audio(r, audio)
    
    if text:
        print_user(f"(Voice) {text}")
        process_query(text)

def hound_speak_and_listen_for_barge_in(text):
    """Speaks the text, but constantly listens for 'stop' or 'listen' to interrupt it."""
    p = multiprocessing.Process(target=_speak_process, args=(text,))
    p.start()
    
    import speech_recognition as sr
    import sounddevice as sd
    
    r = sr.Recognizer()
    fs = 16000
    
    interrupted = False
    
    # Listen for barge-in while speaking
    while p.is_alive():
        try:
            rec = sd.rec(int(1.5 * fs), samplerate=fs, channels=1, dtype='int16')
            sd.wait()
            if not p.is_alive():
                break
                
            audio = sr.AudioData(rec.tobytes(), fs, 2)
            
            # Use local Whisper for fast barge-in detection
            try:
                text_heard = r.recognize_whisper(audio, model="base.en").lower()
            except Exception:
                # Fallback to google if whisper isn't installed
                text_heard = r.recognize_google(audio).lower()
                
            if any(word in text_heard for word in ["stop", "shut up", "listen", "wait", "hold on"]):
                console.print(f"\n[bold red][Barge-in detected! Heard: '{text_heard}'][/bold red]")
                p.terminate()
                interrupted = True
                break
        except Exception:
            pass
            
    if p.is_alive():
        p.join()
        
    if interrupted:
        # If the user interrupted, immediately open the mic for them to speak!
        trigger_voice_input()

def process_query(query):
    if "remind" in query.lower() or "reminder" in query.lower():
        import datetime
        from database import get_all_opportunities, mark_as_reminded
        ops = get_all_opportunities()
        today_str = datetime.date.today().isoformat()
        
        unreminded = [o for o in ops if o.get('last_reminded_date') != today_str]
        
        if not unreminded:
            answer = "You have no new updates right now. Everything has been covered for today."
            print_hound(answer)
            hound_speak_and_listen_for_barge_in(answer)
            return
            
        top_3 = unreminded[:3]
        answer = f"You have {len(unreminded)} new updates. I have printed the full list to your terminal. The top three are: "
        
        # Beautiful Rich Panel for the terminal UI
        items = "\n\n".join([f"[bold]{o['title']}[/bold]\n[dim]{o['link']}[/dim]" for o in ops])
        console.print(Panel(items, title="ALL TRACKED OPPORTUNITIES", border_style="cyan"))
        
        for i, o in enumerate(top_3):
            answer += f"Number {i+1}, {o['title']}. "
            mark_as_reminded(o['id'], today_str)
            
        print_hound(answer)
        hound_speak_and_listen_for_barge_in(answer)
        return

    # Normal LLM Query
    console.print("[dim]Thinking...[/dim]")
    answer = query_llm(query)
    print_hound("")
    console.print(Markdown(answer))
    hound_speak_and_listen_for_barge_in(answer)

def main():
    init_db()
    os.system('cls' if os.name == 'nt' else 'clear')
    console.print(BANNER)
    
    style = Style.from_dict({
        'prompt': 'bold #00ff00',
    })
    
    session = PromptSession()
    
    while True:
        try:
            text = session.prompt(HTML('<prompt>&gt; </prompt>'), style=style)
            
            if not text.strip():
                continue
                
            if text.strip().lower() in ['exit', 'quit']:
                break
                
            if text.strip().lower() == 'scrape':
                search_and_store_opportunities()
                continue
                
            process_query(text)
            
        except KeyboardInterrupt:
            continue
        except EOFError:
            break

if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
