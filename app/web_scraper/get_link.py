from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from app.env import env
import time

BASE_URL = env.BASE_URL

options = Options()
options.add_argument("--headless")

driver = webdriver.Chrome(options=options)

driver.get(BASE_URL)

time.sleep(5)

soup = BeautifulSoup(driver.page_source, "html.parser")

links = set()

for a in soup.find_all("a", href=True):
    href = a["href"].strip()

    if not href:
        continue

    links.add(urljoin(BASE_URL, href))

driver.quit()

with open("link.py", "w", encoding="utf-8") as f:
    f.write("LINKS = [\n")

    for link in sorted(links):
        f.write(f'    "{link}",\n')

    f.write("]\n")

print(f"Total links: {len(links)}")