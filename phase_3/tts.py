import pyttsx3
import multiprocessing

def _speak_process(text):
    try:
        engine = pyttsx3.init()
        engine.setProperty('rate', 180)
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
