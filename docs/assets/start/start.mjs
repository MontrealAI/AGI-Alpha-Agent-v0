// SPDX-License-Identifier: Apache-2.0
import { runMission } from "../portal/mission-engine.mjs?v=1.26.2";

const $ = (id) => document.getElementById(id);
const french = {
    editTasks: "Voir ou modifier les quatre tâches proposées",
    skip: "Aller à votre premier plan",
    brandNote: "UN MONDE DE POSSIBILITÉS",
    largeText: "Texte plus grand",
    eyebrow: "DE GRANDES POSSIBILITÉS. UN PREMIER PAS SIMPLE.",
    headline: "Votre prochaine idée.<br />Un peu plus près.",
    intro: "Créez un plan utile en quelques étapes simples. Nous vous guidons d’un petit exemple à un résultat que vous pouvez comprendre et conserver.",
    begin: 'Créer mon premier plan <span aria-hidden="true">→</span>',
    reassurance:
        "Essai gratuit · Sans compte · Sans portefeuille · Sans installation",
    previewLabel: "Aperçu d’un exemple de plan",
    previewHeading: "UN PETIT DÉPART. UN VRAI RÉSULTAT.",
    previewTitle: "Faites place<br />à l’essentiel.",
    previewDescription:
        "Choisissez votre temps. Comparez vos tâches. Repartez avec un plan clair.",
    sampleTask: "Vérifier les sources",
    sampleTime: "20 min",
    sampleTask2: "Améliorer le brouillon",
    sampleTime2: "40 min",
    sampleBadge: "EXEMPLE ILLUSTRATIF",
    how: "Comment ça marche",
    how1: "Commencez par un exemple",
    how1b: "Aucune connaissance technique requise.",
    how2: "Comprenez le résultat",
    how2b: "Vérifiez le plan avant de l’utiliser.",
    how3: "Gardez ce qui est utile",
    how3b: "Téléchargez votre plan, puis continuez.",
    guided: "VOTRE PREMIÈRE EXPÉRIENCE GUIDÉE",
    journeyTitle: "Un plan pour le temps disponible.",
    pace: "À votre rythme.<br />Vous gardez le contrôle.",
    loading:
        "Chargement du planificateur… S’il ne s’ouvre pas, rechargez cette page ou consultez le guide ci-dessous.",
    progress: "Votre progression",
    step1: "Choisir",
    step2: "Vérifier",
    step3: "Garder",
    oneOfThree: "ÉTAPE 1 SUR 3",
    twoOfThree: "ÉTAPE 2 SUR 3",
    threeOfThree: "ÉTAPE 3 SUR 3",
    chooseTitle: "Combien de temps avez-vous?",
    chooseIntro:
        "Essayez l’exemple ou adaptez les tâches à vos besoins. Nous trouverons la combinaison ayant le plus de points d’importance dans le temps disponible.",
    minutesLabel: "Temps disponible, en minutes",
    minutesUnit: "minutes",
    minutesHelp:
        "Choisissez un nombre entier de 1 à 480. Par exemple, 60 correspond à une heure.",
    pointsHelp:
        "Points d’importance : 1 = un peu utile, 10 = très utile. Les tâches sont indépendantes et doivent tenir en entier. Ces notes sont vos hypothèses.",
    calculate: 'Trouver mon plan <span aria-hidden="true">→</span>',
    privacy:
        "Vos tâches restent sur cette page. Elles ne sont ni envoyées à un serveur ni enregistrées par ce planificateur. Un rechargement les efface. Téléchargez le résultat pour le conserver.",
    reviewTitle: "Voici un plan à vérifier.",
    reviewExplanation:
        "Nous avons comparé les 16 combinaisons de vos quatre tâches. La sélection maximise vos points d’importance dans le temps disponible. Elle ne réalise pas les tâches et ne vérifie pas vos estimations.",
    reviewed: "J’ai vérifié les tâches, les durées et les priorités.",
    continue: 'Continuer pour enregistrer <span aria-hidden="true">→</span>',
    change: "Modifier mes choix",
    keepTitle: "Votre premier plan est prêt.",
    keepIntro:
        "Enregistrez une copie lisible sur votre appareil. Le fichier de preuve contient aussi les données exactes et le résultat calculé pour permettre une vérification.",
    download: 'Télécharger mon plan (.txt) <span aria-hidden="true">↓</span>',
    evidence: "Garder la preuve (.json)",
    printPlan: "Imprimer ou enregistrer en PDF",
    readPlan: "Lire mon plan ici",
    revise: "Revenir à mes choix",
    nextEyebrow: "QUAND VOUS SEREZ PRÊT",
    nextTitle: "Où souhaitez-vous aller ensuite?",
    next1: "Préparer un plus grand plan",
    next1b: "Comparez ressources, échéanciers et prévisions dans Decision Studio.",
    openStudio: "Ouvrir Decision Studio →",
    next2: "Explorer l’amélioration des agents",
    next2b: "Essayez une expérience de mission guidée dans l’espace bilingue SUCCESSOR.",
    openSuccessor: "Explorer SUCCESSOR →",
    next3: "Exécuter votre propre agent",
    next3b: "Suivez le guide d’installation quand vous êtes prêt à effectuer la configuration technique.",
    openInstall: "Lire le guide d’installation →",
    helpEyebrow: "UN PEU D’AIDE, AU BON MOMENT",
    helpTitle: "Pas besoin de connaître le jargon.",
    guide: "Lire le guide de démarrage français/anglais →",
    q1: "Qu’est-ce qu’AGI ALPHA?",
    a1: "Un projet à code source ouvert pour planifier, expérimenter avec des agents d’IA et vérifier leurs résultats. Commencez par de petites tâches délimitées. La vision de recherche dépasse les capacités démontrées ici.",
    q2: "Faut-il payer ou connecter un portefeuille?",
    a2: "Non. Ce premier plan fonctionne dans votre navigateur, sans compte, paiement, portefeuille ni clé de service d’IA. L’installation d’un agent ou le choix de services externes peuvent ensuite avoir leurs propres exigences et coûts.",
    q3: "Puis-je changer d’avis?",
    a3: "Oui. Utilisez « Modifier mes choix » pour revenir en arrière. Rien n’est acheté, publié ni envoyé en votre nom. Vérifiez le résultat avant de vous y fier.",
    q4: "Besoin de plus grands caractères ou d’aide?",
    a4: "Utilisez « Texte plus grand » en haut ou le zoom du navigateur. La touche Tab déplace le focus, Entrée active un bouton et Espace coche une case. Il n’y a pas de minuterie.",
    more: "Plus d’information",
    all: "Tous les espaces",
    notice: "Avis du projet",
};
const english = Object.fromEntries(
    [...document.querySelectorAll("[data-i18n]")].map((el) => [
        el.dataset.i18n,
        el.innerHTML,
    ]),
);
for (const el of document.querySelectorAll("[data-i18n-label]"))
    english[el.dataset.i18nLabel] = el.getAttribute("aria-label");
const extra = {
    en: {
        task: "Task",
        name: "Task name",
        duration: "Minutes needed",
        importance: "Importance (1–10)",
        fix: "Please check these entries:",
        nameError: "Enter a task name (1–80 characters).",
        timeError: "Use a whole number from 1 to 480 minutes.",
        pointsError: "Use a whole number from 1 to 10.",
        used: "minutes planned",
        left: "minutes left",
        score: "importance points",
        empty: "No task fits yet. Go back and increase your available time or shorten a task estimate.",
        others: "Not selected",
        none: "None",
        downloaded:
            "Download requested. Check your browser’s Downloads folder. Your entries are still on this page.",
        unavailable:
            "The calculation could not finish. Check your entries and try again.",
        planTitle: "My first AGI ALPHA plan",
        reviewed:
            "Reviewed by the user; no independent review or external action.",
        limits: "Independent, indivisible tasks. Maximizes user-assigned importance within estimated time; does not verify those estimates or perform the work.",
        inputs: "All task estimates",
        selected: "Selected tasks",
        budget: "Available minutes",
    },
    fr: {
        task: "Tâche",
        name: "Nom de la tâche",
        duration: "Minutes nécessaires",
        importance: "Importance (1–10)",
        fix: "Veuillez vérifier ces champs :",
        nameError: "Indiquez un nom de tâche (1 à 80 caractères).",
        timeError: "Utilisez un nombre entier de 1 à 480 minutes.",
        pointsError: "Utilisez un nombre entier de 1 à 10.",
        used: "minutes planifiées",
        left: "minutes restantes",
        score: "points d’importance",
        empty: "Aucune tâche ne tient pour l’instant. Revenez en arrière et augmentez le temps disponible ou réduisez une durée estimée.",
        others: "Non sélectionnées",
        none: "Aucune",
        downloaded:
            "Téléchargement demandé. Consultez le dossier Téléchargements du navigateur. Vos données sont encore sur cette page.",
        unavailable:
            "Le calcul n’a pas abouti. Vérifiez les champs et réessayez.",
        planTitle: "Mon premier plan AGI ALPHA",
        reviewed:
            "Vérifié par l’utilisateur; aucune vérification indépendante ni action externe.",
        limits: "Tâches indépendantes et indivisibles. Maximise l’importance attribuée selon les durées estimées; ne vérifie pas ces estimations et ne réalise pas les tâches.",
        inputs: "Toutes les estimations",
        selected: "Tâches sélectionnées",
        budget: "Minutes disponibles",
    },
};
const defaults = {
    en: [
        "Write a summary",
        "Check the sources",
        "Improve the draft",
        "Prepare the handoff",
    ],
    fr: [
        "Rédiger un résumé",
        "Vérifier les sources",
        "Améliorer le brouillon",
        "Préparer la livraison",
    ],
};
let language =
    new URLSearchParams(location.search).get("lang") === "fr" ? "fr" : "en";
const largeText = new URLSearchParams(location.search).get("text") === "large";
document.documentElement.classList.toggle("large-text", largeText);
$("text-size").setAttribute("aria-pressed", String(largeText));

// Carry display preferences between the welcome page and this guide without
// storing task inputs or introducing cookies/local storage.
function updateHomeLinks() {
    const query = new URLSearchParams();
    if (language === "fr") query.set("lang", "fr");
    if (document.documentElement.classList.contains("large-text"))
        query.set("text", "large");
    const suffix = query.size ? `?${query}` : "";
    for (const link of document.querySelectorAll("a[data-home-link]"))
        link.setAttribute("href", `../${suffix}`);
}
let currentStep = 0,
    accepted = false,
    snapshot = null;
const words = () => extra[language];
const element = (tag, text, className) => {
    const el = document.createElement(tag);
    el.textContent = text;
    if (className) el.className = className;
    return el;
};
for (let index = 0; index < 4; index++) {
    const group = element("fieldset", "", "task");
    const legend = element("legend", "");
    legend.dataset.taskNumber = String(index + 1);
    group.append(legend);
    const values = element("div", "", "task-values");
    for (const [field, value, type, min, max] of [
        ["name", defaults[language][index], "text", null, null],
        ["duration", [30, 20, 40, 15][index], "number", 1, 480],
        ["importance", [6, 5, 7, 3][index], "number", 1, 10],
    ]) {
        const label = element("label", "");
        label.htmlFor = `${field}-${index}`;
        label.dataset.field = field;
        const input = document.createElement("input");
        input.id = label.htmlFor;
        input.name = input.id;
        input.type = type;
        input.value = value;
        input.required = true;
        if (type === "number") {
            input.min = min;
            input.max = max;
            input.step = 1;
            input.inputMode = "numeric";
        } else input.maxLength = 80;
        if (field === "name") group.append(label, input);
        else {
            const div = document.createElement("div");
            div.append(label, input);
            values.append(div);
        }
    }
    group.append(values);
    $("tasks").append(group);
}
function renderResult() {
    if (!snapshot) return;
    const { result, request, labels } = snapshot,
        totals = result.evidence.totals,
        selected = result.evidence.selected;
    const stats = element("div", "", "result-stats");
    for (const [value, label] of [
        [totals.cost, words().used],
        [request.work.budget - totals.cost, words().left],
        [totals.value, words().score],
    ]) {
        const p = element("p", "");
        p.append(element("strong", value), element("span", label));
        stats.append(p);
    }
    const list = element("ul", "", "result-list");
    for (const id of selected) {
        const item = request.work.items.find((task) => task.id === id);
        const li = element("li", "");
        li.append(
            element("b", labels[id]),
            element(
                "span",
                ` · ${item.cost} min · ${item.value} ${words().score}`,
            ),
        );
        list.append(li);
    }
    const omitted = request.work.items
        .filter((task) => !selected.includes(task.id))
        .map((task) => labels[task.id]);
    $("result").replaceChildren(
        stats,
        selected.length ? list : element("p", words().empty),
        element(
            "p",
            `${words().others}: ${omitted.join(" · ") || words().none}`,
            "hint",
        ),
    );
}
function translate() {
    document.documentElement.lang = language;
    updateHomeLinks();
    document.title =
        language === "fr" ? "Commencer · AGI ALPHA" : "Start here · AGI ALPHA";
    const dictionary = language === "fr" ? french : english;
    for (const el of document.querySelectorAll("[data-i18n]"))
        el.innerHTML = dictionary[el.dataset.i18n];
    for (const el of document.querySelectorAll("[data-i18n-label]"))
        el.setAttribute("aria-label", dictionary[el.dataset.i18nLabel]);
    for (const el of document.querySelectorAll("[data-task-number]"))
        el.textContent = `${words().task} ${el.dataset.taskNumber}`;
    for (const el of document.querySelectorAll("[data-field]"))
        el.textContent = words()[el.dataset.field];
    $("language").textContent = language === "en" ? "Français" : "English";
    $("language").lang = language === "en" ? "fr" : "en";
    $("language").setAttribute(
        "aria-label",
        language === "en" ? "Passer en français" : "Switch to English",
    );
    $("errors").hidden = true;
    $("download-status").textContent = "";
    renderResult();
    updateReadablePlan();
}
function showStep(step) {
    currentStep = step;
    updateReadablePlan();
    ["choose", "review", "keep"].forEach((id, index) => {
        $(id).hidden = index !== step;
        const li = document.querySelectorAll(".steps li")[index];
        if (index === step) li.setAttribute("aria-current", "step");
        else li.removeAttribute("aria-current");
    });
    $(["choose-title", "review-title", "keep-title"][step]).focus();
}
function invalidate() {
    snapshot = null;
    accepted = false;
    $("reviewed").checked = false;
    $("continue").disabled = true;
    $("result").replaceChildren();
    $("download-status").textContent = "";
    updateReadablePlan();
}
$("plan-form").addEventListener("input", (event) => {
    invalidate();
    event.target.removeAttribute("aria-invalid");
});
$("plan-form").addEventListener("submit", (event) => {
    event.preventDefault();
    invalidate();
    const errors = [],
        labels = {},
        items = [];
    const checkNumber = (id, max, message) => {
        const input = $(id),
            n = Number(input.value);
        if (!input.value.trim() || !Number.isSafeInteger(n) || n < 1 || n > max)
            errors.push([id, message]);
        return n;
    };
    for (const input of $("plan-form").querySelectorAll("input"))
        input.removeAttribute("aria-invalid");
    const budget = checkNumber("minutes", 480, words().timeError);
    for (let i = 0; i < 4; i++) {
        const name = $(`name-${i}`).value.trim();
        if (!name || name.length > 80)
            errors.push([`name-${i}`, words().nameError]);
        labels[`task-${i}`] = name;
        items.push({
            id: `task-${i}`,
            cost: checkNumber(`duration-${i}`, 480, words().timeError),
            value: checkNumber(`importance-${i}`, 10, words().pointsError),
            risk: 0,
        });
    }
    $("errors").hidden = !errors.length;
    if (errors.length) {
        const list = document.createElement("ul");
        for (const [id, message] of errors) {
            $(id).setAttribute("aria-invalid", "true");
            const li = document.createElement("li"),
                a = element(
                    "a",
                    `${id === "minutes" ? (language === "fr" ? french.minutesLabel : english.minutesLabel) : `${words().task} ${Number(id.split("-")[1]) + 1} — ${words()[id.split("-")[0]]}`}: ${message}`,
                );
            a.href = `#${id}`;
            a.addEventListener("click", (event) => {
                event.preventDefault();
                $("task-options").open = true;
                $(id).focus();
            });
            li.append(a);
            list.append(li);
        }
        $("errors").replaceChildren(element("b", words().fix), list);
        $("errors").focus();
        return;
    }
    try {
        const request = {
            goal: "Select independent tasks within available minutes",
            work: {
                kind: "allocation",
                items,
                budget,
                max_risk: 0,
                unit: "minutes",
            },
        };
        snapshot = {
            schema: "agialpha.first-plan.v1",
            version: document.querySelector('meta[name="application-version"]')
                .content,
            request,
            labels,
            result: runMission(request),
        };
        renderResult();
        showStep(1);
    } catch {
        $("errors").hidden = false;
        $("errors").textContent = words().unavailable;
        $("errors").focus();
    }
});
$("reviewed").addEventListener("change", () => {
    accepted = $("reviewed").checked;
    $("continue").disabled = !accepted;
});
$("continue").addEventListener("click", () => {
    if (snapshot && accepted) showStep(2);
});
for (const id of ["back", "revise"])
    $(id).addEventListener("click", () => {
        invalidate();
        showStep(0);
    });
$("language").addEventListener("click", () => {
    const previous = language;
    language = language === "en" ? "fr" : "en";
    for (let i = 0; i < 4; i++)
        if ($(`name-${i}`).value === defaults[previous][i]) {
            $(`name-${i}`).value = defaults[language][i];
            if (snapshot) snapshot.labels[`task-${i}`] = defaults[language][i];
        }
    translate();
});
$("text-size").addEventListener("click", () => {
    const large = document.documentElement.classList.toggle("large-text");
    $("text-size").setAttribute("aria-pressed", String(large));
    updateHomeLinks();
});
function readablePlan() {
    if (!snapshot || !accepted || currentStep !== 2) return "";
    const { request, result, labels } = snapshot;
    const lines = [
        words().planTitle,
        "",
        `${words().budget}: ${request.work.budget}`,
        `${result.evidence.totals.cost} ${words().used} · ${result.evidence.totals.value} ${words().score}`,
        "",
        words().selected,
    ];
    for (const id of result.evidence.selected) {
        const item = request.work.items.find((task) => task.id === id);
        lines.push(
            `${labels[id]} — ${item.cost} min — ${item.value} ${words().score}`,
        );
    }
    if (!result.evidence.selected.length) lines.push(words().empty);
    lines.push("", words().inputs);
    for (const item of request.work.items)
        lines.push(
            `${labels[item.id]} — ${item.cost} min — ${item.value} ${words().score}`,
        );
    lines.push(
        "",
        words().limits,
        words().reviewed,
        `AGI ALPHA ${snapshot.version}`,
        "https://montrealai.github.io/AGI-Alpha-Agent-v0/start/",
    );
    return lines.join("\n") + "\n";
}
function updateReadablePlan() {
    document.body.classList.toggle("has-kept-plan", Boolean(readablePlan()));
    $("readable-plan").textContent = readablePlan();
    $("print-text").textContent = readablePlan();
}
function download(evidence) {
    if (!snapshot || !accepted || currentStep !== 2) return;
    const content = evidence
        ? JSON.stringify(
              {
                  ...snapshot,
                  review: {
                      user_checked: true,
                      independent_review: false,
                      external_action: false,
                  },
                  language,
              },
              null,
              2,
          ) + "\n"
        : readablePlan();
    const url = URL.createObjectURL(
        new Blob([content], {
            type: evidence
                ? "application/json;charset=utf-8"
                : "text/plain;charset=utf-8",
        }),
    );
    const a = document.createElement("a");
    a.href = url;
    a.download = evidence
        ? "agi-alpha-plan-evidence.json"
        : "agi-alpha-plan.txt";
    document.body.append(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    $("download-status").textContent = words().downloaded;
}
$("print-plan").addEventListener("click", () => {
    if (snapshot && accepted && currentStep === 2) window.print();
});
$("download").addEventListener("click", () => download(false));
$("evidence").addEventListener("click", () => download(true));
translate();
$("loading").hidden = true;
$("planner").hidden = false;
