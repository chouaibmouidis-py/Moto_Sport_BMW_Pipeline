# Mission de stage personnelle simulée — données de compétition BMW

Version de cadrage : 10 novembre 2026.
Actualisation du jalon local : 11 novembre 2026.

Projet pédagogique indépendant. BMW est le destinataire fictif de la restitution : aucune commande, affiliation, convention de stage ou validation par BMW n'est revendiquée. Le livrable de portfolio sera présenté comme un projet personnel ayant utilisé un tuteur IA comme sparring-partner technique (revue de code critique, challenge d'architecture et scénarios de tests).

## Besoin métier

Permettre à une équipe d'analyse sportive fictive de retrouver les engagements BMW, leurs pilotes et leurs arrêts, avec un contexte de course et une qualité des données vérifiables.

Les premiers résultats doivent permettre de répondre à trois questions : quels engagements BMW figurent dans les documents disponibles ; quelles durées et quels changements de pilotes sont rapportés ; quelles informations sont absentes, illisibles ou incohérentes ? Une durée d'arrêt n'est pas assimilée à une performance des mécaniciens ni à une perte nette de temps en piste.

## Périmètre et progression

- Socle de livraison initial : trois rapports officiels IMSA 2025, Road America, Long Beach et Daytona heure 24 ; tous les concurrents restent disponibles pour contextualiser les engagements BMW.
- Données : préserver les documents sources et les champs vides dans Bronze ; représenter les champs renseignés dans Silver, avec les valeurs sources nécessaires au diagnostic.
- Extension : qualifier puis intégrer une première source de structure différente. L'objectif à terme reste l'étude des participations BMW auto et moto sur les saisons 2022–2026 ; la couverture mondiale n'est pas encore démontrée et fera l'objet d'un inventaire vérifié.
- Premier pilote intégré : classement Official de Road America, 48 participants, rapproché des rapports d'arrêts. Sa projection Silver reste partielle ; les champs non projetés demeurent en Bronze.
- Expérimentation stockage : émulation locale puis validation ciblée dans un cloud de test, avec budget convenu avant utilisation. Aucun déploiement cloud n'est nécessaire pour accepter le premier livrable local.

## Livrables

1. Pipeline local reproductible avec une commande, configuration des sources et dépendances restaurables avec uv.
2. Tables Silver distinctes pour le contexte de session par document, les entrées de voitures, les entrées de pilotes et les arrêts ; relations et granularités documentées.
3. Rapports de qualité et mart des arrêts enrichis, consultables depuis une exécution active cohérente.
4. README de démarrage, dictionnaire de données, architecture et procédure de diagnostic/reprise.
5. Démonstration métier, rapport de mission et soutenance comprenant les limites, les preuves de test et les décisions techniques.

## Critères d'acceptation du premier livrable local

- Une procédure documentée permet de restaurer l'environnement et d'exécuter les cinq étapes du lanceur depuis un autre dossier.
- Les trois documents produisent les volumes de référence : 145 entrées de voitures, 417 entrées de pilotes et 1 791 arrêts ; le filtre BMW retrouve 162 arrêts. Ces nombres sont des références de ce jeu, pas des constantes métier universelles.
- Les numéros textuels, la provenance et la version sont conservés ; les jointures n'ajoutent ni ne suppriment involontairement des arrêts.
- Les conversions, clés, liens parent/enfant et cumuls ont des scénarios valides et invalides testés. Absence et erreur de conversion sont distinguées.
- Les onze fichiers d'une exécution sont préparés et vérifiés avant activation, dont le classement, sa comparaison avec les arrêts et la synthèse par participant. Cette synthèse refuse les clés manquantes ou dupliquées et les participants perdus ou ajoutés. Un échec simulé laisse l'ancienne référence exploitable. Les lecteurs choisissent une seule exécution par lecture.
- La suite de tests passe ; la procédure de lancement et les lecteurs de qualité et de mart sont rejoués conformément au README.
- Les limites sont explicites : sources encore peu nombreuses, dates sans fuseau confirmé, conditions de comparaison sportive, absence de validation de concurrence et de récupération après coupure machine.

## Jalons et accompagnement

1. Stabiliser le lecteur de référence, la documentation et le parcours local existant.
2. Qualifier une nouvelle source et documenter ses écarts avant d'adapter le pipeline.
3. Consolider les résultats métier et présenter la démonstration.
4. Réaliser une revue de code et un examen pratique noté sur les fondamentaux nécessaires à l'autonomie.

Le rythme respecte le travail et les disponibilités de Chouaib ; aucune échéance de livraison n'est inventée. L'évaluation distingue travail autonome, indices et solution fournie. Le nombre de tests du projet n'est pas une mesure suffisante de l'autonomie. Aucun message ni livrable ne sera envoyé à BMW sans demande explicite.
