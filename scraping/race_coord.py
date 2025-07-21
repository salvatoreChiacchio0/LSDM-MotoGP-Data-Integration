import requests
import json
from datetime import datetime
import re
from tqdm import tqdm

def fetch_weather_data(latitude, longitude, date):
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": date,
        "end_date": date,
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,weathercode",
        "timezone": "auto",
    }
    
    try:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Errore API ({response.status_code}) per lat={latitude}, lon={longitude}, data={date}")
            return None
    except Exception as e:
        print(f"Errore nella richiesta API: {e}")
        return None

def interpret_weathercode(code):
    weather_map = {
        0: "Soleggiato",
        1: "Prevalentemente soleggiato",
        2: "Nuvoloso",
        3: "Molto nuvoloso",
        45: "Nebbia",
        48: "Nebbia brinosa",
        51: "Pioggia leggera",
        53: "Pioggia moderata",
        55: "Pioggia intensa",
        61: "Rovesci leggeri",
        63: "Rovesci moderati",
        65: "Rovesci intensi",
        71: "Neve leggera",
        73: "Neve moderata",
        75: "Neve intensa",
        95: "Temporali",
    }
    return weather_map.get(code, "Sconosciuto")

def normalize_date(date_str):
    date_str = date_str.strip().replace("\n", " ").replace("\r", " ")

    if not date_str or re.fullmatch(r"\d{1,2}", date_str):
        return None

    if "," in date_str:
        parts = [p.strip() for p in date_str.split(",")]
        for part in parts:
            if re.search(r"\b\d{4}\b", part):
                date_str = part
                break
        else:
            date_str = parts[0]
    elif "–" in date_str:
        date_str = date_str.split("–")[0].strip()

    date_formats = [
        "%B %d, %Y", "%d %B %Y", "%Y-%m-%d",
        "%B %d %Y", "%b %d, %Y", "%d %b %Y",
    ]

    for fmt in date_formats:
        try:
            parsed_date = datetime.strptime(date_str, fmt)
            return parsed_date.strftime("%Y-%m-%d")
        except ValueError:
            continue

    return None

# === Caricamento dati ===
with open("motogp_gran_premi.json", "r", encoding="utf-8") as f:
    race_data = json.load(f)

weather_results = []

# === Estrazione dati meteo ===
for race in tqdm(race_data, desc="Elaborazione gare"):
    circuit_name = race.get("Circuito", "")
    latitude = race.get("Latitudine", None)
    longitude = race.get("Longitudine", None)
    race_date_str = race.get("Data", "")

    # Normalizza la data
    race_date = normalize_date(race_date_str)
    if not race_date:
        print(f"[!] Data non riconosciuta per gara: {circuit_name}")
        continue

    # Controlla se le coordinate sono valide
    try:
        latitude = float(latitude)
        longitude = float(longitude)
    except (ValueError, TypeError):
        print(f"[!] Coordinate non valide per {circuit_name}: Lat={latitude}, Lon={longitude}")
        continue

    # Recupera i dati meteo
    weather_data = fetch_weather_data(latitude, longitude, race_date)

    if weather_data and "daily" in weather_data:
        daily_data = weather_data["daily"]
        for i, day in enumerate(daily_data["time"]):
            if day == race_date:
                print(f"[+] Dati meteo trovati per {circuit_name} il {race_date}")
                weather = {
                    "Circuito": circuit_name,
                    "Data": race_date,
                    "Temp_Max": daily_data["temperature_2m_max"][i],
                    "Temp_Min": daily_data["temperature_2m_min"][i],
                    "Precipitazione": daily_data["precipitation_sum"][i],
                    "Condizione_Meteo": interpret_weathercode(daily_data["weathercode"][i]),
                }
                weather_results.append(weather)
                break
    else:
        print(f"[!] Nessun dato meteo per {circuit_name} il {race_date}")

# === Salvataggio risultati ===
with open("race_weather_data_final.json", "w", encoding="utf-8") as f:
    json.dump(weather_results, f, indent=4, ensure_ascii=False)

print("✅ Dati meteo salvati in 'race_weather_data_final.json'")