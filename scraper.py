import os
import sys
import json
import requests
import logging
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import pdfminer.high_level
import docx
from urllib.parse import urljoin
from google import genai

load_dotenv()

EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("PASSWORD")
URL = os.getenv("URL")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_PROMPT = os.getenv("GEMINI_PROMPT")
OUTPUT_FILE = os.getenv("OUTPUT_FILE", "lesson_output.txt")
HEADLESS = os.getenv("HEADLESS", "True") == "True"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger(__name__)


def log(msg):
    logger.info(msg)
    print(msg, flush=True)


client = genai.Client(api_key=GEMINI_API_KEY)

def login(page):

    log("Opening login page")

    page.goto("https://app.praxhub.com/login")

    page.fill("input[type=email]", EMAIL)
    page.fill("input[type=password]", PASSWORD)

    page.click("button[type=submit]")

    page.wait_for_load_state("networkidle")

    log("Login successful")


def extract_sections(html):

    soup = BeautifulSoup(html, "html.parser")

    about_text = []
    learning_text = []

    current = None

    for el in soup.find_all(["h1","h2","h3","p","li"]):

        text = el.get_text(strip=True)

        if text == "About":
            current = "about"
            continue

        if text == "Learning Outcomes":
            current = "learning"
            continue

        if text in ["Provider","Resources","Resource"]:
            current = None
            continue

        if current == "about":
            about_text.append(text)

        elif current == "learning":
            learning_text.append(text)

    return "\n".join(about_text), "\n".join(learning_text)


def extract_resource_links(html):

    soup = BeautifulSoup(html, "html.parser")

    resource_links = []

    for a in soup.find_all("a", href=True):

        href = a["href"]

        if any(ext in href for ext in [".pdf",".doc",".docx"]):
            resource_links.append(href)

    for div in soup.find_all("div", class_=lambda x: x and "Education_resources" in x):

        for a in div.find_all("a", href=True):

            href = a["href"]

            if any(ext in href for ext in [".pdf",".doc",".docx"]):
                resource_links.append(href)

    return list(set(resource_links))


def download_with_cookies(context, base_url, url, filename):

    full_url = urljoin(base_url, url)

    cookies = {c["name"]: c["value"] for c in context.cookies()}

    r = requests.get(full_url, cookies=cookies)

    with open(filename, "wb") as f:
        f.write(r.content)


def extract_pdf(path):
    return pdfminer.high_level.extract_text(path)


def extract_docx(path):

    doc = docx.Document(path)

    return "\n".join(p.text for p in doc.paragraphs)


def rewrite_with_gemini(text):

    log("Sending content to Gemini for restructuring. This may take a moment...")

    prompt = f"""
{GEMINI_PROMPT}

Rules:
- keep headings
- remove duplicate sentences
- improve clarity
- keep technical meaning

TEXT:
{text}
"""

    response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=prompt
    )

    log("Gemini processing completed")

    return response.text


def run():

    if os.path.exists(OUTPUT_FILE):
        log("Deleting previous output file")
        os.remove(OUTPUT_FILE)

    with sync_playwright() as p:

        browser = p.chromium.launch(headless=HEADLESS)

        context = browser.new_context()

        page = context.new_page()

        login(page)

        log("Opening course page")

        page.goto(URL)

        page.wait_for_load_state("networkidle")

        html = page.content()

        about, learning = extract_sections(html)

        resources = extract_resource_links(html)

        final_text = "ABOUT\n\n" + about + "\n\n"
        final_text += "LEARNING OUTCOMES\n\n" + learning + "\n\n"

        for i, link in enumerate(resources):

            if ".pdf" in link:

                filename = f"resource_{i}.pdf"

                download_with_cookies(context, URL, link, filename)

                final_text += "\nRESOURCE FILE TEXT\n\n"
                final_text += extract_pdf(filename)

            elif ".docx" in link or ".doc" in link:

                filename = f"resource_{i}.docx"

                download_with_cookies(context, URL, link, filename)

                final_text += "\nRESOURCE FILE TEXT\n\n"
                final_text += extract_docx(filename)

        browser.close()

    processed_text = rewrite_with_gemini(final_text)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(processed_text)

    log("Processing completed")

    return processed_text


if __name__ == "__main__":

    result = run()

    print(json.dumps({"result": result}))