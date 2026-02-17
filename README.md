# ISB ATM Scraper

> **Real-time Accessibility Monitor for the Milan Metro**

**ISB_ATM-Scraper** is a tool that scrapes the [Informazioni Senza Barriere (ISB)](https://isb.atm.it/accessibile) portal managed by ATM (Azienda Trasporti Milanesi). It extracts real-time status updates for elevators and stairlifts across all metro lines (M1, M2, M3, M4, M5).

## Goal

The official ATM page provides accessibility data in a visual HTML format that is difficult for developers to consume programmatically. The main aim is to integrate this data into a larger project that will employ this microservice for path planning accessibility paths.

## Workings

1.  **Scheduled Scraping:** A GitHub Action workflow runs a Python script every hour.
2.  **HTML Parsing:** The script fetches the source code from `https://isb.atm.it/accessibile` and parses the html source to extract facility status.
3.  **Data Versioning:** The data is saved to `data/stations.json`.
4.  **Git Automation:** If something changed from the last parse (github action run), the workflow commits and pushes the new JSON file. This creates a permanent history of when specific elevators went out of service and when they resumed service.

## JSON Structure

This is a generalized structure example:

```json
[
    {
        "station_name": "name",
        "line": "M[1-5]", // line code
        "atm_id": "1", // this is the station id given by ATM
        "last_update": "... time stamp ...",
        "directions": [ // directions are always 2 (one each way)
            {
                "direction_name": "terminus station name A",
                "segments": [ // examples...
                    {
                        "from_to_level": "Da Piano della strada (esterno) a Piano dei tornelli (mezzanino)",
                        "options": [
                            {
                                "type": "Ascensore",
                                "description": "Ascensore P.za Primo Maggio, Stazione FS",
                                "code": "ME 211",
                                "status": "In servizio",
                                "is_working": true
                            }
                        ]
                    },
                    {
                        "from_to_level": "Da Piano dei tornelli (mezzanino) a Banchina dei treni",
                        "options": [
                            {
                                "type": "Ascensore",
                                "description": "Ascensore",
                                "code": "DM 209",
                                "status": "In servizio",
                                "is_working": true
                            }
                        ]
                    }
                ]
            },
            {
                "direction_name": "terminus station name B",
                "segments": [
                    {
                        "from_to_level": "Da Piano della strada (esterno) a Piano dei tornelli (mezzanino)",
                        "options": [
                            {
                                "type": "Ascensore",
                                "description": "Ascensore P.za Primo Maggio, Stazione FS",
                                "code": "ME 211",
                                "status": "In servizio",
                                "is_working": true
                            }
                        ]
                    },
                    {
                        "from_to_level": "Da Piano dei tornelli (mezzanino) a Banchina dei treni",
                        "options": [
                            {
                                "type": "Ascensore",
                                "description": "Ascensore",
                                "code": "PM 210",
                                "status": "In servizio",
                                "is_working": true
                            }
                        ]
                    }
                ]
            }
        ]
    },
    { ... other station ... }
]
```

## Using JSON Data

The generated JSON file is publically accessible by anyone seeking to use it and gets automatically updated every hour if changes are found.

This is how to directly access the [raw JSON data](https://raw.githubusercontent.com/Alberto-Pini-Polimi/ISB_ATM-scraper/main/data/stations.json).

## GitHub Actions

A hourly github action is performed executing the scraper and pushing the JSON changes if any are present.
