# RecruiterAI — Intelligent Hiring Platform

An AI-powered recruitment platform that automates the entire hiring pipeline — from resume screening to proctored assessments, coding rounds, and interview scheduling.

## Features

- **AI Resume Screening** — TF-IDF based matching against job requirements
- **Proctored Assessments** — Timed MCQ tests with anti-cheat monitoring
- **Coding Round** — Web-based coding challenges
- **5-Round Pipeline** — Assessment → Coding → Behavioural → Tech HR → Final HR
- **HR Dashboard** — Manage applications, schedule interviews, track candidates

## Tech Stack

- **Backend:** Python, Flask
- **Database:** MongoDB
- **AI/ML:** scikit-learn (TF-IDF, cosine similarity)
- **Frontend:** Jinja2, Bootstrap Icons, Custom CSS

## Setup

```bash
git clone https://github.com/SudhirMahaaraja/RecruiterAI-Intelligent-Hiring-Platform.git
cd RecruiterAI-Intelligent-Hiring-Platform
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

App runs at **http://localhost:5000**

**Default HR Login:** `admin` / `admin123`

## License

MIT
