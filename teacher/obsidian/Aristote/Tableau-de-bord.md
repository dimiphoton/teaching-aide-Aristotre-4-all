---
type: tableau-de-bord
---
# Tableau de bord Aristote

> Nécessite le plugin **Dataview** (avec « Enable JavaScript Queries » activé).
> Les noms sont affichés grâce à [[_Correspondance-eleves]] ; les fichiers des kiosques ne contiennent que des pseudonymes.

## ⚠️ À revoir (14 derniers jours)

```dataviewjs
const noms = dv.page("Aristote/_Correspondance-eleves")?.eleves ?? {};
const depuis = dv.date("today").minus(dv.duration("14 days"));
const pages = dv.pages('"Aristote/Kiosques"')
  .where(p => p.type === "session" && p.a_revoir_prof && dv.date(p.debut) >= depuis)
  .sort(p => p.debut, "desc");
dv.table(["Élève", "Date", "Notions", "Misconceptions", "Session"],
  pages.map(p => [noms[p.eleve] ?? p.eleve, dv.date(p.debut).toFormat("dd/MM HH:mm"),
    (p.notions ?? []).join(", "), (p.misconceptions ?? []).join(", "), p.file.link]));
```

## 🧩 Misconceptions les plus fréquentes (30 jours)

```dataviewjs
const depuis = dv.date("today").minus(dv.duration("30 days"));
const compte = {};
const eleves = {};
for (const p of dv.pages('"Aristote/Kiosques"').where(p => p.type === "session" && dv.date(p.debut) >= depuis)) {
  for (const m of p.misconceptions ?? []) {
    compte[m] = (compte[m] ?? 0) + 1;
    (eleves[m] ??= new Set()).add(p.eleve);
  }
}
const lignes = Object.entries(compte).sort((a, b) => b[1] - a[1])
  .map(([m, n]) => [m.startsWith("nouvelle:") ? `🆕 ${m}` : m, n, eleves[m].size]);
dv.table(["Misconception", "Sessions", "Élèves touchés"], lignes);
```

🆕 = étiquette proposée par l'IA, absente du catalogue du cours : à ajouter au cours si elle est pertinente.

## 📊 Réussite par notion (30 jours)

```dataviewjs
const depuis = dv.date("today").minus(dv.duration("30 days"));
const stats = {};
for (const p of dv.pages('"Aristote/Kiosques"').where(p => p.type === "session" && dv.date(p.debut) >= depuis)) {
  const texte = await dv.io.load(p.file.path);
  for (const [, notion, statut] of texte.matchAll(/^## Item \d+ — (\S+) — (VALIDÉ|VERROUILLÉ|EN COURS|ABANDONNÉ)/gm)) {
    const s = (stats[notion] ??= { valide: 0, verrou: 0, autre: 0 });
    if (statut === "VALIDÉ") s.valide++; else if (statut === "VERROUILLÉ") s.verrou++; else s.autre++;
  }
}
dv.table(["Notion", "Validés", "Verrouillés", "Taux de verrou"],
  Object.entries(stats).sort((a, b) => b[1].verrou - a[1].verrou).map(([n, s]) =>
    [n, s.valide, s.verrou, `${Math.round(100 * s.verrou / Math.max(1, s.valide + s.verrou))} %`]));
```

## 👥 Activité par élève (7 jours)

```dataviewjs
const noms = dv.page("Aristote/_Correspondance-eleves")?.eleves ?? {};
const depuis = dv.date("today").minus(dv.duration("7 days"));
const parEleve = {};
for (const p of dv.pages('"Aristote/Kiosques"').where(p => p.type === "session" && dv.date(p.debut) >= depuis)) {
  const e = (parEleve[p.eleve] ??= { sessions: 0, minutes: 0, valides: 0, verrous: 0 });
  e.sessions++; e.minutes += p.duree_min ?? 0; e.valides += p.items_valides ?? 0; e.verrous += p.items_verrouilles ?? 0;
}
dv.table(["Élève", "Sessions", "Minutes", "Items validés", "Items verrouillés"],
  Object.entries(parEleve).sort().map(([e, s]) => [noms[e] ?? e, s.sessions, Math.round(s.minutes), s.valides, s.verrous]));
```

## 📌 Notions fragiles (profils)

```dataview
TABLE WITHOUT ID eleve AS "Élève", kiosque AS "Kiosque", notions_fragiles AS "Notions fragiles", derniere_session AS "Dernière session"
FROM "Aristote/Kiosques"
WHERE type = "profil" AND length(notions_fragiles) > 0
SORT length(notions_fragiles) DESC
```

## 🖥️ État des kiosques

```dataview
TABLE WITHOUT ID kiosque AS "Kiosque", version, demarrage AS "Démarrage", cours, llm AS "LLM", ocr AS "OCR", imprimante AS "Imprimante", camera AS "Caméra"
FROM "Aristote/Kiosques"
WHERE type = "kiosque"
SORT kiosque
```
