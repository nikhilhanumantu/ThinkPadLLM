# ThinkPadLLM — The Intelligent Canvas

> AI-powered learning workspace inspired by Google NotebookLM. Upload notes, images, PDFs, or YouTube videos and get AI-generated summaries, explanations, flowcharts, quizzes, and an intelligent chat assistant.

## 🏗️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend |HTML CSS JS |
| Backend | Python Flask + JWT Auth |
| AI | Google Gemini 1.5 Pro |
| Database | MongoDB Atlas |
| OCR | Tesseract + PyPDF2 |
| Diagrams | Mermaid.js |
| PDF Export | jsPDF + html2canvas |

---

## ⚡ Quick Start

### Step 1 — Configure environment variables

**Backend** (`backend/.env`):
```env
MONGO_URI=mongodb+srv://thinkpadllm:think0987@cluster0.ek96tpg.mongodb.net/thinkpadlm
GEMINI_API_KEY=your_gemini_api_key
JWT_SECRET_KEY=your_very_secret_key
```

### Step 2 — Start the Server

Simply double-click the **`start-backend.bat`** file in the root of the project.

Alternatively, run from your terminal:
```bash
cd backend
venv\Scripts\activate
python run.py
```

### Step 3 — Open in Browser

Open your browser and navigate to:
👉 **http://localhost:5000**

That's it! The entire application is fully running, serve-ready, and interactive!

---

## 📁 Project Structure

```
thinkpadlm/
├── api/                    # Vercel serverless integration
│   └── index.py            # Vercel entry bridge to Flask
├── backend/                # Monolithic Flask Server
│   ├── app/
│   │   ├── config/         # MongoDB initialization
│   │   ├── models/         # Database schemas
│   │   ├── routes/         # API & HTML serving blueprints
│   │   ├── services/       # Gemini AI, Multimodal OCR, YouTube transcription
│   │   └── templates/      # Serving HTML views (natively rendered)
│   ├── uploads/            # Temporary upload store
│   └── run.py              # Server run module
├── requirements.txt        # Root-level Vercel pip package dependencies
├── vercel.json             # Vercel serverless configuration
└── start-backend.bat       # One-click local startup script
```

## 🌟 Features

- **Upload & OCR** — JPG, PNG, PDF support with Tesseract
- **YouTube Import** — Paste URL → get transcript + AI notes
- **AI Notes** — Structured markdown notes via Gemini
- **AI Summary** — Key takeaways and executive summary
- **AI Explanation** — Beginner-friendly breakdowns
- **Mermaid Diagrams** — Visual flowcharts from content
- **Quiz Generation** — Multiple-choice quizzes
- **AI Chat** — Contextual conversation about your notes
- **Search** — Full-text search across all workspaces
- **PDF Export** — Download formatted notes as PDF
- **Share** — Generate shareable links
- **Archive** — Organize and archive old workspaces
- **JWT Auth** — Secure login/register

## 🔑 Getting a Gemini API Key

1. Go to https://aistudio.google.com/
2. Click "Get API Key"
3. Add to `backend/.env` as `GEMINI_API_KEY=...`
