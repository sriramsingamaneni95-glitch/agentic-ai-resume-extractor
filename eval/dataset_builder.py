from pathlib import Path
import json
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parent
DATASET_DIR = ROOT / "dataset"

FIRST = ["Aarav","Diya","Rohan","Anika","Vikram","Meera","Kiran","Nisha","Arjun","Tara"]
LAST = ["Sharma","Reddy","Patel","Iyer","Rao"]
COMPANIES = ["Northstar Analytics","BluePeak Systems","Vertex Labs","Orion Digital","Cedar Finance",
             "Nimbus Health","Pioneer Tech","Atlas Consulting","Quantum Retail","Summit Cloud"]
ROLES = ["Data Analyst","Software Engineer","ML Engineer","Business Analyst","Data Scientist",
         "Backend Developer","QA Engineer","Product Analyst","Cloud Engineer","AI Engineer"]
DEGREES = ["B.Tech Computer Science","B.Sc Computer Science","M.Tech Data Science",
           "B.E. Information Technology","M.Sc Computer Science"]
SCHOOLS = ["SRM University","University of Hyderabad","VIT University","Anna University","Andhra University"]
SKILLS = [
    ["Python","SQL","Excel","Pandas"], ["Python","Java","Git","REST APIs"],
    ["Python","TensorFlow","PyTorch","Machine Learning"], ["SQL","Power BI","Excel","Tableau"],
    ["Python","Scikit-learn","SQL","Statistics"], ["Java","Spring Boot","PostgreSQL","Docker"],
    ["Selenium","Python","SQL","Jira"], ["SQL","Python","Tableau","Power BI"],
    ["AWS","Python","Docker","Linux"], ["Python","LLMs","TensorFlow","FastAPI"],
]

def make_fixture(i: int):
    j = i % 10
    category = (
        "clean" if i < 10 else
        "messy" if i < 20 else
        "multi-column" if i < 30 else
        "incomplete" if i < 40 else "ambiguous"
    )

    name = f"{FIRST[j]} {LAST[i % 5]}"
    email = f"{FIRST[j].lower()}.{j+1}@example.com"
    phone = f"+91-9000000{100+i}"
    company, title = COMPANIES[j], ROLES[j]
    degree, school = DEGREES[i % 5], SCHOOLS[i % 5]
    skills = list(SKILLS[j])
    start = f"{2018 + i % 5}-{i % 9 + 1:02d}"
    end = "present" if i % 3 == 0 else f"{2022 + i % 3}-{i % 9 + 1:02d}"
    summary = f"{title} with experience in {', '.join(skills[:3])}."

    ground_truth = {
        "category": category,
        "name": name,
        "email": email,
        "phone": phone,
        "summary": summary,
        "skills": skills,
        "experience": [{
            "company": company,
            "title": title,
            "start_date": start,
            "end_date": end,
            "description": "Built and maintained data and software solutions."
        }],
        "education": [{
            "institution": school,
            "degree": degree,
            "year": str(2018 + i % 5)
        }]
    }

    text = (
        f"NAME: {name}\nEMAIL: {email}\nPHONE: {phone}\nSUMMARY: {summary}\n"
        f"SKILLS: {', '.join(skills)}\nEXPERIENCE:\n"
        f"- {title} | {company} | {start} | {end} | Built and maintained data and software solutions.\n"
        f"EDUCATION:\n- {degree} | {school} | {2018+i%5}\n"
    )

    if category == "messy":
        text = (
            f"*** RESUME {i+1} ***\n{name.upper()} | {email} | {phone}\n"
            f"Summary:: {summary}\nSKILLS >> {' / '.join(skills)}\n"
            f"WORK>> {company} -- {title} ({start} to {end}) -- Built and maintained data and software solutions.\n"
            f"EDU >> {school}; {degree}; {2018+i%5}\nNoise: ### ## tabs ---\n"
        )
    elif category == "incomplete":
        ground_truth["phone"] = None
        ground_truth["summary"] = None
        ground_truth["skills"] = skills[:2]
        text = (
            f"{name}\nEmail: {email}\nSkills: {', '.join(skills[:2])}\n"
            f"Experience: {title} at {company}, {start}-{end}\n"
            f"Education: {degree}, {school}, {2018+i%5}\n"
        )
    elif category == "ambiguous":
        text = (
            f"{name}\nContact: {email} / {phone}\nProfile: {summary}\n"
            f"Skills: {', '.join(skills)}\n"
            f"Career: {start} {company} {title}; moved into {title} in "
            f"{'current period' if end == 'present' else end}.\n"
            f"Education: {school} - {degree} ({2018+i%5})\n"
            "Note: source record defines the canonical interval.\n"
        )

    return category, text, ground_truth

def write_two_column_pdf(path: Path, text: str):
    c = canvas.Canvas(str(path), pagesize=letter)
    width, height = letter
    lines = text.splitlines()
    midpoint = (len(lines) + 1) // 2
    for x, column in ((40, lines[:midpoint]), (315, lines[midpoint:])):
        y = height - 45
        for line in column:
            c.setFont("Helvetica", 9)
            c.drawString(x, y, line[:58])
            y -= 13
    c.save()

def build():
    DATASET_DIR.mkdir(parents=True, exist_ok=True)
    ground_truth, manifest = {}, {}

    for i in range(50):
        category, text, truth = make_fixture(i)
        filename = f"resume_{i+1:02d}.pdf" if category == "multi-column" else f"resume_{i+1:02d}.txt"
        path = DATASET_DIR / filename

        if category == "multi-column":
            write_two_column_pdf(path, text)
        else:
            path.write_text(text, encoding="utf-8")

        ground_truth[filename] = truth
        manifest[filename] = {
            "category": category,
            "source_type": "pdf" if category == "multi-column" else "text",
            "ground_truth_source": "deterministic_fixture_record"
        }

    (DATASET_DIR / "ground_truth.json").write_text(json.dumps(ground_truth, indent=2), encoding="utf-8")
    (DATASET_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (DATASET_DIR / "ground_truth_review.md").write_text(
        "# Ground-truth protocol\n\n"
        "This benchmark contains 50 deterministic synthetic resumes. Ground truth is created "
        "from source fixture records before extraction and is independent of model predictions. "
        "It is not claimed to be human-reviewed.\n\n"
        "Composition: 10 clean, 10 messy, 10 actual two-column PDFs, 10 incomplete, "
        "and 10 ambiguous resumes.\n\n"
        "For external validation, supplement or replace these fixtures with independently "
        "human-reviewed resumes.\n",
        encoding="utf-8"
    )

if __name__ == "__main__":
    build()
