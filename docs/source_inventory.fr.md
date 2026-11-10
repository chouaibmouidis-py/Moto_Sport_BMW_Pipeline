# Inventaire des sources et conséquences pour le pipeline

Vérification du 6 novembre 2026. Ce document distingue les fichiers lus des
familles repérées dans les index officiels. Il ne constitue pas un inventaire
exhaustif de tous les championnats, saisons ou schémas.

## Sources officielles

- [Index IMSA 2025](https://imsa.results.alkamelcloud.com/Results/25_2025/)
- [Course Road America 2025](https://imsa.results.alkamelcloud.com/Results/25_2025/16_Road%20America/01_IMSA%20WeatherTech%20SportsCar%20Championship/202508031310_Race/)
- [Course Long Beach 2025](https://imsa.results.alkamelcloud.com/Results/25_2025/07_Long%20Beach%20Street%20Circuit/01_IMSA%20WeatherTech%20SportsCar%20Championship/202504121405_Race/)
- [Course Daytona 2025](https://imsa.results.alkamelcloud.com/Results/25_2025/02_Daytona%20International%20Speedway/01_IMSA%20WeatherTech%20SportsCar%20Championship/202501251340_Race/)
- [Portail WEC](https://fiawec.alkamelsystems.com/)
- [Portail GT World Challenge Europe](https://www.gt-world-challenge-europe.com/results)
- [Résultats DTM](https://www.dtm.com/ergebnisse/results?season=2025)
- [Portail WorldSBK](https://www.worldsbk.com/en/standings)

Les portails hors IMSA ont été repérés, mais leurs fichiers et schémas ne sont
pas validés comme compatibles avec notre lecteur. L'URL historique WEC testée
renvoie maintenant une application HTML : HTTP 200 ne garantit pas un fichier
de résultats. La disponibilité des sources FIM EWC reste à vérifier.

## Familles présentes dans l'index de course Road America

| Famille | Formats repérés | Usage envisagé |
| --- | --- | --- |
| Grilles de départ, dans un sous-dossier | Inventaire détaillé restant à faire | Position de départ |
| Résultats généraux | CSV, JSON, PDF | Classement, tours, écarts, statut |
| Résultats par catégorie | JSON, PDF | Classements de classes |
| Meilleurs tours par pilote | PDF | Synthèses de performance |
| Lap chart | JSON, PDF | Positions au fil des tours |
| Meilleurs secteurs | JSON, PDF | Analyse des secteurs |
| Séquence des leaders | PDF | Changements en tête |
| Distance et vitesse moyennes | JSON, PDF | Synthèses |
| Séquence des meilleurs tours | JSON, PDF | Progression des références |
| Analyse par tour | PDF | Analyse détaillée |
| Drive time | PDF | Temps de conduite |
| Arrêts au stand | JSON, PDF | Entrées/sorties et durées |
| Time cards | CSV, JSON, PDF | Tours chronométrés |
| Analyse des drapeaux | PDF | Contexte de neutralisation |
| Météo | CSV, JSON, PDF | Mesures horodatées |

Des résultats Official, Provisional et Unofficial coexistent. Des points de
championnat et des récompenses figurent également au niveau supérieur, ainsi
que des essais et qualifications. Plusieurs formats peuvent représenter les
mêmes faits : ne pas les concaténer comme des observations indépendantes.
Présence dans un index ne signifie pas que le contenu de chaque PDF a été lu.

## Comparaison de fichiers effectivement lus

Les volumes suivants concernent le JSON d'arrêts ; ce sont des entrées source,
pas nécessairement des véhicules ou personnes distincts.

| Épreuve 2025 | Entrées voitures | Entrées pilotes | Arrêts |
| --- | ---: | ---: | ---: |
| Long Beach | 26 | 52 | 32 |
| Road America | 50 | 100 | 137 |
| Daytona, rapport Hour 24 | 69 | 265 | 1622 |

Les trois JSON d'arrêts ont les racines `session` et `pit_stop_analysis`.
Les résultats officiels ont `session`, `fastest_lap`, `classification` :
27 entrées à Long Beach, 48 à Road America, 61 à Daytona Hour 24.
Le nombre d'entrées du classement n'est donc pas celui du rapport d'arrêts.
La cause des écarts individuels reste à analyser avant les jointures.

Le JSON Time Cards de Road America a les racines `session`, `participants`
et 48 entrées de participants. Chaque participant possède des listes `drivers`
et `laps`. Les tours exposent numéro, pilote, durée, vitesses, temps écoulé,
heure, validité, indicateurs d'invalidation, passage de ligne des stands et
`sector_times`. Ces indicateurs doivent accompagner l'analyse des chronos ;
un tour invalide ne doit pas devenir une référence de performance par défaut.

La course de Daytona possède des sous-dossiers Hour 1 à Hour 24. Leur contenu
ne doit pas être additionné sans vérifier la portée temporelle et les recouvrements.

Les JSON météo lus ont les racines `session`, `meteoSamples` et les champs :
`time_utc_secconds` (orthographe source), `time_utc_str`, `air_temp`,
`track_temp`, `pressure`, `wind_speed`, `wind_direction`.
Daytona Hour 24 contient 1333 échantillons. Les unités et les conventions de
temps doivent être vérifiées par famille et version ; ne pas déduire une unité
de la seule amplitude des nombres. Pas de mesure d'humidité identifiée dans
ces champs, ni de télémétrie interne de maintenance ou de carburant démontrée.

## Décisions de conception proposées

1. Conserver la source brute intégrale, sa provenance et ses versions.
2. Identifier chaque document par source, championnat, saison, événement,
   session, famille et révision/période de rapport. Le nom de course seul
   ne constitue pas une clé suffisante.
3. Isoler les fichiers par identité et version ; un chemin unique
   `imsa_document.parquet` ne convient pas à une collection de courses.
4. Comparer les volumes calculés depuis le JSON aux volumes relus du Parquet
   correspondant, au lieu d'imposer `(50, 100, 137)` à chaque ingestion.
   Conserver ces nombres seulement dans le test du fichier Road America.
5. Valider aussi schéma, contenu et types : égalité des volumes ne prouve pas
   égalité des données. Vérifier avant publication du fichier final.
6. Prévoir un lecteur par format et un traitement par famille de documents.
   Le lecteur d'arrêts n'est pas un lecteur universel de tous les résultats.
7. Définir la granularité de chaque table Silver : session, engagement,
   équipage, arrêt, tour, mesure météo. Préserver numéros avec zéros initiaux.
8. Contrôler les jointures et conserver les engagements sans arrêt ; ne pas
   utiliser le rapport d'arrêts comme liste complète des participants.
9. Conserver tous les champs en Raw/Bronze. Exclure des projections uniquement
   les champs entièrement vides sur le périmètre profilé, avec possibilité de
   réintégration dans une autre course ou saison.
10. Distinguer absent, vide, inconnu et non applicable. Ne pas assimiler une
    session d'essais à une course pour imposer les mêmes obligations.
11. Vérifier les conditions d'utilisation avant redistribution des données.
    La licence du code du projet ne donne pas de droits sur les résultats.

## Ordre de travail

D'abord remplacer les volumes fixes par une comparaison source/sortie sur
notre fichier actuel. Ensuite introduire le manifeste de sources, les chemins
par document et un deuxième fichier d'arrêts. Ajouter résultats, tours et météo
avec leurs propres contrôles, puis seulement valider un autre championnat.
L'objectif est l'extension progressive, sans promettre une compatibilité non testée.
