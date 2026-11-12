# Contrat initial de la couche Gold

Ébauche du 12 novembre 2026, à éprouver avant toute promesse de livraison.
La couverture historique visée reste 2022–2026 ; seule la saison WeatherTech
2025 est intégrée à ce stade pour classements et arrêts.

## Tables et granularités

- Synthèse des participations : une ligne par source et version du classement,
  numéro textuel de voiture. La course, la saison et le championnat devront être
  exposés explicitement, sans demander au consommateur de décoder source_id.
- Détail des arrêts : une ligne par clé d'arrêt validée dans son rapport/version.
  Préserver la référence de l'entrée source et les liens vers les pilotes.
- Bilan qualité : une ligne par classement/version, avec population, comptages,
  pourcentages et définition des statuts.

## Règles de consommation

Conserver les participants sans détail. Une absence de moyenne reste NULL,
jamais zéro par défaut. Présenter couverture des durées et concordance des
comptages séparément. Le dénominateur du taux de count_mismatch est l'ensemble
des participants du classement ; cet indicateur ne mesure pas toutes les erreurs.
Les durées sont en secondes et ne mesurent pas isolément la performance des
mécaniciens. Toute comparaison sportive devra expliciter ses critères de contexte.

## Traçabilité et réception

Conserver les références et empreintes des deux rapports, les règles de
transformation et le run de publication. Tester les clés, la conservation des
participants, les liens, les conversions et les séparations de courses/versions.
Fournir un dictionnaire des champs et un exemple SQL/notebook de lecture du
run actif. Un futur consommateur IA utilisera les mêmes définitions, unités et
limites ; aucune compatibilité IA n'est démontrée par cette ébauche.
