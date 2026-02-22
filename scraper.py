import json
import re
from datetime import datetime
from bs4 import BeautifulSoup
import requests
import os

URL = "https://isb.atm.it/accessibile"

class Station:
    """
    Rappresenta una singola stazione.
    Il costruttore prende il DIV html grezzo e popola gli attributi.
    """
    def __init__(self, html_div):
        self._div = html_div
        self.atm_id = self._div.get('id', '').replace('dett-', '')
        self.last_update = datetime.now().isoformat()
        
        # Estrazione Dati Principali
        self.name, self.line = self._extract_identity()
        
        # Estrazione Direzioni e Segmenti
        self.directions = self._parse_directions()

    def _clean_text(self, text):
        """Utility interna per pulire stringhe da spazi e newline."""
        if not text:
            return ""
        return " ".join(text.split())

    def _extract_identity(self):
        """
        Separa il nome della stazione dalla linea.
        Esempio input: "Wagner M1" -> ("Wagner", "M1")
        Esempio input: "Sesto 1° Maggio Fs M1" -> ("Sesto 1° Maggio Fs", "M1")
        """
        h1_tag = self._div.find('h1')
        raw_text = self._clean_text(h1_tag.get_text()) if h1_tag else "Sconosciuta ???"
        
        parts = raw_text.split()
        
        # assumiamo che la linea sia sempre l'ultimo elemento (es. M1, M2, M5) del nome scritto sul sito
        # + altro check: se l'ultimo elemento sembra una linea (inizia con M e ha numeri), lo prendiamo
        if parts and parts[-1].upper().startswith('M') and any(char.isdigit() for char in parts[-1]):
            line = parts[-1]
            name = " ".join(parts[:-1])
        else:
            line = "N/A"
            name = raw_text
            
        return name, line

    def _extract_facility_data(self, p_tag):
        """
        Estrae i dati di un singolo impianto dal tag <p>.
        Input atteso: <p> <strong> Descrizione CODICE </strong> Stato </p>

        utile sapere che:
            text: "Descrizione Codice Stato"
            description: "Descrizione CODICE" inizialmente ma poi "Descrizione" (vedi sotto alla fine del metodo)
            status: "Stato" (anche con spazio e tipicamente standardizzato)
        """

        # full text è praticamente tutto il paragrafo senza spazi inutili o new line
        text = self._clean_text(p_tag.get_text())
        
        # skippo i paragrafi "Oppure"
        if "oppure" in text.lower():
            return None # questi tanto sono impliciti nelle liste JSON

        # descrizione dentro <strong>
        # stato fuori dallo strong
        strong_tag = p_tag.find('strong') # quindi prendo quel tag strong dentro al p che mi hanno passato

        if strong_tag: # se il tag contiene qualcosa 
            description = self._clean_text(strong_tag.get_text()) # allora lo pulisco e questa diventa la descrizione intera
            status = text.replace(description, "").strip() # e lo status è tutto il paragrafo p ma senza la descrizione (cose scritte nello storng)
        else: # se non ci sono strong tag allora la struttura non è più la solita (ma non dovrebbe mai essere il caso)
            description = text
            status = "Sconosciuto" # e in questo caso non saprei come recuperare lo status

        # trovo lo stato facilmente (sperando sia appunto sempre scritto così)
        is_working = "in servizio" in status.lower()
        
        # trovo il tipo (Ascensore/Montascale): molto semplicemente se trovo scritto quelle parole nella descrizione
        f_type = "Altro"
        if "ascensore" in description.lower():
            f_type = "Ascensore"
        elif "montascale" in description.lower():
            f_type = "Montascale"
        elif "rampa" in description.lower():
            description = description.replace("<strong>", "").replace("</strong>", "") # questo vale solo per le rampe (almeno tipicamente)
            f_type = "Rampa"

        # Parsing Codice Univoco (es. ME5, DM 121)
        # Regex: Cerca stringa finale composta da LETTERE + spazio opzionale + NUMERI
        code_match = re.search(r'([A-Z]+\s?\d+)$', description)
        code = code_match.group(1) if code_match else "N/A"

        # CAMBIO!! inoltre alla descrizione tolgo il codice finale dato che c'è appunto un campo specifico per quello
        description = description.replace(" " + code, "")

        # e infine ritorno l'oggetto stazione 
        return {
            "type": f_type,
            "description": description,
            "code": code,
            "status": status, # Manteniamo il testo originale dello stato (es. "In servizio")
            "is_working": is_working
        }

    def _parse_directions(self):
        """
        Logica complessa per iterare H3 -> Table -> Rows nell'HTML
        """
        directions_list = []

        # allora la struttura di questo sito non è proprio il top
        # c'è una div con tantissimi tag h1, h2, h3, table, h3, table che sono tutti fratelli (zero annidazione)
        # quindi parto prima dagli h3 per trovare direttamnete le direzioni di ogni stazione
        headers = self._div.find_all('h3')

        for h3 in headers: # itero quindi questi tag
            direction_name = self._clean_text(h3.get_text())
            segments = []

            # becco la tabella successiva ....
            next_node = h3.find_next_sibling()
            target_table = None
            # ... (saltando eventuali <b> o <br>)
            while next_node:
                # se trovo una table allora so che devo parsare per gli impianti
                if next_node.name == 'table':
                    target_table = next_node
                    break
                # trovando un h3 so che passo al secondo h3 con l'altra direzione
                # o con la prima direzione della successiva stazione
                if next_node.name == 'h3':
                    break
                next_node = next_node.find_next_sibling()

            # inizio quindi a parsare la tabella
            if target_table:
                rows = target_table.find_all('tr')
                for row in rows:
                    # ignoriamo le righe di intestazione (th)
                    cells = row.find_all('td')
                    if len(cells) < 2: 
                        continue 
                    
                    # Cella 0: livello (From -> To)
                    from_to = self._clean_text(cells[0].get_text())
                    
                    # Cella 1: lista impianti (<p>)
                    options = []
                    facilities_td = cells[1]
                    paragraphs = facilities_td.find_all('p')
                    
                    for p in paragraphs:
                        facility = self._extract_facility_data(p) # e parso l'effettivo paragrafo
                        if facility:
                            options.append(facility)
                    
                    # aggiungo quindi il segmento se le opzioni sono valide
                    if options:
                        segments.append({
                            "from_to_level": from_to,
                            "options": options
                        })
            
            # finito il parsing aggiungo i risultati dei segmenti parsati
            if segments:
                directions_list.append({
                    "direction_name": direction_name,
                    "segments": segments
                })
        
        return directions_list

    def to_dict(self):
        """
        Restituisce la rappresentazione JSON-ready dell'oggetto python.
        """
        return {
            "station_name": self.name,
            "line": self.line,
            "atm_id": self.atm_id,
            "last_update": self.last_update,
            "directions": self.directions
        }


class ATMScraper:
    """
    Gestisce il parsing dell'intera pagina HTML.
    """
    def __init__(self, html_content):
        self.soup = BeautifulSoup(html_content, 'html.parser')

    def get_stations(self):
        """
        Trova tutti i div delle stazioni e restituisce una lista di dizionari.
        """
        results = []
        # trova tutti i div con classe 'station-detail' o id che inizia per 'dett-', queste
        # sono tutte le stazioni all'interno dell'HTML
        station_divs = self.soup.find_all('div', attrs={'id': re.compile(r'^dett-')})

        print(f"Trovate {len(station_divs)} stazioni.")

        for div in station_divs:
            try:
                station = Station(div) # parso la stazione direttamente chiamando il suo costruttore
                results.append(station.to_dict()) # poi trasformo l'oggetto in un dizionario python per la conversione al JSON successiva
            except Exception as e:
                print(f"Errore nel parsing di una stazione: {e}")
                continue
                
        return results # results è quindi una lista di oggetti stazione pronti ad essere convertiti in JSON

    def save_to_file(self, data, filename="data/stations.json"):
        """Salva tutto in un JSON file."""
        # robe piuttosto standard...
        directory = os.path.dirname(filename)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)
            
        print(f"--> saving data to {filename}...")
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        print("--> done! file saved successfully.")






def fetch_data(url):
    """Prendi il raw HTML dall'URL forzando la lingua italiana."""
    print(f"--> connecting to {url}...")
    
    headers = { # il parsing lo faccio in italiano quindi mi serve l'header
        "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7" 
    }

    try: # e poi chiamo per prendere il content della risposta
        response = requests.Session().get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.content
    except requests.RequestException as e:
        print(f"Request failed: {e}")
        return None

if __name__ == "__main__":
    
    raw_html = fetch_data(URL)

    scraper = ATMScraper(raw_html)
    data = scraper.get_stations()
    
    scraper.save_to_file(data)
