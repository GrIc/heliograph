# 04 — Indexation incrémentale : le détail qui change tout

## Pourquoi c'est critique

Un dev sauvegarde un fichier toutes les ~30 secondes en moyenne pendant une
session active. Si l'index met 60s à se rafraîchir, l'agent travaille
**toujours** sur une vue périmée.

Conséquences observées en pratique :

- Agent suggère d'importer une fonction qu'il vient de renommer 10s plus tôt.
- `find_code "useAuth"` retourne l'ancien fichier supprimé.
- Citations pointent vers des lignes décalées.

C'est *la* fuite de confiance n°1 d'un outil de contexte. Plus aucune autre
amélioration ne compte si l'index est en retard.

---

## L'état actuel

Le repo a `context/.ingest_hashes.json` — donc déjà une forme de tracking de
hash. Bien. Mais :

- Granularité = fichier entier (un changement de 1 ligne re-embed tout le
  fichier).
- Pas de réutilisation cross-fichier (deux fichiers contenant la même fonction
  copiée = double embedding).
- Pas de garantie de fraîcheur côté MCP tool (le tool peut répondre pendant
  qu'un reindex tourne).

---

## Cible : Merkle + content-addressed chunks

### Concept

1. **Chunker déterministe** au niveau symbole (fonction, classe, bloc top-level)
   plutôt qu'au niveau ligne ou fichier.
2. Chaque chunk reçoit un **content hash** (sha256 du texte normalisé).
3. L'embedding est stocké **indexé par hash**, pas par path. Donc :
   - Renommer un fichier sans changer son contenu = 0 re-embedding.
   - Déplacer une fonction d'un fichier à l'autre = 0 re-embedding.
   - Code copié-collé identique = 1 seul embedding partagé.
4. Un **arbre de Merkle** par dossier permet en `O(log n)` de détecter quels
   sous-arbres ont bougé entre deux scans.

### Effet mesurable attendu

- Reindex de 100k LOC après edit d'1 fonction : **< 200ms** (vs ~5-30s pour un
  reindex naïf).
- Reindex initial sur cold cache : inchangé (toujours dominé par embedding API).
- Reindex après `git rebase` qui touche 30 fichiers : seuls les chunks
  effectivement modifiés re-embed, pas les 30 fichiers entiers.

---

## Pipeline

```
File watcher (watchdog ou fsevents)
        │
        ▼
For each changed file:
   1. Parse tree-sitter → liste de chunks (sym_name, content, span)
   2. Pour chaque chunk : compute sha256(normalize(content))
   3. Diff vs hashes précédents → set(new), set(deleted), set(unchanged)
   4. Embedding API call uniquement sur new
   5. Update store :
        - upsert(hash → embedding)        # déduplique automatiquement
        - upsert(file_path → [hash, ...])  # mapping logique
        - drop des references vers deleted hashes orphelins (GC périodique)
   6. Update Merkle tree
```

### Normalisation du contenu (avant hash)

Pour maximiser la déduplication :

- Strip trailing whitespace.
- Normaliser les line endings (LF).
- **Ne pas** strip les commentaires (ils changent le sens pour un LLM).
- **Ne pas** reformater (sinon hash instable selon prettier/black version).

---

## Garanties de fraîcheur côté MCP

Chaque réponse de tool MCP inclut un header :

```json
{
  "answer": "...",
  "sources": [...],
  "index_version": "sha256:abc123...",     // root du Merkle au moment de la query
  "index_age_ms": 142,                     // âge max d'un chunk dans la réponse
  "stale_files": []                        // fichiers modifiés mais pas encore réindexés
}
```

Permet au client (Claude Code, etc.) de décider :

- Si `index_age_ms` > seuil, attendre / réessayer.
- Si `stale_files` contient un fichier que l'agent vient d'éditer, ignorer la
  réponse ou marquer "outdated".

---

## Choix techniques recommandés

| Composant | Choix | Pourquoi |
|-----------|-------|----------|
| Chunker | Tree-sitter au niveau `function_definition` / `class_definition` | Déjà dépendance du projet, langage-agnostique |
| Hash | SHA-256 truncated to 16 bytes | Suffisant pour dédup, compact |
| Store embeddings | Chroma actuel **ou** LanceDB | LanceDB plus rapide sur upsert massif, mais Chroma OK pour MVP |
| Merkle | Implé maison, ~150 lignes Python | Pas de dep externe nécessaire |
| Watch | `watchdog` (déjà dans `watch.py` probablement) | Standard, multiplateforme |

---

## Ce qu'on NE fait pas

- Pas de "ré-embedding nocturne complet de sécurité". Si la pipeline est
  correcte, c'est inutile et ça gaspille du budget API.
- Pas de versioning d'index style "snapshot par commit". Trop lourd, peu
  utile. On a un seul index live, c'est tout.
- Pas de support pour fichiers > 200KB (config actuelle `max_file_size`).
  Garder cette limite — au-delà, c'est probablement du code généré ou un
  asset.
