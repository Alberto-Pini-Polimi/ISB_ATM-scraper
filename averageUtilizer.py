import requests

JSON_URL = "https://raw.githubusercontent.com/Alberto-Pini-Polimi/ISB_ATM-scraper/main/data/stations.json"

def controlla_accessibilita():
    print("Scaricando i dati aggiornati sull'accessibilità ATM...\n")
    try:
        response = requests.get(JSON_URL, timeout=10)
        response.raise_for_status()
        stations_data = response.json()
    except Exception as e:
        print(f"Errore durante il download dei dati: {e}")
        return

    target_stations = ["piola"]
    
    for station in stations_data:
        st_name = station.get("station_name", "").lower()
        
        if any(target in st_name for target in target_stations):
            print(f"\n🚇 Stazione: {station.get('station_name')} (Linea {station.get('line')})")
            
            impianti_trovati = False
            
            for direction in station.get("directions", []):
                for segment in direction.get("segments", []):
                    for facility in segment.get("options", []):
                            
                        impianti_trovati = True
                        
                        tipo = facility.get("type", "Impianto")
                        descrizione = facility.get("description", "Nessuna descrizione")
                        funzionante = facility.get("is_working", False)
                        stato_testo = facility.get("status", "Sconosciuto")
                        percorso = segment.get("from_to_level", "")
                        
                        icona = "✅" if funzionante else "❌"
                        
                        print(f" {icona} [{tipo}] {descrizione}")
                        print(f"     Tratta: {percorso}")
                        print(f"     Stato ATM: {stato_testo}\n")
            
            print("=" * 70)

if __name__ == "__main__":
    controlla_accessibilita()