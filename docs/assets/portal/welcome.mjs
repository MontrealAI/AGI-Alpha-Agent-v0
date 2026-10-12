// SPDX-License-Identifier: Apache-2.0
// Display preferences only. No accounts, cookies, telemetry or task storage.
const french = {
    skip: "Aller au contenu principal",
    "brand-note": "Une prochaine étape plus claire",
    "nav-start": "Commencer",
    "nav-how": "Comment ça marche",
    "nav-questions": "Questions",
    "nav-explore": "Explorer les outils",
    "larger-text": "Texte plus grand",
    "hero-eyebrow": "Un bon point de départ",
    "hero-title-first": "Un peu d’aide.",
    "hero-title-second": "Un plan plus clair.",
    "hero-description":
        "Choisissez quelques tâches et le temps disponible. Ce guide simple vous aide à voir ce qui convient, puis à conserver un plan utile.",
    "hero-start": "Commencer — créer un plan",
    "hero-how": "Voir comment ça marche",
    "hero-reassurance":
        "Prenez votre temps. Essayez l’exemple ou adaptez-le à vos besoins.",
    "trust-account": "Sans compte",
    "trust-payment": "Sans paiement",
    "trust-install": "Rien à installer",
    "example-label": "Un exemple de votre plan",
    "example-title": "Une heure. Deux étapes utiles.",
    "example-description":
        "Un peu de temps pour vous concentrer sur l’essentiel.",
    "example-task-one": "Vérifier les sources",
    "example-time-one": "20 min",
    "example-task-two": "Améliorer le brouillon",
    "example-time-two": "40 min",
    "example-total": "Temps prévu",
    "example-duration": "60 minutes",
    "example-note": "Vous choisissez les tâches. Vous vérifiez le plan.",
    "how-eyebrow": "Simple dès le premier pas",
    "how-title": "À votre rythme. Trois étapes simples.",
    "how-description":
        "Nous vous guidons à chaque étape. Vous pouvez changer d’avis en cours de route.",
    "step-one-title": "Choisissez ce qui convient à votre journée",
    "step-one-description":
        "Indiquez le temps disponible et quelques tâches. Des exemples vous aident à commencer.",
    "step-two-title": "Vérifiez votre plan",
    "step-two-description":
        "Voyez quelles tâches conviennent. Vérifiez le résultat, ajustez vos choix et décidez de ce qui vous convient.",
    "step-three-title": "Gardez-le à portée de main",
    "step-three-description":
        "Enregistrez une copie lisible ou imprimez votre plan. Passez à la prochaine étape quand vous le souhaitez.",
    "questions-eyebrow": "Quelques réponses pour vous guider",
    "questions-title": "Vous vous posez peut-être ces questions.",
    "questions-description": "Ouvrez une question pour lire la réponse.",
    "faq-free-question": "L’exemple guidé est-il gratuit?",
    "faq-free-answer":
        "Oui. Vous pouvez créer et conserver un plan sans compte, paiement ni portefeuille.",
    "faq-install-question": "Faut-il installer quelque chose?",
    "faq-install-answer":
        "Non. L’exemple guidé s’ouvre dans votre navigateur. Vous n’avez pas besoin de télécharger une application ni de savoir programmer.",
    "faq-privacy-question": "Que deviennent les tâches que je saisis?",
    "faq-privacy-answer":
        "Dans l’exemple guidé, vos tâches restent sur votre appareil. Elles ne sont pas envoyées à un serveur ni enregistrées automatiquement. Enregistrez ou imprimez votre plan avant de quitter ou de recharger la page.",
    "faq-guidance-question": "L’outil réalise-t-il les tâches à ma place?",
    "faq-guidance-answer":
        "Cet exemple vous aide à choisir un plan adapté au temps disponible. Il ne réalise pas les tâches et ne décide pas à votre place. Vous gardez le contrôle de la suite.",
    "faq-reading-question": "Puis-je faciliter la lecture?",
    "faq-reading-answer":
        "Oui. Choisissez Texte plus grand en haut de la page ou utilisez le zoom du navigateur. Choisissez English ou Français pour la page d’accueil et l’exemple guidé.",
    "invitation-eyebrow": "Un petit pas suffit",
    "invitation-title": "Quand vous le souhaitez.",
    "invitation-description":
        "Commencez par l’exemple. Adaptez-le au fil des étapes.",
    "invitation-start": "Créer mon premier plan",
    "research-eyebrow": "Pour les curieux",
    "research-title": "Explorez davantage, à votre rythme.",
    "research-description":
        "Vous trouverez aussi des outils de planification, des expériences et les travaux de recherche d’origine.",
    "research-language-note":
        "Les outils avancés et la recherche ci-dessous sont présentés en anglais. Certains proposent leurs propres options de langue et peuvent demander des connaissances techniques. L’exemple guidé ci-dessus est le point de départ le plus simple.",
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
            ? "AGIALPHA · Un peu d’aide. Un plan plus clair."
            : "AGIALPHA · A little help. A clearer plan.";
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
    for (const link of document.querySelectorAll("[data-start-link]"))
        link.setAttribute("href", `start/${query.size ? `?${query}` : ""}`);
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
