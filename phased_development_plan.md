# Unified Phased Development Plan
## Project Hound: 24/7 Autonomous Voice Copilot & Opportunity Scout

**Document Version:** 2.0.0 (Unified Phase Plan)
**Focus:** Continuous 24/7 operation, Wake-word activation ("reminder"), Aggressive Barge-in, and Hybrid Text/Voice CLI.

---

## 1. Unified Software Requirements (New + Existing)

We have combined your original requirements (Resume engine, SQLite tracking, 5-Agent web scraper pipeline, multi-LLM routing) with your newly requested features:

### Core Capabilities
* **Data Storage & Scraping**: Web-scraped data (internships, hackathons) categorized and stored securely in a local JSON/SQLite database.
* **The "Wake Word" Activation**: System runs 24/7 in the background. It stays silent until the user explicitly says **"Reminder"**.
* **Proactive Expiry Alerts**: The system autonomously alerts the user when an intern/hackathon deadline is approaching.
* **Aggressive Barge-In Protocol**: If the system is talking and the user says *"stop stop stop"*, *"listen listen listen"*, or *"stop listen listen stop"*, it instantly cuts off its audio and starts listening.
* **Instant Mute & Sassy Mode Switch**: If the user says *"shut up"*, the system instantly cuts off audio to respect the user's environment, prints a sassy remark to the terminal (e.g. "How rude. Dropping to text mode."), and transitions to silent text Prompt Mode.
* **Conversational QA & RAG (Retrieval-Augmented Generation)**:
  * User can ask for details about an intern.
  * System first queries the local database/JSON.
  * If the data is missing, it autonomously triggers a live web search, synthesizes the answer, and speaks it back.
* **Conversational Scheduling**: User can seamlessly say *"Schedule a reminder to apply for this in 2 hours"*, and the Copilot logs a personal reminder.
* **Global Review**: User can say *"Remind my all work"* to get a full readout/summary of all pending tasks and applications.
* **Hybrid Text/Audio CLI**: A command-line tool where users can *type* their questions/reminders instead of speaking, but the system will reply with **both text and audio**.

---

## 2. Phased Development Strategy (From Easy to Tough)

To build this systematically without getting overwhelmed by complex voice-audio threading, we divide the project into 4 phases. Each phase builds a stable layer on top of the previous one.

### Phase 1: Core Scraper & Text-Based CLI (The Foundation)
*Goal: Build the brain and data layer before adding ears and a mouth.*
* **Scraping & Storage**: Implement the web scraper script to pull intern/hackathon data and store it categorized in a local `data.json` and SQLite database.
* **Text CLI**: Build `cli.py prompt`. User types a question, and the LLM (using Groq/OpenRouter APIs) answers via text.
* **Data Querying**: When the user types *"Details about XYZ intern"*, the LLM reads the JSON file to answer.
* **Manual Web Search Fallback**: If the JSON doesn't have the answer, the LLM triggers DuckDuckGo/Tavily search to find it.

### Phase 2: Proactive Daemon & Text-to-Speech (The Mouth)
*Goal: Give the system the ability to speak and run automatically in the background.*
* **Audio Output**: Integrate Text-to-Speech (ElevenLabs + local Windows TTS fallback). 
* **Hybrid Response**: Update the Phase 1 Text CLI so that when the user *types* a prompt, the system responds in *both text and audio*.
* **24/7 Daemon**: Create a background script (`daemon.py`) that checks the JSON/DB every hour. If an intern deadline is expiring soon, it plays an audio alert.
* **Show All Work**: Implement the *"Remind my all work"* command to fetch and read out the task list.

### Phase 3: Conversational Voice Assistant (The Ears)
*Goal: Enable the user to speak to the system interactively.*
* **Speech-to-Text (STT)**: Integrate Google Speech API and local `faster-whisper`.
* **Conversational Loop**: User runs `cli.py listen`. The system listens, processes via LLM, and speaks back.
* **Conversational Scheduling**: Allow the LLM to parse time (e.g., "remind me in 2 hours") and insert a new custom task into the database.
* **The Barge-in Engine**: Implement the interruption logic. While audio is playing, the microphone listens for exact phrases (*"stop stop stop"*, *"listen listen listen"*). If detected, it kills the audio process immediately.

### Phase 4: The 24/7 "Wake Word" Copilot (The Final Polish)
*Goal: True hands-free 24/7 operation without draining laptop battery.*
* **Wake-Word Engine**: Integrate a lightweight, low-CPU keyword spotter (like Porcupine or OpenWakeWord) that runs 24/7 looking *only* for the word **"Reminder"**.
* **Seamless Handoff**: When "Reminder" is heard, it wakes up the Phase 3 Conversational Voice Assistant, handles the user's requests, and then goes back to sleep.

---

## 3. Potential Inconsistencies & Design Challenges to Address

1. **The 24/7 Microphone Compute Drain**: 
   * *The Problem*: Running a full Speech-to-Text model (like Whisper) 24/7 to listen for the word "Reminder" will heavily drain your laptop's CPU and battery. 
   * *The Fix*: In Phase 4, we must use a specialized, ultra-lightweight "Wake Word Engine" that takes <1% CPU, which only triggers the heavy STT models *after* it hears the wake word.
2. **Audio Dumping on "All Work"**: 
   * *The Problem*: If you have 50 scrapped internships in your database and you say *"remind my all work"*, the TTS will speak non-stop for 10 minutes, which is terrible UX. 
   * *The Fix*: **User-Controlled Cutoff**. Instead of artificially limiting the readout, the AI will print the full list to the terminal and begin reading it aloud. If the user gets the information they need (or gets annoyed by the length), they simply use the *"shut up"* or *"stop"* barge-in command to instantly kill the audio and transition to text mode.
3. **Text Input in Public Spaces**:
   * *The Problem*: If you use the Text CLI in a library, you don't want it responding with loud audio automatically.
   * *The Fix*: The text CLI should have a simple `--mute` flag (e.g. `cli.py prompt "what is my schedule?" --mute`) to suppress the audio when typing.
4. **The "Library Problem" (Emergency Silence vs Persona)**:
   * *The Problem*: If the user frantically says *"shut up"*, they need instant physical silence. Having the agent argue back vocally (*"You are so rude..."*) exacerbates the embarrassment and introduces a rigid conversational loop just to mute the device.
   * *The Fix*: The **Instant Kill-Switch**. The agent instantly complies with physical silence but expresses its sassy persona *in text only* on the terminal before seamlessly transitioning into silent Prompt Mode.
