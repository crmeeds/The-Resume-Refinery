# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Resume Optimizer is a Python CLI tool that uses Claude AI to tailor resumes to specific job postings. It analyzes job posting PDFs, extracts keywords, and generates ATS-optimized resumes by selecting relevant content from a master resume file.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the optimizer (supports PDF, RTF, DOCX, TXT)
python resume_optimizer.py <job_posting>

# Run with custom output name
python resume_optimizer.py job.pdf --output company_role.md

# Analysis only (no resume generation)
python resume_optimizer.py job.pdf --analysis-only
```

## Architecture

```
resume_optimizer.py    # Main CLI - PDF extraction, Claude API calls, file I/O
master_resume.md       # User's complete experience/skills (input)
templates/             # Resume format templates (for future use)
output/                # Generated tailored resumes
```

**Data flow:** Job posting (PDF/RTF/DOCX/TXT) → text extraction (pdfplumber or textutil) → Claude analyzes keywords + selects from master resume → outputs optimized markdown resume

## Key Dependencies

- `anthropic` - Claude API client
- `pdfplumber` - PDF text extraction
- `python-dotenv` - Environment variable management

## Configuration

API key must be set in `.env` file (copy from `.env.example`):
```
ANTHROPIC_API_KEY=your_key_here
```
