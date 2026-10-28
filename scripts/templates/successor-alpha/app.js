// SPDX-License-Identifier: Apache-2.0
const $ = id => document.getElementById(id);
const pageOptions = new URLSearchParams(location.search);
let language = pageOptions.get('lang') === 'fr' || document.documentElement.dataset.language === 'fr' ? 'fr' : 'en';
let largeText = pageOptions.get('text') === 'large' || document.documentElement.dataset.textSize === 'large';
let stage = 0, mode = 'example', mission = null, result = null, dossier = null;
let valueEstimate = null;
let artifacts = null, busy = false, controller = null, runToken = 0, revision = 0, importToken = 0;
let notice = null, lastStatus = null, lastError = null;
let learningRecords = [], nativeHandoffRaw = null, nativeReturnRaw = null, nativeContinuityRaw = null, nativeChecked = null;
let computerHistoryRaw = null, computerHistoryChecked = null, computerHandoffRaw = null, computerChecked = null;
let computerFormRevision = 0, computerBusy = false, computerSelectedIndex = -1, computerSurfaceCustomized = false;
let learningBusy = null, learningController = null, learningToken = 0, nativeFormRevision = 0, researchFormRevision = 0;
const sample = alpha.createSampleMission({seed: 42, leftRows: 240, rightRows: 360});
const en = {};
for (const el of document.querySelectorAll('[data-i18n]')) {
    const clone = el.cloneNode(true);
    clone.querySelectorAll('br').forEach(br => br.replaceWith('\n'));
    en[el.dataset.i18n] = clone.textContent;
}
const fr = {
    admissionEyebrow:'AGI ALPHA FLYWHEEL · LE MOTEUR DES POSSIBLES RENTABLES',
    admissionTitle:'Inventer la possibilité.\nConstruire les moyens manquants.',
    admissionSequence:'Imaginer une activité conséquente. Contester la contrainte. Construire la capacité. Livrer une valeur utile. Financer la suite.',
    admissionStatus:'ESPACE D’EXPLORATION · ADMISSION BLUE SKY NON ÉTABLIE',
    admissionScope:'L’ambition, l’admission d’une candidature, la construction démontrée et la qualification commerciale sont distinctes. Préparer une mission ne prouve pas une percée.',
    admissionGate:'Avant de construire le projet phare : comparer trois possibilités',
    admissionOne:'Quelle activité conséquente devient possible, et pour qui ?',
    admissionTwo:'Quelle limite subsiste avec les meilleurs outils et processus accessibles ?',
    admissionThree:'Quel changement récent à la frontière rend cette limite intéressante à contester maintenant ?',
    admissionFour:'Quel instrument, méthode, représentation ou arrangement productif manquant allez-vous construire ?',
    admissionFive:'Quelle expérience indépendante avant/après, quel retrait et quel remplacement pratique pourraient réfuter le changement ?',
    admissionSix:'Comment la première livraison commerciale utilisera-t-elle directement cette construction ?',
    admissionSeven:'Quelle famille d’autres activités utiles pourrait-elle rendre possible ?',
    admissionRecord:'Conservez ces réponses et incertitudes dans l’historique existant : résultat, hypothèse de valeur, contexte, acceptation et stratégies ci-dessous. Une transformation par le coût doit préciser le seuil franchi et l’activité rendue accessible.',
    admissionHold:'Blue Sky HOLD permet une sonde commerciale séparée avec hypothèse, livrables, allocation et arrêt. Le profit ne lève pas HOLD et ne libère pas le budget principal de construction ou de publication du projet phare.',
    admissionExample:'Les preuves avant l’exemple local maintenu',
    admissionPossibilityLabel:'Possibilité',admissionPossibility:'Transformer des exports de catalogues incohérents en un plan de résolution vérifiable.',
    admissionConstraintLabel:'Contrainte',admissionConstraint:'Des divergences dispersées masquent des décisions répétées ; l’exactitude des sources reste à établir.',
    admissionMeansLabel:'Moyen construit',admissionMeans:'Comparaison locale et actions regroupées conservant chaque référence source.',
    admissionOutcomeLabel:'Résultat utile',admissionOutcome:'Divergences téléchargeables, plan d’action et code réutilisable.',
    admissionEvidenceLabel:'État des preuves',admissionEvidence:'Démonstration locale délimitée. Aucun seuil d’accessibilité, admission Blue Sky ou qualification commerciale établi.',
    licenseNotices: "Licences du code",
    researchTitle:'Aller plus loin : composer une meilleure stratégie',researchIntro:'Explorez des combinaisons délimitées d’opérations connues : partitionnement, réutilisation des clés dupliquées et choix d’index. Figez le plan sélectionné, puis confirmez-le sur de nouvelles données synthétiques publiques. Un HOLD légitime conserve la référence.',researchMemory:'Maximum de références de lignes auxiliaires',researchWeight:'Poids de chaque référence auxiliaire',researchRun:'Composer et tester des stratégies',researchScope:'RECHERCHE DE STRATÉGIE LOCALE · NON QUALIFIÉE INDÉPENDAMMENT',researchCandidates:'Stratégies composées et références',researchPlan:'Plan',researchAuxiliary:'Références de lignes au pic',researchFeasible:'Budget respecté',researchLimits:'Composition délimitée d’opérations examinées, avec une confirmation synthétique publique. Ce n’est ni une évaluation protégée, ni la découverte d’un nouvel algorithme, ni une certification indépendante, ni une valeur organisationnelle réalisée.',researchDownload:'Stratégie, engagement et confirmation',researchExampleNote:'Pour voir pourquoi la structure compte, commencez un cycle synthétique distinct riche en doublons. Cette mission reste dans votre historique.',researchExample:'Essayer une mission d’apprentissage riche en doublons ↗',researchTool:'Télécharger la capacité du plan conservé · .mjs',
    resolutionTitle:'Reformuler : que faut-il décider ?',resolutionIntro:'Une longue liste de divergences peut répéter le même problème. Construisez une action par clé concernée en préservant les références de chaque occurrence originale.',resolutionRun:'Construire mon plan d’action sur les divergences',resolutionScope:'REFORMULATION EXÉCUTABLE · CONTRAT DE SORTIE MODIFIÉ',resolutionLimits:'La tâche passe d’une liste d’occurrences à un regroupement de décisions. Cela ne prouve ni un temps de revue équivalent, ni l’exactitude d’une source, ni une supériorité sur la tâche originale. Jointure et divergences originales restent disponibles.',resolutionDownload:'Plan d’action complet avec références sources',
    nativeTitle:'Poursuivre dans l’espace SUCCESSOR natif',nativeIntro:'Transmettez cette mission de catalogue exacte et son historique au format du workbench SUCCESSOR. Compilez un vrai plan Jobs non financé de sept lots et ramenez les artefacts contrôlés dans le même projet.',nativeScope:'Exécution locale seulement. Sans portefeuille, prestataire distant, fonds ni permission opérationnelle. L’adaptateur de catalogue est inclus dans le SDK du workbench ; les exécuteurs de catalogue compatibles Manager et Fleet ne sont pas installés.',nativeName:'Nom de mission native · 48 caractères maximum',nativeOwner:'Libellé du responsable',nativeRights:'Classe de données autorisée',nativeChooseRights:'Choisir explicitement',nativeSynthetic:'Synthétique',nativePublic:'Public, sans données personnelles',nativeLicensed:'Sous licence, sans données personnelles',nativeReview:'Capacité de revue · minutes, 1–120',nativeSource:'Source des données et déclaration d’usage autorisé',nativeLicense:'Licence ou base de permission explicite',nativePrepare:'Préparer la mission native et le plan Jobs',nativePreparedLabel:'MÊME MISSION · WORKBENCH NATIF · BROUILLON $AGIALPHA NON FINANCÉ',nativeRun:'Répéter localement avec le SDK du workbench',nativeDownloadHandoff:'Mission native exacte, plan et transmission du projet',nativeImportReturn:'Importer un fichier de retour natif',nativeReturnUpload:'Importer un retour natif',nativeHistorical:'RÉSULTAT LOCAL HISTORIQUE · EXAMEN TOUJOURS REQUIS',nativeDownloadReturn:'Retour natif contrôlé',nativeReturnLimits:'Le retour est lié à cette transmission, ces sources, cette mission et cet historique exacts. Les sorties sont recalculées. Les temps restent historiques ; aucune revue actuelle, qualification indépendante, autorité ou règlement ne sont importés.',nativeArtifactLimit:'Le SDK du workbench limite chaque artefact à 200 000 caractères. Une mission valide ici peut nécessiter un périmètre plus petit pour ce transfert. Le téléchargement source reste disponible.',nativeHostCommand:'Pour une exécution hors navigateur : node examples/successor-alpha/native-cli.mjs successor-native-handoff.json NOUVEAU-retour-natif.json ; importez ensuite le retour natif produit.',
    learningHistoryTitle:'Stratégies, plans d’action et retours natifs conservés',learningDownload:'Télécharger l’archive d’apprentissage complète',learningRestore:'Restaurer une archive ou un historique Computer Use',learningUpload:'Restaurer une archive ou un historique Computer Use',learningLimit:'L’archive inclut le même projet, les méthodes, les preuves originales et les retours natifs contrôlés. Jusqu’à 2 Mo ; une archive trop volumineuse est refusée sans supprimer d’historique. Les éléments importés restent historiques, sans autorité.',

    adoptionTitle:'Cette capacité vaudrait-elle la peine d’être adoptée ?',adoptionIntro:'Estimez votre effort complet, y compris l’examen et les corrections. Les millisecondes du navigateur ne mesurent pas le temps humain gagné.',
    valueBefore:'Minutes actuelles par exécution',valueAfter:'Minutes prévues avec cet outil',valueFrequency:'Exécutions par mois',valueHourly:'Votre valeur d’une heure',valueSetup:'Coût initial de mise en place et d’intégration',valueCurrency:'Devise commune',valueCalculate:'Estimer selon mes hypothèses',valueProjection:'PROJECTION · VOS HYPOTHÈSES',valueLimit:'Calcul arithmétique de vos estimations, pas une économie mesurée ni garantie. Il exclut les coûts non saisis, les coûts récurrents et les coûts d’erreur ou de risque. Vérifiez les résultats réels avant adoption.',valueDownload:'Télécharger les hypothèses et la projection',
    joinedPreview:'Aperçu du catalogue joint',comparisonTable:'Comparaison complète des méthodes',largerText:'Agrandir le texte',returnSetup:'Revenir à la préparation',tryExample:'Essayer l’exemple inclus',skip:'Aller à votre mission',brandCaption:'PAR AGI ALPHA',mainNavigation:'Navigation principale',
    howItWorks:'L’expérience',openProject:'Ouvrir un projet',
    heroEyebrow:'LA MISSION · ADMETTRE LA POSSIBILITÉ. CONSTRUIRE VOTRE SUCCESSOR Ω.',
    heroLine1:'Trouvez votre',heroLine2:'Alpha.',heroLine3:'Construisez votre\nSUCCESSOR Ω.',
    heroDescription:'Visez une occasion utile en recherche, en mathématiques, en logiciel public ou en travail numérique. Découvrez de meilleures stratégies. Testez un autre jeu. Conservez les outils, preuves et leçons qui renforcent la prochaine mission.',
    firstAdvantage:'Essayer l’exemple local complet',bringCatalogs:'Utiliser mes propres catalogues',
    startNote:'Gratuit. Sans compte, portefeuille ni installation. Dans votre navigateur.',
    imageAlt:'Illustration ornée violette et dorée du parcours Alpha, Gym, Specialist ASI et SUCCESSOR Ω.',
    artEyebrow:'CONÇU POUR DURER',artCaption:'Possédez l’institution.\nChangez les modèles. Préservez la mission.',
    artNote:'L’ambition est durable. Le premier pas utile vous appartient.',valueLabel:'Ce que vous emportez',
    valueOne:'Un résultat utile',valueOneText:'Résolvez une tâche concrète et délimitée.',
    valueTwo:'Une comparaison vérifiable',valueTwoText:'Voyez ce qui progresse, et à quel coût.',
    valueThree:'Une capacité à conserver',valueThreeText:'Emportez l’outil, les preuves et l’historique.',
    missionEyebrow:'FACULTATIF · EXEMPLE LOCAL COMPLET',missionTitle:'Deux catalogues.\nUne réponse fiable.',
    missionIntro:'Explorez le cycle complet de sauvegarde, comparaison et réutilisation avec un petit exemple local. Trouvez correspondances, produits manquants et divergences, puis conservez un outil fonctionnel.',
    missionLabel:'LA MISSION',missionName:'Des catalogues clairs',
    missionSummary:'Rapprochez deux catalogues publics. Obtenez les données et une méthode réutilisable.',
    missionProgress:'Progression de la mission',stepAlpha:'Définir l’avantage',stepGym:'Comparer les méthodes',
    evidence:'Preuves',stepEvidence:'Examiner le résultat réel',yourSuccessor:'Votre SUCCESSOR',
    stepSuccessor:'Conserver. Utiliser. Poursuivre.',localNote:'Local, par conception.\nVos catalogues restent dans ce navigateur.',
    startHere:'COMMENCEZ ICI',alphaTitle:'Vivez une mission complète.',
    alphaLead:'Un exemple inclus vous mène d’un obstacle quotidien à des fichiers utiles, une comparaison équitable et une capacité à conserver.',
    sourceLabel:'Source des catalogues',includedExample:'Exemple inclus',myCatalogs:'Mes catalogues publics',
    catalogOne:'Votre catalogue de produits',catalogTwo:'Un catalogue fournisseur',
    exampleGoal:'L’avantage à bâtir',exampleGoalText:'Obtenez les correspondances exactes et les exceptions en réduisant le travail de rapprochement.',
    syntheticNote:'Exemple synthétique, sans données personnelles. Les résultats sont calculés à chaque exécution.',
    runExample:'Découvrir mon premier Alpha',
    inputNote:'Collez ou choisissez deux fichiers CSV publics, sans données personnelles. Jusqu’à 200 Ko et 1 500 lignes par catalogue ; 10 000 paires en sortie. Cellules entre guillemets et UTF-8 acceptés.',
    leftCatalog:'Catalogue de référence',rightCatalog:'Second catalogue',chooseCsv:'Choisir un fichier CSV',
    uploadLeft:'Importer le catalogue de référence',uploadRight:'Importer le second catalogue',checkColumns:'Vérifier mes colonnes',
    leftKey:'Relier cette colonne de référence',rightKey:'À cette colonne du second catalogue',
    matchingNote:'Clés et champs communs sont comparés exactement. Les clés doivent être renseignées ; les doublons sont conservés et peuvent produire plusieurs lignes. Sans correspondance approximative ni nettoyage automatique.',
    runMine:'Trouver l’avantage dans mes catalogues',gymTitle:'Mettez de meilleures méthodes au travail.',
    gymLead:'Quatre méthodes établies. Les mêmes catalogues. Des sorties exactes contrôlées face à une référence simple.',
    gymNote:'Nous comptons les comparaisons, les opérations d’index et les paires produites. Le temps du navigateur est mesuré séparément : il varie selon l’appareil et les données.',
    cancelRun:'Annuler cette exécution',resultEyebrow:'VOTRE MISSION, LIVRÉE',localResult:'Calculé localement',
    evidenceTitle:'Une clarté exploitable.',matchedPairs:'paires correspondantes',unmatchedRows:'lignes sans correspondance',
    conflictingPairs:'paires avec divergences',joinedCsv:'Catalogue joint',unmatchedLeft:'Référence : lignes non reliées',
    unmatchedRight:'Second : lignes non reliées',conflictsCsv:'Divergences de valeurs',previewJoined:'Aperçu du catalogue joint',
    previewNote:'Six premières lignes, valeurs exactes. Les CSV neutralisent les cellules de type formule pour la sécurité des tableurs ; le JSON préserve le texte original.',observedAdvantage:'L’AVANTAGE OBSERVÉ',
    comparisonLabel:'Comparaison des opérations logiques',
    operationNote:'Le travail logique compte comparaisons de clés, insertions d’index, recherches et paires produites. Il exclut le hachage interne, les allocations, le tri des sorties, la vérification et l’export. Les lignes indexées/triées ne mesurent ni octets ni mémoire maximale.',
    inspectComparison:'Examiner la comparaison complète',method:'Méthode',operations:'Travail logique',browserTime:'Temps navigateur',
    correctness:'Vérification des sorties',indexedRows:'Lignes indexées',sortedRows:'Lignes triées',
    methodNote:'Cette mission compare des algorithmes classiques. Elle démontre un avantage logiciel délimité ; elle n’établit ni intelligence nouvelle, supériorité générale, qualification indépendante, ni économies organisationnelles.',
    levelObserved:'Observé ici',levelObservedText:'Sorties utiles, contrôles exacts et travail mesuré sur ces données.',
    levelNext:'Ensuite : qualification indépendante',levelNextText:'Cas nouveaux et protégés, alternatives crédibles et examen avant une confiance élargie.',
    keepCapability:'Conserver cette capacité',tryDifferent:'Essayer d’autres données',successorEyebrow:'VOTRE SUCCESSOR · À VOUS DE POURSUIVRE',
    successorTitle:'Gardez plus qu’un résultat.',
    successorLead:'Emportez l’outil, la comparaison et l’historique. Ajoutez de nouveaux catalogues. Lancez le cycle suivant. Bâtissez sur ce qui a fait ses preuves.',
    nameProject:'Donnez un nom à votre projet',portableTitle:'Votre espace complet',
    portableText:'Un seul fichier HTML. Ouvrez-le hors ligne pour traiter de nouveaux catalogues, retrouver la comparaison et poursuivre votre projet.',
    downloadWorkspace:'Télécharger mon espace',toolTitle:'Votre capacité réutilisable',
    toolText:'Un outil Node.js lisible pour la même jointure exacte. Intégrez la méthode à votre propre travail.',
    downloadTool:'Télécharger l’outil · .mjs',downloadReport:'Rapport de preuve',downloadProject:'Projet et historique des cycles',
    historyTitle:'Ce que votre institution retient',
    historyNote:'Un projet portable conserve les données de mission et les observations locales. Les résultats importés restent historiques : recalculez-les avant de vous y fier. Aucune permission ni aucun fonds ne sont importés.',
    beyondBrowser:'Poursuivre au-delà de ce navigateur',
    beyondText:'Préparez une revue indépendante ou une réalisation sous forme de travail délimité. Ces fichiers sont des brouillons non financés ; examinez le périmètre, le prestataire et l’état de préparation avant de commander.',
    handoffUsdc:'Préparer un brouillon USDC',handoffAgialpha:'Préparer un brouillon $AGIALPHA',
    contractsTitle:'Contrats Alpha actuels',contractsNote:'Dossier du 18 octobre 2026 : cinq résultats EXACT_MATCH et graphe d’autorité observé au bloc 26220072 par un fournisseur de confiance. Dossier conservé, sans nouvelle vérification RPC en direct. L’activation et le financement public ne sont pas approuvés. Cette mission gratuite ne nécessite aucune interaction avec les contrats.',contractsDirectory:'Adresses actuelles et dossier conservé ↗',contractsEvidence:'Sources, preuves et limites opérationnelles ↗',
    nextCycle:'Commencer mon prochain cycle',backEvidence:'Revenir aux preuves',
    continuity:'Déjà commencé ? Emportez l’historique de votre projet.',restoreProject:'Restaurer un projet',restoreFile:'Restaurer un fichier de projet',
    experienceEyebrow:'UNE MISSION. UNE INSTITUTION DURABLE.',experienceTitle:'Bâtissez l’avantage.\nPréservez ce qui le rend possible.',
    experienceIntro:'Votre mission reste centrale. Modèles, méthodes et prestataires peuvent changer à mesure que de meilleures capacités font leurs preuves.',
    alphaMeaning:'Trouvez l’avantage à bâtir. Précisez qui en bénéficie, ce qui compte et ce qu’un meilleur résultat apporterait.',
    gymMeaning:'Développez des approches concurrentes dans un environnement délimité. Apprenez des résultats utiles et des échecs.',
    asiMeaning:'Une désignation propre à la mission qui se mérite : figer une candidate, tester du travail nouveau et protégé, surpasser des alternatives crédibles.',
    omegaMeaning:'Après preuve et autorisation explicite, conservez la capacité, les éléments probants et la mémoire opérationnelle pour la suite.',
    biggerMission:'UNE AUTRE MISSION EN TÊTE ?',biggerTitle:'Partez de l’avantage qui compte pour vous.',
    biggerText:'Cadrez une opportunité de recherche, d’ingénierie ou d’organisation dans le carnet de découverte Alpha. Il prépare un plan ; l’exécution et la preuve dépendent de la mission.',
    openNotebook:'Ouvrir la découverte Alpha',questionsTitle:'Quelques points utiles.',questionFree:'Que puis-je faire gratuitement ?',
    answerFree:'Exécutez l’exemple ou vos propres catalogues CSV publics dans les limites indiquées, examinez les résultats et téléchargez la capacité, le rapport et l’espace. Cette mission n’utilise aucune API de modèle et ne demande ni compte ni portefeuille.',
    questionAlpha:'Qu’est-ce qui constitue Alpha ici ?',
    answerAlpha:'Vous obtenez des données rapprochées exploitables et une capacité réutilisable. Comparez chaque méthode sur votre charge réelle. Ces résultats aident à évaluer une opportunité Alpha ; supériorité indépendante et valeur économique réalisée exigent d’autres preuves, y compris les coûts d’intégration et l’effort humain.',
    questionOwn:'Que puis-je conserver ?',
    answerOwn:'Vous contrôlez les fichiers téléchargés : espace, code réutilisable, données, sorties et historique. Le code inclus est sous licence Apache 2.0 ; les composants AGI Jobs intégrés conservent leur licence MIT. Les droits sur les données et les travaux commandés ou tiers restent à établir.',
    questionTrust:'Cela certifie-t-il Specialist ASI ou autorise-t-il un déploiement ?',
    answerTrust:'Non. C’est une démonstration locale opérationnelle et délimitée. Une évaluation indépendante sur du travail nouveau et protégé et une autorisation explicite restent des étapes distinctes. Le Gym développe la capacité ; il ne la certifie pas.',
    footerMotto:'POSSÉDEZ L’INSTITUTION. PRÉSERVEZ LA MISSION.',footerScope:'Une première capacité utile. Une ambition ouverte.',
    sourceGuide:'Source et guide de reproduction ↗',missionProtocol:'Protocole de mission SUCCESSOR ↗',disclaimer:'Prototype de recherche et avis'
};
Object.assign(fr, {
    startNote:'Commencez gratuitement par une mission qui compte. L’exécution utilise votre exécuteur natif configuré ; les résultats réels exigent un examen réel.',
    computerStart:'Découvrir ma prochaine capacité',
    computerEyebrow:'COMPUTER USE · NIVEAU 3 → NIVEAU 4',
    computerTitle:'Quelle capacité utile\ndevrait exister ensuite ?',
    computerIntro:'Commencez par une opportunité qui compte. Explorez des stratégies concurrentes et une approche fondamentalement différente. Confiez un travail d’écran délimité, examinez le livrable et réutilisez les leçons à la tentative suivante.',
    computerVision:'Construisez quelque chose à conserver.',
    computerVisionText:'Une proposition d’implémentation. Une nouvelle piste de recherche. Un argument mathématique qui résiste à l’examen. La mission est un progrès utile ; modèles et méthodes peuvent évoluer avec le projet.',
    computerStageOne:'Définir un travail utile',
    computerStageOneText:'Fixez le résultat avant de choisir la méthode.',
    computerStageThree:'Niveau 3 · Intelligence métastratégique',
    computerStageThreeText:'Découvrez, testez, combinez et améliorez les stratégies elles-mêmes.',
    computerStageFour:'Niveau 4 · Intelligence transformationnelle',
    computerStageFourText:'Repérez une formulation inutilement restrictive. Testez un jeu fondamentalement différent en préservant le résultat utile.',
    computerCurrentScope:'Computer Use relie raisonnement et travail visible à l’écran. L’exécuteur actuel utilise un navigateur jetable délimité ; exécution de code revue, outils de preuve, bureaux complets et règlement nécessitent leurs propres connexions.',
    computerRunnerGuide:'Configurer l’exécuteur Computer Use ↗',
    computerDesign:'01 · TROUVEZ UNE OPPORTUNITÉ QUI MÉRITE D’ÊTRE CONSTRUITE',
    computerExample:'Choisissez votre opportunité',
    computerExampleRelease:'Logiciel public · opportunité de performance utile',
    computerExampleResearch:'Recherche de pointe · nouvelle approche testable',
    computerExampleCustom:'Mon propre travail à l’écran',
    computerProjectName:'Nommez la capacité à construire',
    computerOutcome:'À quelle opportunité cette capacité répondra-t-elle ?',
    computerAcceptance:'Que doit accomplir un livrable utile ?',
    computerAcceptanceNote:'Conservez ce contrat d’acceptation pour comparer les stratégies. Un autre résultat commence une nouvelle comparaison.',
    computerApproach:'Approche à confier d’abord',
    computerBaseline:'Référence · méthode actuelle',
    computerComposed:'Niveau 3 · stratégie combinée ou améliorée',
    computerReframed:'Niveau 4 · autre formulation du problème',
    computerModel:'Utilisez le modèle actuel qualifié par votre opérateur',
    computerModelNote:'Sélectionnez le modèle et le conteneur immuable lors de l’exécution native. Aucune clé API n’appartient à cet espace.',
    computerStrategy:'Quelles stratégies doivent rivaliser ? · une par ligne, 2–6',
    computerCombination:'Comment combiner leurs meilleurs éléments ?',
    computerReframe:'Quelle restriction inutile remettez-vous en question ?',
    computerReframeNote:'Expliquez pourquoi l’alternative atteint toujours le résultat exigé. Une nouvelle formulation reste une hypothèse jusqu’à l’examen de son résultat.',
    computerSurfaceTitle:'03 · Configuration d’exécution et contrôles avancés',
    computerSurfaceNote:'L’exécution native actuelle utilise un espace Chromium jetable guidé par captures. Elle lit des sources publiques approuvées et crée des livrables visibles. Exécution de code, mesures de performance et vérification formelle exigent des outils qualifiés séparément ; les propositions restent à vérifier.',
    computerBuildSurface:'Construire la surface à partir de ces sources',
    computerHtml:'Avancé : surface de travail personnalisée · HTML facultatif',
    computerUrls:'Sources publiques pour cette opportunité · une URL par ligne',
    computerRights:'Droits sur les données',
    computerLicense:'Licence ou permission',
    computerActions:'Maximum d’actions',
    computerSeconds:'Maximum de secondes',
    computerReviewMinutes:'Temps alloué à l’examen · minutes',
    computerPrepare:'Préparer ma mission de capacité',
    computerPrepareNote:'La préparation est gratuite et n’appelle aucun modèle. Un exécuteur natif configuré et un compte fournisseur réalisent le travail. Mission et preuves retournées restent réunies dans votre projet.',
    computerPrepared:'VOTRE MISSION DE CAPACITÉ · PRÊTE À EXÉCUTER',
    computerDownload:'Transmettre la mission à mon exécuteur',
    computerImport:'Rapporter le travail réalisé',
    computerImportAria:'Importer un résultat Computer Use',
    computerImportNote:'Importez computer-return.json depuis le dossier de sortie de l’exécuteur. L’import conserve un résultat historique. L’achèvement annoncé par le fournisseur reste une déclaration ; examinez les captures et le livrable réel avant de donner votre avis.',
    computerReturned:'TENTATIVE HISTORIQUE · VOTRE EXAMEN',
    computerReviewDecision:'Le résultat réel satisfait-il toutes les conditions d’acceptation ?',
    computerReviewChoose:'Examinez, puis choisissez',
    computerReviewAccepted:'Oui · résultat utile accepté',
    computerReviewRejected:'Non · conserver la tentative infructueuse',
    computerReviewNote:'Qu’avez-vous examiné, et que faut-il améliorer ensuite ?',
    computerReviewActual:'Temps d’examen réel · minutes',
    computerReviewSave:'Conserver mon avis avec cette tentative',
    computerHistory:'UN PROJET · STRATÉGIES, RÉSULTATS ET LEÇONS',
    computerSaveWorkspace:'Enregistrer mon espace complet',
    computerSaveHistory:'Télécharger l’archive complète du projet',
    computerRestoreAria:'Restaurer une archive de projet ou un historique Computer Use',
    computerHistoryNote:'Même identité de projet pour les catalogues et Computer Use. Vos avis sont des jugements consignés, sans certification indépendante, approbation de paiement ni preuve de capacité universelle.',
    computerProposalNote:'Parcours fournisseur public : Jobs prépare la mission native exacte. Après exécution, transmettez sa mission, son retour et son rapport figé à l’un des deux récepteurs pour un brouillon non signé et non financé. Aucun portefeuille, paiement ou déploiement n’est activé.',
    computerJobsProposal:'Jobs · brouillon $AGIALPHA non signé ↗',
    computerManagerProposal:'Manager · brouillon USDC non signé ↗',
    tiFirstEyebrow:'INTELLIGENCE TRANSFORMATIONNELLE · EXPÉRIENCE GRATUITE HORS LIGNE',tiFirstTitle:'Changez la représentation. Préservez le but.',tiFirstText:'Créez un résumé de source utile. Comparez critique après rédaction et graphe argumentatif inspecté avant compression, examinez les énoncés exacts et conservez votre historique. Prototype local déterministe ; couverture structurelle seulement, revue indépendante en attente.',tiFirstOpen:'Essayer l’expérience de compréhension de source',
    heroEyebrow:'LE PROJET PHARE · TROUVEZ VOTRE ALPHA. CONSTRUISEZ VOTRE SUCCESSOR Ω.',
    heroLine1:'Trouvez votre',
    heroLine2:'Alpha.',
    heroLine3:'Construisez votre SUCCESSOR Ω.',
    heroDescription:'Découvrez une opportunité de valeur. Construisez la capacité pour la réaliser. Améliorez la stratégie. Changez de jeu. Explorez logiciel, recherche et mathématiques avec les modèles de pointe et Computer Use, puis conservez ce qui mérite sa place.',
    computerJourneyLink:'Voir le parcours de capacité',
    firstAdvantage:'Lancer l’exemple de catalogues maintenu',
    bringCatalogs:'Utiliser les outils de catalogues avec mes données',
    secondaryExampleNote:'Exemple maintenu · outils locaux de catalogues',
    computerExampleMath:'Mathématiques · exploration rigoureuse et preuve',
    computerValueHypothesis:'Qui en bénéficie, et pourquoi serait-ce utile ?',
    computerValueNote:'Une hypothèse de valeur à confronter à l’utilité réelle, aux coûts complets et aux alternatives. Préparer une mission ne démontre ni revenu ni économies.',
    computerStrategyStep:'02 · Améliorez la stratégie. Contestez le cadre.',
    computerStrategyHelp:'Les approches initiales sont modifiables. Demandez au modèle configuré de découvrir, tester, combiner et affiner les alternatives, puis d’expliquer ce qui pourrait changer le jeu en préservant le résultat utile.',
    computerSourcesHelp:'Utilisez du contenu public non personnel avec les droits nécessaires. L’exécuteur configuré lit les URL exactes approuvées ; il ne se connecte pas à des comptes privés.',
    computerImproveNext:'Améliorer la prochaine stratégie',
    computerReframeNext:'Tester un autre jeu',
    missionEyebrow:'SECONDAIRE · EXEMPLE LOCAL MAINTENU',
    answerFree:'Développez gratuitement une mission utile, comparez les stratégies proposées et sauvegardez votre espace. L’exécuteur natif configuré réalise le travail Computer Use avec son fournisseur de modèles. Un exemple de catalogues maintenu reste disponible comme outil local.',
    answerAlpha:'Alpha est l’avantage utile démontrable pour une opportunité précise. Proposition, code généré ou argument mathématique restent candidats : testez le résultat réel, examinez les preuves et les coûts complets avant de revendiquer la valeur.',
    footerScope:'Des opportunités utiles. De meilleures stratégies. De nouveaux jeux à explorer.',
    computerExampleOpportunity:'Découvrir une occasion de travail numérique',
    computerExampleSoftware:'Logiciel public · opportunité de performance utile',
    computerExampleMathematics:'Mathématiques · exploration rigoureuse et preuve',
    computerPresetNote:'Adaptez ces missions à votre problème et à vos sources. Propositions, preuves candidates et hypothèses de marché doivent être examinées et testées avant de devenir des résultats établis.',
    computerContext:'Dossier de départ facultatif · problème, capacités et contraintes',
    computerContextNote:'Ajoutez les faits connus, hypothèses, contraintes et ressources disponibles. Le texte sera visible dans la surface de travail et conservé avec cette tentative ; une hypothèse ne devient pas une preuve externe.'
});

const ariaEn = {};
for (const el of document.querySelectorAll('[data-i18n-aria]')) ariaEn[el.dataset.i18nAria] = el.getAttribute('aria-label');
const altEn = {};
for (const el of document.querySelectorAll('[data-i18n-alt]')) altEn[el.dataset.i18nAlt] = el.getAttribute('alt');
const say = (english, french) => language === 'fr' ? french : english;
const number = n => new Intl.NumberFormat(language === 'fr' ? 'fr-CA' : 'en-CA').format(n);
const percentage = n => new Intl.NumberFormat(language === 'fr' ? 'fr-CA' : 'en-CA', {maximumFractionDigits:1}).format(n);
function node(tag, parent, text, className) {
    const el = document.createElement(tag);
    if (text !== undefined) el.textContent = text;
    if (className) el.className = className;
    if (parent) parent.append(el);
    return el;
}
function translate() {
    document.documentElement.lang = language; document.documentElement.dataset.language = language;
    document.title = say('Find your Alpha. Build your SUCCESSOR Ω.','Trouvez votre Alpha. Construisez votre SUCCESSOR Ω.');
    document.querySelectorAll('[data-i18n]').forEach(el => { el.textContent = language === 'fr' ? fr[el.dataset.i18n] || en[el.dataset.i18n] : en[el.dataset.i18n]; });
    document.querySelectorAll('[data-i18n-aria]').forEach(el => el.setAttribute('aria-label', language === 'fr' ? fr[el.dataset.i18nAria] || ariaEn[el.dataset.i18nAria] : ariaEn[el.dataset.i18nAria]));
    document.querySelectorAll('[data-i18n-alt]').forEach(el => el.setAttribute('alt', language === 'fr' ? fr[el.dataset.i18nAlt] : altEn[el.dataset.i18nAlt]));
    $('lang-en').setAttribute('aria-pressed', String(language === 'en'));
    $('lang-fr').setAttribute('aria-pressed', String(language === 'fr'));
    $('computer-jobs-proposal').href = say('https://montrealai.github.io/AGIJobsv0/successor/computer/#computer-project', 'https://montrealai.github.io/AGIJobsv0/successor/computer/fr/#computer-project');
    $('computer-manager-proposal').href = say('https://montrealai.github.io/AGIJobManager/computer-receipt/', 'https://montrealai.github.io/AGIJobManager/fr/computer-receipt/');
    renderSample();
    if (result) renderResult();
    renderHistory();
    renderNotice();
    if (lastStatus) $('status').textContent = say(...lastStatus);
    if (lastError && !$('error').hidden) $('error').textContent = errorMessage(lastError);
    renderValue();
    renderLearning(); renderComputer();
    if (!$('key-mapping').hidden) updateMappingSummary();
}
function status(english, french) { lastStatus = [english, french]; $('status').textContent = say(english, french); }
function renderNotice() {
    if (!notice) return;
    $('restored-note').textContent = notice.type === 'restored' ? say(
        `“${notice.name}” restored with ${notice.cycles} historical cycles. Inputs are ready. Run again for fresh local evidence; imported timings and claims are not new observations.`,
        `« ${notice.name} » restauré avec ${notice.cycles} cycles historiques. Les données sont prêtes. Relancez pour de nouvelles preuves locales ; temps et déclarations importés restent historiques.`
    ) : say('Your history is preserved. Replace either catalog or run these inputs again to begin the next cycle.',
        'Votre historique est conservé. Remplacez un catalogue ou relancez ces données pour le cycle suivant.');
    $('restored-note').hidden = false;
}
function errorMessage(error) {
    const message = String(error?.message || error);
    const computerMessages = {
        COMPUTER_CUSTOM_SURFACE_CONTEXT:['The starting brief differs from this custom work surface. Rebuild the work surface from these sources or restore its matching brief.','Le dossier de départ diffère de cette surface de travail personnalisée. Reconstruisez la surface à partir de ces sources ou rétablissez le dossier correspondant.'],
        COMPUTER_REVIEW_INCOMPLETE:['To accept useful work, inspect the deliverable, confirm every criterion and stay within the agreed review allowance. Otherwise preserve it as needing work.','Pour accepter un travail utile, examinez le livrable, confirmez chaque critère et respectez le temps d’examen convenu. Sinon, conservez-le comme travail à améliorer.'],
        COMPUTER_REVIEW:['Enter a review note, whole minutes within the agreed allowance, and a decision after inspecting each criterion.','Saisissez une note, un nombre entier de minutes dans le temps convenu et un avis après l’examen de chaque critère.'],
        COMPUTER_STRATEGY:['Enter an outcome and value hypothesis, 1–6 acceptance conditions and 2–6 strategy hypotheses, one per line (up to 500 characters each), plus a combination and a reframing.','Saisissez un résultat et une hypothèse de valeur, 1 à 6 conditions et 2 à 6 hypothèses, une par ligne (500 caractères maximum chacune), puis une combinaison et une reformulation.'],
        COMPUTER_TASK:['Check the work surface, input rights and limits: 1–100 actions, 10–600 seconds and 1–120 review minutes.','Vérifiez la surface, les droits et les limites : 1 à 100 actions, 10 à 600 secondes et 1 à 120 minutes d’examen.'],
        COMPUTER_PROJECT_CAPACITY:['The complete native mission, including project history, must fit within 2 MB. Save your complete archive; no history has been removed.','La mission native complète, avec l’historique du projet, doit tenir dans 2 Mo. Enregistrez l’archive complète ; aucun historique n’a été supprimé.'],
        COMPUTER_HISTORY:['This project can retain up to eight Computer Use attempts. Save the complete workspace before starting a separate project.','Ce projet conserve jusqu’à huit tentatives Computer Use. Enregistrez l’espace complet avant de commencer un autre projet.'],
        COMPUTER_RESULT_ALREADY_RETAINED:['This attempt already has a different result. Prepare a fresh attempt so both outcomes remain in the history.','Cette tentative possède déjà un autre résultat. Préparez une nouvelle tentative pour conserver les deux résultats.']
    };
    if (computerMessages[message]) return say(...computerMessages[message]);
    const localized = {
        'CSV needs a header row.':'Le CSV doit contenir une ligne d’en-tête.',
        'CSV headers must be nonempty and unique.':'Les en-têtes CSV doivent être renseignés et uniques.',
        'Every CSV row must have the header column count.':'Chaque ligne CSV doit contenir autant de colonnes que l’en-tête.',
        'Unclosed quoted CSV cell.':'Une cellule CSV entre guillemets n’est pas refermée.',
        'Quote inside an unquoted CSV cell.':'Un guillemet apparaît dans une cellule CSV non délimitée.',
        'Unexpected text after a closing CSV quote.':'Du texte suit le guillemet de fermeture d’une cellule CSV.',
        'Join keys must be nonempty exact strings.':'Toutes les clés de jointure doivent être renseignées.',
        'Choose a key column present in each CSV.':'Choisissez une colonne clé présente dans chaque CSV.',
        'CSV cannot contain NUL characters.':'Le CSV ne doit pas contenir de caractères NUL.',
        'Each CSV must contain at most 200000 UTF-8 bytes.':'Chaque CSV est limité à 200 000 octets UTF-8.',
        'CSV exceeds 1500 data rows.':'Chaque catalogue est limité à 1 500 lignes de données.',
        'CSV exceeds 32 columns.':'Chaque CSV est limité à 32 colonnes.',
        'CSV cells exceed 4096 characters.':'Une cellule CSV dépasse la limite de 4 096 caractères.',
        'Join exceeds 10000 output pairs.':'Cette jointure dépasse 10 000 paires. Réduisez les données ou les doublons.',
        'Unsupported or invalid SUCCESSOR project.':'Ce fichier n’est pas un projet SUCCESSOR pris en charge ou valide.',
        'This project contains six full cycles. Export it before starting a separate project.':'Ce projet contient six cycles complets. Téléchargez-le avant de commencer un projet distinct.',
        'Invalid name.':'Donnez au projet un nom de 1 à 80 caractères.'
    };
    return language === 'fr' ? localized[message] || `L’opération n’a pas abouti. Vérifiez le format et les limites du fichier. Détail : ${message}` : message;
}
function showError(error, focusEl) {
    lastError = error;
    $('error').textContent = errorMessage(error);
    $('error').hidden = false; $('error-actions').hidden = false;
    if (focusEl) { focusEl.setAttribute('aria-invalid','true'); focusEl.focus(); }
    else $('error').scrollIntoView({block:'nearest'});
}
function clearError() {
    lastError = null;
    $('error').hidden = true; $('error-actions').hidden = true;
    document.querySelectorAll('[aria-invalid=true]').forEach(el => el.removeAttribute('aria-invalid'));
}
function go(next, focus = true) {
    stage = next;
    ['alpha','gym','evidence','successor'].forEach((name, i) => {
        $(`pane-${name}`).hidden = i !== next;
        const item = $(`journey-${i}`);
        item.classList.toggle('completed', i < next);
        if (i === next) item.setAttribute('aria-current','step'); else item.removeAttribute('aria-current');
    });
    if (focus) {
        const target = $(`${['alpha','gym','evidence','successor'][next]}-title`);
        target.focus({preventScroll:true});
        $('mission').scrollIntoView({block:'start',behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth'});
    }
}
function setMode(next, focus = false) {
    mode = next;
    $('example-inputs').hidden = next !== 'example';
    $('custom-form').hidden = next !== 'custom';
    $('mode-example').setAttribute('aria-pressed',String(next === 'example'));
    $('mode-custom').setAttribute('aria-pressed',String(next === 'custom'));
    if (focus && next === 'custom') $('left-csv').focus();
}
function renderSample() {
    for (const [side, table] of [['left',sample.left],['right',sample.right]]) {
        $(`sample-${side}-count`).textContent = say(`${number(table.rows.length)} synthetic records`,`${number(table.rows.length)} lignes synthétiques`);
        const container = document.querySelectorAll('.sample-grid')[side === 'left' ? 0 : 1];
        container.replaceChildren();
        const columns = table.headers.slice(0,3);
        for (const cell of columns) node('span',container,cell);
        for (const row of table.rows.slice(0,3)) for (const cell of row.slice(0,3)) node('span',container,cell);
    }
}
function clearCurrent() {
    if (learningBusy) stopLearning();
    nativeHandoffRaw = null; nativeReturnRaw = null; nativeChecked = null;
    if (busy) cancelRun(false);
    revision += 1; result = null; artifacts = null; mission = null; valueEstimate = null; $('value-result').hidden = true;
    $('restored-note').hidden = true;
    notice = null;
    clearError();
}
function updateMappingSummary() {
    try {
        const left = alpha.parseCsv($('left-csv').value), right = alpha.parseCsv($('right-csv').value);
        const names = left.headers.filter(name => name !== $('left-key').value && name !== $('right-key').value && right.headers.includes(name));
        $('mapping-summary').textContent = say(
            `${number(left.rows.length)} reference rows · ${number(right.rows.length)} second rows. Shared fields compared: ${names.length ? names.join(', ') : 'none'}.`,
            `${number(left.rows.length)} lignes de référence · ${number(right.rows.length)} lignes du second catalogue. Champs communs comparés : ${names.length ? names.join(', ') : 'aucun'}.`
        );
    } catch { $('key-mapping').hidden = true; }
}
function checkColumns() {
    clearError();
    for (const side of ['left','right']) {
        try {
            const table = alpha.parseCsv($(`${side}-csv`).value);
            const select = $(`${side}-key`), previous = select.value;
            select.replaceChildren();
            for (const header of table.headers) { const option = node('option',select,header); option.value = header; }
            select.value = table.headers.includes(previous) ? previous : table.headers[0];
        } catch (error) { showError(error,$(`${side}-csv`)); return false; }
    }
    $('key-mapping').hidden = false;
    updateMappingSummary();
    $('left-key').focus();
    return true;
}
function controls(disabled) {
    for (const id of ['hero-start','hero-custom','example-start','custom-start','mode-example','mode-custom','check-columns','open-project-top','open-project-bottom']) $(id).disabled = disabled;
}
const strategyNames = {
    nested_scan:['Nested scan · current method','Balayage imbriqué · méthode actuelle'],
    fixed_right_hash:['Hash the right table · alternative','Hachage à droite · alternative'],
    smaller_side_hash:['Hash the smaller table · candidate','Hachage du petit côté · candidate'],
    sort_merge:['Sort and merge · alternative','Tri et fusion · alternative']
};
function strategyName(strategy) { return say(...(strategyNames[strategy.strategyId] || [strategy.label,strategy.label])); }
async function run(m, origin = m === sample ? 'synthetic' : 'public') {
    if (busy || learningBusy) return;
    clearError();
    if (dossier?.cycles.length >= 6) {
        showError(Error(say('This project contains six full cycles. Export it before starting a separate project.','Ce projet contient six cycles complets. Téléchargez-le avant de commencer un projet distinct.')));
        if (result) go(3);
        return;
    }
    busy = true; controls(true); controller = new AbortController();
    const token = ++runToken, expectedRevision = revision;
    $('run-progress').style.width = '5%';
    $('run-status').textContent = say('Preparing your comparison…','Préparation de votre comparaison…');
    go(1);
    try {
        const next = await runAlphaMission(m, {signal:controller.signal,onProgress: progress => {
            if (token !== runToken) return;
            const completed = Number(progress.completed ?? 0), total = Number(progress.total ?? 4);
            $('run-progress').style.width = `${Math.max(8,Math.min(95,(completed / total) * 100))}%`;
            const definition = alpha.STRATEGIES.find(s => s.id === progress.strategyId);
            $('run-status').textContent = definition ? say(`Comparing: ${strategyName({strategyId:definition.id,label:definition.label})}`,`Comparaison : ${strategyName({strategyId:definition.id,label:definition.label})}`) : say('Verifying exact outputs…','Vérification des sorties exactes…');
        }});
        if (token !== runToken || revision !== expectedRevision) return;
        alpha.verifyExperiment(m,next);
        const nextArtifacts = alpha.buildArtifacts(m,next);
        const nextDossier = project.appendCycle(dossier || project.createProject({
            name:say('My first Alpha','Mon premier Alpha'),
            goal:say('Reconcile public catalogs exactly and retain a useful, reusable method.','Rapprocher exactement des catalogues publics et conserver une méthode utile et réutilisable.')
        }),{mission:m,result:next,sourceHash:SOURCE_HASH});
        mission = m; result = next; artifacts = nextArtifacts; dossier = nextDossier;
        $('project-name').value = dossier.name;
        $('run-progress').style.width = '100%';
        $('computer-project-name').value = dossier.name;
        nativeFormForMission(origin); renderResult(); renderHistory(); renderLearning(); renderComputer(); go(2);
        status('Your mission is ready. Download the catalog or keep the capability.','Votre mission est prête. Téléchargez le catalogue ou conservez la capacité.');
    } catch (error) {
        if (token !== runToken) return;
        go(0);
        if (error?.name !== 'AbortError') showError(error);
    } finally {
        if (token === runToken) { busy = false; controls(false); controller = null; }
    }
}
function cancelRun(focus = true) {
    runToken += 1; controller?.abort(); controller = null; busy = false; controls(false);
    go(0,focus);
    status('Run canceled. Your previous project history is preserved.','Exécution annulée. L’historique précédent de votre projet est conservé.');
}
function renderResult() {
    if (!result || !mission) return;
    const rec = result.reconciliation;
    $('matched-count').textContent = number(rec.matchedPairs);
    $('unmatched-count').textContent = number(rec.unmatchedLeft.length + rec.unmatchedRight.length);
    $('conflict-count').textContent = number(rec.conflicts.length);
    $('result-summary').textContent = say(
        `${number(mission.left.rows.length + mission.right.rows.length)} source records reconciled. Matching pairs, unmatched rows and exact value differences are ready to download.`,
        `${number(mission.left.rows.length + mission.right.rows.length)} lignes sources rapprochées. Correspondances, lignes non reliées et divergences exactes sont prêtes à télécharger.`
    );
    const baseline = result.strategies.find(s => s.strategyId === 'nested_scan');
    const best = result.strategies.find(s => s.strategyId === 'smaller_side_hash');
        const strongest = [...result.strategies].filter(s => ['fixed_right_hash','sort_merge'].includes(s.strategyId)).sort((a,b)=>a.metrics.logicalOperations-b.metrics.logicalOperations)[0];
    const competitiveGain = strongest.metrics.logicalOperations - best.metrics.logicalOperations;
    const competitivePercent = strongest.metrics.logicalOperations ? 100 * competitiveGain / strongest.metrics.logicalOperations : 0;
    $('advantage-title').textContent = competitiveGain > 0 ? say(
        `${percentage(competitivePercent)}% less logical work than the strongest alternative.`,
        `${percentage(competitivePercent)} % de travail logique en moins que la meilleure alternative.`
    ) : competitiveGain === 0 ? say(
        'Matches the strongest alternative on logical work.',
        'Même travail logique que la meilleure alternative.'
    ) : say('The strongest alternative does less logical work.','La meilleure alternative effectue moins de travail logique.');
    $('advantage-detail').textContent = say(
        `The smaller-side candidate uses ${number(best.metrics.logicalOperations)} logical operations, versus ${number(strongest.metrics.logicalOperations)} for ${strategyName(strongest)} and ${number(baseline.metrics.logicalOperations)} for the current nested scan. All return the same exact matches.`,
        `La candidate du petit côté utilise ${number(best.metrics.logicalOperations)} opérations logiques, contre ${number(strongest.metrics.logicalOperations)} pour ${strategyName(strongest)} et ${number(baseline.metrics.logicalOperations)} pour le balayage actuel. Toutes produisent les mêmes correspondances exactes.`
    );
    $('comparison-bars').replaceChildren(); $('comparison-table').replaceChildren();
    const max = Math.max(1,...result.strategies.map(s => s.metrics.logicalOperations));
    for (const strategy of result.strategies) {
        const block = node('div',$('comparison-bars'));
        const heading = node('div',block,undefined,'bar-heading');
        node('span',heading,strategyName(strategy)); node('strong',heading,number(strategy.metrics.logicalOperations));
        const track = node('div',block,undefined,'bar-track');
        const fill = node('div',track,undefined,`bar-fill${strategy.strategyId === best.strategyId ? ' best' : ''}`);
        fill.style.setProperty('--bar-width',`${100 * strategy.metrics.logicalOperations / max}%`);
        const row = node('tr',$('comparison-table'));
        node('td',row,strategyName(strategy)); node('td',row,number(strategy.metrics.logicalOperations));
        node('td',row,number(strategy.metrics.indexedRows)); node('td',row,number(strategy.metrics.sortedRows));
        node('td',row,`${percentage(strategy.metrics.elapsedMicros / 1000)} ms`);
        node('td',row,strategy.verified?say('Exact match','Correspondance exacte'):say('Unverified','Non vérifié'),'verified');
    }
    for (const comparison of result.assessment.comparisons.filter(c => c.strategyId !== 'nested_scan')) {
        const alternative = result.strategies.find(s => s.strategyId === comparison.strategyId);
        const text = say(
            `Against ${strategyName(alternative)}: ${number(comparison.logicalOperationsSaved)} logical operations saved; ${number(comparison.auxiliaryRowsSaved)} fewer auxiliary row references (negative means more).`,
            `Face à ${strategyName(alternative)} : ${number(comparison.logicalOperationsSaved)} opérations logiques économisées ; ${number(comparison.auxiliaryRowsSaved)} références de lignes auxiliaires en moins (négatif = davantage).`
        );
        const line = node('p',$('advantage-detail'),text); line.className = 'competitive-note';
    }
    const preview = $('joined-preview'); preview.replaceChildren();
    const table = node('table',preview), thead = node('thead',table), header = node('tr',thead), body = node('tbody',table);
    for (const text of [...mission.left.headers.map(h=>`left.${h}`),...mission.right.headers.map(h=>`right.${h}`)]) node('th',header,text);
    for (const [left,right] of best.pairs.slice(0,6)) { const tr = node('tr',body); for (const value of [...mission.left.rows[left],...mission.right.rows[right]]) node('td',tr,value); }
}
function syncName() {
    if (!dossier) return;
    const name = $('project-name').value.trim();
    if (!name || name.length > 80) throw Error(say('Give your project a name from 1 to 80 characters.','Donnez au projet un nom de 1 à 80 caractères.'));
    dossier = project.renameProject(dossier,name);
}
function renderHistory() {
    $('cycle-history').replaceChildren();
    $('cycle-count').textContent = dossier ? say(`${dossier.cycles.length} ${dossier.cycles.length === 1?'cycle':'cycles'}`,`${dossier.cycles.length} ${dossier.cycles.length === 1?'cycle':'cycles'}`) : say('No cycles yet','Aucun cycle');
    if (!dossier) return;
    for (const [index,cycle] of dossier.cycles.entries()) {
        const item = node('li',$('cycle-history'));
        node('strong',item,say(`Cycle ${index+1} · Catalog reconciliation`,`Cycle ${index+1} · Rapprochement de catalogues`));
        node('span',item,say(`${number(cycle.mission.left.rows.length + cycle.mission.right.rows.length)} source records · ${number(cycle.result.reconciliation.matchedPairs)} matched pairs`,`${number(cycle.mission.left.rows.length + cycle.mission.right.rows.length)} lignes sources · ${number(cycle.result.reconciliation.matchedPairs)} paires`));
        node('small',item,say(`Local engineering run · ${new Intl.DateTimeFormat('en-CA',{dateStyle:'medium',timeStyle:'short'}).format(new Date(cycle.createdAt))}`,`Exécution d’ingénierie locale · ${new Intl.DateTimeFormat('fr-CA',{dateStyle:'medium',timeStyle:'short'}).format(new Date(cycle.createdAt))}`));
    }
}
function download(name, contents, type = 'text/plain;charset=utf-8') {
    const blob = new Blob([contents],{type});
    const url = URL.createObjectURL(blob), anchor = document.createElement('a');
    anchor.href = url; anchor.download = name; document.body.append(anchor); anchor.click(); anchor.remove();
    setTimeout(() => URL.revokeObjectURL(url),1500);
    status(`Downloaded ${name}. Your browser may ask where to save it.`,`Téléchargement de ${name}. Votre navigateur peut demander où l’enregistrer.`);
}
async function safeDownload(action) {
    clearError();
    try { syncName(); await action(); } catch (error) { showError(error,/name|nom/.test(String(error.message)) ? $('project-name') : undefined); }
}
function fillMission(m) {
    $('left-csv').value = project.tableCsv(m.left); $('right-csv').value = project.tableCsv(m.right);
    setMode('custom');
    checkColumns();
    $('left-key').value = m.left.key; $('right-key').value = m.right.key;
    updateMappingSummary();
}
function restoreSerialized(serialized) {
    const restored = project.inspectProject(serialized);
    learningRecords = []; nativeContinuityRaw = null;
    computerHistoryRaw = null; computerHistoryChecked = null; computerHandoffRaw = null; computerChecked = null; computerSelectedIndex = -1;
    clearCurrent(); dossier = restored; $('project-name').value = restored.name;
    notice = {type:'restored',name:restored.name,cycles:restored.cycles.length};
    if (restored.cycles.length) fillMission(restored.cycles.at(-1).mission);
    else setMode('custom');
    go(0,Boolean(restored.cycles.length));
    $('restored-note').textContent = say(
        `“${restored.name}” restored with ${restored.cycles.length} historical ${restored.cycles.length === 1 ? 'cycle' : 'cycles'}. Inputs are ready. Run again for fresh local evidence; imported timings and claims are not new observations.`,
        `« ${restored.name} » restauré avec ${restored.cycles.length} ${restored.cycles.length === 1 ? 'cycle historique' : 'cycles historiques'}. Les données sont prêtes. Relancez pour de nouvelles preuves locales ; temps et déclarations importés restent historiques.`
    );
    $('computer-project-name').value = restored.name;
    renderNotice(); renderHistory(); renderComputer();
    status('Project restored. Run the inputs again for current evidence.','Projet restauré. Relancez les données pour obtenir des preuves actuelles.');
}
$('error-setup').addEventListener('click',() => { clearError(); go(0); });
$('error-example').addEventListener('click',() => { clearError(); go(0); setMode('example'); });
$('hero-start').addEventListener('click',() => { setMode('example'); run(sample); });
$('example-start').addEventListener('click',() => run(sample));
$('hero-custom').addEventListener('click',() => { go(0); setMode('custom',true); });
$('mode-example').addEventListener('click',() => setMode('example'));
$('mode-custom').addEventListener('click',() => setMode('custom',true));
$('check-columns').addEventListener('click',checkColumns);
$('cancel-run').addEventListener('click',() => cancelRun());
$('custom-form').addEventListener('submit',event => {
    event.preventDefault(); clearError();
    if ($('key-mapping').hidden && !checkColumns()) return;
    try {
        const next = alpha.createJoinMission({leftCsv:$('left-csv').value,rightCsv:$('right-csv').value,leftKey:$('left-key').value,rightKey:$('right-key').value});
        run(next);
    } catch (error) { showError(error); }
});
for (const side of ['left','right']) {
    $(`${side}-csv`).addEventListener('input',() => { clearCurrent(); importToken += 1; $('key-mapping').hidden = true; $(`${side}-file-name`).textContent = ''; });
    $(`${side}-key`).addEventListener('change',() => { clearCurrent(); updateMappingSummary(); });
    $(`${side}-file`).addEventListener('change',async () => {
        const input = $(`${side}-file`), file = input.files[0]; if (!file) return;
        const token = ++importToken, expected = revision;
        clearError();
        try {
            if (file.size > 200000) throw Error(say('Choose a CSV no larger than 200 KB. Split a larger catalog before importing.','Choisissez un CSV de 200 Ko au maximum. Divisez un catalogue plus volumineux.'));
            const text = new TextDecoder('utf-8',{fatal:true}).decode(await file.arrayBuffer());
            if (token !== importToken || expected !== revision) throw Error(say('Inputs changed while the file was being read. Choose the file again.','Les données ont changé pendant la lecture. Choisissez le fichier à nouveau.'));
            alpha.parseCsv(text);
            clearCurrent(); $(`${side}-csv`).value = text; $(`${side}-file-name`).textContent = file.name;
            $('key-mapping').hidden = true;
            status('CSV loaded. Check your columns when both catalogs are ready.','CSV chargé. Vérifiez les colonnes lorsque les deux catalogues sont prêts.');
        } catch (error) { showError(error,$(`${side}-csv`)); }
        finally { input.value = ''; }
    });
}
for (const [id,key,name] of [['download-joined','joinedCsv','joined-catalog.csv'],['download-unmatched-left','unmatchedLeftCsv','unmatched-reference.csv'],['download-unmatched-right','unmatchedRightCsv','unmatched-second.csv'],['download-conflicts','conflictsCsv','catalog-conflicts.csv']]) {
    $(id).addEventListener('click',() => { if (artifacts) download(name,artifacts[key],'text/csv;charset=utf-8'); });
}
$('keep-capability').addEventListener('click',() => { if (result) { renderHistory(); go(3); } });
$('back-evidence').addEventListener('click',() => { if (result) go(2); });
$('edit-inputs').addEventListener('click',() => { if (mission) fillMission(mission); go(0); });
$('next-cycle').addEventListener('click',() => {
    try {
        syncName();
        if (dossier?.cycles.length >= 6) throw Error(say('This project contains six full cycles. Download your project and workspace, then open a fresh page for a separate project.','Ce projet contient six cycles. Téléchargez le projet et l’espace, puis ouvrez une nouvelle page pour un projet distinct.'));
        if (mission) fillMission(mission);
        clearCurrent(); go(0);
        notice = {type:'next'};
        $('restored-note').textContent = say('Your history is preserved. Replace either catalog or run these inputs again to begin the next cycle.','Votre historique est conservé. Remplacez un catalogue ou relancez ces données pour le cycle suivant.');
        $('restored-note').hidden = false;
    } catch (error) { showError(error); }
});
$('download-workspace').addEventListener('click',() => safeDownload(async () => download('my-successor-workspace.html',await exportPortable(dossier),'text/html;charset=utf-8')));
$('download-tool').addEventListener('click',() => safeDownload(() => download('successor-catalog-capability.mjs',project.buildCapability(mission,result),'text/javascript;charset=utf-8')));
$('download-report').addEventListener('click',() => safeDownload(() => download('successor-alpha-evidence.html',project.buildReport(mission,result,{name:dossier.name,goal:dossier.goal,language}),'text/html;charset=utf-8')));
$('download-project').addEventListener('click',() => safeDownload(() => download('my-successor-project.json',computerHistoryRaw ? serializeLearningArchive() : project.serializeProject(dossier),'application/json')));
for (const [id,route] of [['handoff-usdc','USDC'],['handoff-agialpha','AGIALPHA']]) $(id).addEventListener('click',() => safeDownload(() => download(`successor-${route.toLowerCase()}-unfunded-draft.json`,JSON.stringify(project.prepareHandoff(dossier,route),null,2),'application/json')));
function renderValue() {
    $('value-result').hidden = !valueEstimate;
    if (!valueEstimate) return;
    const currency = $('value-currency').value;
    const money = cents => new Intl.NumberFormat(language === 'fr' ? 'fr-CA' : 'en-CA',{style:'currency',currency}).format(cents/100);
    $('value-summary').textContent = say(
        `Projected monthly time value: ${money(valueEstimate.monthlyCents)}. After entered setup cost, first month: ${money(valueEstimate.netFirstMonthCents)}. Setup recovery: ${valueEstimate.breakEvenMonths === null ? 'not established' : `${number(valueEstimate.breakEvenMonths)} ${valueEstimate.breakEvenMonths === 1 ? 'month' : 'months'}`}.`,
        `Valeur mensuelle projetée du temps : ${money(valueEstimate.monthlyCents)}. Premier mois après le coût initial saisi : ${money(valueEstimate.netFirstMonthCents)}. Récupération du coût initial : ${valueEstimate.breakEvenMonths === null ? 'non établie' : `${number(valueEstimate.breakEvenMonths)} mois`}.`
    );
}
function wholeInput(id) {
    const input = $(id);
    if (!/^\d+$/.test(input.value) || Number(input.value) > 1000000) {
        input.setAttribute('aria-invalid','true'); input.focus();
        throw Error(say('Enter whole, nonnegative minutes and monthly runs, up to 1,000,000.','Saisissez des minutes et exécutions entières, non négatives, jusqu’à 1 000 000.'));
    }
    return Number(input.value);
}
function centsInput(id) {
    const input = $(id);
    if (!/^\d+(?:\.\d{1,2})?$/.test(input.value) || Number(input.value) > 10000) {
        input.setAttribute('aria-invalid','true'); input.focus();
        throw Error(say('Enter a nonnegative amount up to 10,000, using at most two decimal places.','Saisissez un montant non négatif jusqu’à 10 000, avec deux décimales au maximum.'));
    }
    return Math.round(Number(input.value)*100);
}
$('value-form').addEventListener('submit',event => {
    event.preventDefault(); $('value-error').hidden = true;
    try {
        valueEstimate = project.estimateValue({beforeMinutes:wholeInput('value-before'),afterMinutes:wholeInput('value-after'),runsPerMonth:wholeInput('value-frequency'),hourlyValueCents:centsInput('value-hourly'),setupCents:centsInput('value-setup')});
        renderValue();
    } catch (error) { $('value-error').hidden = false; $('value-error').textContent = errorMessage(error); }
});
$('value-form').addEventListener('input',() => { valueEstimate = null; $('value-result').hidden = true; $('value-error').hidden = true; $('value-form').querySelectorAll('[aria-invalid]').forEach(el=>el.removeAttribute('aria-invalid')); });
$('download-value').addEventListener('click',() => { if (valueEstimate) download('successor-alpha-value-assumptions.json',JSON.stringify({...valueEstimate,currency:$('value-currency').value,projectId:dossier?.id,cycleId:dossier?.cycles.at(-1)?.id},null,2),'application/json'); });
$('project-name').addEventListener('input',() => { $('project-name').removeAttribute('aria-invalid'); });
for (const id of ['open-project-top','open-project-bottom']) $(id).addEventListener('click',() => $('restore-project').click());
$('restore-project').addEventListener('change',async () => {
    const file = $('restore-project').files[0]; if (!file) return;
    const token = ++importToken, expected = revision;
    try {
        if (file.size > 2000000) throw Error(say('Choose a project JSON file no larger than 2 MB.','Choisissez un fichier JSON de projet de 2 Mo au maximum.'));
        const text = new TextDecoder('utf-8',{fatal:true,ignoreBOM:true}).decode(await file.arrayBuffer());
        if (token !== importToken || revision !== expected) throw Error(say('Inputs changed while the project was being read. Reopen the file.','Les données ont changé pendant la lecture du projet. Rouvrez le fichier.'));
        const schema=transport.parseBounded(text)?.schema;
        if(['successor-alpha-learning-archive/v1','successor-alpha-learning-archive/v2'].includes(schema))await restoreLearning(text,expected,token);
        else await restoreSerialized(text);
    } catch (error) { showError(error); }
    finally { $('restore-project').value = ''; }
});
function applyTextSize() {
    document.documentElement.dataset.textSize = largeText ? 'large' : 'standard';
    document.body.classList.toggle('large-text',largeText);
    $('text-size').setAttribute('aria-pressed',String(largeText));
}
$('text-size').addEventListener('click',() => { largeText = !largeText; applyTextSize(); });
applyTextSize();
$('lang-en').addEventListener('click',() => { language = 'en'; translate(); });
$('lang-fr').addEventListener('click',() => { language = 'fr'; translate(); });
$('contract-list').replaceChildren();
if (typeof DEPLOYMENT !== 'undefined' && DEPLOYMENT.contracts) {
    for (const entry of Object.values(DEPLOYMENT.contracts)) {
        if (!/^0x[0-9a-fA-F]{40}$/.test(entry.address)) continue;
        const a = node('a',$('contract-list'));
        a.href = `https://etherscan.io/address/${entry.address}#code`; a.target = '_blank'; a.rel = 'noopener noreferrer';
        node('span',a,entry.name); node('code',a,entry.address);
    }
}
function latestCycle() { return dossier?.cycles.at(-1) || null; }
function learningRecord(create = false) {
    const cycle = latestCycle();
    if (!cycle) return null;
    let entry = learningRecords.find(item => item.cycleId === cycle.id);
    if (!entry && create) { entry = {cycleId:cycle.id,strategy:null,resolution:null}; learningRecords.push(entry); }
    return entry;
}
function boundedInteger(id, maximum) {
    const el = $(id);
    if (!/^\d+$/.test(el.value) || Number(el.value) > maximum) {
        el.focus(); throw Error(say(`Enter a whole value from 0 to ${maximum}.`,`Saisissez une valeur entière de 0 à ${maximum}.`));
    }
    return Number(el.value);
}
function localPanelError(id, error) { $(id).textContent = errorMessage(error); $(id).hidden = false; }
function setLearningBusy(kind, active) {
    learningBusy = active ? kind : null;
    controls(active || busy);
    for (const id of ['research-run','research-example','resolution-run','native-prepare','native-run','next-cycle','keep-capability','edit-inputs','project-name','download-workspace','download-project','download-learning','native-return-input','research-memory','research-weight']) $(id).disabled = active;
    $('research-cancel').hidden = !(active && kind === 'research');
    $('native-cancel').hidden = !(active && kind === 'native');
    if (!active) renderNative();
}
function stopLearning() {
    learningToken += 1; learningController?.abort(); learningController = null;
    setLearningBusy(null,false);
}
function nativeFormForMission(origin) {
    const name = dossier?.name || '';
    $('native-name').value = name.length <= 48 ? name : '';
    $('native-rights').value = origin === 'synthetic' ? 'synthetic' : '';
    $('native-source').value = origin === 'synthetic' ? say('Included synthetic catalog mission generated locally; no personal or third-party customer records.','Mission de catalogue synthétique incluse, générée localement ; aucune donnée personnelle ou client tiers.') : '';
    $('native-license').value = origin === 'synthetic' ? 'Apache-2.0 synthetic example' : '';
    nativeHandoffRaw = null; nativeReturnRaw = null; nativeChecked = null;
    $('native-error').hidden = true; $('native-status').textContent = '';
    renderNative();
}
function researchLabel(record) {
    if (record.id.startsWith('constructed_')) return say(`Constructed plan ${record.id.split('_').at(-1)}`,`Plan composé ${record.id.split('_').at(-1)}`);
    if (language === 'en') return record.label;
    if (record.id === 'baseline_nested') return 'Jointure imbriquée exacte';
    const side = record.id.endsWith('left') ? 'gauche' : record.id.endsWith('right') ? 'droit' : 'le plus petit';
    return record.id.includes('_block_') ? `Hachage délimité · côté ${side}` : `Hachage complet · côté ${side}`;
}
function renderResearch() {
    const retained = result && learningRecord()?.strategy;
    const report = retained && Number($('research-memory').value) === retained.objective.maxAuxiliaryRows && Number($('research-weight').value) === retained.objective.auxiliaryWeight ? retained : null;
    $('research-result').hidden = !report;
    if (!report) return;
    $('research-decision').textContent = report.decision.promoted ? say('A locally improved strategy, retained.','Une stratégie améliorée localement, conservée.') : say('HOLD. Keep the strongest feasible incumbent.','HOLD. Conservez la meilleure référence réalisable.');
    $('research-summary').textContent = say(
        `${report.candidates.length} compositions tested against ${report.baselines.length} declared baselines. Fresh public synthetic confirmation: ${report.confirmation.passed ? 'strict improvement' : 'no strict improvement'}. Objective: logical work + ${number(report.objective.auxiliaryWeight)} × auxiliary references, capped at ${number(report.objective.maxAuxiliaryRows)} references.`,
        `${report.candidates.length} compositions testées face à ${report.baselines.length} références déclarées. Confirmation synthétique publique nouvelle : ${report.confirmation.passed ? 'amélioration stricte' : 'pas d’amélioration stricte'}. Objectif : travail logique + ${number(report.objective.auxiliaryWeight)} × références auxiliaires, limité à ${number(report.objective.maxAuxiliaryRows)} références.`
    );
    if(report.evaluationLedger) {
        const ledger=report.evaluationLedger;
        $('research-summary').textContent += say(` Search and verification ledger retained: ${number(ledger.development.executionLogicalOperations + ledger.confirmation.executionLogicalOperations)} plan-execution operations, plus separately recorded oracle checks.`,` Coût de recherche et de vérification conservé : ${number(ledger.development.executionLogicalOperations + ledger.confirmation.executionLogicalOperations)} opérations d’exécution de plans, avec contrôles d’oracle enregistrés séparément.`);
    }
    $('research-commitment').textContent = say(`Frozen plan SHA-256: ${report.frozen.planHash} · commitment: ${report.frozen.commitment}`,`Plan figé SHA-256 : ${report.frozen.planHash} · engagement : ${report.frozen.commitment}`);
    $('research-candidates').replaceChildren();
    for (const entry of [...report.baselines,...report.candidates]) {
        const row = node('tr',$('research-candidates'));
        node('td',row,researchLabel(entry)); node('td',row,number(entry.metrics.logicalOperations));
        node('td',row,number(entry.metrics.peakAuxiliaryRows)); node('td',row,entry.feasible?say('Yes · exact','Oui · exact'):say('No · exact','Non · exact'));
    }
}
function renderResolution() {
    const report = result && learningRecord()?.resolution;
    $('resolution-result').hidden = !report;
    if (!report) return;
    $('resolution-summary').textContent = say(`${number(report.burden.pairwiseReviewItems)} review occurrences → ${number(report.burden.groupedActions)} proposed key-level actions.`,`${number(report.burden.pairwiseReviewItems)} occurrences à examiner → ${number(report.burden.groupedActions)} actions proposées par clé.`);
    $('resolution-coverage').textContent = say(`${number(report.coverage.coveredOccurrences)} of ${number(report.coverage.originalOccurrences)} original occurrences accounted for exactly once. Every original row reference is retained.`,`${number(report.coverage.coveredOccurrences)} occurrences sur ${number(report.coverage.originalOccurrences)} couvertes exactement une fois. Chaque référence de ligne originale est conservée.`);
    $('resolution-preview').replaceChildren();
    for (const action of report.actions.slice(0,4)) {
        const article = node('article',$('resolution-preview'));
        node('strong',article,action.key);
        const kind = action.type === 'review_shared_values' ? say('Review conflicting values','Examiner les divergences') : action.type === 'missing_from_left' ? say('Check omission from reference','Vérifier l’absence dans la référence') : say('Check omission from second catalog','Vérifier l’absence dans le second catalogue');
        node('p',article,`${kind} · ${number(action.occurrences.length)} ${say('linked occurrences','occurrences liées')}`);
    }
}
function parsedNativeRecord() {
    return nativeContinuityRaw ? transport.parseBounded(nativeContinuityRaw) : null;
}
function renderNative() {
    $('native-prepared').hidden = !nativeHandoffRaw;
    $('native-result').hidden = !nativeChecked;
    if (nativeHandoffRaw) {
        const handoff = transport.parseBounded(nativeHandoffRaw), compilation = transport.parseBounded(handoff.compilationRaw);
        const jobs = compilation.executionOrder;
        const exact = dossier && handoff.project.raw === project.serializeProject(dossier);
        $('native-prepared-summary').textContent = say(
            `Project ${handoff.project.id}, cycle ${handoff.cycle.index+1}. ${Array.isArray(jobs)?jobs.length:0} native Jobs packages compiled. $AGIALPHA route, zero funded budget. ${exact?'Exact project snapshot ready.':'Historical project snapshot: prepare again before a new run.'}`,
            `Projet ${handoff.project.id}, cycle ${handoff.cycle.index+1}. ${Array.isArray(jobs)?jobs.length:0} lots Jobs natifs compilés. Route $AGIALPHA, budget financé nul. ${exact?'Instantané exact du projet prêt.':'Instantané historique : préparez à nouveau avant une nouvelle exécution.'}`
        );
        $('native-run').disabled = Boolean(learningBusy) || !exact;
    }
    if (nativeChecked) {
        const summary = nativeChecked.pack.result.summary;
        $('native-result-summary').textContent = say(`${number(summary.matchedPairs)} exact pairs returned to the same project.`,`${number(summary.matchedPairs)} paires exactes revenues dans le même projet.`);
        $('native-result-detail').textContent = say('Actual local SDK execution checked against the catalog source. Preserved as a historical, local, unreviewed return; independent admission remains HOLD.','Exécution locale réelle du SDK, contrôlée face aux sources du catalogue. Conservée comme résultat historique local non examiné ; l’admission indépendante reste HOLD.');
        $('native-artifacts').replaceChildren();
        for (const file of nativeChecked.files) {
            const button = node('button',$('native-artifacts'),undefined,'download-link'); button.type = 'button';
            node('span',button,file.name); node('span',button,'↓');
            button.addEventListener('click',()=>download(`native-${file.name}`,file.content,file.type));
        }
    }
}
function renderLearningHistory() {
    const strategies = learningRecords.filter(item=>item.strategy).length, resolutions = learningRecords.filter(item=>item.resolution).length;
    const native = parsedNativeRecord(), returns = native?.returns.length || 0;
    const exists = Boolean(strategies || resolutions || returns || nativeHandoffRaw);
    $('learning-history-panel').hidden = !exists;
    $('learning-count').textContent = String(strategies + resolutions + returns);
    $('learning-summary').textContent = say(`${strategies} retained strategy studies · ${resolutions} action plans · ${returns} checked native returns. These remain local historical evidence.`,`${strategies} études de stratégie conservées · ${resolutions} plans d’action · ${returns} retours natifs contrôlés. Ces éléments restent des preuves locales historiques.`);
    $('learning-history').replaceChildren();
    for (const entry of learningRecords) {
        const index = dossier?.cycles.findIndex(cycle=>cycle.id===entry.cycleId);
        const item = node('li',$('learning-history'));
        node('strong',item,say(`Cycle ${index+1} · retained learning`,`Cycle ${index+1} · apprentissages conservés`));
        if (entry.strategy) node('span',item,say(`Strategy: ${entry.strategy.decision.promoted ? 'local improvement' : 'HOLD'}. Frozen plan ${entry.strategy.frozen.planHash.slice(0,16)}…`,`Stratégie : ${entry.strategy.decision.promoted ? 'amélioration locale' : 'HOLD'}. Plan figé ${entry.strategy.frozen.planHash.slice(0,16)}…`));
        if (entry.resolution) node('small',item,say(`Changed task: ${entry.resolution.burden.pairwiseReviewItems} occurrences / ${entry.resolution.burden.groupedActions} actions; complete source coverage.`,`Tâche reformulée : ${entry.resolution.burden.pairwiseReviewItems} occurrences / ${entry.resolution.burden.groupedActions} actions ; sources couvertes intégralement.`));
    }
    for (const entry of native?.returns || []) {
        const returned = transport.parseBounded(entry.returnRaw), index = dossier?.cycles.findIndex(cycle=>cycle.id===returned.cycleId);
        const item = node('li',$('learning-history'));
        node('strong',item,say(`Cycle ${index+1} · native return preserved`,`Cycle ${index+1} · retour natif conservé`));
        node('span',item,say('Source-bound artifacts checked. Historical, local and unreviewed. No current proof or authority inherited.','Artefacts liés aux sources contrôlés. Historiques, locaux et non examinés. Aucune preuve actuelle ni autorité héritée.'));
    }
}
function renderLearning() { renderResearch(); renderResolution(); renderNative(); renderLearningHistory(); }
function serializeLearningArchive() {
    if (!dossier) return '{}';
    const archive = {schema:'successor-alpha-learning-archive/v1',project:project.inspectProject(dossier),records:learningRecords,nativeHandoffRaw,nativeContinuityRaw};
    if (computerHistoryRaw) { archive.schema='successor-alpha-learning-archive/v2'; archive.computerHistoryRaw=computerHistoryRaw; }
    const raw=transport.canonical(archive);
    if(new TextEncoder().encode(raw).length>2000000)throw Error(say('The complete archive exceeds 2 MB. Keep the existing workspace; history will not be dropped to reduce its size.','L’archive complète dépasse 2 Mo. Conservez l’espace existant ; aucun historique ne sera supprimé pour réduire sa taille.'));
    return raw;
}
async function inspectComputerHistoryImport(raw) {
    const snapshot = {project:dossier ? project.inspectProject(dossier) : null, records:transport.parseBounded(transport.canonical(learningRecords)),
        nativeHandoffRaw,nativeContinuityRaw,historyRaw:computerHistoryRaw};
    const incoming = await computer.inspectComputerHistory(raw);
    function latest(current, previous) {
        if (computer.projectContains(current,previous)) return current;
        if (computer.projectContains(previous,current)) return previous;
        throw Error('COMPUTER_HISTORY_PROJECT_BINDING');
    }
    const checkedProject = snapshot.project ? latest(snapshot.project,incoming.project) : incoming.project;
    let historyRaw = raw;
    if (snapshot.historyRaw) {
        const previous = await computer.inspectComputerHistory(snapshot.historyRaw);
        const historyProject = latest(previous.project,incoming.project);
        const records = previous.records.map(record=>({...record}));
        for (const record of incoming.records) {
            const attemptId = transport.parseBounded(record.handoffRaw).attemptId;
            const retained = records.find(item=>transport.parseBounded(item.handoffRaw).attemptId===attemptId);
            if (!retained) { records.push({...record}); continue; }
            if (retained.handoffRaw !== record.handoffRaw
                || retained.returnRaw !== null && record.returnRaw !== null && retained.returnRaw !== record.returnRaw
                || retained.review !== null && record.review !== null && transport.canonical(retained.review)!==transport.canonical(record.review)) {
                throw Error('COMPUTER_HISTORY_CONFLICT');
            }
            retained.returnRaw ??= record.returnRaw;
            retained.review ??= record.review;
        }
        const combined = transport.canonical({schema:computer.HISTORY_SCHEMA,project:historyProject,records,
            authority:'none',settlement:'not_connected'});
        historyRaw = combined === transport.canonical(transport.parseBounded(snapshot.historyRaw)) ? snapshot.historyRaw
            : combined === transport.canonical(transport.parseBounded(raw)) ? raw : combined;
    }
    return learning.inspectLearningArchive(transport.canonical({schema:'successor-alpha-learning-archive/v2',
        project:checkedProject,records:snapshot.records,nativeHandoffRaw:snapshot.nativeHandoffRaw,
        nativeContinuityRaw:snapshot.nativeContinuityRaw,computerHistoryRaw:historyRaw}));
}
async function validateLearningArchive(raw) {
    try {
        if (transport.parseBounded(raw)?.schema === computer.HISTORY_SCHEMA) return await inspectComputerHistoryImport(raw);
        return await learning.inspectLearningArchive(raw);
    }
    catch (error) {
        if (error.message === 'LEARNING_ARCHIVE_FIELDS') throw Error(say('Unsupported learning archive.','Archive d’apprentissage non prise en charge.'));
        throw error;
    }
}
async function restoreLearning(raw, expectedRevision = revision, expectedImportToken = importToken) {
    const priorProject = dossier ? project.serializeProject(dossier) : null;
    const priorComputerForm=computerFormRevision, priorComputerHistory=computerHistoryRaw;
    const priorLearning = {records:transport.canonical(learningRecords),nativeHandoffRaw,nativeContinuityRaw,
        nativeReturnRaw,nativeFormRevision,researchFormRevision};
    const learningUnchanged = () => priorLearning.records === transport.canonical(learningRecords)
        && priorLearning.nativeHandoffRaw === nativeHandoffRaw && priorLearning.nativeContinuityRaw === nativeContinuityRaw
        && priorLearning.nativeReturnRaw === nativeReturnRaw && priorLearning.nativeFormRevision === nativeFormRevision
        && priorLearning.researchFormRevision === researchFormRevision;
    status('Checking the complete learning archive locally…','Vérification locale de l’archive d’apprentissage complète…');
    const checked = await validateLearningArchive(raw);
    let checkedReturn = null, returnRaw = null;
    if (checked.nativeHandoffRaw && checked.nativeContinuityRaw) {
        const history = transport.parseBounded(checked.nativeContinuityRaw);
        const entry = history.returns.find(item=>item.handoffRaw===checked.nativeHandoffRaw);
        if (entry) { returnRaw=entry.returnRaw; checkedReturn=await continuity.inspectNativeReturn(checked.nativeHandoffRaw,returnRaw); }
    }
    let checkedComputerReturn=null;
    const lastComputer=checked.checkedComputer?.records.at(-1);
    if(lastComputer?.returnRaw)checkedComputerReturn=await computer.inspectComputerReturn(lastComputer.handoffRaw,lastComputer.returnRaw);
    if (revision !== expectedRevision || importToken !== expectedImportToken
        || computerFormRevision !== priorComputerForm || computerHistoryRaw !== priorComputerHistory
        || !learningUnchanged()
        || (dossier ? project.serializeProject(dossier) : null) !== priorProject) {
        throw Error(say('Inputs or project changed during archive verification. Reopen the archive.','Les données ou le projet ont changé pendant la vérification. Rouvrez l’archive.'));
    }
    restoreSerialized(project.serializeProject(checked.project));
    learningRecords=checked.records; nativeContinuityRaw=checked.nativeContinuityRaw;
    computerHistoryRaw=checked.computerHistoryRaw || null; computerHistoryChecked=checked.checkedComputer;
    if (computerHistoryChecked?.records.length) applyComputerRecord(computerHistoryChecked.records.length-1,checkedComputerReturn);
    nativeHandoffRaw=checked.nativeHandoffRaw; nativeChecked=checkedReturn; nativeReturnRaw=returnRaw;
    if(nativeHandoffRaw){const h=transport.parseBounded(nativeHandoffRaw),spec=transport.parseBounded(h.specRaw);$('native-name').value=spec.name;$('native-owner').value=spec.owner;$('native-rights').value=spec.rights.dataClass;$('native-source').value=spec.rights.source;$('native-license').value=spec.rights.license;$('native-review-minutes').value=String(spec.reviewMinutes);}
    renderLearning(); renderComputer(); $('learning-history-panel').open=true;
    status('Learning archive restored and rechecked. Records remain historical; no authority was imported.','Archive d’apprentissage restaurée et contrôlée. Les éléments restent historiques ; aucune autorité n’a été importée.');
}

async function acceptNativeReturn(raw) {
    if (!dossier || !nativeHandoffRaw) throw Error(say('Prepare the exact native handoff before importing its return.','Préparez la transmission native exacte avant d’importer son retour.'));
    const expected = revision, exactProject = project.serializeProject(dossier), handoff = nativeHandoffRaw, priorRecord = nativeContinuityRaw, expectedForm=nativeFormRevision;
    const checked = await continuity.inspectNativeReturn(handoff,raw);
    const retained = await continuity.importNativeReturn(dossier,handoff,raw,{sourceHash:SOURCE_HASH,priorRecord});
    if (revision !== expected || project.serializeProject(dossier) !== exactProject || nativeHandoffRaw !== handoff || nativeContinuityRaw !== priorRecord || nativeFormRevision !== expectedForm) throw Error('LEARNING_STALE_NATIVE_RETURN');
    nativeReturnRaw = raw; nativeChecked = checked; nativeContinuityRaw = retained;
    renderNative(); renderLearningHistory();
    $('native-status').textContent = say('Native return checked and retained in this project. Review remains required.','Retour natif contrôlé et conservé dans ce projet. Examen toujours requis.');
}
$('research-run').addEventListener('click',async()=>{
    if (!mission || !result || learningBusy) return;
    const token = ++learningToken, expected = revision, cycleId = latestCycle().id, expectedProject = project.serializeProject(dossier), expectedForm=researchFormRevision;
    $('research-error').hidden = true;
    try {
        const maxAuxiliaryRows = boundedInteger('research-memory',4500), auxiliaryWeight = boundedInteger('research-weight',1000000);
        learningController = new AbortController(); setLearningBusy('research',true);
        $('research-status').textContent = say('Constructing and checking bounded strategies…','Construction et vérification des stratégies délimitées…');
        const report = await runAlphaResearch(mission,{sourceHash:SOURCE_HASH,maxAuxiliaryRows,auxiliaryWeight,signal:learningController.signal,onProgress:p=>{
            if (token===learningToken) $('research-status').textContent = say(`Strategy search: ${p.stage} · ${p.completed ?? 0}/${p.total ?? 0}`,`Recherche de stratégie : ${p.stage} · ${p.completed ?? 0}/${p.total ?? 0}`);
        }});
        await research.validateResearch(report,mission,{sourceHash:SOURCE_HASH});
        if (token !== learningToken || revision !== expected || latestCycle()?.id !== cycleId || project.serializeProject(dossier) !== expectedProject || researchFormRevision !== expectedForm) return;
        learningRecord(true).strategy = report; renderResearch(); renderLearningHistory();
        $('research-status').textContent = say('Study complete. The frozen plan and confirmation are retained.','Étude terminée. Le plan figé et la confirmation sont conservés.');
    } catch (error) { if (token===learningToken) localPanelError('research-error',error); }
    finally { if (token===learningToken) { learningController=null; setLearningBusy(null,false); } }
});
for(const id of ['research-memory','research-weight'])$(id).addEventListener('input',()=>{researchFormRevision+=1;renderResearch();if(!learningBusy)$('research-status').textContent=say('Objective changed. Run again for a current comparison; previous studies remain in history.','Objectif modifié. Relancez pour une comparaison actuelle ; les études précédentes restent dans l’historique.');});
$('research-cancel').addEventListener('click',()=>{stopLearning();$('research-status').textContent=say('Canceled. No partial strategy report retained.','Annulé. Aucun rapport de stratégie partiel conservé.');});
$('research-example').addEventListener('click',()=>{if(!learningBusy)run(research.strategyExampleMission(),'synthetic');});
$('download-research').addEventListener('click',()=>{const report=learningRecord()?.strategy;if(report)download('successor-strategy-study.json',transport.canonical(report),'application/json');});
$('download-plan-tool').addEventListener('click',async()=>{
    const report=learningRecord()?.strategy;if(!report||!mission)return;$('research-error').hidden=true;
    const expected=revision, cycleId=latestCycle().id;
    try{const source=await capability.buildPlanCapability(mission,report,{sourceHash:SOURCE_HASH,...REUSABLE_SOURCE});if(revision!==expected||latestCycle()?.id!==cycleId)throw Error('LEARNING_STALE_CAPABILITY');download('successor-retained-plan.mjs',source,'text/javascript;charset=utf-8');}
    catch(error){localPanelError('research-error',error);}
});
$('resolution-run').addEventListener('click',()=>{
    if (!mission || !result || learningBusy) return;
    $('resolution-error').hidden=true;
    try { const report=research.resolveDiscrepancies(mission,result);research.validateResolution(report,mission,result);learningRecord(true).resolution=report;renderResolution();renderLearningHistory(); }
    catch(error){localPanelError('resolution-error',error);}
});
$('download-actions').addEventListener('click',()=>{const report=learningRecord()?.resolution;if(report)download('successor-discrepancy-actions.csv',report.actionsCsv,'text/csv;charset=utf-8');});
$('native-form').addEventListener('submit',async event=>{
    event.preventDefault(); if (!dossier || !result || learningBusy) return;
    $('native-error').hidden=true;
    try {
        syncName();
        const nativeExact=transport.canonical({schemaVersion:1,mission,result})+'\n';
        if(nativeExact.length>200000||Object.entries(artifacts).some(([key,value])=>key!=='exactJson'&&value.length>200000))throw Error(say('This mission exceeds the native workbench limit of 200,000 characters per artifact. Keep the original downloads and try a smaller catalog mission.','Cette mission dépasse la limite native de 200 000 caractères par artefact. Conservez les téléchargements et essayez une mission plus petite.'));
        const inputs=[$('native-name'),$('native-owner'),$('native-rights'),$('native-source'),$('native-license')];
        const missing=inputs.find(el=>!el.value.trim());if(missing){missing.focus();throw Error(say('Complete the native mission name, accountable owner and explicit input rights before preparing.','Renseignez le nom natif, le responsable et les droits explicites des données avant préparation.'));}
        const reviewMinutes=boundedInteger('native-review-minutes',120);if(reviewMinutes<1)throw Error(say('Choose a review allowance from 1 to 120 minutes.','Choisissez une capacité d’examen de 1 à 120 minutes.'));
        const expected=revision, snapshot=project.serializeProject(dossier), expectedForm=nativeFormRevision;setLearningBusy('prepare',true);
        const raw=await continuity.createNativeHandoff(dossier,{route:'AGIALPHA',sourceHash:SOURCE_HASH,rights:{dataClass:$('native-rights').value,source:$('native-source').value,license:$('native-license').value},owner:$('native-owner').value,reviewMinutes,name:$('native-name').value.normalize('NFC'),language});
        if(revision!==expected||project.serializeProject(dossier)!==snapshot||nativeFormRevision!==expectedForm)throw Error('LEARNING_STALE_NATIVE_HANDOFF');
        nativeHandoffRaw=raw;nativeReturnRaw=null;nativeChecked=null;renderNative();renderLearningHistory();
        $('native-status').textContent=say('Exact native mission and unfunded Jobs plan prepared. Download it for the host runner or rehearse locally with the SDK.','Mission native exacte et plan Jobs non financé préparés. Téléchargez-les pour l’exécuteur hôte ou répétez localement avec le SDK.');
    } catch(error){localPanelError('native-error',error);} finally{setLearningBusy(null,false);}
});
$('native-form').addEventListener('input',()=>{nativeFormRevision+=1;if(!learningBusy){nativeHandoffRaw=null;nativeReturnRaw=null;nativeChecked=null;renderNative();}});
$('native-run').addEventListener('click',async()=>{
    if(!nativeHandoffRaw||learningBusy)return;
    const token=++learningToken, expectedForm=nativeFormRevision;learningController=new AbortController();setLearningBusy('native',true);$('native-error').hidden=true;
    try{
        const returned=await runAlphaNative(nativeHandoffRaw,{signal:learningController.signal,onProgress:p=>{if(token===learningToken)$('native-status').textContent=say(`Native workbench: ${p.stage||p.kind||'executing'}`,`Workbench natif : ${p.stage||p.kind||'exécution'}`);}});
        if(token!==learningToken)return;if(nativeFormRevision!==expectedForm)throw Error('LEARNING_STALE_NATIVE_INPUTS');await acceptNativeReturn(returned);
    }catch(error){if(token===learningToken)localPanelError('native-error',error);}finally{if(token===learningToken){learningController=null;setLearningBusy(null,false);}}
});
$('native-cancel').addEventListener('click',()=>{stopLearning();$('native-status').textContent=say('Native run canceled. No partial return retained.','Exécution native annulée. Aucun retour partiel conservé.');});
$('download-native-handoff').addEventListener('click',()=>{if(nativeHandoffRaw)download('successor-native-handoff.json',nativeHandoffRaw,'application/json');});
$('download-native-return').addEventListener('click',()=>{if(nativeReturnRaw)download('successor-native-return.json',nativeReturnRaw,'application/json');});
$('native-return-input').addEventListener('change',async()=>{
    const file=$('native-return-input').files[0];if(!file)return;$('native-error').hidden=true;
    try{if(file.size>2000000)throw Error(say('Native returns are limited to 2 MB.','Les retours natifs sont limités à 2 Mo.'));const raw=new TextDecoder('utf-8',{fatal:true,ignoreBOM:true}).decode(await file.arrayBuffer());await acceptNativeReturn(raw);}
    catch(error){localPanelError('native-error',error);}finally{$('native-return-input').value='';}
});
$('download-learning').addEventListener('click',()=>safeDownload(()=>download('successor-learning-archive.json',serializeLearningArchive(),'application/json')));
for(const id of ['restore-learning','restore-learning-top','restore-computer-history'])$(id).addEventListener('change',async()=>{
    const file=$(id).files[0];if(!file)return;const expected=revision, token=++importToken;
    try{if(file.size>2000000)throw Error(say('Learning archives are limited to 2 MB.','Les archives d’apprentissage sont limitées à 2 Mo.'));const raw=new TextDecoder('utf-8',{fatal:true,ignoreBOM:true}).decode(await file.arrayBuffer());if(token!==importToken||revision!==expected)throw Error('LEARNING_IMPORT_CHANGED');await restoreLearning(raw,expected,token);}
    catch(error){showError(error);}finally{$(id).value='';}
});

function computerContext() {
    return {form:computerFormRevision,revision,project:dossier ? project.serializeProject(dossier) : null,history:computerHistoryRaw};
}
function computerContextCurrent(expected) {
    return expected.form === computerFormRevision && expected.revision === revision
        && expected.project === (dossier ? project.serializeProject(dossier) : null) && expected.history === computerHistoryRaw;
}
function computerUnchanged(expected) {
    if (!computerContextCurrent(expected)) throw Error(say('Your mission or project changed during checking. Try again with the current inputs.','La mission ou le projet a changé pendant la vérification. Réessayez avec les données actuelles.'));
}
function computerLines(id) { return $(id).value.split(/\r?\n/).map(line=>line.trim()).filter(Boolean); }
function setComputerBusy(value) {
    computerBusy=value;
    $('computer-prepare').disabled=value;
    $('computer-review-save').disabled=value;
}
function computerBriefSurface() { return computerWorkSurface(); }
function computerWorkSurface(existingHtml=null) {
    const context=$('computer-context').value;
    if(existingHtml){
        if(computer.readWorkSurfaceContext(existingHtml)===context)return existingHtml;
        if(computerSurfaceCustomized)throw Error('COMPUTER_CUSTOM_SURFACE_CONTEXT');
    }
    return computer.buildWorkSurface({goal:$('computer-outcome').value.trim(),valueHypothesis:$('computer-value-hypothesis').value.trim(),allowedUrls:computerLines('computer-urls'),context});
}
function computerPreset(kind) {
    if(kind==='math')kind='mathematics';
    $('computer-example').value=kind;
    if (kind === 'custom') {
        $('computer-outcome').value='';$('computer-value-hypothesis').value='';$('computer-context').value='';$('computer-acceptance').value='';
        $('computer-strategy').value=say('Develop a direct solution using the strongest available evidence.\nChallenge the most expensive assumption and investigate an alternative approach.','Développer une solution directe à partir des meilleures preuves disponibles.\nContester l’hypothèse la plus coûteuse et explorer une autre approche.');
        $('computer-combination').value=say('Combine the most promising parts, with a test that could show the combination is worse.','Combiner les éléments prometteurs avec un test susceptible de montrer que la combinaison est moins bonne.');
        $('computer-reframe').value=say('Ask whether a different representation, objective or workflow could achieve the original useful outcome with fewer unnecessary constraints.','Chercher si une autre représentation, un autre objectif ou un autre processus peut atteindre le résultat utile initial avec moins de contraintes inutiles.');
        $('computer-urls').value='';$('computer-html').value='';$('computer-license').value='';
        computerSurfaceCustomized=false;computerFormRevision+=1;computerHandoffRaw=null;computerChecked=null;computerSelectedIndex=-1;renderComputer();return;
    }
    const source='https://raw.githubusercontent.com/MontrealAI/AGI-Alpha-Agent-v0/70dac8e5ce739978f5cd96d0fc190b6ebfcdf8d7/alpha_factory_v1/core/runtime/successor/computer.py';
    const choices={
        opportunity:{
            value:say('A repeatable digital-work offer could be valuable if real beneficiaries accept the deliverable at a total delivery and review cost below its useful value. Demand and revenue remain hypotheses until tested.','Une offre de travail numérique répétable pourrait être utile si de vrais bénéficiaires acceptent le livrable pour un coût total inférieur à sa valeur utile. Demande et revenu restent hypothétiques avant essai.'),
            goal:say('Choose one valuable digital-work opportunity to test: identify a public, unmet need and design a bounded deliverable that could earn its execution and review costs.','Choisir une occasion de travail numérique à tester : repérer un besoin public mal servi et concevoir un livrable délimité pouvant couvrir ses coûts d’exécution et de revue.'),
            criteria:say('Define the beneficiary, current bottleneck and deliverable; cite the supplied public evidence for each factual claim.\nCompare at least three approaches, including the current method, with explicit delivery and review costs or stated unknowns.\nRecommend one small demand-and-value experiment with a stop rule; distinguish hypothetical revenue from observed demand.\nWithout source material, return an evidence-gathering plan and missing inputs instead of a market conclusion.',
                'Définir le bénéficiaire, l’obstacle actuel et le livrable ; citer les sources publiques fournies pour chaque fait.\nComparer au moins trois approches, dont la méthode actuelle, avec coûts de livraison et de revue explicites ou inconnues déclarées.\nRecommander une petite expérience de demande et de valeur avec règle d’arrêt ; distinguer revenu hypothétique et demande observée.\nSans documents sources, rendre un plan de collecte et les données manquantes plutôt qu’une conclusion de marché.'),
            hypotheses:say('Start from public requests and trace the cost of completing the work with the current method.\nStart from a reusable capability and search the supplied public material for repeated unmet needs.\nStart from a buyer’s decision and identify the smallest deliverable that changes that decision.',
                'Partir des demandes publiques et retracer le coût du travail avec la méthode actuelle.\nPartir d’une capacité réutilisable et chercher les besoins répétés dans les documents publics fournis.\nPartir de la décision d’un acheteur et chercher le plus petit livrable qui la change.'),
            combination:say('Combine evidence of repeated need with a reusable method and the smallest acceptance test. Rank strategies by expected useful value after execution, correction and review, stating uncertainty.','Combiner les preuves d’un besoin répété, une méthode réutilisable et le plus petit test d’acceptation. Classer les stratégies selon leur valeur utile attendue après exécution, correction et revue, en précisant l’incertitude.'),
            reframing:say('Challenge the assumption that the opportunity requires selling more hours of the original task. Test whether a reusable public tool, a different workflow or removing the task itself achieves the beneficiary’s same useful outcome.','Remettre en question la vente d’heures supplémentaires sur la tâche initiale. Tester si un outil public réutilisable, un autre parcours ou la suppression de la tâche atteint le même résultat utile pour le bénéficiaire.'),
            urls:[],license:say('Operator-authored digital-work planning brief, Apache-2.0. No observed customer demand is supplied; establish rights for added public material.','Dossier de planification rédigé par l’opérateur, Apache-2.0. Aucune demande client observée fournie ; établir les droits des sources ajoutées.')
        },
        software:{
            goal:say('Discover one implementable way to reduce redundant work, latency or operating cost in the supplied public Computer Use runtime while preserving its task limits, accurate accounting and stop controls. Deliver a source-linked patch proposal and a reproducible validation plan.','Découvrir une façon réalisable de réduire le travail redondant, la latence ou le coût du runtime public Computer Use fourni, en préservant limites, comptabilité exacte et arrêt. Livrer une proposition de correctif sourcée et un plan de validation reproductible.'),
            value:say('Developers operating repeated screen-work missions could benefit from less repeated effort and lower cost per useful accepted result. The benefit is a hypothesis until representative execution, review effort and full costs are measured.','Les développeurs de missions répétées à l’écran pourraient réduire l’effort répété et le coût par résultat utile accepté. Ce bénéfice reste une hypothèse avant la mesure des exécutions représentatives, de la revue et des coûts complets.'),
            criteria:say('Identify the exact source locations and produce an implementable patch or a precise reason to keep the current design.\nPreserve task limits, stop behavior, usage accounting and the useful output; state risks and a rollback.\nProvide a reproducible before-and-after test plan; do not invent benchmark results, actual savings or executed tests.','Identifier les sources exactes et produire un correctif réalisable ou une raison précise de garder la conception actuelle.\nPréserver limites, arrêt, comptabilité et sortie utile ; préciser risques et retour arrière.\nFournir un plan reproductible avant-après ; ne pas inventer de mesures, d’économies réelles ou de tests exécutés.'),
            hypotheses:say('Trace the screenshot/advisor/action loop and identify repeated transformations or work that can be safely avoided.\nRedesign the workflow around the required final artifact and investigate whether fewer interaction steps preserve the same outcome.','Tracer la boucle capture/conseiller/action et trouver les transformations ou travaux répétés évitables sans risque.\nReconcevoir le processus autour du livrable exigé et examiner si moins d’interactions préservent le même résultat.'),
            combination:say('Combine source-level elimination of redundant work with a simpler artifact-centered workflow. Compare against the unchanged baseline using useful results, review effort, failures and full operating cost.','Combiner l’élimination des tâches redondantes dans le code avec un processus plus simple centré sur le livrable. Comparer à la référence inchangée : résultats utiles, effort de revue, échecs et coût complet.'),
            reframing:say('Challenge the assumption that every task needs the same sequence of screen interactions. Separate indispensable screen work from reusable preparation or a different task representation, while preserving the required deliverable and execution boundaries.','Contester l’idée que toute tâche nécessite la même séquence d’interactions. Séparer le travail d’écran indispensable de la préparation réutilisable ou d’une autre représentation, en préservant livrable et limites d’exécution.'),
            urls:[source],license:'Apache-2.0 public source at the pinned AGI Alpha release. Establish rights separately for added material.'
        },
        research:{
            goal:say('Develop a testable new approach to reliable long-horizon Computer Use. Identify a consequential failure mode in the supplied public material, compare credible approaches and produce a concrete design plus an experiment that could falsify its claimed advantage.','Développer une nouvelle approche testable du Computer Use fiable à long horizon. Identifier un échec important dans les sources publiques, comparer des approches crédibles et produire une conception concrète avec une expérience pouvant réfuter son avantage.'),
            value:say('A reliable improvement could make a difficult class of public screen-work tasks economical or practical. Novelty, reliability and economic value remain hypotheses until compared with prior work and tested on representative tasks.','Une amélioration fiable pourrait rendre praticables ou économiques des tâches difficiles sur données publiques. Nouveauté, fiabilité et valeur économique restent hypothétiques avant comparaison aux travaux existants et essais représentatifs.'),
            criteria:say('State a precise failure mode and trace important claims to the supplied sources; label missing evidence.\nDeliver a concrete mechanism, credible alternatives and an experiment with failure criteria, costs and review effort.\nDistinguish new hypotheses from established results; do not claim novel discovery or measured superiority without verification.','Définir un échec précis et sourcer les affirmations importantes ; signaler les preuves manquantes.\nLivrer un mécanisme concret, des alternatives crédibles et une expérience avec critères d’échec, coûts et effort de revue.\nDistinguer hypothèses et résultats établis ; ne pas revendiquer de découverte nouvelle ou de supériorité mesurée sans vérification.'),
            hypotheses:say('Improve planning and error recovery within the existing screenshot/action loop.\nChange the task representation so a reusable intermediate artifact replaces repeated long interaction sequences.','Améliorer planification et récupération dans la boucle capture/action existante.\nChanger la représentation afin qu’un artefact intermédiaire réutilisable remplace de longues séquences répétées.'),
            combination:say('Combine bounded execution with reusable intermediate artifacts and explicit failure recovery. Propose a controlled comparison that can reveal when the combined approach adds cost without improving usefulness.','Combiner exécution délimitée, artefacts intermédiaires réutilisables et récupération explicite. Proposer une comparaison contrôlée pouvant révéler un coût accru sans meilleure utilité.'),
            reframing:say('Question whether the task should be solved as one long autonomous interaction. Investigate a different decomposition, interface or artifact that changes the difficulty while preserving the user’s actual outcome.','Remettre en question la résolution par une longue interaction autonome. Examiner une autre décomposition, interface ou artefact qui change la difficulté tout en préservant le résultat réel de l’utilisateur.'),
            urls:['https://developers.openai.com/api/docs/guides/tools-computer-use'],license:say('Public documentation for source-grounded analysis; preserve attribution and verify permission for any redistribution.','Documentation publique pour analyse sourcée ; préserver l’attribution et vérifier les droits avant redistribution.')
        },
        mathematics:{
            goal:say('Investigate an adaptive portfolio of theorem-proving strategies: under what allocation assumptions can it preserve refutation completeness, and what useful finite-budget guarantee or counterexample can be established? Develop a precise statement, competing proof routes and a checkable candidate argument; identify prior work and unresolved gaps.','Étudier un portefeuille adaptatif de stratégies de preuve : sous quelles hypothèses d’allocation conserve-t-il la complétude de réfutation, et quelle garantie utile à budget fini ou quel contre-exemple établir ? Formuler précisément, comparer les pistes, produire un argument vérifiable et préciser travaux antérieurs et lacunes.'),
            value:say('A valid mathematical result could guide how limited compute is allocated across competing reasoning strategies. Its originality, correctness and practical relevance require literature review, independent scrutiny and appropriate proof checking.','Un résultat valide pourrait guider l’allocation de calcul limité entre stratégies de raisonnement. Originalité, exactitude et pertinence pratique exigent revue de littérature, examen indépendant et vérification de preuve adaptée.'),
            criteria:say('State definitions, assumptions and the exact theorem or counterexample; distinguish finite-budget guarantees from asymptotic completeness.\nProvide a checkable derivation, formalization outline or explicit unresolved gap, with alternatives and relevant prior work.\nNever label a conjecture solved, a proof checked or a result novel without the corresponding verification and evidence.','Énoncer définitions, hypothèses et théorème ou contre-exemple exact ; distinguer budget fini et complétude asymptotique.\nFournir une dérivation vérifiable, une formalisation ou une lacune explicite, avec alternatives et travaux pertinents.\nNe jamais annoncer conjecture résolue, preuve vérifiée ou nouveauté sans les vérifications et preuves correspondantes.'),
            hypotheses:say('Seek a direct completeness proof under an explicit fair resource-allocation rule, then examine finite-budget limitations.\nConstruct adversarial allocation schedules and counterexamples, then search for a weaker theorem with useful assumptions.','Chercher une preuve directe sous une règle d’allocation équitable explicite, puis examiner les limites à budget fini.\nConstruire des allocations adverses et contre-exemples, puis chercher un théorème plus faible sous des hypothèses utiles.'),
            combination:say('Use counterexamples to refine the assumptions of a constructive proof. Present a candidate theorem and a verification plan that tests the fragile steps rather than hiding them.','Utiliser les contre-exemples pour affiner les hypothèses d’une preuve constructive. Présenter un théorème candidat et un plan de vérification ciblant les étapes fragiles.'),
            reframing:say('Challenge an unnecessarily strong universal guarantee. Seek the strongest useful statement for a precisely defined task class or resource model, and explicitly explain how it still serves the original compute-allocation objective.','Contester une garantie universelle inutilement forte. Chercher l’énoncé utile le plus fort pour une classe ou un modèle de ressources précis, en expliquant comment il sert toujours l’objectif initial d’allocation.'),
            urls:[],license:say('Operator-authored research question. Add only public or licensed non-personal mathematical sources and establish their permitted use.','Question de recherche rédigée par l’opérateur. Ajouter uniquement des sources publiques ou autorisées non personnelles, avec droits établis.')
        }
    };
    const contexts={
        opportunity:say('Starting capability: inspect public web material, compare evidence and save a written deliverable with a Computer Use runner. No existing customers, demand or revenue is assumed.\nCompare three proposed offers: a cited public product-decision brief; a reproduction and correction plan for a public software issue; a research-gap and experiment brief.\nChoose one first experiment that fits the action, runtime and review limits below. Deliver its beneficiary hypothesis, exact sample deliverable, demand evidence to gather and a stop rule. Do not contact anyone or spend funds.',
            'Capacité de départ : examiner des documents web publics, comparer les preuves et enregistrer un livrable écrit avec un exécuteur Computer Use. Aucun client, demande ou revenu existant n’est présumé.\nComparer trois offres proposées : une note de décision sur un produit public, sourcée ; un plan de reproduction et correction d’un problème logiciel public ; une note de lacune et expérience de recherche.\nChoisir une première expérience respectant les limites d’actions, de durée et de revue ci-dessous. Livrer le bénéficiaire hypothétique, le livrable témoin exact, les preuves de demande à recueillir et une règle d’arrêt. Ne contacter personne et ne rien dépenser.'),
        mathematics:say('Add the exact mathematical statement, definitions, source, known partial results and why this question matters. Choose the next lemma or counterexample test that fits this attempt. Until these inputs exist, design the investigation protocol rather than claim progress on an unspecified problem.',
            'Ajouter l’énoncé mathématique exact, les définitions, la source, les résultats partiels connus et l’utilité de la question. Choisir le prochain lemme ou test de contre-exemple adapté à cette tentative. Sans ces données, concevoir le protocole d’enquête plutôt que prétendre avancer sur un problème non précisé.'),
        software:say('The pinned public Computer Use runtime source is listed below. No measured bottleneck or speedup is assumed. Investigate an implementable opportunity and record the tests still required. This browser runner can inspect approved pages and write a proposal; executing code and measuring performance require a separately qualified route.',
            'La source publique figée du runtime Computer Use est indiquée ci-dessous. Aucun obstacle mesuré ni accélération n’est présumé. Examiner une amélioration réalisable et les tests requis. Le navigateur examine les sources et écrit une proposition ; exécuter le code et mesurer les performances exige un parcours qualifié séparément.'),
        research:say('Add the exact public papers, research question, conflicting observations and available experimental resources. This attempt should produce one falsifiable experiment design. Running that experiment and validating a discovery are later tasks requiring their own material and acceptance.',
            'Ajouter les articles publics exacts, la question de recherche, les observations contradictoires et les ressources expérimentales disponibles. Cette tentative doit produire un protocole expérimental réfutable. Exécuter l’expérience et valider une découverte sont des tâches suivantes avec leurs données et leur acceptation propres.'),
    };
    const preset=choices[kind] || choices.software;
    $('computer-context').value=contexts[kind] || '';
    if(!dossier)$('computer-project-name').value=kind==='opportunity'?say('Digital work opportunity','Opportunité de travail numérique'):kind==='mathematics'?say('Mathematical strategy research','Recherche de stratégies mathématiques'):kind==='research'?say('Reliable Computer Use research','Recherche Computer Use fiable'):say('Computer Use performance capability','Capacité de performance Computer Use');
    $('computer-outcome').value=preset.goal;$('computer-value-hypothesis').value=preset.value;$('computer-acceptance').value=preset.criteria;
    $('computer-strategy').value=preset.hypotheses;$('computer-combination').value=preset.combination;$('computer-reframe').value=preset.reframing;
    $('computer-license').value=preset.license;$('computer-urls').value=preset.urls.join('\n');$('computer-rights').value='public';
    $('computer-html').value='';$('computer-approach').value='combine';computerSurfaceCustomized=false;
    computerFormRevision+=1; computerHandoffRaw=null; computerChecked=null; computerSelectedIndex=-1;
    renderComputer();
}
function computerApproachLabel(selected) {
    return selected === 'baseline' ? say('Baseline','Référence') : selected === 'combine'
        ? say('Level 3 · combined strategy','Niveau 3 · stratégie combinée') : say('Level 4 · reframed task','Niveau 4 · tâche reformulée');
}
function renderComputer() {
    $('computer-prepared').hidden=!computerHandoffRaw;
    $('computer-returned').hidden=!computerChecked;
    $('computer-history-panel').hidden=!computerHistoryChecked?.records.length;
    if (computerHandoffRaw) {
        const h=transport.parseBounded(computerHandoffRaw);
        $('computer-prepared-title').textContent=computerApproachLabel(h.strategy.selected);
        $('computer-prepared-summary').textContent=h.strategy.originalGoal;
        $('computer-commitment').textContent=say(`Project ${transport.parseBounded(h.projectRaw).id} · ${h.task.max_actions} actions · ${h.task.max_seconds} s · ${h.task.allowed_urls.length} exact public URLs`,
            `Projet ${transport.parseBounded(h.projectRaw).id} · ${h.task.max_actions} actions · ${h.task.max_seconds} s · ${h.task.allowed_urls.length} URL publiques exactes`);
    }
    const record=computerHistoryChecked?.records[computerSelectedIndex];
    if (computerChecked) {
        const summary=computerChecked.summary;
        $('computer-return-summary').textContent=say(`State: ${summary.state}. Model: ${summary.model}. ${summary.actions} reserved actions, ${summary.turns} turns, ${number(summary.elapsedMilliseconds)} ms including cleanup. Billing remains unknown. Browser import checks consistent bytes; signer trust is not verified here.`,
            `État : ${summary.state}. Modèle : ${summary.model}. ${summary.actions} actions réservées, ${summary.turns} tours, ${number(summary.elapsedMilliseconds)} ms, nettoyage compris. Facturation inconnue. L’import vérifie la cohérence des données ; la confiance du signataire n’est pas vérifiée ici.`);
        $('computer-deliverable').textContent=summary.observedText ?? say('No final observed page text was retained. Inspect the runner’s screenshots and interruption record.','Aucun texte final observé n’a été conservé. Examinez les captures et le relevé d’interruption de l’exécuteur.');
        $('computer-review-form').hidden=Boolean(record?.review);
    }
    $('computer-history').replaceChildren();
    const records=computerHistoryChecked?.records || [];
    $('computer-history-count').textContent=say(`${records.length} attempts`,`${records.length} tentatives`);
    for (const [index,entry] of records.entries()) {
        const h=transport.parseBounded(entry.handoffRaw), returned=entry.returnRaw ? transport.parseBounded(entry.returnRaw) : null;
        const item=node('li',$('computer-history'));
        node('strong',item,`${index+1} · ${computerApproachLabel(h.strategy.selected)}`);
        node('span',item,h.strategy.originalGoal);
        if(h.strategy.valueHypothesis)node('small',item,say('Value hypothesis: ','Hypothèse de valeur : ')+h.strategy.valueHypothesis);
        const review=entry.review;
        node('small',item,review ? say(`Owner review: ${review.decision === 'useful' ? 'useful' : 'needs work'} · ${review.minutes} min · ${returned.receipt.actions_reserved} reserved actions. ${review.note}`,
            `Avis du propriétaire : ${review.decision === 'useful' ? 'utile' : 'à améliorer'} · ${review.minutes} min · ${returned.receipt.actions_reserved} actions réservées. ${review.note}`)
            : returned ? say(`Historical result: ${returned.receipt.state} · review required.`,`Résultat historique : ${returned.receipt.state} · examen requis.`)
                : say('Prepared mission · no execution result imported.','Mission préparée · aucun résultat d’exécution importé.'));
        const open=node('button',item,say('Open this attempt','Ouvrir cette tentative'),'text-button');open.type='button';
        open.addEventListener('click',()=>selectComputerRecord(index).catch(error=>localPanelError('computer-error',error)));
    }
    if (records.length) {
        const groups=new Map();
        for (const entry of records) {
            const h=transport.parseBounded(entry.handoffRaw), key=transport.canonical([h.strategy.originalGoal,h.strategy.valueHypothesis,h.strategy.successCriteria,h.sourceHash,h.task.html,h.task.allowed_urls,h.task.input_rights,h.task.license,h.task.max_turns,h.task.max_actions,h.task.max_seconds,h.task.review_minutes]);
            const group=groups.get(key)||{total:0,useful:0,reviewed:0};group.total+=1;group.reviewed+=entry.review ? 1 : 0;group.useful+=entry.review?.decision==='useful' ? 1 : 0;groups.set(key,group);
        }
        const useful=records.filter(entry=>entry.review?.decision==='useful').length;
        $('computer-comparison').textContent=say(`${groups.size} comparable scope(s) · ${useful} owner-accepted useful result(s). Compare actions, review effort and remaining uncertainty only with the same outcome, value hypothesis, work surface, sources, rights and limits. A changed framing earns its place through a useful result; this history does not declare an independently qualified winner.`,
            `${groups.size} périmètre(s) comparable(s) · ${useful} résultat(s) utile(s) accepté(s) par le propriétaire. Comparez actions, effort d’examen et incertitudes uniquement avec les mêmes résultat, hypothèse de valeur, surface, sources, droits et limites. Une reformulation mérite sa place par un résultat utile ; cet historique ne déclare aucun gagnant qualifié indépendamment.`);
    }
}
async function selectComputerRecord(index) {
    if (computerBusy) return;
    const entry=computerHistoryChecked?.records[index];if(!entry)return;
    const expected=computerContext();setComputerBusy(true);$('computer-error').hidden=true;
    try {
        const checked=entry.returnRaw ? await computer.inspectComputerReturn(entry.handoffRaw,entry.returnRaw) : null;
        computerUnchanged(expected);applyComputerRecord(index,checked);
    } finally {setComputerBusy(false);}
}
function applyComputerRecord(index,checked) {
    const entry=computerHistoryChecked.records[index],h=transport.parseBounded(entry.handoffRaw);
    computerSelectedIndex=index;computerHandoffRaw=entry.handoffRaw;computerChecked=checked;
    $('computer-outcome').value=h.strategy.originalGoal;$('computer-value-hypothesis').value=h.strategy.valueHypothesis || '';computerSurfaceCustomized=true;$('computer-acceptance').value=h.strategy.successCriteria.join('\n');
    $('computer-strategy').value=h.strategy.hypotheses.join('\n');$('computer-combination').value=h.strategy.combination;
    $('computer-reframe').value=h.strategy.reframing;$('computer-approach').value=h.strategy.selected;
    $('computer-html').value=h.task.html;$('computer-context').value=computer.readWorkSurfaceContext(h.task.html);$('computer-urls').value=h.task.allowed_urls.join('\n');$('computer-rights').value=h.task.input_rights;
    $('computer-license').value=h.task.license;$('computer-actions').value=h.task.max_actions;$('computer-seconds').value=h.task.max_seconds;$('computer-review-minutes').value=h.task.review_minutes;
    computerFormRevision+=1;prepareComputerReview(h,entry.review);renderComputer();
}
function prepareComputerReview(handoff,review=null) {
    $('computer-review-decision').value=review ? review.decision==='useful' ? 'accepted' : 'rejected' : '';
    $('computer-review-note').value=review?.note || '';
    $('computer-review-actual').value=String(review?.minutes ?? handoff.task.review_minutes);
    $('computer-criteria-review').replaceChildren();
    for (const [index,criterion] of handoff.strategy.successCriteria.entries()) {
        const label=node('label',$('computer-criteria-review'),undefined,'computer-criterion');
        const input=node('input',label);input.type='checkbox';input.dataset.criterion=String(index);input.checked=Boolean(review?.criterionResults[index]);
        node('span',label,criterion);
    }
}
$('computer-example').addEventListener('change',()=>computerPreset($('computer-example').value));
$('computer-build-surface').addEventListener('click',()=>{
    $('computer-error').hidden=true;
    try {
        $('computer-html').value=computerWorkSurface();computerSurfaceCustomized=false;
        computerFormRevision+=1;computerHandoffRaw=null;computerChecked=null;computerSelectedIndex=-1;renderComputer();
        $('computer-status').textContent=say('Work surface rebuilt. Confirm the source rights and execution limits before preparing.','Surface reconstruite. Confirmez les droits des sources et les limites avant de préparer.');
    } catch(error){localPanelError('computer-error',error);}
});
$('computer-form').addEventListener('input',event=>{
    if(event.target.id==='computer-html')computerSurfaceCustomized=true;
    if(['computer-outcome','computer-value-hypothesis','computer-context','computer-urls'].includes(event.target.id) && !computerSurfaceCustomized)$('computer-html').value='';
    computerFormRevision+=1;importToken+=1;computerHandoffRaw=null;computerChecked=null;computerSelectedIndex=-1;
    $('computer-error').hidden=true;renderComputer();
});
$('computer-form').addEventListener('submit',async event=>{
    event.preventDefault();if(computerBusy || busy || learningBusy)return;
    const expected=computerContext();setComputerBusy(true);$('computer-error').hidden=true;
    try {
        const name=$('computer-project-name').value.trim();
        if (!name || name.length>80) throw Error(say('Give this project a name of 1–80 characters.','Donnez au projet un nom de 1 à 80 caractères.'));
        let nextProject=dossier || project.createProject({name,goal:$('computer-outcome').value.trim()});
        if(nextProject.name!==name)nextProject=project.renameProject(nextProject,name);
        const allowedUrls=computerLines('computer-urls'),html=computerWorkSurface($('computer-html').value.trim() ? $('computer-html').value : null);
        const handoffRaw=await computer.createComputerHandoff(nextProject,{sourceHash:SOURCE_HASH,
            goal:$('computer-outcome').value.trim(),valueHypothesis:$('computer-value-hypothesis').value.trim(),successCriteria:computerLines('computer-acceptance'),hypotheses:computerLines('computer-strategy'),
            combination:$('computer-combination').value.trim(),reframing:$('computer-reframe').value.trim(),selected:$('computer-approach').value,
            allowedUrls,inputRights:$('computer-rights').value,license:$('computer-license').value.trim(),maxActions:boundedInteger('computer-actions',100),
            maxSeconds:boundedInteger('computer-seconds',600),reviewMinutes:boundedInteger('computer-review-minutes',120),...(html.trim()?{html}:{})});
        const historyRaw=await computer.retainComputerHandoff(nextProject,handoffRaw,{priorRecord:computerHistoryRaw});
        const checked=await computer.inspectComputerHistory(historyRaw);computerUnchanged(expected);
        dossier=nextProject;computerHistoryRaw=historyRaw;computerHistoryChecked=checked;computerHandoffRaw=handoffRaw;computerChecked=null;
        computerSelectedIndex=checked.records.findIndex(entry=>entry.handoffRaw===handoffRaw);$('project-name').value=dossier.name;
        $('computer-status').textContent=say('Mission prepared and retained in your project. Download the pack for the configured native runner, then import its result here.','Mission préparée et conservée dans votre projet. Téléchargez le dossier pour l’exécuteur natif configuré, puis importez son résultat ici.');
        renderHistory();renderLearning();renderComputer();
    } catch(error){localPanelError('computer-error',error);} finally {setComputerBusy(false);}
});
$('computer-download').addEventListener('click',()=>{if(computerHandoffRaw)download('successor-computer-handoff.json',computerHandoffRaw,'application/json');});
$('computer-return').addEventListener('change',async()=>{
    const file=$('computer-return').files[0];if(!file || !computerHandoffRaw || computerBusy)return;
    const expected=computerContext(),handoffRaw=computerHandoffRaw;setComputerBusy(true);$('computer-error').hidden=true;
    try {
        if(file.size>2000000)throw Error(say('Computer Use returns are limited to 2 MB.','Les retours Computer Use sont limités à 2 Mo.'));
        const raw=new TextDecoder('utf-8',{fatal:true,ignoreBOM:true}).decode(await file.arrayBuffer());
        const checked=await computer.inspectComputerReturn(handoffRaw,raw);
        const historyRaw=await computer.importComputerReturn(dossier,handoffRaw,raw,{priorRecord:computerHistoryRaw});
        const historyChecked=await computer.inspectComputerHistory(historyRaw);computerUnchanged(expected);
        computerHistoryRaw=historyRaw;computerHistoryChecked=historyChecked;computerChecked=checked;
        computerSelectedIndex=historyChecked.records.findIndex(entry=>entry.handoffRaw===handoffRaw);
        prepareComputerReview(checked.handoff,historyChecked.records[computerSelectedIndex].review);
        $('computer-status').textContent=say('Historical result retained. Inspect its actual work product and native screenshots, then record your review.','Résultat historique conservé. Examinez le livrable réel et les captures natives, puis consignez votre avis.');renderComputer();
    } catch(error){localPanelError('computer-error',error);} finally {setComputerBusy(false);$('computer-return').value='';}
});
$('computer-review-form').addEventListener('input',()=>{computerFormRevision+=1;});
$('computer-review-form').addEventListener('submit',async event=>{
    event.preventDefault();if(computerBusy || !computerChecked || !computerHandoffRaw)return;
    const expected=computerContext(),handoffRaw=computerHandoffRaw;setComputerBusy(true);$('computer-error').hidden=true;
    try {
        const decision=$('computer-review-decision').value;
        if(!['accepted','rejected'].includes(decision))throw Error(say('Inspect the result and choose a review decision.','Examinez le résultat et choisissez un avis.'));
        const historyRaw=await computer.reviewComputerReturn(dossier,handoffRaw,{decision:decision==='accepted'?'useful':'needs-work',
            note:$('computer-review-note').value.trim(),minutes:boundedInteger('computer-review-actual',120),
            criterionResults:[...$('computer-criteria-review').querySelectorAll('input')].map(input=>input.checked)},{priorRecord:computerHistoryRaw});
        const checked=await computer.inspectComputerHistory(historyRaw);computerUnchanged(expected);
        computerHistoryRaw=historyRaw;computerHistoryChecked=checked;
        $('computer-status').textContent=say('Your review is preserved. Keep the outcome and acceptance conditions fixed, choose a different approach and prepare the next attempt.','Votre avis est conservé. Gardez le résultat attendu et les conditions d’acceptation, choisissez une autre approche et préparez la tentative suivante.');renderComputer();
    } catch(error){localPanelError('computer-error',error);} finally {setComputerBusy(false);}
});
for(const [id,selected] of [['computer-improve-next','combine'],['computer-reframe-next','reframe']])$(id).addEventListener('click',()=>{
    $('computer-approach').value=selected;$('computer-strategy-panel').open=true;
    computerFormRevision+=1;importToken+=1;computerHandoffRaw=null;computerChecked=null;computerSelectedIndex=-1;renderComputer();
    $('computer-status').textContent=say('Your outcome, value hypothesis and acceptance conditions are preserved. Refine the next approach, then prepare a fresh attempt.','Résultat, hypothèse de valeur et conditions d’acceptation sont conservés. Affinez l’approche, puis préparez une nouvelle tentative.');
    $('computer-strategy-panel').scrollIntoView({block:'start'});$(selected==='combine'?'computer-combination':'computer-reframe').focus();
});
$('computer-save-history').addEventListener('click',()=>safeDownload(()=>download('successor-learning-archive.json',serializeLearningArchive(),'application/json')));
$('computer-save-workspace').addEventListener('click',()=>safeDownload(async()=>download('my-successor-workspace.html',await exportPortable(dossier),'text/html;charset=utf-8')));
computerPreset('software');

translate(); go(0,false);
(async()=>{
    const savedLearning = $('saved-learning').textContent.trim();
    const saved = $('saved-project').textContent.trim();
    try {
        if (savedLearning && savedLearning !== '{}') await restoreLearning(savedLearning);
        else if (saved && saved !== '{}') await restoreSerialized(saved);
    } catch(error) { showError(error); }
})();
