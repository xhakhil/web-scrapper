import os
import time
# import google.generativeai as genai
from google import genai
from urllib.parse import urljoin


from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from urllib.parse import urlparse

load_dotenv()

ALISON_EMAIL = os.getenv("ALISON_EMAIL")
ALISON_PASSWORD = os.getenv("ALISON_PASSWORD")

FLORENCE_EMAIL = os.getenv("FLORENCE_EMAIL")
FLORENCE_PASSWORD = os.getenv("FLORENCE_PASSWORD")

COURSE_URL = os.getenv("COURSE_URL")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

RAW_FILE = "course_raw.txt"
FINAL_FILE = "course_rewritten.txt"


# -----------------------------
# GEMINI SETUP
# -----------------------------
# genai.configure(api_key=GEMINI_KEY)
# model = genai.GenerativeModel("gemini-2.5-flash")


client = genai.Client(api_key=GEMINI_KEY)

# -----------------------------
# COMMON HTML CLEANER
# -----------------------------
def clean_text(html):

    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(["script","style","nav","footer","header","iframe"]):
        tag.decompose()

    text = soup.get_text("\n", strip=True)

    return text


def extract_text(html):

    soup = BeautifulSoup(html, "html.parser")

    main = soup.select_one(".new-player--inner")

    if not main:
        return ""

    for tag in main.select("nav, footer, script, style, .player-nav"):
        tag.decompose()

    return main.get_text("\n", strip=True)


def extract_title(html):

    soup = BeautifulSoup(html, "html.parser")

    t = soup.select_one("h1, h2")

    if t:
        return t.get_text(strip=True)

    return "Lesson"


def get_next_url(html):

    soup = BeautifulSoup(html, "html.parser")

    next_link = soup.select_one(".player-nav--top a")

    if next_link:
        return next_link.get("href")

    return None




# -----------------------------
# ALISON SCRAPER
# -----------------------------

def scrape_alison():

    content = []

    with sync_playwright() as p:

        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        # LOGIN
        page.goto("https://alison.com/login", wait_until="domcontentloaded")

        page.fill('input[name="email"]', ALISON_EMAIL)
        page.fill('input[name="password"]', ALISON_PASSWORD)

        page.click("button[type='submit']")

        page.wait_for_load_state("domcontentloaded")

        current_url = COURSE_URL
        visited = set()

        page_no = 1

        while current_url:

            if current_url in visited:
                break

            visited.add(current_url)

            print("Opening:", current_url)

            page.goto(current_url, wait_until="domcontentloaded")

            # Wait for Angular course player
            page.wait_for_selector(".angular-course-player", timeout=60000)

            # Wait for lesson container
            page.wait_for_selector(".new-player--inner", timeout=60000)

            # Scroll once to trigger lazy loading
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")

            # Allow Angular content rendering
            page.wait_for_timeout(3000)

            html = page.content()

            title = extract_title(html)
            text = extract_text(html)

            section = (
                "\n\n"
                + "=" * 70
                + "\n"
                + title
                + "\n"
                + "=" * 70
                + "\n\n"
                + text
            )

            content.append(section)

            next_url = get_next_url(html)

            if next_url:
                current_url = urljoin(current_url, next_url)
            else:
                break

            page_no += 1

        browser.close()

    return "\n".join(content)





# def scrape_alison():

#     content = []

#     with sync_playwright() as p:

#         browser = p.chromium.launch(headless=False)
#         page = browser.new_page()

#         page.goto("https://alison.com/login")

#         page.fill('input[name="email"]', ALISON_EMAIL)
#         page.fill('input[name="password"]', ALISON_PASSWORD)
#         page.click("button[type='submit']")

#         page.wait_for_load_state("domcontentloaded")

#         current_url = COURSE_URL
#         visited = set()

#         while current_url:

#             if current_url in visited:
#                 break

#             visited.add(current_url)

#             print("Opening:", current_url)

#             page.goto(current_url, wait_until="domcontentloaded")

#             page.wait_for_selector(".angular-course-player", timeout=60000)

#             html = page.content()

#             text = clean_text(html)

#             content.append(text)

#             soup = BeautifulSoup(html, "html.parser")

#             next_link = soup.select_one(".player-nav--top a")

#             if next_link:
#                 current_url = urljoin(current_url, next_link.get("href"))
#             else:
#                 break

#         browser.close()

#     return "\n\n".join(content)


# -----------------------------
# FLORENCE SCRAPER
# -----------------------------



def scrape_florence():

    content = []

    with sync_playwright() as p:

        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )

        page = context.new_page()

        # LOGIN
        page.goto("https://academy.florence.co.uk/login", wait_until="domcontentloaded")

        page.fill('input[type="email"]', FLORENCE_EMAIL)
        page.fill('input[type="password"]', FLORENCE_PASSWORD)

        page.click('button[type="submit"]')

        page.wait_for_load_state("domcontentloaded")
        time.sleep(3)

        # OPEN COURSE
        page.goto(COURSE_URL, wait_until="domcontentloaded")
        time.sleep(3)

        # FIND CHAPTER LINKS
        chapters = []

        selectors = [
            "a[href*='chapter=']",
            ".chapter-link",
            "[data-chapter]",
            "nav a"
        ]

        for selector in selectors:

            try:

                links = page.locator(selector)

                for i in range(links.count()):

                    link = links.nth(i)

                    if link.is_visible():

                        href = link.get_attribute("href")
                        text = link.text_content().strip()

                        if href and text and any(c.isdigit() for c in text):
                            chapters.append((text, href))

            except:
                pass

        # REMOVE DUPLICATES
        seen = set()
        unique = []

        for title, url in chapters:
            if url not in seen:
                seen.add(url)
                unique.append((title, url))

        # SCRAPE EACH CHAPTER
        for title, url in unique:

            print("Opening:", title)

            full_url = urljoin("https://academy.florence.co.uk", url)

            page.goto(full_url, wait_until="domcontentloaded")
            time.sleep(2)

            html = page.content()

            text = clean_text(html)

            if text:
                content.append(f"{title}\n{text}")

        browser.close()

    return "\n\n".join(content)




# -----------------------------
# PLATFORM DETECTOR
# -----------------------------
def run_crawler():

    domain = urlparse(COURSE_URL).netloc

    if "alison" in domain:

        print("Detected Alison course")

        return scrape_alison()

    elif "florence" in domain:

        print("Detected Florence course")

        return scrape_florence()

    else:

        raise Exception("Unsupported platform")


# -----------------------------
# GEMINI REWRITE
# -----------------------------
def rewrite_with_gemini(text):

    prompt = f"""
Rewrite the following course material clearly.

- keep headings
- remove duplicate sentences
- improve clarity
- keep technical meaning

TEXT:
{text}
"""

    # response = model.generate_content(prompt)
    response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=prompt
    )

    return response.text


# -----------------------------
# MAIN PIPELINE
# -----------------------------
def main():

    print("Starting crawler")

    raw_text = run_crawler()

    with open(RAW_FILE, "w", encoding="utf8") as f:
        f.write(raw_text)

    print("Raw content saved")

    print("Sending to AI for rewriting...")

    rewritten = rewrite_with_gemini(raw_text)

    with open(FINAL_FILE, "w", encoding="utf8") as f:
        f.write(rewritten)

    print("Finished")


if __name__ == "__main__":
    main()