import requests
from bs4 import BeautifulSoup
from datetime import datetime
import json
import time
import re

BASE_URL = "https://it.wikipedia.org/wiki/Motomondiale_ {}"
START_YEAR = 2005
END_YEAR = datetime.now().year

headers = {
    "User-Agent": "Mozilla/5.0"
}

output = []

months = {
    "gennaio": "01", "febbraio": "02", "marzo": "03", "aprile": "04",
    "maggio": "05", "giugno": "06", "luglio": "07", "agosto": "08",
    "settembre": "09", "ottobre": "10", "novembre": "11", "dicembre": "12"
}

def extract_day(raw_date):
    """
    Estrae il primo giorno da date tipo:
    - "1º maggio" → 1
    - "12-13 giugno" → 12
    - "12–13 giugno" → 12 (trattino lungo)
    """
    raw_date = raw_date.replace("º", "").strip()
    parts = raw_date.split()
    if len(parts) < 2:
        return None, None

    day_part = parts[0]
    month_part = parts[1].lower()

    day_part = re.split(r"[-–]", day_part)[0]
    
    try:
        day = int(day_part)
        month_number = months.get(month_part, None)
        return day, month_number
    except:
        return None, None

def extract_coordinates(soup):
    """
    Estrae le coordinate geografiche dal contenuto della pagina.
    """
    coord_div = soup.find("span", {"id": "coordinates"})
    lat, lon = None, None

    if coord_div:
        coord_link = coord_div.find("a", class_="mw-kartographer-maplink")
        if coord_link and "data-lat" in coord_link.attrs and "data-lon" in coord_link.attrs:
            lat = coord_link["data-lat"]
            lon = coord_link["data-lon"]
        else:
            # Estrai coordinate dal testo usando regex
            coord_text = coord_div.get_text()
            match = re.search(r"(\d+)°(\d+)[′'](\d+)[″\"]([NS])\s+(\d+)°(\d+)[′'](\d+)[″\"]([EW])", coord_text)
            if match:
                lat_deg, lat_min, lat_sec, lat_dir = match.group(1), match.group(2), match.group(3), match.group(4)
                lon_deg, lon_min, lon_sec, lon_dir = match.group(5), match.group(6), match.group(7), match.group(8)

                lat = float(lat_deg) + float(lat_min) / 60 + float(lat_sec) / 3600
                lon = float(lon_deg) + float(lon_min) / 60 + float(lon_sec) / 3600

                if lat_dir.upper() == "S":
                    lat = -lat
                if lon_dir.upper() == "W":
                    lon = -lon
    return lat, lon

for year in range(START_YEAR, END_YEAR + 1):
    print(f"Processing year {year}...")
    url = BASE_URL.format(year)
    res = requests.get(url, headers=headers)
    if res.status_code != 200:
        print(f"Failed to fetch {url}")
        continue

    soup = BeautifulSoup(res.content, "html.parser")
    table = soup.find("table", {"class": "wikitable"})

    if not table:
        print(f"No table found for {year}")
        continue

    rows = table.find_all("tr")[1:]

    for row in rows:
        cols = row.find_all("td")
        if len(cols) < 5:
            continue

        try:
            raw_date = cols[0].text.strip()
            day, month_number = extract_day(raw_date)

            if not day or not month_number:
                continue

            date_str = f"{year}-{month_number}-{day:02d}"
            circuito = cols[2].text.strip()

            # Trova il link del circuito
            circuit_link_tag = cols[2].find("a")
            if not circuit_link_tag:
                print(f"Nessun link trovato per il circuito '{circuito}'")
                continue

            circuit_url = "https://it.wikipedia.org" + circuit_link_tag['href']
            circuit_res = requests.get(circuit_url, headers=headers)

            if circuit_res.status_code != 200:
                print(f"Failed to fetch circuit page: {circuit_url}")
                continue

            circuit_soup = BeautifulSoup(circuit_res.content, "html.parser")

            # Estrai coordinate dalla pagina del circuito
            lat, lon = extract_coordinates(circuit_soup)

            # Estrai informazioni dal resoconto dettagliato
            link_tag = cols[-1].find("a")
            if not link_tag:
                continue

            dettaglio_url = "https://it.wikipedia.org" + link_tag['href']
            dettaglio_res = requests.get(dettaglio_url, headers=headers)

            if dettaglio_res.status_code != 200:
                print(f"Failed to fetch detail page: {dettaglio_url}")
                continue

            dettaglio_soup = BeautifulSoup(dettaglio_res.content, "html.parser")
            infobox = dettaglio_soup.find("table", class_="infobox")

            nome_ufficiale, percorso, notturna = "", "", "No"

            if infobox:
                for r in infobox.find_all("tr"):
                    header = r.find("th")
                    value = r.find("td")
                    if not header or not value:
                        continue

                    label = header.text.strip().lower()
                    content = value.text.strip()

                    if "nome ufficiale" in label:
                        nome_ufficiale = content
                    elif "percorso" in label:
                        percorso = content
                    elif "note" in label and "notturna" in content.lower():
                        notturna = "Sì"

            print(year, date_str, circuito, nome_ufficiale, percorso, notturna, lat, lon)
            output.append({
                "Anno": year,
                "Data": date_str,
                "Circuito": circuito,
                "Nome ufficiale": nome_ufficiale,
                "Percorso": percorso,
                "Notturna": notturna,
                "Latitudine": lat,
                "Longitudine": lon
            })


        except Exception as e:
            print(f"Errore con anno {year}: {e}")
            continue

# Scrivi su JSON
with open("motogp_gran_premi.json", "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=4)

print("Scraping completato. File salvato come 'motogp_gran_premi.json'")