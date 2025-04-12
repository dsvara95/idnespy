import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re
import time
import random
import webbrowser
from urllib.parse import quote_plus
from pathlib import Path

## === important for edge brw === ##
#import subprocess
#import os

# ==== NASTAVENÍ ====
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 Edg/135.0.0.0"
}
COOKIES_FILE = "cookies.json"
NAVSTIVENE_SOUBOR = "navstivene.txt"
SOUTEZNI_REGEX = re.compile(r"https://www\.idnes\.cz/ekonomika/megahra-o-auto[^\"]+")

# ==== FUNKCE ====
#def otevri_edge_a_zavri(url, cekani_vterin=8):
    #try:
        ## Spustí Microsoft Edge s daným URL
        #subprocess.Popen(['start', 'msedge', url], shell=True)
        #log_udalost(f"Otevřen Edge s URL: {url}")
        #time.sleep(cekani_vterin)

        # Zavře celý Edge (pozor: i ostatní okna/taby!)
        #os.system("taskkill /IM msedge.exe /F")
        #log_udalost("Edge zavřen.")
    #except Exception as e:
        #log_udalost(f"Chyba při otevírání/zavírání Edge: {e}")

def load_cookies(filename):
    import json
    with open(filename, "r", encoding="utf-8") as f:
        raw = json.load(f)
    return {cookie["name"]: cookie["value"] for cookie in raw}

def log_udalost(text):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"{now}: {text}"
    print(line)
    with open("soutez_log.txt", "a", encoding="utf-8") as f:
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
        return "David Švára" in r.text
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
    r = requests.get(url, cookies=cookies, headers=HEADERS) #, params=params)
    print(f"Ziskej odkazy z archivu: {url}")  # a parametry {params}")
    soup = BeautifulSoup(r.text, "html.parser")
    odkazy = []

    for art_div in soup.select("div.art"):
        a_tag = art_div.find("a", class_="art-link")
        if a_tag and a_tag.get("href"):
            odkazy.append(a_tag["href"])

    #soup = BeautifulSoup(r.text, "html.parser")
    #odkazy = [a["href"] for a in soup.select("a[href^='https://www.idnes.cz/']") if "/zpravy/" in a["href"]]
    return list(set(odkazy))  # odstraní duplicity

# ==== HLAVNÍ LOGIKA ====

datum_puvodni = "1. 1. 2025"  # zapsáno s mezerami
datum = quote_plus(datum_puvodni)  # výstup bude "1.+1.+2025"

cookies = load_cookies(COOKIES_FILE)
if not je_prihlaseny(cookies):
    log_udalost("❌ Nejste přihlášený. Skript ukončen.")
    exit()

navstivene = nacti_navstivene()
stranka = 1
while True:
    log_udalost(f"Jak vypadaji promenne {datum}")
    odkazy = ziskej_odkazy_z_archivu(datum, stranka)
    if not odkazy:
        log_udalost(f"✅ Konec – žádné další články na stránce {stranka}")
        break

    for odkaz in odkazy:
        if odkaz in navstivene:
            continue

        log_udalost(f"🔍 Kontroluji článek: {odkaz}")
        try:
            html = requests.get(odkaz, cookies=cookies, headers=HEADERS, timeout=10).text
            match = SOUTEZNI_REGEX.search(html)
            if match:
                soutez_odkaz = match.group(0)
                log_udalost(f"🎯 Nalezen soutěžní odkaz: {soutez_odkaz}")

                try:
                    soutez_resp = requests.get(soutez_odkaz, cookies=cookies, headers=HEADERS, timeout=10)
                    log_udalost(f"Odeslán požadavek na soutěžní odkaz – status: {soutez_resp.status_code}")
                except Exception as e:
                    log_udalost(f"Chyba při odesílání soutěžního odkazu: {e}")


                #requests.get(soutez_odkaz, cookies=cookies, headers=HEADERS, timeout=10)
                #webbrowser.open(soutez_odkaz)
                #otevri_edge_a_zavri(soutez_odkaz)
            else:
                log_udalost("❌ Soutěžní odkaz nenalezen.")
        except Exception as e:
            log_udalost(f"⚠️ Chyba při načítání článku: {e}")

        uloz_navstiveny(odkaz)
        time.sleep(random.randint(3, 10))

    stranka += 1

