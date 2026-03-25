#!/usr/bin/env python3
"""
Resume Optimizer - Tailors resumes to job postings using Claude AI.

Usage:
    python resume_optimizer.py <job_posting> [--output <filename>]

Supported formats: PDF, RTF, DOCX, TXT
"""

import argparse
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import anthropic
import pdfplumber
from dotenv import load_dotenv

SUPPORTED_EXTENSIONS = {".pdf", ".rtf", ".docx", ".txt"}

load_dotenv()

SCRIPT_DIR = Path(__file__).parent

# Allow gui.py / PyInstaller bundle to override these before calling any functions
def _default_base_dir() -> Path:
    if getattr(__import__("sys"), "frozen", False):
        return Path(__import__("sys").executable).parent
    return SCRIPT_DIR

BASE_DIR = _default_base_dir()
MASTER_RESUME_PATH = BASE_DIR / "master_resume.md"
OUTPUT_DIR = BASE_DIR / "output"
TEMPLATE_DIR = BASE_DIR / "templates"


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text content from a PDF file."""
    try:
        text_parts = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text)
        return "\n\n".join(text_parts)
    except Exception as e:
        raise RuntimeError(
            f"Could not read PDF '{pdf_path}'. The file may be corrupted, password-protected, "
            f"or image-based (scanned). Try an OCR tool first.\nDetails: {e}"
        ) from e


def extract_text_with_textutil(file_path: str) -> str:
    """Extract text from RTF or DOCX using macOS textutil."""
    result = subprocess.run(
        ["textutil", "-convert", "txt", "-stdout", file_path],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"textutil failed: {result.stderr}")
    return result.stdout


def extract_text_from_docx(file_path: str) -> str:
    """Extract text from a DOCX file using python-docx (cross-platform)."""
    try:
        from docx import Document
    except ImportError:
        raise RuntimeError(
            "python-docx is required to read .docx files. Install it with: pip install python-docx"
        )
    doc = Document(file_path)
    return "\n".join(para.text for para in doc.paragraphs if para.text)


def extract_text(file_path: Path) -> str:
    """Extract text from a file based on its extension."""
    ext = file_path.suffix.lower()

    if ext == ".pdf":
        return extract_text_from_pdf(str(file_path))
    elif ext == ".docx":
        if sys.platform == "darwin":
            return extract_text_with_textutil(str(file_path))
        return extract_text_from_docx(str(file_path))
    elif ext == ".rtf":
        if sys.platform != "darwin":
            raise RuntimeError("RTF extraction requires macOS (textutil). Convert to .docx or .txt first.")
        return extract_text_with_textutil(str(file_path))
    elif ext == ".txt":
        return file_path.read_text()
    else:
        raise ValueError(f"Unsupported file format: {ext}")


def load_master_resume() -> str:
    """Load the master resume markdown file."""
    if not MASTER_RESUME_PATH.exists():
        print(f"Error: Master resume not found at {MASTER_RESUME_PATH}")
        print("Please create your master_resume.md file first.")
        sys.exit(1)
    return MASTER_RESUME_PATH.read_text()


MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
RESUME_SEPARATOR = "---RESUME START---"


def analyze_and_optimize(job_posting: str, master_resume: str) -> str:
    """Use Claude to analyze the job posting and create an optimized resume."""
    client = anthropic.Anthropic()
    current_year = datetime.now().year

    prompt = f"""You are an expert resume writer specializing in technical roles at defense contractors. You understand ATS (Applicant Tracking System) optimization and modern resume design for {current_year}.

I need you to analyze the job posting, identify gaps, and then produce a revised resume that actively incorporates your recommendations.

## Step 1 — Analysis (PART 1)

Produce a concise analysis covering:
- **Top keywords/phrases to emphasize**: List 5-7 exact terms from the job posting (use the posting's exact wording)
- **Requirements I meet**: Where my experience clearly aligns
- **Gaps & how to address them**: Specific bullet points or language changes that would close each gap

## Step 2 — Changes Made (PART 2)

Before writing the resume, produce a concise before/after comparison of the most impactful changes. For each change, show:
- **What changed**: The section or bullet that was modified
- **Before**: The original wording (quote directly from the master resume)
- **After**: The new wording in the optimized resume
- **Why**: One sentence explaining the strategic reason (keyword match, gap closure, stronger framing)

Limit to the 5-8 most significant changes. Minor wording tweaks do not need to be listed.

## Step 3 — Revised Resume (PART 3)

Using the analysis above as your guide, write a complete revised resume. This is NOT a copy-paste of my master resume — it is a rewritten version that:

- **Incorporates the keywords** identified in Step 1 naturally into bullet points where the experience genuinely supports it
- **Addresses the gaps** by reframing existing experience with language that speaks to the job's requirements
- **Rewrites bullet points** to lead with the most relevant action and outcome for this specific role
- **Removes or deprioritizes** experience that is irrelevant to this posting
- **Quantifies every achievement** possible (dollars saved, percentage improvements, hours reduced, team size)

### Resume Structure (follow exactly)

**Section Order:**
1. **Header**: Name, contact info, citizenship, security clearance on same line
2. **Professional Summary**: 2-3 sentences written specifically for this role, using keywords from the posting
3. **Skills**: Categorized groups that mirror the job posting's language
4. **Professional Experience**: Reverse-chronological; rewritten bullets that incorporate Step 1 recommendations
5. **Education**: Degrees with honors/GPA if notable
6. **Certifications**: Relevant only

**Formatting Rules:**
- Target 1-2 pages
- Plain text only — no markdown syntax (no **, ##, *, _, or backticks anywhere in the output)
- Section headers in ALL CAPS (e.g. PROFESSIONAL EXPERIENCE)
- Bullets using a simple dash (-)
- Each bullet: [Action Verb] + [Task/Achievement] + [Quantified Result]
- Action verbs: Architected, Designed, Developed, Led, Implemented, Delivered, Reduced, Increased
- ATS-safe: no tables, columns, graphics, icons, or special characters
- Standard section headers only

**Defense Contractor Style:**
- Conservative, professional tone
- Emphasize accomplishments, leadership, and technical depth
- Security clearance and citizenship near the top

## Job Posting:

{job_posting}

## My Master Resume:

{master_resume}

## Output Format:

Write PART 1 (analysis), then PART 2 (before/after changes), then place the exact separator below, then write PART 3 (the revised resume).

Separator: {RESUME_SEPARATOR}

The resume must be immediately usable — professional, polished, and ready to submit.
"""

    last_error = None
    for attempt in range(3):
        try:
            message = client.messages.create(
                model=MODEL,
                max_tokens=8192,
                messages=[{"role": "user", "content": prompt}],
                timeout=90,
            )
            return message.content[0].text
        except anthropic.APIConnectionError as e:
            last_error = e
            if attempt < 2:
                wait = 2 ** attempt
                print(f"Connection error, retrying in {wait}s... (attempt {attempt + 1}/3)")
                time.sleep(wait)
        except anthropic.RateLimitError as e:
            last_error = e
            if attempt < 2:
                wait = 10 * (attempt + 1)
                print(f"Rate limited, retrying in {wait}s... (attempt {attempt + 1}/3)")
                time.sleep(wait)

    raise RuntimeError(f"Claude API call failed after 3 attempts: {last_error}") from last_error


def save_resume(content: str, output_name: Optional[str] = None, job_source: Optional[str] = None) -> Path:
    """Save the optimized resume to the output directory."""
    OUTPUT_DIR.mkdir(exist_ok=True)

    if output_name:
        filename = output_name if output_name.endswith(".md") else f"{output_name}.md"
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        stem = Path(job_source).stem if job_source else "resume"
        filename = f"{stem}_{timestamp}.txt"

    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    source_note = f" | Source: {job_source}" if job_source else ""
    metadata = f"<!-- Generated: {generated_at}{source_note} -->\n\n"

    output_path = OUTPUT_DIR / filename
    output_path.write_text(metadata + content)
    return output_path


def main():
    parser = argparse.ArgumentParser(
        description="Optimize your resume for a specific job posting using Claude AI."
    )
    parser.add_argument("job_posting", help="Path to the job posting file (PDF, RTF, DOCX, or TXT)")
    parser.add_argument(
        "--output", "-o", help="Output filename (default: resume_<timestamp>.md)"
    )
    parser.add_argument(
        "--analysis-only",
        action="store_true",
        help="Only show keyword analysis, don't generate resume",
    )

    args = parser.parse_args()

    # Validate job posting file
    job_posting_path = Path(args.job_posting)
    if not job_posting_path.exists():
        print(f"Error: Job posting file not found: {args.job_posting}")
        sys.exit(1)

    # Validate file extension
    if job_posting_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        print(f"Error: Unsupported file format: {job_posting_path.suffix}")
        print(f"Supported formats: {', '.join(SUPPORTED_EXTENSIONS)}")
        sys.exit(1)

    # Check for API key
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("Error: ANTHROPIC_API_KEY environment variable not set.")
        print("Copy .env.example to .env and add your API key.")
        sys.exit(1)

    print(f"Loading job posting from: {job_posting_path}")
    try:
        job_posting_text = extract_text(job_posting_path)
    except Exception as e:
        print(f"Error extracting text: {e}")
        sys.exit(1)

    if not job_posting_text.strip():
        print("Warning: Could not extract text from file. The file may be image-based or empty.")
        print("Consider using an OCR tool first or pasting the job posting text directly.")
        sys.exit(1)

    print("Loading master resume...")
    master_resume = load_master_resume()

    print("Analyzing job posting and optimizing resume with Claude...")
    result = analyze_and_optimize(job_posting_text, master_resume)

    if RESUME_SEPARATOR not in result:
        print("\nWarning: Claude did not include the expected separator. The full output will be used.")

    if args.analysis_only:
        # Only print the analysis portion
        if RESUME_SEPARATOR in result:
            analysis = result.split(RESUME_SEPARATOR)[0]
            print("\n" + analysis)
        else:
            print("\n" + result)
    else:
        # Save the full result
        output_path = save_resume(result, args.output, job_source=job_posting_path.name)
        print(f"\nOptimized resume saved to: {output_path}")
        print("\nTip: Review the analysis section at the top of the file,")
        print(f"then copy the resume portion below '{RESUME_SEPARATOR}'")


if __name__ == "__main__":
    main()
