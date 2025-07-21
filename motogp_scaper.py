import requests
from bs4 import BeautifulSoup
import json
from tqdm import tqdm
import time

BASE_URL = "https://en.wikipedia.org"
START_URL = "https://en.wikipedia.org/wiki/List_of_Grand_Prix_motorcycle_races"
OUTPUT_FILE = "output2.json"
LIMIT = 55
results = []
log = []

def get_soup(url):
    try:
        res = requests.get(url)
        res.raise_for_status()
        return BeautifulSoup(res.text, "html.parser")
    except Exception as e:
        log.append(f"Errore nel recuperare {url}: {e}")
        return None

def extract_infobox_data(soup, url):
    infobox = soup.find("table", class_="infobox")
    if not infobox:
        log.append(f"Nessuna infobox trovata in {url}")
        return None

    data = {}
    rows = infobox.find_all("tr")
    for row in rows:
        th = row.find("th")
        td = row.find("td")
        if th and td:
            label = th.text.strip()
            value = td.text.strip()
            if label in ["Date", "Official name", "Location", "Course"]:
                data[label] = value

    return data if data else None

def process_single_event(link):
    soup = get_soup(link)
    if not soup:
        return None
    return extract_infobox_data(soup, link)

def process_multiple_events(event_url):
    soup = get_soup(event_url)
    if not soup:
        return []

    # Find the 'By year' section
    by_year_header = soup.find(id="By_year")
    if not by_year_header:
            by_year_header = soup.find(id="Winners_by_season")
            if not by_year_header:
                by_year_header = soup.find(id="Winners_of_the_Italian_motorcycle_Grand_Prix")
                if not by_year_header:
                    by_year_header = soup.find(id="Winners_of_the_Czech_Republic_motorcycle_Grand_Prix")
                    if not by_year_header:
                        by_year_header = soup.find(id="Grand_Prix_motorcycle_racing_winners")
                        if not by_year_header:
                            log.append(f"Nessuna sezione WINNERS trovata in {event_url}")
                            return []

    # Initialize variables
    sub_results = []
    current_table = by_year_header.find_next("table")

    while current_table:
        # Process rows in the current table
        rows = current_table.find_all("tr")[1:]  # Skip header
        for row in rows:
            cols = row.find_all("td")
            if not cols:
                continue
            link_tag = cols[-1].find("a")  # Last column often contains links
            if link_tag and link_tag.get("href"):
                race_link = BASE_URL + link_tag["href"]
                race_soup = get_soup(race_link)
                if race_soup:
                    data = extract_infobox_data(race_soup, race_link)
                    if data:
                        sub_results.append(data)
                time.sleep(1)

        # Check if there are more tables to process
        next_section = current_table.find_next("h2")  # Look for the next section header
        if next_section and next_section.text.strip() == "References":
            break  # Stop if we reach the 'References' section

        # Move to the next table
        current_table = current_table.find_next("table")

    return sub_results

def main():
    soup = get_soup(START_URL)
    if not soup:
        print("❌ Impossibile caricare la pagina principale.")
        return

    tables = soup.find_all("table", class_="wikitable sortable")
    if not tables:
        print("❌ Nessuna tabella 'wikitable sortable' trovata.")
        return
    table = tables[0]
    rows = table.find_all("tr")[1:LIMIT+1]  # Limit to first LIMIT rows for testing


    for row in tqdm(rows, desc="Processing races"):
        cols = row.find_all("td")
        if len(cols) < 3:
            log.append("Riga saltata (non ha 3 colonne).")
            continue
        links = cols[0].find_all("a")
        if len(links) > 1:
            race_link_tag = links[1]  # secondo link, quello giusto
        elif len(links) == 1:
            race_link_tag = links[0]
        else:
            race_link_tag = None

        if not race_link_tag:
            log.append(f"Nessun link utile nella riga {cols[0].text.strip()}")
            continue
        race_url = BASE_URL + race_link_tag.get("href")
        try:
            num_races = int(cols[2].text.strip())
        except:
            log.append(f"Errore nel leggere numero gare per {race_url}")
            continue

        if num_races == 1:
            data = process_single_event(race_url)
            if data:
                results.append(data)
        else:
            sub_data = process_multiple_events(race_url)
            if sub_data:
                results.extend(sub_data)
        time.sleep(0.2)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    with open("log.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(log))

    print(f"\n✅ {len(results)} eventi salvati in {OUTPUT_FILE}")
    print(f"📄 Log dettagliato in log.txt")

if __name__ == "__main__":
    main()
