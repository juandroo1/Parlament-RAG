// Texte der Oberfläche auf Französisch (Spec 002, US-10). Typ wie de.ts (AK-10.5).
// Vor «?», «:» und «;» steht ein geschütztes Leerzeichen, damit das Zeichen nicht allein umbricht.
// Apostroph typografisch («’»), wie in der Romandie empfohlen (Guide du typographe romand).

import type { Messages } from "./de";

const NBSP = " ";

export const fr: Messages = {
  locale: "fr-CH",
  pageTitle: "Frag das Parlament",
  pageDescription:
    "Questions sur les débats et les objets du Parlement fédéral suisse, avec des sources vérifiables.",
  notice: "Projet privé – pas une publication officielle",
  languageLabel: "Langue",
  theme: {
    label: "Affichage",
    light: "Clair",
    dark: "Sombre",
    system: "Comme le système",
    current: (name) => `Affichage${NBSP}: ${name}`,
  },
  hero: {
    title: `Qu’a-t-on dit au Parlement${NBSP}?`,
    lead: "Posez une question en français ou en allemand. La réponse s’appuie sur le Bulletin officiel et Curia Vista, chaque affirmation avec sa source.",
  },
  form: {
    label: "Votre question",
    hint: "(français ou allemand)",
    placeholder: `p. ex. Qu’a dit le Conseil fédéral sur la motion …${NBSP}?`,
    examples: `Exemples${NBSP}:`,
    exampleQuestions: [
      {
        text: `Qu’a dit le Conseil fédéral sur la 13e rente AVS au Conseil des Etats${NBSP}?`,
        lang: "fr",
      },
      {
        text: `Pourquoi le Conseil fédéral a-t-il rejeté l’initiative paysage${NBSP}?`,
        lang: "fr",
      },
      {
        text: "Was sagte Bundesrat Rösti zum Kühlwasser der Kernkraftwerke während der Hitzewelle?",
        lang: "de",
      },
    ],
    filter: "Filtres",
    activeFilters: (count) => (count === 1 ? "1 actif" : `${count} actifs`),
    council: "Conseil",
    allCouncils: "Tous les conseils",
    group: "Groupe parlementaire",
    allGroups: "Tous les groupes",
    groupNote:
      "Avec un filtre de groupe, seules les interventions sont consultées, pas les textes des objets.",
    from: "Du",
    to: "Au",
    submit: "Demander",
    searching: "Recherche en cours …",
  },
  loading:
    "Recherche des sources et rédaction de la réponse. Cela peut prendre 5 à 15 secondes …",
  answer: {
    title: "Réponse",
    sources: "Sources",
    badge: (count) =>
      count === 1
        ? "Réponse IA tirée d’une source"
        : `Réponse IA tirée de ${count} sources`,
    citation: (number) => `Source ${number}`,
    insufficientTitle: "Pas de base suffisante",
    reasons: {
      no_hits: "La recherche n’a trouvé aucun passage pertinent.",
      low_similarity:
        "Les passages trouvés correspondent trop peu à la question.",
      model: "Les passages trouvés ne répondent pas à la question.",
    },
    tryAgain: "Essayez une question plus précise ou d’autres filtres.",
  },
  source: {
    label: "Source",
    federalCouncil: "Conseil fédéral",
    unknown: "Inconnu",
    business: "Objet",
    submitted: (date) => `déposé le ${date}`,
    expand: "Afficher tout le passage",
    collapse: "Afficher moins",
    original: "Passage original sur parlament.ch",
  },
  usage: {
    noModel: "Aucun appel à l’IA",
    tokens: (input, output) =>
      `${input} tokens d’entrée et ${output} de sortie`,
    costUnknown: "Coût inconnu",
    costEstimated: (cost) =>
      `≈ ${cost} USD estimés, inclus dans l’abonnement Claude`,
  },
  councils: {
    NR: "Conseil national",
    SR: "Conseil des Etats",
    V: "Assemblée fédérale (Chambres réunies)",
  },
  parlGroups: {
    V: "Groupe de l’Union démocratique du centre",
    S: "Groupe socialiste",
    "M-E": "Groupe du Centre",
    RL: "Groupe libéral-radical",
    G: "Groupe des VERT-E-S",
    GL: "Groupe vert’libéral",
  },
  errors: {
    network: `L’API n’est pas joignable. Le serveur fonctionne-t-il${NBSP}?`,
    invalid: (fields) =>
      `La saisie n’est pas valable${fields ? `${NBSP}: ${fields}` : "."}`,
    http: (status) => `La requête a échoué (HTTP ${status}).`,
    unexpected: "Erreur inattendue. Veuillez réessayer.",
    codes: {
      rate_limit: (minutes) =>
        `Trop de questions en peu de temps. Veuillez réessayer dans ${minutes === 1 ? "1 minute" : `${minutes} minutes`}.`,
      daily_budget: () =>
        `Le budget quotidien de la démo est épuisé. De nouvelles questions seront possibles dès minuit (UTC)${NBSP}; la recherche dans les sources reste possible en tout temps sur parlament.ch.`,
      llm_unavailable: () =>
        "Le modèle de langue est momentanément indisponible. Veuillez réessayer plus tard.",
      unavailable: () =>
        "La démo est momentanément indisponible. Veuillez réessayer plus tard.",
      model_refused: () =>
        "Le modèle de langue a refusé la requête. Essayez de reformuler la question.",
      model_output: () =>
        "Le modèle de langue n’a pas fourni de réponse valable. Veuillez réessayer.",
    },
  },
  howItWorks: {
    button: "Comment ça marche",
    title: "Comment ça marche",
    close: "Fermer",
    sections: [
      {
        title: "Ce que fait ce site",
        text: "Vous posez une question sur les débats ou les objets du Parlement fédéral. Le site cherche les passages pertinents dans les procès-verbaux et les résume en indiquant les sources.",
      },
      {
        title: "D’où viennent les données",
        text: "Bulletin officiel (procès-verbaux) et Curia Vista (objets), données ouvertes des Services du Parlement de l’Assemblée fédérale. Sessions de décembre 2023 à octobre 2026, en français et en allemand.",
      },
      {
        title: "Comment naît une réponse",
        text: `Une recherche trouve les passages les plus pertinents, y compris dans l’autre langue. Un modèle d’IA rédige la réponse uniquement à partir de ces passages${NBSP}; chaque affirmation porte un numéro qui renvoie à sa source. Si les sources ne suffisent pas, le site le dit.`,
      },
      {
        title: "Limites",
        text: "L’IA peut se tromper ou simplifier. Seul le passage original sur parlament.ch fait foi. Le site restitue ce qui a été dit et n’évalue ni personnes, ni partis, ni objets.",
      },
      {
        title: "Protection des données et limites de la démo",
        text: "Vos questions ne sont pas enregistrées. La démo publique dispose d’un budget quotidien et permet 10 questions par heure.",
      },
    ],
    linkCode: "Code sur GitHub",
    linkEvals: "Résultats des évaluations",
  },
  footer: {
    sourceLabel: `Source${NBSP}:`,
    sourceBefore:
      "Services du Parlement de l’Assemblée fédérale, Berne. Données ouvertes via le service web",
    sourceAfter:
      "(Bulletin officiel et Curia Vista), sessions jusqu’au 2 octobre 2026, téléchargées les 12 et 13 novembre 2026.",
    notOfficialLabel: `Pas une publication officielle${NBSP}:`,
    notOfficial:
      "un projet privé, qui n’émane pas des Services du Parlement. Les réponses sont rédigées par un modèle d’IA à partir des passages trouvés. Seuls les passages originaux liés sur parlament.ch font foi. Le système restitue ce qui a été dit et n’évalue ni personnes, ni partis, ni objets.",
    demo: "La démo publique dispose d’un budget quotidien limité et d’un nombre limité de questions par heure.",
    codeBefore: "Code sous",
    license: "licence MIT",
    codeAfter: ".",
  },
};
