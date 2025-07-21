import requests
from bs4 import BeautifulSoup
import csv
import re
from datetime import datetime

WIKI_BASE = "https://it.wikipedia.org"
START_YEAR = 2005
END_YEAR = datetime.now().year

def normalizza_categoria(titolo):
    t = titolo.lower()
    if "motogp" in t:
        return "MotoGP"
    elif "moto2" in t or "classe 250" in t:
        return "Moto2"
    elif "moto3" in t or "classe 125" in t:
        return "Moto3"
    return None

def parse_data(data_raw):
    match = re.search(r'(\d{1,2})[-–](\d{1,2})[-–](\d{4})', data_raw)
    if match:
        g, m, a = match.groups()
        return f"{a}-{m.zfill(2)}-{g.zfill(2)}"
    match = re.search(r'(\d{1,2})\s+\w+\s+(\d{4})', data_raw)
    if match:
        g, a = match.groups()
        mesi = {
            "gennaio": "01", "febbraio": "02", "marzo": "03", "aprile": "04",
            "maggio": "05", "giugno": "06", "luglio": "07", "agosto": "08",
            "settembre": "09", "ottobre": "10", "novembre": "11", "dicembre": "12"
        }
        for mese, numero in mesi.items():
            if mese in data_raw.lower():
                return f"{a}-{numero}-{g.zfill(2)}"
    return ""

def estrai_nome_pilota(td_pilota):
    """Estrae il nome del pilota dalla cella, rimuovendo link e bandiere"""
    # Cerca tutti i link <a> nella cella
    links = td_pilota.find_all('a')
    for link in links:
        # Se il link ha un title che non contiene "bandiera", è probabilmente il pilota
        if link.get('title') and 'bandiera' not in link.get('title', '').lower():
            return link.get_text(strip=True)
    
    # Se non trova un link appropriato, prende tutto il testo pulito
    text = td_pilota.get_text(strip=True)
    # Rimuove eventuali caratteri speciali e spazi extra
    return re.sub(r'\s+', ' ', text)

def estrai_da_arrivati(soup, year, date_str, circuito, nome_ufficiale):
    risultati = []
    
    # Cerca la sezione MotoGP
    motogp_heading = soup.find('h2', {'id': 'MotoGP'})
    if not motogp_heading:
        print(f"   ❌ Sezione MotoGP non trovata")
        return risultati
    
    print(f"   ✅ Sezione MotoGP trovata")
    
    # Trova il div contenitore della sezione MotoGP
    motogp_div = motogp_heading.find_parent('div', class_='mw-heading')
    if not motogp_div:
        print(f"   ❌ Div MotoGP non trovato")
        return risultati
    
    # Cerca la sezione "Arrivati al traguardo"
    current_element = motogp_div
    arrivati_heading = None
    
    # Scorri gli elementi successivi fino a trovare "Arrivati al traguardo"
    while current_element:
        current_element = current_element.find_next_sibling()
        if not current_element:
            break
            
        # Controlla se è un heading h3 con "Arrivati al traguardo"
        h3 = current_element.find('h3')
        if h3 and 'arrivati al traguardo' in h3.get_text(strip=True).lower():
            arrivati_heading = h3
            break
    
    if arrivati_heading:
        print(f"   ✅ Sezione 'Arrivati al traguardo' trovata")
        
        # Trova la tabella degli arrivati
        arrivati_div = arrivati_heading.find_parent('div', class_='mw-heading')
        tabella_arrivati = arrivati_div.find_next_sibling('table', class_='wikitable')
        
        if tabella_arrivati:
            print(f"   ✅ Tabella arrivati trovata")
            
            # Estrai i dati dalla tabella
            rows = tabella_arrivati.find_all('tr')
            if len(rows) > 1:  # Salta l'header
                header_row = rows[0]
                headers = [th.get_text(strip=True).lower() for th in header_row.find_all(['th', 'td'])]
                
                # Trova gli indici delle colonne
                try:
                    pilota_idx = headers.index('pilota')
                    griglia_idx = headers.index('griglia')
                    
                    for row in rows[1:]:
                        cells = row.find_all(['td', 'th'])
                        if len(cells) > max(pilota_idx, griglia_idx):
                            pilota_nome = estrai_nome_pilota(cells[pilota_idx])
                            griglia_pos = cells[griglia_idx].get_text(strip=True)
                            
                            if pilota_nome and griglia_pos:
                                risultati.append({
                                    "Year": str(year),
                                    "Date": date_str,
                                    "Circuit": circuito,
                                    "OfficialName": nome_ufficiale,
                                    "Class": "MotoGP",
                                    "RiderName": pilota_nome,
                                    "Position": griglia_pos
                                })
                    
                    print(f"   ✅ Estratti {len(risultati)} piloti da MotoGP - Arrivati")
                    
                except ValueError as e:
                    print(f"   ❌ Errore nell'identificare le colonne: {e}")
        else:
            print(f"   ❌ Tabella arrivati non trovata")
    else:
        print(f"   ❌ Sezione 'Arrivati al traguardo' non trovata")
    
    # Cerca la sezione "Ritirati"
    current_element = motogp_div
    ritirati_heading = None
    
    # Scorri gli elementi successivi fino a trovare "Ritirati"
    while current_element:
        current_element = current_element.find_next_sibling()
        if not current_element:
            break
            
        # Controlla se è un heading h3 con "Ritirati"
        h3 = current_element.find('h3')
        if h3 and 'ritirati' in h3.get_text(strip=True).lower():
            ritirati_heading = h3
            break
    
    if ritirati_heading:
        print(f"   ✅ Sezione 'Ritirati' trovata")
        
        # Trova la tabella dei ritirati
        ritirati_div = ritirati_heading.find_parent('div', class_='mw-heading')
        tabella_ritirati = ritirati_div.find_next_sibling('table', class_='wikitable')
        
        if tabella_ritirati:
            print(f"   ✅ Tabella ritirati trovata")
            
            # Estrai i dati dalla tabella
            rows = tabella_ritirati.find_all('tr')
            if len(rows) > 1:  # Salta l'header
                header_row = rows[0]
                headers = [th.get_text(strip=True).lower() for th in header_row.find_all(['th', 'td'])]
                
                # Trova gli indici delle colonne
                try:
                    pilota_idx = headers.index('pilota')
                    griglia_idx = headers.index('griglia')
                    
                    ritirati_count = 0
                    for row in rows[1:]:
                        cells = row.find_all(['td', 'th'])
                        if len(cells) > max(pilota_idx, griglia_idx):
                            pilota_nome = estrai_nome_pilota(cells[pilota_idx])
                            griglia_pos = cells[griglia_idx].get_text(strip=True)
                            
                            if pilota_nome and griglia_pos:
                                risultati.append({
                                    "Year": str(year),
                                    "Date": date_str,
                                    "Circuit": circuito,
                                    "OfficialName": nome_ufficiale,
                                    "Class": "MotoGP",
                                    "RiderName": pilota_nome,
                                    "Position": griglia_pos
                                })
                                ritirati_count += 1
                    
                    print(f"   ✅ Estratti {ritirati_count} piloti da MotoGP - Ritirati")
                    
                except ValueError as e:
                    print(f"   ❌ Errore nell'identificare le colonne dei ritirati: {e}")
        else:
            print(f"   ❌ Tabella ritirati non trovata")
    else:
        print(f"   ❌ Sezione 'Ritirati' non trovata")
    
    return risultati

def main():
    csv_data = []
    for year in range(START_YEAR, END_YEAR + 1):
        url = f"{WIKI_BASE}/wiki/Motomondiale_{year}"
        print(f"\n➡️ Elaboro stagione {year}: {url}")
        r = requests.get(url)
        if r.status_code != 200:
            print(f"   ⚠️ Impossibile aprire pagina {url}")
            continue
        soup = BeautifulSoup(r.content, "html.parser")
        
        # Trova la tabella con i Gran Premi
        for tab in soup.find_all("table", {"class": "wikitable"}):
            for row in tab.find_all("tr")[1:]:  # Salta l'header
                cols = row.find_all(["td", "th"])
                if len(cols) < 6:
                    continue
                
                data_str = parse_data(cols[0].text.strip())
                circuito = cols[1].text.strip()
                nome_ufficiale = cols[2].text.strip()
                
                # Cerca il link al resoconto
                link_resoconto = None
                for a in cols[-1].find_all("a", href=True):
                    if "resoconto" in a.text.lower():
                        link_resoconto = a["href"]
                        break
                
                if not link_resoconto:
                    continue
                
                full_url = WIKI_BASE + link_resoconto
                print(f"   🔗 {nome_ufficiale} - carico resoconto: {full_url}")
                
                gr = requests.get(full_url)
                if gr.status_code != 200:
                    print(f"   ⚠️ Impossibile accedere resoconto {full_url}")
                    continue
                
                soup_gp = BeautifulSoup(gr.content, "html.parser")
                q = estrai_da_arrivati(soup_gp, year, data_str, circuito, nome_ufficiale)
                
                if q:
                    print(f"   ✅ {nome_ufficiale}: trovati {len(q)} piloti (griglia)")
                    csv_data.extend(q)
                else:
                    print(f"   ❌ Nessun dato trovato per {nome_ufficiale}")
    
    # Salva i dati in CSV
    with open("motogp_griglia.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["Year", "Date", "Circuit", "OfficialName", "Class", "RiderName", "Position"])
        w.writeheader()
        w.writerows(csv_data)
    
    print(f"\n✅ CSV creato: motogp_griglia.csv con {len(csv_data)} righe")

if __name__ == "__main__":
    main()