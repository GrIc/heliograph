# 01 — La thèse, recadrée

## Le problème, en une phrase

**Un agent IA qui code dans un gros repo passe 80% de son temps à chercher du
contexte qu'il oublie d'une session à l'autre, et finit par inventer ce qu'il
ne trouve pas.**

C'est ça qu'on attaque. Pas la "transformation digitale du code". Pas la
"productivité 10x". Juste : *donner à l'agent un meilleur cerveau pour ce repo
précis*.

---

## Les 5 frictions concrètes du dev qui code avec agents

| # | Friction | Symptôme observable | Ce qu'Agent Hub doit livrer |
|---|----------|---------------------|------------------------------|
| 1 | **Découverte** | Agent re-grep les mêmes choses, ouvre 12 fichiers pour comprendre 1 flow | `locate_feature`, `find_similar`, `expert_ask` rapides + cités |
| 2 | **Architecture mentale** | Agent ignore les conventions, casse les couches, duplique du code existant | Pyramide L0→L3 + `discover_patterns` |
| 3 | **Impact d'un changement** | Agent modifie 1 fonction sans voir les 40 callers | `get_callers`, `preview_impact` + graphe à jour |
| 4 | **Historique / pourquoi** | Agent ne sait pas pourquoi le code est comme ça, redéfait des décisions | `why_does_this_exist`, `what_changed_here`, `blame+` |
| 5 | **Boucle d'écho** | Agent fait une PR, le reviewer (humain ou autre agent) refait tout le contexte from scratch | Sortie MCP structurée + cache contextuel partageable |

Si Agent Hub réduit *mesurablement* ces 5 frictions, il est utile.
Sinon, il est mort.

---

## Pourquoi un outil dédié, pas juste un long-context

Argument fréquent : "Gemini fait 2M tokens, dumpe ton repo dedans, problème
réglé". Réponses :

1. **Coût** — 2M tokens × N requêtes × N devs = ruineux, même en self-hosted
   sur GPU local (latence + RAM KV cache).
2. **Latence** — TTFT (time-to-first-token) sur 1M+ context = 5-30s. Inutile en
   boucle interactive.
3. **Précision** — "needle-in-haystack" reste imparfait au-delà de 200k tokens
   pour la majorité des modèles. Le RAG + graphe pré-distille mieux.
4. **Fraîcheur** — un long-context perd l'état git temps réel. Index incrémental
   le gagne.
5. **Multi-agent** — si tu as 4 sub-agents qui travaillent en parallèle, tu ne
   veux PAS recharger 2M tokens par appel. Tu veux un service de contexte.

Conclusion : long-context et Agent Hub ne sont pas en compétition. Agent Hub
*prépare* le contexte que tu mettras dans la fenêtre, quelle qu'en soit la
taille.

---

## Définition de "ça marche"

Agent Hub réussit quand, sur un dépôt > 100k LOC inconnu de l'agent :

- L'agent répond à "où est implémentée la feature X" en **< 5s** avec
  citations exactes (path + lignes).
- L'agent propose une modification correcte au **premier essai** dans
  **≥ 70% des tickets** d'un benchmark style SWE-bench Lite.
- Le coût en tokens d'une session de codage est **divisé par ≥ 3** vs
  approche "balance tout dans le context".
- Le dev garde l'outil branché **2 semaines après l'install** (rétention =
  le seul vrai signal d'utilité).

Tout le reste — verification formelle, world model, swarms, etc. — n'a
d'intérêt que s'il fait bouger ces 4 chiffres.
