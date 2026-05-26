# 06 — Verification : re-scoper la Phase 6 dans le réel

## Le problème avec le scope actuel

`docs/roadmap/06_PHASE_VERIFIABLE_AUTONOMY.md` promet :

> *"Une preuve mathématique (via SMT solver Z3) qu'un changement respecte les
> invariants du codebase, avec contre-exemple si violation."*

Soyons honnêtes : **vérifier formellement du code applicatif réel via Z3 est
un problème de recherche depuis 30 ans, toujours pas résolu en général.**

Ce qui marche en pratique avec Z3 :

- Vérifier des contraintes sur **types simples** (ints, booléens, arrays
  bornés).
- Vérifier la **logique de bouts de code isolés** (un petit DSL, une
  fonction pure, une transition d'état machine).
- Vérifier des **politiques déclaratives** ("ce endpoint doit avoir
  `@auth_required`").

Ce qui ne marche **pas** :

- Vérifier la sémantique d'un code Python/JS arbitraire (effets de bord,
  monkey-patching, types dynamiques).
- Vérifier des invariants temporels sur l'état d'un système distribué.
- Garantir l'absence de race conditions ou de fuites mémoire dans un
  framework async.

Vendre Phase 6 sur la première promesse = sous-livraison garantie.

---

## Le re-scope : vérification **utile et tractable**

Trois familles de vérification ont un ROI réel en outil dev :

### A. Vérification de politiques déclaratives (le Z3 utile)

Des règles **structurelles** sur le graphe / l'AST, exprimées en YAML :

```yaml
- id: auth-required-on-admin
  pattern: "function decorated with @admin_route"
  must_also_have: "@auth_required OR @public_admin"
  severity: error

- id: no-raw-sql-in-services
  pattern: "service/**/*.py contains 'cursor.execute('"
  exception: "service/internal_migrations/*"
  severity: warning
```

C'est ce que font Semgrep, OpenRewrite, Coccinelle, etc. Le solveur n'a pas
besoin de Z3 pour ça — un moteur de pattern AST suffit. **Honnêteté** : on
n'a pas besoin de SMT pour 90% de ce que les users vont écrire comme
règles.

→ Adopter **Semgrep** comme moteur de base (open source, marche sur 30+
langages, communauté de règles). Wrapper MCP minimal.

### B. Tracking de capabilities et effets

Inspiré WebAssembly Components, Roc lang, Koka effects, capability-safe
languages.

Idée : annoter chaque fonction par les **catégories d'effet** qu'elle
exerce :

```
fn process_order :: [DB.read, DB.write, Net.http, Log]
```

L'agent peut alors répondre à :

- "Cette fonction touche-t-elle la DB ?" → trivial.
- "Si je modifie X, est-ce que ça ajoute un nouvel effet IO inattendu ?"
  → diff de capabilities entre versions.
- "Quelles fonctions exercent `Net.http` sur le chemin de la requête login ?"
  → query graphe + effets.

**Calculable statiquement** par traversée du call graph (Phase 2 actuelle)
+ table de stdlib annotée (open ou Net ou DB selon module appelé).

Bénéfice user direct, sans LLM, sans Z3. Latence ms.

### C. Vérification de patch contre tests existants (le pragmatique)

Ce que les devs font déjà à la main :

1. Patch proposé par l'agent.
2. `git apply` dans un sandbox.
3. Tour de tests minimal ciblé sur les fichiers touchés (via `pytest --co`
   + `git diff`).
4. Si rouge → renvoyer au LLM avec la trace d'erreur.
5. Si vert → annoter le patch "passes targeted tests".

Outil MCP `verify_patch_against_tests` : déterministe, mesurable, utile.
Pas besoin de prouver quoi que ce soit formellement.

---

## Ce qui DISPARAÎT de la Phase 6

| Promesse historique | Verdict | Remplacé par |
|---------------------|---------|--------------|
| "Preuve SMT que le changement respecte les invariants" | Trop large | Politique YAML + Semgrep |
| "Counterexample du solveur" | Vrai pour règles simples, trompeur en général | Trace d'échec de règle Semgrep ou trace de test |
| "10 politiques shipped by default" | Garder, mais via Semgrep registry | Idem |
| "Zero false-positive guarantee" | Marketing irréaliste | "False positive rate < X% mesuré sur eval set" |
| "Federated avec Chiasmus MCP" | Niche, peu maintenue | Z3 en option pour règles arithmétiques uniquement |

---

## Plan minimum viable (4 sem au lieu de 9)

| Sem | Livrable |
|-----|----------|
| 1 | Sub-agent `ah-verify` wrappant Semgrep, MCP tool `check_policies(paths)` |
| 2 | Système d'annotations effets/capabilities (stdlib seeds Python + JS), MCP tool `get_effects(fn)` |
| 3 | MCP tool `verify_patch_against_tests` avec sandbox `git worktree` + pytest/jest |
| 4 | Intégration dans eval harness (doc 07), mesure baseline vs sans-verif |

Si le bénéfice mesuré au harnais est faible, on s'arrête là. Si fort, on
investit plus (règles custom DSL, SMT pour règles arithmétiques, etc.).
