# Qualification Long Beach, Canadian Tire et VIR 2024

JSON officiels inspectés le 12 novembre 2026. Après confirmation par Chouaib
des résultats attendus du pipeline et des anomalies signalées, les six sources
sont marquées `tested_locally`. Le pipeline de ce lot n'a pas été rejoué par
l'agent ; la suite complète précédente comptait 105 tests réussis.

| Course | Session | Participants | BMW | Entrées voitures | Pilotes | Arrêts | Arrêts BMW |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Long Beach | 202404201335-race | 27 | 3 | 25 | 50 | 31 | 4 |
| Canadian Tire | 202407141105-race | 34 | 2 | 34 | 68 | 95 | 9 |
| VIR | 202408251210-race | 23 | 2 | 23 | 46 | 58 | 4 |

Les trois classements portent `Official` et appartiennent à IMSA WeatherTech.
Rapports : `03_Results_Race_Official.JSON` et
`20_Pit Stops Time Cards_Race.JSON`, liens exacts dans le manifeste.

Long Beach : écarts de comptage pour 25 (3 déclarés / 2 détaillés),
27 (2/1) et 12 (3/2), soit 3/27 = 11,11 %. La voiture 120 déclare un arrêt
sans détail : `missing_stop_details`, à ne pas compter comme `count_mismatch`.
Canadian Tire et VIR : aucun écart de comptage repéré dans les JSON.
Aucune correction automatique des valeurs source.

Les BMW GT sont des M4 GT3, sans ajout du suffixe EVO. Les BMW 24 et 25
sont présentes à Long Beach ; ne pas exiger leur présence aux deux autres courses.

Références cumulées confirmées par Chouaib : 655 participations dont 66 BMW,
4 584 arrêts dont 426 BMW, 693 entrées voitures et 1 716 entrées pilotes,
17 sessions et 17 bilans qualité de comptage. Toujours douze fichiers de sortie.
