import { parseUSDC } from "./payments.mjs";

export const DRAFT_KEY = "agijobmanager_employer_onboarding_v1";
export const LANGUAGE_KEY = "agijobmanager_employer_language_v1";
export const CONSOLE_DRAFT_KEY = "agijobmanager_usdc_v096_builder_draft_v11_1";
export const DRAFT_SCHEMA = "agijobmanager/employer-draft/v1";
export const LIMITS = Object.freeze({
  title: 120,
  summary: 3000,
  inputs: 8000,
  deliverables: 4000,
  acceptance: 4000,
  requirements: 2000,
  budget: 25,
  days: 3,
});
const template = (id, category, en, fr) => ({ id, category, en, fr });
const content = (
  title,
  summary,
  deliverables,
  acceptance,
  requirements = "",
) => ({ title, summary, deliverables, acceptance, requirements });
export const PRIMARY_TEMPLATE_IDS = Object.freeze([
  "website",
  "intelligence",
  "presentation",
  "report",
  "dashboard",
  "custom",
]);
export const TEMPLATES = [
  template(
    "website",
    "Website design",
    content(
      "Create a simple website",
      "Create a welcoming one-page website for my project. I will describe who it is for, what it should say and the style I like.",
      "A finished website I can preview in my browser\nThe website files\nSimple instructions for putting it online",
      "The agreed words and sections are included.\nThe page is easy to read on a phone and a computer.\nLinks and buttons work, and the page can be used with a keyboard.",
    ),
    content(
      "Créer un site simple",
      "Créer un site accueillant d’une page pour mon projet. Je préciserai à qui il s’adresse, ce qu’il doit dire et le style que j’aime.",
      "Un site terminé que je peux voir dans mon navigateur\nLes fichiers du site\nDes instructions simples pour le mettre en ligne",
      "Les textes et les sections convenus sont présents.\nLa page est facile à lire sur téléphone et ordinateur.\nLes liens et les boutons fonctionnent, et la page est utilisable au clavier.",
    ),
  ),
  template(
    "presentation",
    "Presentation design",
    content(
      "Prepare a presentation",
      "Prepare a clear, attractive presentation about my topic. I will specify the audience, the main message and the number of slides.",
      "An editable presentation\nA PDF copy that is easy to share\nShort notes to help me present each slide",
      "The presentation covers the agreed points in the agreed number of slides.\nText is easy to read and the visual style is consistent.\nFactual claims include public sources where needed.",
    ),
    content(
      "Préparer une présentation",
      "Préparer une présentation claire et attrayante sur mon sujet. Je préciserai le public, le message principal et le nombre de diapositives.",
      "Une présentation modifiable\nUne copie PDF facile à partager\nDe courtes notes pour présenter chaque diapositive",
      "La présentation couvre les points convenus avec le nombre de diapositives demandé.\nLe texte est facile à lire et le style est cohérent.\nLes faits sont accompagnés de sources publiques au besoin.",
    ),
  ),
  template(
    "report",
    "Public research report",
    content(
      "Research a topic",
      "Research a topic using public information and explain the findings in plain language. I will specify my questions and the length of the report.",
      "A clearly written report\nA short summary of the most useful findings\nLinks to the public sources used",
      "The report answers each agreed question.\nImportant facts link to their sources and show the research date.\nUncertainty and missing information are clearly explained.",
    ),
    content(
      "Faire une recherche",
      "Étudier un sujet à partir d’informations publiques et expliquer les résultats simplement. Je préciserai mes questions et la longueur du rapport.",
      "Un rapport clair\nUn court résumé des résultats les plus utiles\nLes liens vers les sources publiques utilisées",
      "Le rapport répond à chaque question convenue.\nLes faits importants renvoient à leurs sources et indiquent la date de recherche.\nLes incertitudes et les informations manquantes sont clairement expliquées.",
    ),
  ),
  template(
    "custom",
    "Custom digital work",
    content("My own request", "", "", ""),
    content("Ma propre demande", "", "", ""),
  ),
  template(
    "performance",
    "Performance optimization",
    content(
      "Make public software faster",
      "Improve a measured performance bottleneck in a public software project while preserving its documented behavior.",
      "Reviewable patch\nRepeatable before-and-after benchmark\nShort explanation of the trade-offs",
      "Run the same benchmark on the baseline and proposed change.\nDocument the environment and report measurements.\nExisting relevant tests pass; document any known failures.",
    ),
    content(
      "Accélérer un logiciel public",
      "Améliorer un goulot d’étranglement mesuré dans un projet logiciel public en préservant son comportement documenté.",
      "Correctif révisable\nMesure comparative reproductible\nCourte explication des compromis",
      "Exécuter la même mesure sur la version initiale et la version proposée.\nDocumenter l’environnement et présenter les résultats.\nLes tests pertinents existants réussissent; documenter les échecs connus.",
    ),
  ),
  template(
    "feature",
    "Open-source feature",
    content(
      "Add an open-source feature",
      "Implement one clearly scoped feature in a public repository, with tests and instructions for maintainers.",
      "Reviewable implementation\nTests for the agreed behavior\nUpdated usage documentation",
      "Describe the expected behavior and demonstrate it.\nInclude relevant success and error cases in the tests.\nProvide reproducible setup and verification commands.",
    ),
    content(
      "Ajouter une fonction libre",
      "Implémenter une fonction bien délimitée dans un dépôt public, avec des tests et des instructions pour la maintenance.",
      "Implémentation révisable\nTests du comportement convenu\nDocumentation d’utilisation mise à jour",
      "Décrire et démontrer le comportement attendu.\nTester les principaux cas de réussite et d’erreur.\nFournir les commandes reproductibles d’installation et de vérification.",
    ),
  ),
  template(
    "sdk",
    "API and SDK tooling",
    content(
      "Build API or SDK tooling",
      "Create a small client library, command-line tool or integration example for a documented public API, using fixtures or a public sandbox.",
      "Source code and example usage\nFixture-based tests\nInstallation and error-handling guide",
      "Examples run without private credentials.\nTests cover valid responses, errors and timeouts.\nDocument supported API versions and dependencies.",
    ),
    content(
      "Créer un outil API ou SDK",
      "Créer une bibliothèque cliente, un outil en ligne de commande ou un exemple pour une API publique documentée, avec des données simulées ou un environnement de test public.",
      "Code source et exemples\nTests avec données simulées\nGuide d’installation et de gestion des erreurs",
      "Les exemples fonctionnent sans identifiants privés.\nLes tests couvrent les réponses valides, les erreurs et les délais dépassés.\nDocumenter les versions d’API et les dépendances prises en charge.",
    ),
  ),
  template(
    "tests",
    "Automated tests",
    content(
      "Strengthen an automated test suite",
      "Add focused regression tests to a public project for specified behaviors and known edge cases.",
      "Automated tests\nInstructions to run the test suite\nSummary of coverage and remaining gaps",
      "Tests reproduce each agreed behavior and regression.\nDemonstrate that a relevant broken fixture is detected.\nThe suite runs reproducibly without private data.",
    ),
    content(
      "Renforcer les tests automatisés",
      "Ajouter des tests de non-régression ciblés à un projet public pour les comportements définis et les cas limites connus.",
      "Tests automatisés\nInstructions d’exécution\nRésumé de la couverture et des lacunes",
      "Les tests reproduisent chaque comportement et régression convenus.\nDémontrer qu’un cas défectueux pertinent est détecté.\nLa suite s’exécute de façon reproductible sans données privées.",
    ),
  ),
  template(
    "evals",
    "AI evaluation package",
    content(
      "Build an AI evaluation package",
      "Create a reproducible evaluation harness using public, licensed or synthetic examples, with explicit scoring and limitations.",
      "Evaluation dataset with provenance\nScoring code and baseline results\nReproduction and limitations report",
      "Document the source or generation method for every dataset.\nMake scoring rules and baseline configuration explicit.\nA reviewer can reproduce the reported results.",
    ),
    content(
      "Créer un ensemble d’évaluation IA",
      "Créer un banc d’évaluation reproductible à partir d’exemples publics, sous licence ou synthétiques, avec des règles de notation et des limites explicites.",
      "Jeu d’évaluation avec provenance\nCode de notation et résultats de référence\nRapport de reproduction et de limites",
      "Documenter la source ou la méthode de génération de chaque jeu de données.\nExpliciter les règles de notation et la configuration de référence.\nUn évaluateur peut reproduire les résultats présentés.",
    ),
  ),
  template(
    "dashboard",
    "Public-data dashboard",
    content(
      "Turn data into a dashboard",
      "Turn public information into a clear dashboard with useful charts. I will name the information to use and the questions I want the charts to answer.",
      "A working dashboard I can preview\nThe files and simple instructions for using it\nLinks to the data and notes explaining the numbers",
      "Every number can be checked against its source.\nThe charts are easy to read on a phone and a computer.\nShow when the data was updated and explain any missing information.",
    ),
    content(
      "Présenter des données clairement",
      "Présenter des informations publiques dans un tableau de bord avec des graphiques clairs. Je préciserai les données à utiliser et les questions auxquelles les graphiques doivent répondre.",
      "Un tableau de bord que je peux consulter\nLes fichiers et des instructions simples\nLes liens vers les données et une explication des chiffres",
      "Chaque chiffre peut être vérifié dans sa source.\nLes graphiques sont faciles à lire sur téléphone et ordinateur.\nIndiquer la date des données et expliquer les informations manquantes.",
    ),
  ),
  template(
    "demo",
    "Interactive demonstration",
    content(
      "Build an interactive demonstration",
      "Create a self-contained interactive demo that explains a defined concept using public or synthetic inputs.",
      "Working demo and source code\nInstructions and sample scenarios\nAccessibility and browser verification notes",
      "Every primary control has a useful, documented result.\nThe demo works with keyboard navigation and on mobile.\nClearly label assumptions, simulations and limitations.",
    ),
    content(
      "Construire une démonstration interactive",
      "Créer une démonstration interactive autonome expliquant un concept défini à l’aide de données publiques ou synthétiques.",
      "Démonstration fonctionnelle et code source\nInstructions et exemples de scénarios\nNotes de vérification d’accessibilité et de navigateurs",
      "Chaque commande principale produit un résultat utile et documenté.\nLa démonstration fonctionne au clavier et sur mobile.\nIndiquer clairement les hypothèses, les simulations et les limites.",
    ),
  ),
  template(
    "intelligence",
    "Public product research",
    content(
      "Compare products or services",
      "Compare the products or services I name using their official public information. I will explain which differences matter most to my decision.",
      "An easy-to-read comparison table\nThe main advantages and limitations of each option\nLinks to sources and the date of the comparison",
      "Compare every option on the points we agree on.\nLink important facts to their public sources.\nClearly explain opinions, estimates and missing information.",
    ),
    content(
      "Comparer des produits ou services",
      "Comparer les produits ou services que je nomme à partir de leurs informations publiques officielles. Je préciserai les différences qui comptent le plus pour mon choix.",
      "Un tableau comparatif facile à lire\nLes principaux avantages et limites de chaque option\nLes liens vers les sources et la date de la comparaison",
      "Comparer chaque option sur les points convenus.\nRelier les faits importants à leurs sources publiques.\nExpliquer clairement les opinions, les estimations et les informations manquantes.",
    ),
  ),
  template(
    "docs",
    "Executable documentation",
    content(
      "Make documentation executable",
      "Improve a public project's onboarding documentation and provide commands or examples that can be verified in a clean environment.",
      "Updated quick-start guide\nExecutable examples or verification script\nTroubleshooting notes",
      "Follow the guide successfully in a clean environment.\nCommands match the documented dependency versions.\nDescribe expected outputs and common recoverable errors.",
    ),
    content(
      "Rendre la documentation exécutable",
      "Améliorer le guide de démarrage d’un projet public avec des commandes ou exemples vérifiables dans un environnement neuf.",
      "Guide de démarrage mis à jour\nExemples exécutables ou script de vérification\nNotes de dépannage",
      "Suivre le guide avec succès dans un environnement neuf.\nLes commandes correspondent aux versions documentées.\nDécrire les résultats attendus et les erreurs courantes corrigibles.",
    ),
  ),
  template(
    "reproduction",
    "Scientific reproduction",
    content(
      "Reproduce a scientific result",
      "Reproduce a defined numerical result from a public paper or dataset, with a documented method and honest comparison to the reference.",
      "Reproducible code or notebook\nResults and comparison figures\nEnvironment, provenance and limitations",
      "Record exact inputs, versions and random seeds where relevant.\nCompare results with a stated tolerance or explain deviations.\nProvide one clear command or procedure to reproduce the work.",
    ),
    content(
      "Reproduire un résultat scientifique",
      "Reproduire un résultat numérique défini à partir d’un article ou jeu de données public, avec une méthode documentée et une comparaison honnête.",
      "Code ou carnet reproductible\nRésultats et graphiques comparatifs\nEnvironnement, provenance et limites",
      "Consigner les données, versions et graines aléatoires pertinentes.\nComparer les résultats avec une tolérance définie ou expliquer les écarts.\nFournir une commande ou procédure claire de reproduction.",
    ),
  ),
];

export function emptyDraft() {
  return {
    schema: DRAFT_SCHEMA,
    template: "",
    stage: 0,
    fields: {
      title: "",
      summary: "",
      inputs: "",
      deliverables: "",
      acceptance: "",
      requirements: "",
      budget: "1000",
      days: "7",
    },
  };
}
export function templateFields(id, lang = "en") {
  const selected = TEMPLATES.find((item) => item.id === id);
  if (!selected) throw Error("template");
  return { ...selected[lang === "fr" ? "fr" : "en"] };
}
export function normalizeBudget(value) {
  const amount = parseUSDC(value);
  const fraction = (amount % 1_000_000n)
    .toString()
    .padStart(6, "0")
    .replace(/0+$/, "");
  return (amount / 1_000_000n).toString() + (fraction ? "." + fraction : "");
}
export function durationSeconds(value) {
  if (
    typeof value !== "string" ||
    !/^[1-9]\d{0,2}$/.test(value) ||
    Number(value) > 365
  )
    throw Error("days");
  return Number(value) * 86400;
}
export function lines(value) {
  return value
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);
}
export function publicInputURLs(value) {
  const urls = lines(value);
  if (urls.length > 10) throw Error("inputs");
  for (const raw of urls) {
    if (raw.length > 2048 || /\s/.test(raw)) throw Error("inputs");
    let url;
    try {
      url = new URL(raw);
    } catch {
      throw Error("inputs");
    }
    const host = url.hostname.toLowerCase();
    if (
      url.protocol !== "https:" ||
      url.username ||
      url.password ||
      !host.includes(".") ||
      /[:\[\]]/.test(host) ||
      /^[\d.]+$/.test(host) ||
      /(?:^|\.)(?:localhost|local|internal|home|lan|test|invalid|example)$/.test(
        host,
      ) ||
      host.endsWith(".")
    )
      throw Error("inputs");
    const sensitive =
      /^(?:access[_-]?token|refresh[_-]?token|id[_-]?token|token|api[_-]?key|apikey|key|secret|password|passwd|authorization|credential|signature|sig|x-amz-.+|x-goog-.+)$/i;
    if (
      [
        ...url.searchParams.keys(),
        ...new URLSearchParams(url.hash.slice(1)).keys(),
      ].some((key) => sensitive.test(key))
    )
      throw Error("inputs");
  }
  return urls;
}
export function parseDraft(raw) {
  if (typeof raw !== "string" || raw.length > 65536) throw Error("draft");
  let value;
  try {
    value = JSON.parse(raw);
  } catch {
    throw Error("draft");
  }
  if (
    !value ||
    typeof value !== "object" ||
    Array.isArray(value) ||
    value.schema !== DRAFT_SCHEMA ||
    typeof value.template !== "string" ||
    (value.template && !TEMPLATES.some((item) => item.id === value.template)) ||
    !Number.isInteger(value.stage) ||
    value.stage < 0 ||
    value.stage > 3 ||
    !value.fields ||
    typeof value.fields !== "object" ||
    Array.isArray(value.fields)
  )
    throw Error("draft");
  const draft = emptyDraft();
  draft.template = value.template;
  draft.stage = value.stage;
  for (const [key, max] of Object.entries(LIMITS)) {
    if (
      typeof value.fields[key] !== "string" ||
      value.fields[key].length > max ||
      /[\u0000-\u0008\u000b\u000c\u000e-\u001f]/.test(value.fields[key])
    )
      throw Error("draft");
    draft.fields[key] = value.fields[key];
  }
  return draft;
}
export function validateDraft(draft, throughStage = 2) {
  const errors = [];
  try {
    parseDraft(JSON.stringify(draft));
  } catch {
    return [{ field: "title", code: "draft" }];
  }
  if (!TEMPLATES.some((item) => item.id === draft.template))
    errors.push({ field: "template", code: "template" });
  if (throughStage >= 1) {
    for (const key of ["summary", "deliverables", "acceptance"])
      if (!draft.fields[key].trim())
        errors.push({ field: key, code: "required" });
    for (const key of ["deliverables", "acceptance", "requirements"])
      if (
        lines(draft.fields[key]).length > 20 ||
        lines(draft.fields[key]).some((line) => line.length > 500)
      )
        errors.push({ field: key, code: "lines" });
    try {
      publicInputURLs(draft.fields.inputs);
    } catch {
      errors.push({ field: "inputs", code: "inputs" });
    }
  }
  if (throughStage >= 2) {
    try {
      normalizeBudget(draft.fields.budget);
    } catch {
      errors.push({ field: "budget", code: "budget" });
    }
    try {
      durationSeconds(draft.fields.days);
    } catch {
      errors.push({ field: "days", code: "days" });
    }
  }
  return errors;
}
export function draftTitle(fields) {
  return (
    fields.title.trim() ||
    Array.from(fields.summary.trim().replace(/\s+/g, " ")).slice(0, 60).join("")
  );
}
function validated(draft) {
  const errors = validateDraft(draft);
  if (errors.length) throw Error(errors[0].code);
  return draft.fields;
}
export function toMetadata(
  draft,
  lang = "en",
  generatedAt = new Date().toISOString(),
) {
  const fields = validated(draft),
    selected = TEMPLATES.find((item) => item.id === draft.template),
    inputURLs = publicInputURLs(fields.inputs),
    payout = normalizeBudget(fields.budget),
    duration = durationSeconds(fields.days),
    locale = lang === "fr" ? "fr-CA" : "en-CA";
  return {
    name: `AGI Job · ${draftTitle(fields)}`,
    description: fields.summary.trim(),
    ...(inputURLs.length ? { external_url: inputURLs[0] } : {}),
    attributes: [
      { trait_type: "Category", value: selected.category },
      { trait_type: "Payout (USDC)", value: payout },
      {
        display_type: "number",
        trait_type: "Duration (seconds)",
        value: duration,
      },
      { trait_type: "Locale", value: locale },
    ],
    properties: {
      schema: "agijobmanager/job-spec/v1",
      kind: "job-spec",
      version: "1.0.1",
      locale,
      title: draftTitle(fields),
      category: selected.category,
      summary: fields.summary.trim(),
      details: draftTitle(fields),
      tags: [draft.template],
      inputURLs,
      deliverables: lines(fields.deliverables),
      acceptanceCriteria: lines(fields.acceptance),
      requirements: lines(fields.requirements),
      payoutUSDC: payout,
      durationSeconds: duration,
      employer: null,
      chainId: null,
      contract: null,
      ensPreview: null,
      ensURI: null,
      generatedAt,
      createdVia: "AGIJobManager employer onboarding",
      draftOnly: true,
    },
  };
}
export function toConsoleDraft(draft, lang = "en") {
  const fields = validated(draft),
    selected = TEMPLATES.find((item) => item.id === draft.template),
    urls = publicInputURLs(fields.inputs),
    summary =
      fields.summary.trim() +
      (urls.length
        ? `\n\n${lang === "fr" ? "Sources publiques" : "Public inputs"}:\n${urls.join("\n")}`
        : "");
  return {
    jobTitle: draftTitle(fields),
    jobCategory: selected.category,
    jobTags: draft.template,
    jobSummaryBuilder: summary,
    jobDeliverables: lines(fields.deliverables).join("\n"),
    jobAcceptance: lines(fields.acceptance).join("\n"),
    jobRequirements: lines(fields.requirements).join("\n"),
    jobImageURI: "",
    jobExternalURI: urls[0] || "",
    jobSpecVersion: "agijobmanager/job-spec/v1",
    jobLocale: lang === "fr" ? "fr-CA" : "en-CA",
    jobPayout: normalizeBudget(fields.budget),
    jobDuration: String(durationSeconds(fields.days)),
    jobDetails: draftTitle(fields),
    jobSpecURI: "",
  };
}

export function toReadableBrief(draft, lang = "en") {
  const fields = validated(draft),
    fr = lang === "fr",
    sections = [
      [fr ? "MA DEMANDE AGI JOBS" : "MY AGI JOBS REQUEST", draftTitle(fields)],
      [fr ? "Ce que je souhaite" : "What I would like", fields.summary.trim()],
      [
        fr ? "Ce que je souhaite recevoir" : "What I would like to receive",
        fields.deliverables.trim(),
      ],
      [
        fr ? "Comment vérifier le résultat" : "How to check the result",
        fields.acceptance.trim(),
      ],
      [fr ? "Budget" : "Budget", normalizeBudget(fields.budget) + " USDC"],
      [
        fr ? "Délai" : "Time allowed",
        fields.days +
          (fr ? " jours après l’attribution" : " days after assignment"),
      ],
    ];
  if (fields.inputs.trim())
    sections.push([
      fr ? "Liens publics" : "Public links",
      publicInputURLs(fields.inputs).join("\n"),
    ]);
  if (fields.requirements.trim())
    sections.push([
      fr ? "Autres précisions" : "Other details",
      fields.requirements.trim(),
    ]);
  sections.push([
    fr ? "À retenir" : "Please remember",
    fr
      ? "Ceci est un brouillon. Aucune demande n’a été publiée et aucun paiement n’a été effectué. Les frais de réseau s’ajoutent au budget. La publication et le paiement se font ensuite dans la console, où les frais et les conditions doivent être vérifiés."
      : "This is a draft. No request has been published and no payment has been made. Network fees are extra. Publishing and payment happen later in the console, where you must check the fees and terms.",
  ]);
  return (
    sections.map(([label, value]) => label + "\n" + value).join("\n\n") + "\n"
  );
}
