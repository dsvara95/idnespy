import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re
import time
import random
from urllib.parse import quote_plus
from pathlib import Path
import argparse
import json

# ==== PARSOVÁNÍ ARGUMENTU --jmeno ====
parser = argparse.ArgumentParser(description="Skript pro iDNES soutěže")
parser.add_argument("--jmeno", required=True, help="Zadej jméno, např. 'david' nebo 'hanka'")
args = parser.parse_args()

JMENO = args.jmeno.lower()
JMENO_HLEDANI = JMENO.capitalize()  # pro hledání v HTML
COOKIES_FILE = f"cookies_{JMENO}.json"
NAVSTIVENE_SOUBOR = f"navstivene_{JMENO}.txt"
LOG_SOUBOR = f"soutez_log_{JMENO}.txt"

# ==== NASTAVENÍ ====
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 Edg/135.0.0.0"
}
SOUTEZNI_REGEX = re.compile(r"https://www\.idnes\.cz/auto/megahra-o-auto[^\"]+")

# ==== FUNKCE ====
def load_cookies(filename):
    with open(filename, "r", encoding="utf-8") as f:
        raw = json.load(f)
    return {cookie["name"]: cookie["value"] for cookie in raw}

def log_udalost(text):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"{now}: {text}"
    print(line)
    with open(LOG_SOUBOR, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def nacti_navstivene():
    path = Path(NAVSTIVENE_SOUBOR)
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return set(line.strip() for line in f.readlines())
    return set()

def uloz_navstiveny(odkaz):
    with open(NAVSTIVENE_SOUBOR, "a", encoding="utf-8") as f:
        f.write(odkaz + "\n")

def je_prihlaseny(cookies):
    try:
        r = requests.get("https://www.idnes.cz/ucet", cookies=cookies, headers=HEADERS)
        return JMENO_HLEDANI in r.text
    except:
        return False

def ziskej_odkazy_z_archivu(datum, stranka=1):
    url = "https://www.idnes.cz/zpravy/archiv"
    if stranka > 1:
        url = f"{url}/{stranka}"
    params = {
        "datum": datum,
        "idostrova": "idnes"
    }
    r = requests.get(url, cookies=cookies, headers=HEADERS)
    log_udalost(f"📄 Získávám články z: {url}")
    soup = BeautifulSoup(r.text, "html.parser")
    odkazy = []

    for art_div in soup.select("div.art"):
        a_tag = art_div.find("a", class_="art-link")
        if a_tag and a_tag.get("href"):
            odkazy.append(a_tag["href"])

    return list(set(odkazy))

# ==== HLAVNÍ LOGIKA ====

datum_puvodni = "1. 1. 2025"
datum = quote_plus(datum_puvodni)

cookies = load_cookies(COOKIES_FILE)
if not je_prihlaseny(cookies):
    log_udalost("❌ Nejste přihlášený. Skript ukončen.")
    exit()

navstivene = nacti_navstivene()
stranka = 1
while True:
    odkazy = ziskej_odkazy_z_archivu(datum, stranka)
    if not odkazy:
        log_udalost(f"✅ Konec – žádné další články na stránce {stranka}")
        break

    for odkaz in odkazy:
        if odkaz in navstivene:
            log_udalost(f"✅ Článek již navštíven: {odkaz}")
            continue

        log_udalost(f"🔍 Kontroluji článek: {odkaz}")
        try:
            html = requests.get(odkaz, cookies=cookies, headers=HEADERS, timeout=10).text
            soup = BeautifulSoup(html, "html.parser")

            # === NOVÁ ČÁST: zjištění data aktualizace ===
            time_span = soup.find("span", class_="time-date", itemprop="datePublished")
            aktual_span = soup.find("span", class_="aktual")
            datum_aktualizace = None
            if aktual_span:
                date_modified = aktual_span.find("span", itemprop="dateModified")
                if date_modified and date_modified.get("content"):
                    datum_aktualizace = date_modified["content"].split("T")[0]
                    log_udalost(f"📅 Datum aktualizace článku: {datum_aktualizace}")
                else:
                    log_udalost("⚠️ Datum aktualizace článku nenalezeno.")

            if time_span and time_span.get("content"):
                datum_clanku = time_span["content"]
                log_udalost(f"📅 Datum článku: {datum_clanku}")
            else:
                log_udalost("⚠️ Datum článku nenalezeno.")
                datum_clanku = "9999-12-31"  # fallback

            last_date = "2025-03-20"
            if datum_clanku < last_date and (datum_aktualizace and datum_aktualizace < last_date):
                log_udalost(f"🛑 Článek je starší než {last_date}. Ukončuji cyklus.")
                exit()

            match = SOUTEZNI_REGEX.search(html)
            if match:
                soutez_odkaz = match.group(0)
                log_udalost(f"🎯 Nalezen soutěžní odkaz: {soutez_odkaz}")

                try:
                    soutez_resp = requests.get(soutez_odkaz, cookies=cookies, headers=HEADERS, timeout=10)
                    log_udalost(f"📨 Odeslán požadavek na soutěžní odkaz – status: {soutez_resp.status_code}")
                except Exception as e:
                    log_udalost(f"❗ Chyba při odesílání soutěžního odkazu: {e}")
            else:
                log_udalost("❌ Soutěžní odkaz nenalezen.")
        except Exception as e:
            log_udalost(f"⚠️ Chyba při načítání článku: {e}")

        uloz_navstiveny(odkaz)
        time.sleep(random.randint(3, 10))

    stranka += 1
