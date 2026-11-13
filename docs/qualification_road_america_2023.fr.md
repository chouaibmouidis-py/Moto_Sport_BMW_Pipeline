# Qualification initiale Road America 2023

Inspection du 12 novembre 2026. Aucun ajout au manifeste actif : les formats
disponibles diffèrent des couples JSON intégrés pour 2024 et 2025.

[Répertoire officiel de la course](https://imsa.results.alkamelcloud.com/Results/23_2023/17_Road%20America/01_IMSA%20WeatherTech%20SportsCar%20Championship/202308061010_Race/).

## Disponibilité constatée

- Classement : `03_Results_Race_Official.CSV` et PDF.
- Arrêts : `20_Pit Stops Time Cards_Race.PDF` ; aucun équivalent JSON ou CSV
  n'est listé dans cet index.
- Chronos : `23_Time Cards_Race.CSV`, granularité voiture/tour, avec
  `PIT_TIME`, `DRIVER_NUMBER`, `LAP_NUMBER`, `HOUR`, `MANUFACTURER` et
  `CROSSING_FINISH_LINE_IN_PIT`. Ce n'est pas le rapport d'arrêts déjà intégré.

## Premières différences

CSV séparés par point-virgule, avec BOM UTF-8. Les en-têtes des chronos
comportent parfois des espaces initiaux. Préserver les numéros textuels
comme `01`. Le classement contient `POSITION`, `NUMBER`, `VEHICLE`, `CLASS`,
mais pas de colonne de comptage d'arrêts ni de constructeur textuel ;
`IMSA_ManufacturerId` est un identifiant, pas un libellé.

Lecture du classement vérifiée avec DuckDB : 45 participants. L'en-tête a
93 champs, chaque ligne de participant en a 73. `null_padding=True` permet
de remplir les champs finaux absents avec NULL, sans ignorer de lignes.
`all_varchar=True` préserve les numéros textuels. Cette lecture exploratoire
ne constitue pas encore une validation ni une publication Bronze.

Ne pas fabriquer un nombre d'arrêts déclaré à partir des chronos : il ne
serait plus indépendant du comptage observé. Ne pas assimiler `PIT_TIME`
à la durée des rapports JSON sans examiner sa définition et vérifier le PDF.

## Exploration vérifiée et référence Git

`explore_classification_csv.py` lit le classement et un échantillon des chronos.
Le chemin des chronos reste temporairement fixé à `/tmp/imsa-ra2023-timing.csv`.
Pour la BMW 24, les deux durées CSV correspondent au PDF (1:28.481 et 1:22.665).
La BMW 25 possède quatre lignes de chronos sans PIT_TIME, alors que le PDF
contient un passage de 1:59:53.389 : les chronos ne remplacent pas le PDF.

`explore_pit_stop_pdf.py` extrait 116 arrêts pour 44 voitures, sans doublon de
clé voiture/arrêt sur le PDF inspecté. Les coordonnées, limites de corps et
tailles de police sont spécifiques à ce rapport. Le contexte voiture traverse
les colonnes/pages ; les numéros à un, deux ou trois chiffres sont reconnus.
Les contrôles refusent un arrêt sans contexte, un numéro hors séquence ou une
ligne candidate dont la durée ne peut être extraite. Une dégradation qui
empêche même la reconnaissance comme candidate peut encore passer inaperçue.

Validation avant commit de référence : 114 tests réussis, dont neuf ciblent
l'exploration PDF ; les deux scripts ont été exécutés sur les sources locales.
Ces contrôles ne prouvent pas l'exhaustivité sur d'autres PDF. Les fichiers
sources temporaires ne sont pas inclus dans Git. Aucune source 2023 n'a été
activée dans le pipeline, et aucune publication n'est déclenchée par ces scripts.

Le commit précédent couvre 2024 et 2025. Le nouveau jalon ajoute en bloc
l'exploration 2023 ; faute de commits intermédiaires, Git ne permet pas de
séparer rétrospectivement les contributions des différents assistants.

## Synthèse exploratoire et contrôles — 13 novembre 2026

Le script PDF reçoit désormais deux chemins : PDF d'arrêts puis CSV de
classement. Les deux fichiers doivent exister avant toute extraction.
`convert_extracted_stops` réutilise la macro SQL de durée et conserve le texte
brut, avec un résultat arrondi à la milliseconde. `build_pdf_car_summary`
regroupe les arrêts par voiture avant la jointure gauche avec le classement.

Chouaib confirme la synthèse de 45 participants. La voiture 57, absente du
rapport PDF inspecté, est conservée avec un comptage observé NULL, sans
affirmer qu'elle a effectué zéro arrêt. Le classement ne fournit pas de
comptage déclaré indépendant permettant une comparaison similaire à 2024–2025.

Contrôles : refus des numéros de classement NULL/vides/blancs ou répétés,
préservation de la distinction textuelle entre 01 et 1, refus des arrêts sans
participant correspondant. Un participant sans détail reste accepté.
La revue a détecté un contrôle de rattachement testé isolément mais absent de
`main()` : l'appel a été ajouté et un test de `main()` vérifie désormais le refus
avant construction de la synthèse. Ces ajouts restent exploratoires ; aucune
source 2023 n'est activée ou publiée par le pipeline principal.
