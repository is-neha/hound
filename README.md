# Hound 🐕: Autonomous AI Research Agent

Hound is an advanced, autonomous background research agent and interactive voice assistant. It proactively scours the internet for high-value opportunities—such as software engineering internships, open-source hackathons, technology news, and scholarships—tailored specifically to a dynamic user profile. 

Instead of waiting for you to search, Hound constantly finds the needle in the haystack and uses real-time conversational AI to alert you via a local wake-word engine.

---

## 🌟 Key Features

* **Autonomous Background Research**: Runs silently in the background (via \daemon.py\), generating unique DuckDuckGo and Jina AI queries using Google Gemini to hunt for niche opportunities.
* **LLM Data Structuring**: Converts messy website markdown into structured JSON, intelligently guessing deadlines and generating conversational alerts.
* **Smart Deduplication & Idempotency**: Uses a local SQLite database (\hound.db\) to ensure you are never notified of the same event twice.
* **Offline Wake Word Detection**: Uses \openwakeword\ to listen for \"hey_jarvis"\ or \"alexa"\ entirely locally, preserving privacy.
* **Full-Duplex Voice AI**: Connects directly to the Gemini Live API over WebSockets for natural, instantaneous, and uninterrupted voice conversations.
* **Dynamic Memory Updates**: Hound can permanently update its own internal user profile through conversational function calling, learning what you like and dislike over time.

---

## 🏗️ System Architecture

The ecosystem is decoupled into highly specialized, asynchronous Python modules:

1. **The Daemon (\daemon.py\)**: The autonomous workhorse. Generates queries, fetches URLs via DDG/Brave, scrapes full markdown using \.jina.ai\, and structures the data using Gemini 3.6 Flash.
2. **The Database (\database.py\)**: An SQLite3 Write-Ahead Logging (WAL) persistent layer. It manages expiration dates, urgency scores, and duplicate prevention.
3. **The Trigger (\wake.py\)**: A lightweight TFLite inference engine monitoring a 16kHz audio stream for the wake word.
4. **The Live Session (\live_session.py\)**: A real-time WebSocket connection to \gemini-2.5-flash-native-audio\, passing the top urgent alerts as system instructions for the AI to read aloud to the user.

---

## 🚀 Getting Started

### Prerequisites
* Python 3.10+
* A valid Google Gemini API Key

### Installation

1. **Clone the repository:**
   \\\ash
   git clone https://github.com/yourusername/anthropoic-sdk-hound.git
   cd anthropoic-sdk-hound/phase_6
   \\\

2. **Install dependencies:**
   \\\ash
   pip install -r requirements.txt
   \\\

3. **Configure API Keys:**
   Create an \pi_keys.json\ and \.env\ file in your root tracking directories (these are deliberately ignored by \.gitignore\ to prevent secret leaks).
   \\\json
   {
       "gemini": ["YOUR_GEMINI_API_KEY"]
   }
   \\\

### Running Hound

**1. Start the Autonomous Daemon:**
Leave this running in the background. It will wake up every 45-75 minutes to scour the internet.
\\\ash
python daemon.py
\\\

**2. Start the Wake Word Listener:**
Run this in a separate terminal. When you say the wake word, it will instantly fetch the highest urgency alerts from the database and start a real-time voice conversation.
\\\ash
python wake.py
\\\

