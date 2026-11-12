# Qualification Daytona et Sebring 2024

Inspection des JSON officiels le 12 novembre 2026. Après confirmation par
Chouaib des résultats attendus, les quatre sources sont marquées `tested_locally`.
L'agent n'a pas rejoué ce lot ni la suite de tests après cette confirmation.
Les index officiels ont permis de sélectionner seulement les rapports finaux
Hour 24 et Hour 12, sans concaténer les relevés intermédiaires.

| Course | Session | Participants | BMW | Fragments voitures | Pilotes | Arrêts | Arrêts BMW |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Daytona, heure 24 | 202401271340-race | 59 | 4 | 112 | 423 | 1 545 | 123 |
| Sebring, heure 12 | 202403160940-race | 58 | 4 | 69 | 207 | 788 | 51 |

Les classements portent `Official`, championnat IMSA WeatherTech.
Daytona : `20_Pit Stops Time Cards.JSON`, sans suffixe `_Race`.
Sebring : `20_Pit Stops Time Cards_Race.JSON`.
Les chemins exacts des quatre rapports sont dans le manifeste.

Daytona : 59 numéros distincts dans 112 fragments ; aucun doublon de clé
voiture/numéro d'arrêt repéré. Seize écarts de comptage, soit 27,12 %,
dont la BMW 24 (30 déclarés / 31 détaillés).
Sebring : 57 numéros dans le rapport d'arrêts pour 58 participants classés.
Quatre écarts : 45 (13/12), 80 (12/11), 85 (7/6), 83 (9/8), soit 6,90 %.
Voiture 32 : un arrêt déclaré, aucune ligne détaillée (`missing_stop_details`).
Les causes ne sont pas établies et aucune valeur source n'est remplacée.

BMW présentes dans les deux classements : 24, 25 (M Hybrid V8),
1 et 96 (M4 GT3, sans EVO).

Références cumulées confirmées par Chouaib après publication : 772 participations dont
74 BMW, 6 917 arrêts dont 600 BMW, 874 fragments voitures,
2 346 entrées pilotes et 19 bilans de comptage. Toujours douze sorties.
Les anomalies signalées sont conservées dans les rapports qualité.
