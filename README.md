# 🏭 The-Resume-Refinery

**The-Resume-Refinery** is a data-driven tool designed to bridge the gap between your professional history and specific job requirements. It pairs Python with Claude to analyze job descriptions and refine your resume for better ATS alignment and impact.

---

## 🚀 Overview
Most resumes fail not because of a lack of experience, but because of a lack of **relevance**. This application "refines" your raw experience into a format that highlights exactly what recruiters (and algorithms) are looking for.

### Key Features
* **ATS Keyword Matching:** Identifies missing technical and soft skills.
* **Contextual Refinement:** Suggests bullet point rewrites for maximum impact.
* **Alignment Scoring:** Provides a "Match Score" between your CV and the Job Description.

## 🛠️ Tech Stack
* **Language:** Python 3.x
* **Processing:** Claude (API key required)

## 📥 Installation & Setup

**Prerequisites:** Python 3.9+ and an [Anthropic API key](https://console.anthropic.com)

### 1. Get the code
- **New to GitHub:** Click the green **Code** button → **Download ZIP**, then unzip the folder
- **Git users:** `git clone https://github.com/[your-username]/The-Resume-Refinery.git`

### 2. Install dependencies
```bash
cd The-Resume-Refinery
pip install -r requirements.txt
```

### 3. Set up your API key
```bash
cp .env.example .env
```
Open `.env` and replace `your_api_key_here` with your actual Anthropic API key.

### 4. Add your master resume
```bash
cp master_resume.md.example master_resume.md
```
Open `master_resume.md` and replace the placeholder content with your full resume. Include everything — the tool selects and tailors the relevant portions for each job.

### 5. Launch the app
```bash
python3 gui.py
```
Your browser opens automatically to `http://localhost:5000`.

> Steps 3 and 4 are one-time setup. After that, just run `python3 gui.py` each time.
