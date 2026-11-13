# Qualification exploratoire Long Beach 2023

Inspection du 13 novembre 2026, sans activation dans le manifeste principal.
[Répertoire officiel](https://imsa.results.alkamelcloud.com/Results/23_2023/08_Long%20Beach%20Street%20Circuit/01_IMSA%20WeatherTech%20SportsCar%20Championship/202304151405_Race/).
Sources inspectées : `03_Results_Race_Official.CSV` et
`20_Pit Stops Time Cards_Race.PDF`.

Le lecteur PDF de Road America, exécuté sans modification et sans publication,
extrait 28 arrêts pour 25 numéros de voiture sur une page. Tous ces numéros
existent dans les 28 entrées du CSV. Cela apporte un deuxième cas réel de
compatibilité, mais pas une preuve d'exhaustivité pour tous les rapports IMSA.

BMW du classement : 25 (position 2), 24 (4), 1 (11), 96 (19), 97 (23).
Ne pas appliquer le filtre d'affichage 24/25 pour mesurer le volume total.

Trois entrées n'ont aucun détail dans l'extraction : 01, 80 et 93.
Le CSV indique 01 : Classified, position 26, zéro tour ; 80 et 93 :
Not started, position absente, zéro tour. Les positions absentes sont à
conserver, ainsi que le statut source. Elles ne prouvent pas une erreur de lecture.
Ne pas convertir une absence de détail en zéro arrêt certifié.

Le script principal d'exploration reste configuré pour le contexte et le chemin
de sortie Road America 2023 : ne pas le lancer pour publier Long Beach avant
d'avoir rendu ce contexte explicite. Aucun résultat Road America n'a été
remplacé pendant cette qualification. Une comparaison indépendante du contenu
complet du PDF reste à effectuer avant validation d'exhaustivité.

La synthèse exploratoire conserve maintenant `STATUS` sous le nom
`classification_status`. Vérification en mémoire : 28 lignes, onze colonnes,
01 Classified/position 26, 80 et 93 Not started/position NULL, avec comptage
observé NULL pour les trois. Les positions absentes sont triées en dernier.
Les 21 tests ciblés passent, dont la synthèse avec un non-partant fictif.
