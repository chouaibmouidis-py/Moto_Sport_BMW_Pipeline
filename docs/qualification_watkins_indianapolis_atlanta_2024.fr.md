# Qualification Watkins Glen, Indianapolis et Road Atlanta 2024

JSON officiels inspectés le 12 novembre 2026. Après confirmation par Chouaib
des résultats attendus de l'exécution complète, les six sources sont marquées
`tested_locally`. L'agent n'a pas rejoué ce lot ni la suite de tests.
Classements marqués Official. Les rapports finaux sont sélectionnés seuls,
sans concaténer les relevés horaires. Indianapolis : dossier 17 WeatherTech,
pas le dossier 18 Mustang Challenge.

| Course | Session | Heure | Participants | BMW | Fragments voitures | Pilotes | Arrêts | Arrêts BMW |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Watkins Glen | 202406231110-race | 6 | 56 | 4 | 65 | 171 | 407 | 38 |
| Indianapolis | 202409221230-race | 6 | 56 | 4 | 64 | 171 | 405 | 32 |
| Road Atlanta | 202410121210-race | 10 | 53 | 4 | 63 | 189 | 578 | 41 |

Les six liens exacts sont dans le manifeste. Fichiers :
`03_Results_Race_Official.JSON` et `20_Pit Stops Time Cards_Race.JSON`.
Aucun doublon voiture/numéro d'arrêt repéré dans les trois rapports d'arrêts.

## Anomalies à conserver

- Watkins Glen : sept `count_mismatch` (12,50 %), dont BMW 25 (10/11).
  Autres voitures : 19 (9/8), 11 (8/7), 81 (8/7), 62 (7/6), 63 (7/6), 27 (4/3).
  Voitures 47 et 18 : zéro déclaré, aucun détail (`zero_reported_no_detail`).
- Indianapolis : neuf `count_mismatch` (16,07 %) : 66 (5/6), 55 (7/6),
  83 (7/6), 20 (11/10), 34 (9/8), 63 (6/5), 21 (5/4), 023 (6/5), 31 (4/3).
  Voiture 19 : un arrêt déclaré sans détail (`missing_stop_details`).
- Road Atlanta : six `count_mismatch` (11,32 %) : 10 (11/10), 86 (11/10),
  120 (10/9), 4 (9/10), BMW 25 (6/5), 85 (5/4).
  Voiture 44 : un arrêt déclaré sans détail (`missing_stop_details`).

Les causes ne sont pas établies ; aucune correction automatique.
BMW présentes : 24 et 25 (M Hybrid V8), 1 et 96 (M4 GT3, sans EVO).

## Références cumulées confirmées par Chouaib

Les onze courses 2024 et onze courses 2025 représentent
44 documents, 937 participations dont 86 BMW, 8 307 arrêts dont 711 BMW,
1 066 fragments voitures, 2 877 entrées pilotes et 22 bilans qualité de comptage.
Toujours douze fichiers de sortie. L'exécution complète a été confirmée
par Chouaib ; les anomalies restent visibles dans les rapports qualité.
