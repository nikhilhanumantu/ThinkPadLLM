# 🚀 ThinkPadLLM — Vercel Deployment Guide

Your codebase has been fully organized and structured following Vercel's official best practices for Python/Flask serverless deployments.

---

## 📂 Deployment-Ready Architecture

Vercel scans your repository and serves the entire system using the following production-optimized structure:

```
thinkpadlm/
├── api/
│   └── index.py            # Vercel Serverless Entrypoint (maps requests to Flask app)
├── backend/
│   ├── app/                # Main Flask package (routes, services, models)
│   │   ├── templates/      # HTML Pages (upload.html, main.html, previews.html, login.html)
│   │   └── ...
│   └── run.py              # Local execution runner
├── vercel.json             # Vercel routing & python runtime configuration
└── requirements.txt        # Shared python package dependencies (scanned by Vercel)
```

---

## 🛠️ Step-by-Step Vercel Deployment

Deploying **ThinkPadLLM** takes less than 2 minutes using Vercel:

### Option A: Via GitHub (Recommended)
1. Push your **`thinkpadlm`** directory to a new private or public repository on **GitHub**, **GitLab**, or **Bitbucket**.
2. Go to [Vercel's Dashboard](https://vercel.com) and click **"Add New"** ➔ **"Project"**.
3. Import your repository.
4. **Environment Variables (CRITICAL)**:
   Open the **"Environment Variables"** dropdown and add your active keys:
   * `GEMINI_API_KEY` ➔ `[Your Gemini API Key]`
   * `MONGO_URI` ➔ `[Your MongoDB Atlas Connection String]`
   * `JWT_SECRET_KEY` ➔ `[Secure secret key string]`
5. Click **"Deploy"**! Vercel will install all Python dependencies from the root `requirements.txt` and serve the application serverlessly.

### Option B: Via Vercel CLI (Command Line)
If you prefer deploying directly from your local terminal:
1. Install Vercel CLI globally:
   ```bash
   npm install -g vercel
   ```
2. Navigate into the project folder:
   ```bash
   cd thinkpadlm
   ```
3. Run the setup and deploy command:
   ```bash
   vercel
   ```
4. Follow the prompts to log in and link the project.
5. Add your environment keys on the Vercel dashboard, then release the production build:
   ```bash
   vercel --prod
   ```

---

## 🔒 Crucial Deployment Environment Variables

Make sure to configure the following keys inside the Vercel Dashboard dashboard settings:

| Variable Name | Description | Example / Recommended Value |
| :--- | :--- | :--- |
| `GEMINI_API_KEY` | Gemini Pro active API Key | `AIzaSy...` |
| `MONGO_URI` | Live MongoDB Atlas DB connection | `mongodb+srv://...` |
| `JWT_SECRET_KEY` | Secure session authorization key | `super-secret-jwt-key` |
| `FLASK_ENV` | Environment flag | `production` |
