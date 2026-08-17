import re
import requests
import fitz  # PyMuPDF
from pathlib import Path

headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;"
        "q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8"
    ),
    "Accept-Language": "en-GB,en;q=0.9",
    "Connection": "keep-alive",
    "Referer": "https://www.cambridgeinternational.org/",
    "DNT": "1",
    "Upgrade-Insecure-Requests": "1"
}

syllabus_links = None

with open("urls.txt", "r") as f:
    syllabus_links = [link.strip() for link in f.readlines()]

base_url = "https://www.cambridgeinternational.org"
output_dir = Path("syllabus_papers")
output_dir.mkdir(exist_ok=True)

for link in syllabus_links:
    filename = link.split("/")[-1]
    pdf_path = output_dir / filename

    response = requests.get(f"{base_url}{link}", headers=headers)
    if response.status_code == 200:
        pdf_path.write_bytes(response.content)
    else:
        print(f"{base_url}{link}")
        print(response.status_code)
        print(f"Failed to download {link}")
        continue

    doc = fitz.open(pdf_path)
    full_text = "\n".join(page.get_text() for page in doc)
    doc.close()

    paper_lines = re.findall(r"^.*Paper\s+\d+.*$", full_text, re.IGNORECASE | re.MULTILINE)

    txt_path = output_dir / (pdf_path.stem + ".txt")
    txt_path.write_text("\n".join(paper_lines), encoding="utf-8")
    print(f"Saved to {txt_path.name}")