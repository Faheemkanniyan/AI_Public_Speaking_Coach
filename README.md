# SpeakPro AI – AI Public Speaking Coach Web Application

**SpeakPro AI** is an enterprise-grade AI-powered Public Speaking Coach web application built with **Python**, **Django 5**, **Google Gemini AI**, **ReportLab PDF generation**, and modern **Glassmorphic Dark Mode UI/UX** (with neon green `#00ff88` and electric blue `#00d2ff` aesthetics).

---

## 🌟 Key Features

1. **Speech Practice Studio (`/practice/`)**
   - **Real-Time Audio Waveform Visualizer**: Uses HTML5 Canvas and Web Audio API (`AnalyserNode`) to display a live, glowing audio waveform while speaking.
   - **Countdown & Speech Timer**: Interactive 3-2-1 countdown before recording and digital speech elapsed timer.
   - **Web Speech API Speech-to-Text**: Automatic real-time speech transcription into an editable text box.
   - **Demo Speech Simulator**: Instant testing of AI analysis even without a microphone.
   - **Topic Generator**: Fetches random speaking challenges across 5 categories (*General, Leadership, Technology, Social, Job Interview*).

2. **10-Dimension AI Speech Evaluation Engine (`/result/<id>/`)**
   - Evaluates speech recordings and transcripts across 10 key metrics:
     1. Overall Speaking Score (`0-100`)
     2. Grammar & Syntax Accuracy
     3. Lexical Variety & Vocabulary
     4. Vocal Confidence & Authority
     5. Fluency & Rhythm
     6. Overall Communication Impact
     7. Filler Word Detection (`"um"`, `"uh"`, `"like"`, `"basically"`)
     8. Pacing & WPM Analysis
     9. Structure & Transition Analysis
     10. Executive Actionable Suggestions
   - **Highlighted Grammar Corrections**: Side-by-side table displaying the original phrase, recommended correction, and executive coaching explanation.
   - **Circular Score Gauge**: Dynamic animated SVG score gauge and skill competency progress bars.

3. **ReportLab Professional PDF Report Generator (`/report/download/<id>/`)**
   - Generates and stores professional multi-page PDF reports in `D:\AI_Public_Speaking_Coach\reports\`.
   - Includes custom typography, executive summary tables, skill progress bars, and highlighted corrections.

4. **Interactive AI Public Speaking Coach (`/ai-coach/`)**
   - Real-time conversational Q&A assistant powered by Google Gemini AI.
   - Interactive quick prompt chips for instant advice on vocal variety, filler words, stage fright, and interview structure.

5. **Gamified Speaker Dashboard & Analytics (`/dashboard/` & `/analytics/`)**
   - **Practice Streak Tracking**: Calculates and rewards consecutive daily practice streaks.
   - **Chart.js Visualizations**:
     - **Radar Chart**: 5-core competency breakdown.
     - **Line Chart**: Historical speaking score progression.
     - **Bar Chart**: Performance comparison by topic category.
     - **Pie Chart**: Practice topic distribution.
   - **Achievement Badges**: Unlocks gamified badges (*First Speech, 7-Day Streak, Grammar Master, Fluent Orator, Executive Speaker*).

---

## 📁 Workspace & Project Directory Structure

All files, databases, media uploads, ReportLab PDFs, and virtual environments are contained exclusively inside **`D:\AI_Public_Speaking_Coach\`**:

```text
D:\AI_Public_Speaking_Coach\
├── app\                           # Core Django App (Models, Views, Forms, API, Services)
│   ├── management\
│   │   └── commands\
│   │       └── seed_data.py       # Automated database seeding command
│   ├── services\
│   │   ├── gemini_service.py      # 10-dimension Google Gemini AI evaluator + NLP fallback
│   │   ├── speech_service.py      # Audio upload & speech processing workflow
│   │   ├── report_service.py      # ReportLab PDF generation engine
│   │   ├── analytics_service.py   # Chart.js JSON dataset builder
│   │   └── ai_coach_service.py    # Conversational AI coach chatbot engine
│   ├── models.py                  # 9 schema models (UserProfile, Topic, SpeechSession, SpeechReport, etc.)
│   ├── views.py                   # HTML template rendering controllers
│   ├── api_views.py               # AJAX/JSON endpoints (/api/speech/analyze/, /api/coach/chat/, etc.)
│   └── urls.py                    # App URL routing
├── config\                        # Django Project Configuration
│   ├── settings.py                # Override paths to D:\AI_Public_Speaking_Coach\
│   └── urls.py                    # Root URL configuration
├── database\                      # SQLite Database Directory
│   └── db.sqlite3                 # Main database file
├── uploads\                       # User recorded speech audio webm/wav files
├── reports\                       # Generated ReportLab PDF evaluation reports
├── templates\                     # Modern Glassmorphic Dark Mode HTML Templates
│   ├── base.html
│   ├── landing.html
│   ├── dashboard.html
│   ├── practice.html
│   ├── result.html
│   ├── history.html
│   ├── analytics.html
│   ├── profile.html
│   ├── ai_coach.html
│   ├── settings_page.html
│   └── auth\
│       ├── login.html
│       ├── signup.html
│       └── forgot_password.html
├── static\                        # Frontend CSS, JavaScript & Assets
│   ├── css\style.css              # Dark mode glassmorphism, glowing borders, neon accents
│   └── js\
│       ├── main.js                # Toasts, theme toggle, utilities
│       ├── recorder.js            # Live audio waveform, countdown, Web Speech API STT
│       ├── charts.js              # Chart.js Radar, Line, Bar, and Pie graphs
│       └── ai_coach.js            # Real-time AI chat bubbles
├── venv\                          # Isolated Python Virtual Environment
├── manage.py
└── requirements.txt               # Dependencies (django, reportlab, google-generativeai, etc.)
```

---

## 🚀 Getting Started & Running Locally

### 1. Activate the Python Virtual Environment
Open PowerShell or Command Prompt:
```powershell
D:\AI_Public_Speaking_Coach\venv\Scripts\activate
```

### 2. Configure API Keys (`.env` file)
All API keys and environment configuration are stored centrally in `.env` at the project root.
- Open `.env` (or copy `.env.example` to `.env`) and add your **Google Gemini AI API Key**:
  ```ini
  GEMINI_API_KEY=your_google_gemini_api_key_here
  DJANGO_SECRET_KEY=django-insecure-speakpro-ai-public-speaking-coach-2026-secret-key-!@#
  DEBUG=True
  ```
> **Note:** If `GEMINI_API_KEY` is left blank, SpeakPro AI automatically switches to its intelligent offline NLP fallback engine so you can run and test the app without an API key!

### 3. Apply Database Migrations & Seed Data
```powershell
python D:\AI_Public_Speaking_Coach\manage.py migrate
python D:\AI_Public_Speaking_Coach\manage.py seed_data
```
The `seed_data` command creates:
- **Admin Account**: `admin` / `admin12345` (`admin@speakpro.ai`)
- **Demo Speaker Account**: `speaker` / `speakpro2026` (`speaker@speakpro.ai`)
- **15+ Diverse Speaking Topics** across 5 categories
- **Demo Speech Sessions & AI Reports** with ReportLab PDF reports
- **Achievement Badges & Dashboard Analytics**

### 4. Run the Development Server
```powershell
python D:\AI_Public_Speaking_Coach\manage.py runserver
```
Open your browser and navigate to: **`http://127.0.0.1:8000/`**

---

## 🔑 Configuring Google Gemini AI Key (Optional)

By default, **SpeakPro AI works out-of-the-box** using an intelligent NLP heuristic fallback engine if no API key is provided.

To enable **live Google Gemini 3.1 Pro (High)** evaluations:
1. Set your `GEMINI_API_KEY` environment variable in your system or terminal:
   ```powershell
   $env:GEMINI_API_KEY="your-google-gemini-api-key"
   ```
2. Or configure it inside `D:\AI_Public_Speaking_Coach\config\settings.py`.

---

## 📄 License & Storage Verification

- Stored exclusively on `D:\AI_Public_Speaking_Coach\`.
- All user audio recordings reside in `D:\AI_Public_Speaking_Coach\uploads\`.
- All downloadable ReportLab PDF reports reside in `D:\AI_Public_Speaking_Coach\reports\`.
