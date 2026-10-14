<%*
/*
 * Templater : crée une note « Données … » contenant, en texte brut et pseudonymisé, toutes les sessions
 * d'une période + la structure du cours. Les prompts Text Generator s'appliquent ensuite à cette note.
 * Prérequis : plugins Templater et Dataview.
 */
const dv = app.plugins.plugins.dataview?.api;
if (!dv) { new Notice("Le plugin Dataview est requis."); return; }
const jours = Number(await tp.system.prompt("Période à analyser (en jours)", "14")) || 14;
const depuis = moment().subtract(jours, "days");
const sessions = dv.pages('"Aristote/Kiosques"')
  .where(p => p.type === "session" && moment(String(p.debut)).isAfter(depuis))
  .sort(p => String(p.debut), "asc");

const garder = /^(## Item |\*\*Question\*\*|- \*\*Tentative|  > |- \*\*Diagnostic|- \*\*Prérequis|- \*\*Remédiation)/;
let sortie = `---\ntype: donnees-analyse\nperiode_jours: ${jours}\ngenere: ${moment().format("YYYY-MM-DD HH:mm")}\nsessions: ${sessions.length}\n---\n`;
sortie += `# Données Aristote — ${depuis.format("DD/MM")} → ${moment().format("DD/MM/YYYY")} (pseudonymisées)\n\n`;

sortie += `## Structure du cours\n\n`;
const cours = dv.pages('"Aristote/Kiosques"').where(p => p.type === "cours").first();
if (cours) {
  const texteCours = await app.vault.adapter.read(cours.file.path);
  sortie += texteCours.replace(/^---[\s\S]*?---\n/, "").replace(/^# .*\n/m, "").replace(/^## /gm, "### ") + "\n";
}

sortie += `## Sessions\n\n`;
for (const p of sessions) {
  const texte = await app.vault.adapter.read(p.file.path);
  const corps = texte.replace(/^---[\s\S]*?---\n/, "").split("\n").filter(l => garder.test(l));
  sortie += `### Session ${p.eleve} · ${p.kiosque} · ${moment(String(p.debut)).format("YYYY-MM-DD HH:mm")} · ${p.duree_min ?? "?"} min\n`;
  sortie += corps.map(l => l.replace(/^## /, "#### ")).join("\n") + "\n\n";
}

const nom = `Données ${moment().format("YYYY-MM-DD")} (${jours} j)`;
const dossier = app.vault.getAbstractFileByPath("Aristote/Analyses") ?? await app.vault.createFolder("Aristote/Analyses");
await tp.file.create_new(sortie, nom, true, dossier);
new Notice(`${sessions.length} sessions exportées dans « Aristote/Analyses/${nom} ».`);
%>
