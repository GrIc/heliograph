# MCP Tools Reference

## ask_expert

Ask a free-form question about the codebase. Returns a grounded answer with citations to source files. Use for architecture, debugging, and review questions.

### Input Schema

```json
{
  "type": "object",
  "required": [
    "question"
  ],
  "properties": {
    "question": {
      "type": "string",
      "minLength": 1,
      "maxLength": 2000
    },
    "scope": {
      "type": "string",
      "description": "Optional scope filter (module path or topic).",
      "maxLength": 200
    }
  },
  "additionalProperties": false
}
```

### Output Schema

```json
{
  "type": "object",
  "required": [
    "answer",
    "sources"
  ],
  "properties": {
    "answer": {
      "type": "string"
    },
    "sources": {
      "type": "array",
      "items": {
        "type": "object",
        "required": [
          "path",
          "line_start",
          "line_end"
        ],
        "properties": {
          "path": {
            "type": "string"
          },
          "line_start": {
            "type": "integer",
            "minimum": 1
          },
          "line_end": {
            "type": "integer",
            "minimum": 1
          },
          "score": {
            "type": "number"
          }
        },
        "additionalProperties": true
      }
    },
    "notes": {
      "type": "string"
    }
  },
  "additionalProperties": false
}
```

### Examples

#### Example 1

**Input**

```json
{
  "question": "How is authentication handled?"
}
```

**Output**

```json
{
  "answer": "JWT validation in src/auth/jwt.py:verify_jwt…",
  "sources": [
    {
      "path": "src/auth/jwt.py",
      "line_start": 12,
      "line_end": 60
    }
  ]
}
```

### Attributes

- `requires_citations`: `True`
- `auth_required`: `False`
- `rate_limit_per_minute`: `30`


## blame_plus

Run git blame on a specific line and enrich the result with the corresponding commit's enriched summary (intent, risk, modules).

### Input Schema

```json
{
  "type": "object",
  "required": [
    "filepath",
    "line"
  ],
  "properties": {
    "filepath": {
      "type": "string",
      "minLength": 1,
      "maxLength": 500
    },
    "line": {
      "type": "integer",
      "minimum": 1
    }
  },
  "additionalProperties": false
}
```

### Output Schema

```json
{
  "type": "object",
  "required": [
    "filepath",
    "line",
    "sources"
  ],
  "properties": {
    "filepath": {
      "type": "string"
    },
    "line": {
      "type": "integer"
    },
    "blame": {
      "type": "object",
      "additionalProperties": true
    },
    "enriched": {
      "type": "object",
      "additionalProperties": true
    },
    "sources": {
      "type": "array",
      "items": {
        "type": "object",
        "required": [
          "path",
          "line_start",
          "line_end"
        ],
        "properties": {
          "path": {
            "type": "string"
          },
          "line_start": {
            "type": "integer",
            "minimum": 1
          },
          "line_end": {
            "type": "integer",
            "minimum": 1
          },
          "score": {
            "type": "number"
          }
        },
        "additionalProperties": true
      }
    },
    "notes": {
      "type": "string"
    }
  },
  "additionalProperties": false
}
```

### Examples

#### Example 1

**Input**

```json
{
  "filepath": "src/main.py",
  "line": 1
}
```

**Output**

```json
{
  "filepath": "src/main.py",
  "line": 1,
  "sources": []
}
```

### Attributes

- `requires_citations`: `True`
- `auth_required`: `False`
- `rate_limit_per_minute`: `60`


## check_conventions

Check proposed code against inferred conventions (stub — Phase 5 trains rules).

### Input Schema

```json
{
  "type": "object",
  "additionalProperties": true
}
```

### Output Schema

```json
{
  "type": "object",
  "properties": {
    "status": {
      "type": "string"
    },
    "notes": {
      "type": "string"
    }
  },
  "additionalProperties": true
}
```

### Attributes

- `requires_citations`: `False`
- `auth_required`: `False`
- `rate_limit_per_minute`: `60`


## explain_change

Return the enriched summary of a single change identified by SHA (git) or fs-<timestamp> (filesystem sync).

### Input Schema

```json
{
  "type": "object",
  "required": [
    "change_id"
  ],
  "properties": {
    "change_id": {
      "type": "string",
      "minLength": 4,
      "maxLength": 200
    }
  },
  "additionalProperties": false
}
```

### Output Schema

```json
{
  "type": "object",
  "required": [
    "change",
    "sources"
  ],
  "properties": {
    "change": {
      "type": "object",
      "required": [
        "sha",
        "subject"
      ],
      "additionalProperties": true
    },
    "sources": {
      "type": "array",
      "items": {
        "type": "object",
        "required": [
          "path",
          "line_start",
          "line_end"
        ],
        "properties": {
          "path": {
            "type": "string"
          },
          "line_start": {
            "type": "integer",
            "minimum": 1
          },
          "line_end": {
            "type": "integer",
            "minimum": 1
          },
          "score": {
            "type": "number"
          }
        },
        "additionalProperties": true
      }
    },
    "notes": {
      "type": "string"
    }
  },
  "additionalProperties": false
}
```

### Examples

#### Example 1

**Input**

```json
{
  "change_id": "abc1234"
}
```

**Output**

```json
{
  "change": {
    "sha": "abc1234",
    "subject": "..."
  },
  "sources": []
}
```

### Attributes

- `requires_citations`: `True`
- `auth_required`: `False`
- `rate_limit_per_minute`: `60`


## explain_module

Return a concise summary of a module pulled from the L1/L2 synthesis documents, with citations to the source files.

### Input Schema

```json
{
  "type": "object",
  "required": [
    "module_id"
  ],
  "properties": {
    "module_id": {
      "type": "string",
      "minLength": 1,
      "maxLength": 200
    },
    "max_chars": {
      "type": "integer",
      "minimum": 100,
      "maximum": 4000,
      "default": 1500
    }
  },
  "additionalProperties": false
}
```

### Output Schema

```json
{
  "type": "object",
  "required": [
    "summary",
    "sources"
  ],
  "properties": {
    "summary": {
      "type": "string"
    },
    "sources": {
      "type": "array",
      "items": {
        "type": "object",
        "required": [
          "path",
          "line_start",
          "line_end"
        ],
        "properties": {
          "path": {
            "type": "string"
          },
          "line_start": {
            "type": "integer",
            "minimum": 1
          },
          "line_end": {
            "type": "integer",
            "minimum": 1
          },
          "score": {
            "type": "number"
          }
        },
        "additionalProperties": true
      }
    },
    "notes": {
      "type": "string"
    }
  },
  "additionalProperties": false
}
```

### Examples

#### Example 1

**Input**

```json
{
  "module_id": "src/auth"
}
```

**Output**

```json
{
  "summary": "Handles JWT…",
  "sources": [
    {
      "path": "src/auth/__init__.py",
      "line_start": 1,
      "line_end": 40
    }
  ]
}
```

### Attributes

- `requires_citations`: `True`
- `auth_required`: `False`
- `rate_limit_per_minute`: `60`


## find_code

Semantic search over the indexed codebase with optional filters. Returns ranked snippets with verifiable line-level citations.

### Input Schema

```json
{
  "type": "object",
  "required": [
    "intent"
  ],
  "properties": {
    "intent": {
      "type": "string",
      "minLength": 1,
      "maxLength": 500
    },
    "top_k": {
      "type": "integer",
      "minimum": 1,
      "maximum": 20,
      "default": 8
    },
    "filters": {
      "type": "object",
      "properties": {
        "module": {
          "type": "string"
        },
        "doc_level": {
          "type": "string",
          "enum": [
            "L0",
            "L1",
            "L2",
            "L3",
            "code",
            "context"
          ]
        },
        "content_type": {
          "type": "string",
          "enum": [
            "code",
            "codex_doc",
            "synthesis",
            "config",
            "test"
          ]
        }
      },
      "additionalProperties": false
    }
  },
  "additionalProperties": false
}
```

### Output Schema

```json
{
  "type": "object",
  "required": [
    "results",
    "sources"
  ],
  "properties": {
    "results": {
      "type": "array",
      "items": {
        "type": "object",
        "required": [
          "snippet",
          "score",
          "source"
        ],
        "properties": {
          "snippet": {
            "type": "string"
          },
          "score": {
            "type": "number"
          },
          "doc_level": {
            "type": "string"
          },
          "module": {
            "type": "string"
          },
          "source": {
            "type": "object",
            "required": [
              "path",
              "line_start",
              "line_end"
            ],
            "additionalProperties": true
          }
        },
        "additionalProperties": true
      }
    },
    "sources": {
      "type": "array",
      "items": {
        "type": "object",
        "required": [
          "path",
          "line_start",
          "line_end"
        ],
        "properties": {
          "path": {
            "type": "string"
          },
          "line_start": {
            "type": "integer",
            "minimum": 1
          },
          "line_end": {
            "type": "integer",
            "minimum": 1
          },
          "score": {
            "type": "number"
          }
        },
        "additionalProperties": true
      }
    },
    "notes": {
      "type": "string"
    }
  },
  "additionalProperties": false
}
```

### Examples

#### Example 1

**Input**

```json
{
  "intent": "JWT token validation",
  "top_k": 5
}
```

**Output**

```json
{
  "results": [
    {
      "snippet": "def verify_jwt(token):...",
      "score": 0.84,
      "source": {
        "path": "src/auth/jwt.py",
        "line_start": 12,
        "line_end": 30
      }
    }
  ],
  "sources": [
    {
      "path": "src/auth/jwt.py",
      "line_start": 12,
      "line_end": 30
    }
  ]
}
```

### Attributes

- `requires_citations`: `True`
- `auth_required`: `False`
- `rate_limit_per_minute`: `120`


## find_hub_modules

Return modules with the highest combined in/out degree in the knowledge graph. These are the 'hub' nodes — useful for impact analysis and high-blast-radius changes.

### Input Schema

```json
{
  "type": "object",
  "properties": {
    "limit": {
      "type": "integer",
      "minimum": 1,
      "maximum": 100,
      "default": 15
    },
    "min_degree": {
      "type": "integer",
      "minimum": 1,
      "default": 3
    },
    "type_filter": {
      "type": "string",
      "description": "Optional node type to filter (e.g. 'Module')."
    }
  },
  "additionalProperties": false
}
```

### Output Schema

```json
{
  "type": "object",
  "required": [
    "hubs",
    "sources"
  ],
  "properties": {
    "hubs": {
      "type": "array",
      "items": {
        "type": "object",
        "required": [
          "id",
          "degree"
        ],
        "properties": {
          "id": {
            "type": "string"
          },
          "label": {
            "type": "string"
          },
          "type": {
            "type": "string"
          },
          "in_degree": {
            "type": "integer"
          },
          "out_degree": {
            "type": "integer"
          },
          "degree": {
            "type": "integer"
          }
        },
        "additionalProperties": true
      }
    },
    "sources": {
      "type": "array",
      "items": {
        "type": "object",
        "required": [
          "path",
          "line_start",
          "line_end"
        ],
        "properties": {
          "path": {
            "type": "string"
          },
          "line_start": {
            "type": "integer",
            "minimum": 1
          },
          "line_end": {
            "type": "integer",
            "minimum": 1
          },
          "score": {
            "type": "number"
          }
        },
        "additionalProperties": true
      }
    },
    "notes": {
      "type": "string"
    }
  },
  "additionalProperties": false
}
```

### Examples

#### Example 1

**Input**

```json
{
  "limit": 5
}
```

**Output**

```json
{
  "hubs": [],
  "sources": []
}
```

### Attributes

- `requires_citations`: `True`
- `auth_required`: `False`
- `rate_limit_per_minute`: `30`


## find_similar

Find code chunks similar to a given reference. The reference may be a workspace file path, a class name, or a free-form description.

### Input Schema

```json
{
  "type": "object",
  "required": [
    "reference"
  ],
  "properties": {
    "reference": {
      "type": "string",
      "minLength": 1,
      "maxLength": 1000
    },
    "kind": {
      "type": "string",
      "enum": [
        "auto",
        "file",
        "description"
      ],
      "default": "auto"
    },
    "top_k": {
      "type": "integer",
      "minimum": 1,
      "maximum": 20,
      "default": 8
    }
  },
  "additionalProperties": false
}
```

### Output Schema

```json
{
  "type": "object",
  "required": [
    "results",
    "sources"
  ],
  "properties": {
    "results": {
      "type": "array",
      "items": {
        "type": "object",
        "required": [
          "snippet",
          "score",
          "source"
        ],
        "properties": {
          "snippet": {
            "type": "string"
          },
          "score": {
            "type": "number"
          },
          "source": {
            "type": "object",
            "additionalProperties": true
          }
        },
        "additionalProperties": true
      }
    },
    "sources": {
      "type": "array",
      "items": {
        "type": "object",
        "required": [
          "path",
          "line_start",
          "line_end"
        ],
        "properties": {
          "path": {
            "type": "string"
          },
          "line_start": {
            "type": "integer",
            "minimum": 1
          },
          "line_end": {
            "type": "integer",
            "minimum": 1
          },
          "score": {
            "type": "number"
          }
        },
        "additionalProperties": true
      }
    },
    "notes": {
      "type": "string"
    },
    "resolved_kind": {
      "type": "string"
    }
  },
  "additionalProperties": false
}
```

### Examples

#### Example 1

**Input**

```json
{
  "reference": "src/auth/jwt.py"
}
```

**Output**

```json
{
  "results": [],
  "sources": []
}
```

### Attributes

- `requires_citations`: `True`
- `auth_required`: `False`
- `rate_limit_per_minute`: `60`


## get_architecture_blueprint

Compose a structured implementation plan for a feature (similar features, modules, insertion points, risks). Deferred to Phase 5.

### Input Schema

```json
{
  "type": "object",
  "additionalProperties": true
}
```

### Output Schema

```json
{
  "type": "object",
  "properties": {
    "status": {
      "type": "string"
    },
    "notes": {
      "type": "string"
    }
  },
  "additionalProperties": true
}
```

### Attributes

- `requires_citations`: `False`
- `auth_required`: `False`
- `rate_limit_per_minute`: `60`


## get_callees

Return the set of modules/functions that the given symbol calls (outgoing edges in the knowledge graph).

### Input Schema

```json
{
  "type": "object",
  "required": [
    "symbol"
  ],
  "properties": {
    "symbol": {
      "type": "string",
      "minLength": 1,
      "maxLength": 200
    },
    "limit": {
      "type": "integer",
      "minimum": 1,
      "maximum": 100,
      "default": 25
    }
  },
  "additionalProperties": false
}
```

### Output Schema

```json
{
  "type": "object",
  "required": [
    "matched_entities",
    "callees",
    "sources"
  ],
  "properties": {
    "matched_entities": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": true
      }
    },
    "callees": {
      "type": "array",
      "items": {
        "type": "object",
        "required": [
          "id",
          "type"
        ],
        "properties": {
          "id": {
            "type": "string"
          },
          "label": {
            "type": "string"
          },
          "type": {
            "type": "string"
          },
          "relation": {
            "type": "string"
          }
        },
        "additionalProperties": true
      }
    },
    "sources": {
      "type": "array",
      "items": {
        "type": "object",
        "required": [
          "path",
          "line_start",
          "line_end"
        ],
        "properties": {
          "path": {
            "type": "string"
          },
          "line_start": {
            "type": "integer",
            "minimum": 1
          },
          "line_end": {
            "type": "integer",
            "minimum": 1
          },
          "score": {
            "type": "number"
          }
        },
        "additionalProperties": true
      }
    },
    "notes": {
      "type": "string"
    }
  },
  "additionalProperties": false
}
```

### Examples

#### Example 1

**Input**

```json
{
  "symbol": "main"
}
```

**Output**

```json
{
  "matched_entities": [],
  "callees": [],
  "sources": []
}
```

### Attributes

- `requires_citations`: `True`
- `auth_required`: `False`
- `rate_limit_per_minute`: `60`


## get_callers

Return the set of modules/functions that call (or depend on) a given symbol. Backed by the knowledge graph (Phase 2).

### Input Schema

```json
{
  "type": "object",
  "required": [
    "symbol"
  ],
  "properties": {
    "symbol": {
      "type": "string",
      "minLength": 1,
      "maxLength": 200
    },
    "limit": {
      "type": "integer",
      "minimum": 1,
      "maximum": 100,
      "default": 25
    }
  },
  "additionalProperties": false
}
```

### Output Schema

```json
{
  "type": "object",
  "required": [
    "matched_entities",
    "callers",
    "sources"
  ],
  "properties": {
    "matched_entities": {
      "type": "array",
      "items": {
        "type": "object",
        "required": [
          "id",
          "confidence"
        ],
        "properties": {
          "id": {
            "type": "string"
          },
          "confidence": {
            "type": "number"
          }
        },
        "additionalProperties": true
      }
    },
    "callers": {
      "type": "array",
      "items": {
        "type": "object",
        "required": [
          "id",
          "type"
        ],
        "properties": {
          "id": {
            "type": "string"
          },
          "label": {
            "type": "string"
          },
          "type": {
            "type": "string"
          },
          "relation": {
            "type": "string"
          }
        },
        "additionalProperties": true
      }
    },
    "sources": {
      "type": "array",
      "items": {
        "type": "object",
        "required": [
          "path",
          "line_start",
          "line_end"
        ],
        "properties": {
          "path": {
            "type": "string"
          },
          "line_start": {
            "type": "integer",
            "minimum": 1
          },
          "line_end": {
            "type": "integer",
            "minimum": 1
          },
          "score": {
            "type": "number"
          }
        },
        "additionalProperties": true
      }
    },
    "notes": {
      "type": "string"
    }
  },
  "additionalProperties": false
}
```

### Examples

#### Example 1

**Input**

```json
{
  "symbol": "verify_jwt"
}
```

**Output**

```json
{
  "matched_entities": [],
  "callers": [],
  "sources": [],
  "notes": "..."
}
```

### Attributes

- `requires_citations`: `True`
- `auth_required`: `False`
- `rate_limit_per_minute`: `60`


## get_coverage_report

Return the indexing quality / coverage report (Phase 4 stub).

### Input Schema

```json
{
  "type": "object",
  "additionalProperties": true
}
```

### Output Schema

```json
{
  "type": "object",
  "properties": {
    "status": {
      "type": "string"
    },
    "notes": {
      "type": "string"
    }
  },
  "additionalProperties": true
}
```

### Attributes

- `requires_citations`: `False`
- `auth_required`: `True`
- `rate_limit_per_minute`: `10`


## get_module_dependencies

Return the inbound, outbound, or both sets of dependencies for a module-level entity in the knowledge graph.

### Input Schema

```json
{
  "type": "object",
  "required": [
    "module"
  ],
  "properties": {
    "module": {
      "type": "string",
      "minLength": 1,
      "maxLength": 200
    },
    "direction": {
      "type": "string",
      "enum": [
        "in",
        "out",
        "both"
      ],
      "default": "both"
    },
    "limit": {
      "type": "integer",
      "minimum": 1,
      "maximum": 200,
      "default": 50
    }
  },
  "additionalProperties": false
}
```

### Output Schema

```json
{
  "type": "object",
  "required": [
    "module",
    "matches",
    "inbound",
    "outbound",
    "sources"
  ],
  "properties": {
    "module": {
      "type": "string"
    },
    "matches": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": true
      }
    },
    "inbound": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": true
      }
    },
    "outbound": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": true
      }
    },
    "sources": {
      "type": "array",
      "items": {
        "type": "object",
        "required": [
          "path",
          "line_start",
          "line_end"
        ],
        "properties": {
          "path": {
            "type": "string"
          },
          "line_start": {
            "type": "integer",
            "minimum": 1
          },
          "line_end": {
            "type": "integer",
            "minimum": 1
          },
          "score": {
            "type": "number"
          }
        },
        "additionalProperties": true
      }
    },
    "notes": {
      "type": "string"
    }
  },
  "additionalProperties": false
}
```

### Examples

#### Example 1

**Input**

```json
{
  "module": "src/auth"
}
```

**Output**

```json
{
  "module": "src/auth",
  "matches": [],
  "inbound": [],
  "outbound": [],
  "sources": []
}
```

### Attributes

- `requires_citations`: `True`
- `auth_required`: `False`
- `rate_limit_per_minute`: `60`


## guided_tour

Produce a recommended reading order for understanding a topic (stub).

### Input Schema

```json
{
  "type": "object",
  "additionalProperties": true
}
```

### Output Schema

```json
{
  "type": "object",
  "properties": {
    "status": {
      "type": "string"
    },
    "notes": {
      "type": "string"
    }
  },
  "additionalProperties": true
}
```

### Attributes

- `requires_citations`: `False`
- `auth_required`: `False`
- `rate_limit_per_minute`: `60`


## ingest_files

Index ad-hoc files into the RAG store (Phase 4 stub).

### Input Schema

```json
{
  "type": "object",
  "additionalProperties": true
}
```

### Output Schema

```json
{
  "type": "object",
  "properties": {
    "status": {
      "type": "string"
    },
    "notes": {
      "type": "string"
    }
  },
  "additionalProperties": true
}
```

### Attributes

- `requires_citations`: `False`
- `auth_required`: `True`
- `rate_limit_per_minute`: `10`


## list_tools

Return the catalog of all registered MCP tools, including their names, descriptions, and input schemas. Use this to discover what Agent Hub can do.

### Input Schema

```json
{
  "type": "object",
  "properties": {
    "include_schema": {
      "type": "boolean",
      "description": "If true, embed each tool's full JSON Schema.",
      "default": false
    }
  },
  "additionalProperties": false
}
```

### Output Schema

```json
{
  "type": "object",
  "required": [
    "tools",
    "count"
  ],
  "properties": {
    "count": {
      "type": "integer"
    },
    "tools": {
      "type": "array",
      "items": {
        "type": "object",
        "required": [
          "name",
          "description"
        ],
        "properties": {
          "name": {
            "type": "string"
          },
          "description": {
            "type": "string"
          },
          "requires_citations": {
            "type": "boolean"
          },
          "auth_required": {
            "type": "boolean"
          },
          "input_schema": {
            "type": "object"
          },
          "output_schema": {
            "type": "object"
          }
        },
        "additionalProperties": true
      }
    }
  },
  "additionalProperties": false
}
```

### Examples

#### Example 1

**Input**

```json
{}
```

**Output**

```json
{
  "count": 1,
  "tools": [
    {
      "name": "ping",
      "description": "..."
    }
  ]
}
```

### Attributes

- `requires_citations`: `False`
- `auth_required`: `False`
- `rate_limit_per_minute`: `120`


## locate_feature

Given a feature description in natural language, return ranked file paths where the feature is implemented, with confidence scores.

### Input Schema

```json
{
  "type": "object",
  "required": [
    "description"
  ],
  "properties": {
    "description": {
      "type": "string",
      "minLength": 1,
      "maxLength": 500
    },
    "top_k": {
      "type": "integer",
      "minimum": 1,
      "maximum": 15,
      "default": 5
    }
  },
  "additionalProperties": false
}
```

### Output Schema

```json
{
  "type": "object",
  "required": [
    "locations",
    "sources"
  ],
  "properties": {
    "locations": {
      "type": "array",
      "items": {
        "type": "object",
        "required": [
          "path",
          "confidence",
          "hits"
        ],
        "properties": {
          "path": {
            "type": "string"
          },
          "confidence": {
            "type": "number"
          },
          "hits": {
            "type": "integer"
          },
          "best_range": {
            "type": "object",
            "additionalProperties": true
          }
        },
        "additionalProperties": true
      }
    },
    "sources": {
      "type": "array",
      "items": {
        "type": "object",
        "required": [
          "path",
          "line_start",
          "line_end"
        ],
        "properties": {
          "path": {
            "type": "string"
          },
          "line_start": {
            "type": "integer",
            "minimum": 1
          },
          "line_end": {
            "type": "integer",
            "minimum": 1
          },
          "score": {
            "type": "number"
          }
        },
        "additionalProperties": true
      }
    },
    "notes": {
      "type": "string"
    }
  },
  "additionalProperties": false
}
```

### Examples

#### Example 1

**Input**

```json
{
  "description": "user login flow"
}
```

**Output**

```json
{
  "locations": [
    {
      "path": "src/auth/login.py",
      "confidence": 0.92,
      "hits": 3,
      "best_range": {
        "line_start": 10,
        "line_end": 80
      }
    }
  ],
  "sources": [
    {
      "path": "src/auth/login.py",
      "line_start": 10,
      "line_end": 80
    }
  ]
}
```

### Attributes

- `requires_citations`: `True`
- `auth_required`: `False`
- `rate_limit_per_minute`: `60`


## ping

Health check. Returns server status, uptime, and which subsystems (vector store, knowledge graph, temporal store) are available.

### Input Schema

```json
{
  "type": "object",
  "properties": {},
  "additionalProperties": false
}
```

### Output Schema

```json
{
  "type": "object",
  "required": [
    "status",
    "uptime_seconds",
    "subsystems"
  ],
  "properties": {
    "status": {
      "type": "string"
    },
    "uptime_seconds": {
      "type": "integer"
    },
    "subsystems": {
      "type": "object",
      "properties": {
        "vector_store": {
          "type": "boolean"
        },
        "knowledge_graph": {
          "type": "boolean"
        },
        "temporal_store": {
          "type": "boolean"
        }
      },
      "required": [
        "vector_store",
        "knowledge_graph",
        "temporal_store"
      ],
      "additionalProperties": false
    }
  },
  "additionalProperties": false
}
```

### Examples

#### Example 1

**Input**

```json
{}
```

**Output**

```json
{
  "status": "ok",
  "uptime_seconds": 42,
  "subsystems": {
    "vector_store": true,
    "knowledge_graph": false,
    "temporal_store": true
  }
}
```

### Attributes

- `requires_citations`: `False`
- `auth_required`: `False`
- `rate_limit_per_minute`: `300`


## preview_impact

Given a list of changed files or symbols, return weighted estimates of downstream impact via the knowledge graph.

### Input Schema

```json
{
  "type": "object",
  "required": [
    "changed"
  ],
  "properties": {
    "changed": {
      "type": "array",
      "items": {
        "type": "string",
        "minLength": 1
      },
      "minItems": 1,
      "maxItems": 50
    },
    "max_hops": {
      "type": "integer",
      "minimum": 1,
      "maximum": 4,
      "default": 2
    },
    "limit": {
      "type": "integer",
      "minimum": 1,
      "maximum": 100,
      "default": 30
    }
  },
  "additionalProperties": false
}
```

### Output Schema

```json
{
  "type": "object",
  "required": [
    "impacted",
    "sources"
  ],
  "properties": {
    "impacted": {
      "type": "array",
      "items": {
        "type": "object",
        "required": [
          "id",
          "weight",
          "hops"
        ],
        "properties": {
          "id": {
            "type": "string"
          },
          "label": {
            "type": "string"
          },
          "type": {
            "type": "string"
          },
          "weight": {
            "type": "number"
          },
          "hops": {
            "type": "integer"
          }
        },
        "additionalProperties": true
      }
    },
    "sources": {
      "type": "array",
      "items": {
        "type": "object",
        "required": [
          "path",
          "line_start",
          "line_end"
        ],
        "properties": {
          "path": {
            "type": "string"
          },
          "line_start": {
            "type": "integer",
            "minimum": 1
          },
          "line_end": {
            "type": "integer",
            "minimum": 1
          },
          "score": {
            "type": "number"
          }
        },
        "additionalProperties": true
      }
    },
    "notes": {
      "type": "string"
    }
  },
  "additionalProperties": false
}
```

### Examples

#### Example 1

**Input**

```json
{
  "changed": [
    "src/auth/jwt.py"
  ],
  "max_hops": 2
}
```

**Output**

```json
{
  "impacted": [],
  "sources": [],
  "notes": "..."
}
```

### Attributes

- `requires_citations`: `True`
- `auth_required`: `False`
- `rate_limit_per_minute`: `30`


## read_file

Read a file from the workspace directory. Refuses path traversal and returns size + content. Useful for agents that need raw source.

### Input Schema

```json
{
  "type": "object",
  "required": [
    "filepath"
  ],
  "properties": {
    "filepath": {
      "type": "string",
      "minLength": 1,
      "maxLength": 500
    },
    "max_bytes": {
      "type": "integer",
      "minimum": 1,
      "maximum": 2000000,
      "default": 500000
    }
  },
  "additionalProperties": false
}
```

### Output Schema

```json
{
  "type": "object",
  "required": [
    "filepath",
    "content",
    "size"
  ],
  "properties": {
    "filepath": {
      "type": "string"
    },
    "content": {
      "type": "string"
    },
    "size": {
      "type": "integer"
    },
    "truncated": {
      "type": "boolean"
    }
  },
  "additionalProperties": false
}
```

### Examples

#### Example 1

**Input**

```json
{
  "filepath": "src/main.py"
}
```

**Output**

```json
{
  "filepath": "src/main.py",
  "content": "...",
  "size": 1234,
  "truncated": false
}
```

### Attributes

- `requires_citations`: `False`
- `auth_required`: `False`
- `rate_limit_per_minute`: `120`


## recent_changes

Return recent enriched changes with intent classification, summaries, and affected modules. Sourced from the temporal store (git commits or filesystem sync snapshots).

### Input Schema

```json
{
  "type": "object",
  "properties": {
    "limit": {
      "type": "integer",
      "minimum": 1,
      "maximum": 200,
      "default": 25
    },
    "intent": {
      "type": "string",
      "enum": [
        "feature",
        "fix",
        "refactor",
        "chore",
        "docs",
        "test",
        "unknown"
      ]
    },
    "module": {
      "type": "string",
      "maxLength": 200
    }
  },
  "additionalProperties": false
}
```

### Output Schema

```json
{
  "type": "object",
  "required": [
    "changes",
    "sources"
  ],
  "properties": {
    "changes": {
      "type": "array",
      "items": {
        "type": "object",
        "required": [
          "sha",
          "subject"
        ],
        "properties": {
          "sha": {
            "type": "string"
          },
          "author": {
            "type": "string"
          },
          "date": {
            "type": "string"
          },
          "subject": {
            "type": "string"
          },
          "intent": {
            "type": "string"
          },
          "summary": {
            "type": "string"
          },
          "modules_affected": {
            "type": "array",
            "items": {
              "type": "string"
            }
          },
          "risk_score": {
            "type": "number"
          }
        },
        "additionalProperties": true
      }
    },
    "sources": {
      "type": "array",
      "items": {
        "type": "object",
        "required": [
          "path",
          "line_start",
          "line_end"
        ],
        "properties": {
          "path": {
            "type": "string"
          },
          "line_start": {
            "type": "integer",
            "minimum": 1
          },
          "line_end": {
            "type": "integer",
            "minimum": 1
          },
          "score": {
            "type": "number"
          }
        },
        "additionalProperties": true
      }
    },
    "notes": {
      "type": "string"
    }
  },
  "additionalProperties": false
}
```

### Examples

#### Example 1

**Input**

```json
{
  "limit": 5
}
```

**Output**

```json
{
  "changes": [],
  "sources": [],
  "notes": "..."
}
```

### Attributes

- `requires_citations`: `True`
- `auth_required`: `False`
- `rate_limit_per_minute`: `60`


## reindex

Trigger a full reindex of the workspace (Phase 4 stub).

### Input Schema

```json
{
  "type": "object",
  "additionalProperties": true
}
```

### Output Schema

```json
{
  "type": "object",
  "properties": {
    "status": {
      "type": "string"
    },
    "notes": {
      "type": "string"
    }
  },
  "additionalProperties": true
}
```

### Attributes

- `requires_citations`: `False`
- `auth_required`: `True`
- `rate_limit_per_minute`: `5`


## search_graph

Search the knowledge graph for an entity by name. Returns the matched entities, their neighbors within max_hops, and a textual subgraph summary.

### Input Schema

```json
{
  "type": "object",
  "required": [
    "entity"
  ],
  "properties": {
    "entity": {
      "type": "string",
      "minLength": 1,
      "maxLength": 200
    },
    "max_hops": {
      "type": "integer",
      "minimum": 1,
      "maximum": 4,
      "default": 2
    }
  },
  "additionalProperties": false
}
```

### Output Schema

```json
{
  "type": "object",
  "required": [
    "entity",
    "matches",
    "sources"
  ],
  "properties": {
    "entity": {
      "type": "string"
    },
    "matches": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "id": {
            "type": "string"
          },
          "confidence": {
            "type": "number"
          }
        },
        "required": [
          "id",
          "confidence"
        ],
        "additionalProperties": true
      }
    },
    "neighbor_count": {
      "type": "integer"
    },
    "summary": {
      "type": "string"
    },
    "sources": {
      "type": "array",
      "items": {
        "type": "object",
        "required": [
          "path",
          "line_start",
          "line_end"
        ],
        "properties": {
          "path": {
            "type": "string"
          },
          "line_start": {
            "type": "integer",
            "minimum": 1
          },
          "line_end": {
            "type": "integer",
            "minimum": 1
          },
          "score": {
            "type": "number"
          }
        },
        "additionalProperties": true
      }
    },
    "notes": {
      "type": "string"
    }
  },
  "additionalProperties": false
}
```

### Examples

#### Example 1

**Input**

```json
{
  "entity": "UserService"
}
```

**Output**

```json
{
  "entity": "UserService",
  "matches": [],
  "sources": []
}
```

### Attributes

- `requires_citations`: `True`
- `auth_required`: `False`
- `rate_limit_per_minute`: `60`


## shortest_path

Shortest path in the call graph between two symbols (Phase 4 stub).

### Input Schema

```json
{
  "type": "object",
  "additionalProperties": true
}
```

### Output Schema

```json
{
  "type": "object",
  "properties": {
    "status": {
      "type": "string"
    },
    "notes": {
      "type": "string"
    }
  },
  "additionalProperties": true
}
```

### Attributes

- `requires_citations`: `False`
- `auth_required`: `False`
- `rate_limit_per_minute`: `60`


## what_changed_here

Return the timeline of enriched commits that touched a specific file, newest first.

### Input Schema

```json
{
  "type": "object",
  "required": [
    "filepath"
  ],
  "properties": {
    "filepath": {
      "type": "string",
      "minLength": 1,
      "maxLength": 500
    },
    "limit": {
      "type": "integer",
      "minimum": 1,
      "maximum": 100,
      "default": 25
    }
  },
  "additionalProperties": false
}
```

### Output Schema

```json
{
  "type": "object",
  "required": [
    "filepath",
    "history",
    "sources"
  ],
  "properties": {
    "filepath": {
      "type": "string"
    },
    "history": {
      "type": "array",
      "items": {
        "type": "object",
        "required": [
          "sha",
          "subject"
        ],
        "properties": {
          "sha": {
            "type": "string"
          },
          "author": {
            "type": "string"
          },
          "date": {
            "type": "string"
          },
          "subject": {
            "type": "string"
          },
          "intent": {
            "type": "string"
          },
          "summary": {
            "type": "string"
          },
          "risk_score": {
            "type": "number"
          }
        },
        "additionalProperties": true
      }
    },
    "sources": {
      "type": "array",
      "items": {
        "type": "object",
        "required": [
          "path",
          "line_start",
          "line_end"
        ],
        "properties": {
          "path": {
            "type": "string"
          },
          "line_start": {
            "type": "integer",
            "minimum": 1
          },
          "line_end": {
            "type": "integer",
            "minimum": 1
          },
          "score": {
            "type": "number"
          }
        },
        "additionalProperties": true
      }
    },
    "notes": {
      "type": "string"
    }
  },
  "additionalProperties": false
}
```

### Examples

#### Example 1

**Input**

```json
{
  "filepath": "src/main.py"
}
```

**Output**

```json
{
  "filepath": "src/main.py",
  "history": [],
  "sources": []
}
```

### Attributes

- `requires_citations`: `True`
- `auth_required`: `False`
- `rate_limit_per_minute`: `60`


## why_does_this_exist

Return the oldest enriched commit that touched a file matching the given path, with its summary — typically the commit that introduced it.

### Input Schema

```json
{
  "type": "object",
  "required": [
    "filepath"
  ],
  "properties": {
    "filepath": {
      "type": "string",
      "minLength": 1,
      "maxLength": 500
    }
  },
  "additionalProperties": false
}
```

### Output Schema

```json
{
  "type": "object",
  "required": [
    "filepath",
    "sources"
  ],
  "properties": {
    "filepath": {
      "type": "string"
    },
    "introducing_commit": {
      "type": "object",
      "additionalProperties": true
    },
    "sources": {
      "type": "array",
      "items": {
        "type": "object",
        "required": [
          "path",
          "line_start",
          "line_end"
        ],
        "properties": {
          "path": {
            "type": "string"
          },
          "line_start": {
            "type": "integer",
            "minimum": 1
          },
          "line_end": {
            "type": "integer",
            "minimum": 1
          },
          "score": {
            "type": "number"
          }
        },
        "additionalProperties": true
      }
    },
    "notes": {
      "type": "string"
    }
  },
  "additionalProperties": false
}
```

### Examples

#### Example 1

**Input**

```json
{
  "filepath": "src/main.py"
}
```

**Output**

```json
{
  "filepath": "src/main.py",
  "sources": []
}
```

### Attributes

- `requires_citations`: `True`
- `auth_required`: `False`
- `rate_limit_per_minute`: `60`


## workspace_tree

Return a text rendering of the workspace directory tree up to a given depth, with common build/vendor directories skipped.

### Input Schema

```json
{
  "type": "object",
  "properties": {
    "max_depth": {
      "type": "integer",
      "minimum": 1,
      "maximum": 8,
      "default": 3
    },
    "subdir": {
      "type": "string",
      "default": ""
    }
  },
  "additionalProperties": false
}
```

### Output Schema

```json
{
  "type": "object",
  "required": [
    "root",
    "tree"
  ],
  "properties": {
    "root": {
      "type": "string"
    },
    "tree": {
      "type": "string"
    }
  },
  "additionalProperties": false
}
```

### Examples

#### Example 1

**Input**

```json
{
  "max_depth": 2
}
```

**Output**

```json
{
  "root": "workspace",
  "tree": "..."
}
```

### Attributes

- `requires_citations`: `False`
- `auth_required`: `False`
- `rate_limit_per_minute`: `60`

