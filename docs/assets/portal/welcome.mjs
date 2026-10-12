// SPDX-License-Identifier: Apache-2.0
// Display preferences only. No accounts, cookies, telemetry or task storage.
const french = {
    "omega-start": "Créer mon SUCCESSOR Ω",
    skip: "Aller au contenu principal",
    "brand-note": "La curiosité entre vos mains",
    "nav-start": "Commencer",
    "nav-how": "Comment ça marche",
    "nav-questions": "Questions",
    "nav-explore": "Explorer les outils",
    "larger-text": "Texte plus grand",
    "hero-eyebrow": "DÉCOUVREZ VOTRE SUCCESSOR Ω",
    "hero-title-first": "Un petit univers.",
    "hero-title-second": "À vous d’explorer.",
    "hero-description":
        "Créez votre laboratoire SUCCESSOR Ω. Donnez-lui un nom, lancez une vraie expérience et gardez une copie fonctionnelle à rouvrir, même hors ligne.",
    "hero-start": "Commencer — créer un plan",
    "hero-how": "Voir comment ça marche",
    "hero-reassurance":
        "Des exemples prêts. Des étapes claires. Prenez tout le temps nécessaire.",
    "trust-account": "Sans compte",
    "trust-payment": "Sans paiement",
    "trust-install": "Rien à installer",
    "example-label": "Votre SUCCESSOR Ω personnel",
    "example-title": "À votre image. En action.",
    "example-description":
        "Un petit laboratoire fonctionnel à garder.",
    "example-task-one": "Faire des expériences",
    "example-time-one": "Explorer",
    "example-task-two": "Garder vos découvertes",
    "example-time-two": "Garder",
    "example-total": "Votre laboratoire complet",
    "example-duration": "Un fichier",
    "example-note": "Nommez-le. Explorez-le. Rouvrez-le hors ligne.",
    "how-eyebrow": "Simple dès le premier pas",
    "how-title": "À votre rythme. Trois étapes simples.",
    "how-description":
        "Commencez par un exemple. Faites une découverte. Emportez votre laboratoire.",
    "step-one-title": "Personnalisez votre Ω",
    "step-one-description":
        "Nommez votre laboratoire et choisissez un petit ou un grand défi. L’exemple est déjà prêt.",
    "step-two-title": "Lancez une vraie expérience",
    "step-two-description":
        "Voyez quatre petits programmes se comparer. Le laboratoire vérifie les réponses sur de nouveaux exemples et affiche les résultats.",
    "step-three-title": "Gardez toute l’expérience",
    "step-three-description":
        "Enregistrez un fichier interactif contenant votre laboratoire et vos expériences. Ouvrez-le dans un navigateur sur ordinateur, même sans internet.",
    "questions-eyebrow": "Quelques réponses pour vous guider",
    "questions-title": "Vous vous posez peut-être ces questions.",
    "questions-description": "Ouvrez une question pour lire la réponse.",
    "faq-free-question": "SUCCESSOR Ω est-il gratuit à essayer?",
    "faq-free-answer":
        "Oui. Créez votre laboratoire, expérimentez et enregistrez-le sans compte, paiement, portefeuille ni abonnement.",
    "faq-install-question": "Faut-il installer quelque chose?",
    "faq-install-answer":
        "Rien à installer pour le laboratoire personnel ou le planificateur. Ouvrez-les dans votre navigateur. Le laboratoire enregistré est un fichier HTML; un navigateur sur ordinateur peut l’ouvrir hors ligne.",
    "faq-privacy-question": "Où vont mon nom et mes expériences?",
    "faq-privacy-answer":
        "Le laboratoire personnel les garde sur votre appareil. Il ne les envoie pas à un serveur et ne les enregistre pas automatiquement. Téléchargez votre copie avant de fermer ou de recharger, puis enregistrez après vos modifications.",
    "faq-guidance-question": "Que fait mon Ω exactement?",
    "faq-guidance-answer":
        "Il réalise de vrais calculs ciblés sur des enregistrements fictifs. Il compare les approches, vérifie les réponses et vous laisse garder les résultats. Ce laboratoire personnel n’est pas un assistant IA généraliste et n’effectue pas de missions à votre place.",
    "faq-reading-question": "Puis-je faciliter la lecture?",
    "faq-reading-answer":
        "Oui. Choisissez Texte plus grand ou utilisez le zoom. Le français et l’anglais sont proposés sur l’accueil, dans votre laboratoire personnel et dans le planificateur simple.",
    "invitation-eyebrow": "VOTRE PROCHAINE DÉCOUVERTE COMMENCE ICI",
    "invitation-title": "Emportez quelque chose.",
    "invitation-description":
        "Votre nom. Vos expériences. Un laboratoire à retrouver.",
    "invitation-start": "Créer mon premier plan",
    "research-eyebrow": "Pour les curieux",
    "research-title": "Explorez davantage, à votre rythme.",
    "research-description":
        "Vous trouverez aussi des outils de planification, des expériences et les travaux de recherche d’origine.",
    "research-language-note":
        "Commencez par le laboratoire personnel SUCCESSOR Ω ci-dessus ou essayez le planificateur simple. Les outils avancés et la recherche ci-dessous sont en anglais; certains offrent des options de langue et demandent des connaissances techniques.",
    "brand-label": "Accueil AGIALPHA",
    "preferences-label": "Préférences de lecture",
    "navigation-label": "Navigation principale",
    "language-label": "Langue",
    "trust-label": "L’exemple guidé",
    "directory-label": "Advanced tools and research",
};

const textElements = [...document.querySelectorAll("[data-home-key]")];
const labelElements = [...document.querySelectorAll("[data-home-label]")];
const english = Object.fromEntries([
    ...textElements.map((el) => [el.dataset.homeKey, el.textContent]),
    ...labelElements.map((el) => [
        el.dataset.homeLabel,
        el.getAttribute("aria-label"),
    ]),
]);
const preferences = new URLSearchParams(location.search);
let language = preferences.get("lang") === "fr" ? "fr" : "en";
let largeText = preferences.get("text") === "large";

function render() {
    const words = language === "fr" ? french : english;
    document.documentElement.lang = language;
    document.documentElement.classList.toggle("home-large-text", largeText);
    document.title =
        language === "fr"
            ? "AGIALPHA · Votre SUCCESSOR Ω. À vous d’explorer."
            : "AGIALPHA · Your SUCCESSOR Ω. Yours to explore.";
    for (const el of textElements) el.textContent = words[el.dataset.homeKey];
    for (const el of labelElements)
        el.setAttribute("aria-label", words[el.dataset.homeLabel]);
    document
        .getElementById("home-en")
        .setAttribute("aria-pressed", String(language === "en"));
    document
        .getElementById("home-fr")
        .setAttribute("aria-pressed", String(language === "fr"));
    document
        .getElementById("home-text-size")
        .setAttribute("aria-pressed", String(largeText));
    const query = new URLSearchParams();
    if (language === "fr") query.set("lang", "fr");
    if (largeText) query.set("text", "large");
    for (const link of document.querySelectorAll("[data-start-link]")) {
        const fragment = new URL(link.href).hash;
        link.setAttribute("href", `start/${query.size ? `?${query}` : ""}${fragment}`);
    }
    for (const link of document.querySelectorAll("[data-omega-link]")) {
        link.setAttribute("href", `successor/play/${query.size ? `?${query}` : ""}`);
    }
    // Keep this entry bookmarkable without adding history or forwarding other parameters.
    const address = new URL(location.href);
    address.searchParams.delete("lang");
    address.searchParams.delete("text");
    for (const [key, value] of query) address.searchParams.set(key, value);
    if (address.href !== location.href)
        history.replaceState(history.state, "", address.href);
}

for (const lang of ["en", "fr"])
    document.getElementById(`home-${lang}`).addEventListener("click", () => {
        language = lang;
        render();
    });
document.getElementById("home-text-size").addEventListener("click", () => {
    largeText = !largeText;
    render();
});
window.addEventListener("popstate", () => {
    const query = new URLSearchParams(location.search);
    language = query.get("lang") === "fr" ? "fr" : "en";
    largeText = query.get("text") === "large";
    render();
});
render();
document.querySelector(".welcome-preferences").hidden = false;
