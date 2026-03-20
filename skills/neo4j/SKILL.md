# SKILL: Neo4J — Querying Metabolic Networks with Cypher

## What This Tool Does
Once a GEM has been loaded into Neo4J via Neo4JSBML, you can query the entire
metabolic network as a graph using Cypher. This unlocks analyses that are
impossible or slow with matrix-based tools like COBRApy — path finding,
hub detection, dead-end analysis, and cross-model comparison.

The Neo4J MCP server (official Neo4J integration) exposes `run_query` and
`run_schema` tools. Use them directly with the Cypher examples below.

---

## Graph Schema (Neo4JSBML node/relationship types)

```
(:Reaction)   -[:HAS_REACTANT]->  (:Metabolite)
(:Reaction)   -[:HAS_PRODUCT]->   (:Metabolite)
(:Reaction)   -[:CATALYZED_BY]->  (:Gene)
(:Metabolite) -[:IN_COMPARTMENT]-> (:Compartment)
```

Key properties:
- `Reaction.id`, `Reaction.name`, `Reaction.subsystem`
- `Metabolite.id`, `Metabolite.name`, `Metabolite.formula`
- `Gene.id`, `Gene.name`

---

## Essential Cypher Queries

### 1. Check the model loaded correctly
```cypher
MATCH (r:Reaction) RETURN count(r) AS reactions;
MATCH (m:Metabolite) RETURN count(m) AS metabolites;
MATCH (g:Gene) RETURN count(g) AS genes;
```

### 2. Find all reactions involving a metabolite
```cypher
MATCH (m:Metabolite {id: "glc__D_c"})-[:HAS_REACTANT|HAS_PRODUCT]-(r:Reaction)
RETURN r.id, r.name, r.subsystem
ORDER BY r.subsystem;
```

### 3. Find dead-end metabolites
Metabolites that are only produced or only consumed indicate gaps in the model.
```cypher
// Only produced, never consumed
MATCH (m:Metabolite)
WHERE NOT (m)<-[:HAS_REACTANT]-(:Reaction)
  AND (m)<-[:HAS_PRODUCT]-(:Reaction)
RETURN m.id, m.name, m.formula
ORDER BY m.id;
```

### 4. Find hub reactions (highest metabolite connectivity)
```cypher
MATCH (r:Reaction)-[:HAS_REACTANT|HAS_PRODUCT]->(m:Metabolite)
WITH r, count(m) AS degree
ORDER BY degree DESC
LIMIT 20
RETURN r.id, r.name, r.subsystem, degree;
```

### 5. Shortest metabolic path between two metabolites
```cypher
MATCH path = shortestPath(
  (a:Metabolite {id: "glc__D_c"})-[*]-(b:Metabolite {id: "atp_c"})
)
RETURN [node IN nodes(path) | coalesce(node.id, '')] AS path_nodes,
       length(path) AS steps;
```

### 6. List all reactions in a subsystem
```cypher
MATCH (r:Reaction)
WHERE r.subsystem = "Glycolysis/Gluconeogenesis"
RETURN r.id, r.name
ORDER BY r.id;
```

### 7. Find reactions catalysed by a specific gene
```cypher
MATCH (g:Gene {id: "b0008"})<-[:CATALYZED_BY]-(r:Reaction)
RETURN r.id, r.name, r.subsystem;
```

### 8. Find all genes associated with a subsystem
```cypher
MATCH (r:Reaction)-[:CATALYZED_BY]->(g:Gene)
WHERE r.subsystem = "Oxidative Phosphorylation"
RETURN DISTINCT g.id, g.name
ORDER BY g.id;
```

### 9. Count reactions per subsystem (model coverage overview)
```cypher
MATCH (r:Reaction)
WHERE r.subsystem IS NOT NULL
RETURN r.subsystem, count(r) AS reaction_count
ORDER BY reaction_count DESC;
```

### 10. Find all metabolites in a compartment
```cypher
MATCH (m:Metabolite)-[:IN_COMPARTMENT]->(c:Compartment {id: "c"})
RETURN m.id, m.name, m.formula
ORDER BY m.id;
```

---

## Workflow: Load Model and Query

```
1. Ensure model.xml is at /models/{organism_id}/model.xml
   (written there by CarveMe via the shared Docker volume)

2. Push it into Neo4J using Neo4JSBML:
     docker exec sysbio-neo4jsbml neo4jsbml load \
       --input /models/{organism_id}/model.xml \
       --uri bolt://neo4j:7687 \
       --user neo4j --password changeme

3. Verify the load:
     MATCH (r:Reaction) RETURN count(r) AS reactions

4. Run analysis queries above via the Neo4J MCP server tools
   or the Neo4J Browser at http://localhost:7474
```

---

## BiGG Identifier Reference

Metabolite IDs use BiGG notation. The compartment suffix is always present:

| Suffix | Compartment   |
|--------|---------------|
| `_c`   | Cytoplasm     |
| `_e`   | Extracellular |
| `_p`   | Periplasm     |
| `_m`   | Mitochondria  |

Examples: `glc__D_c` (cytoplasmic D-glucose), `atp_c` (cytoplasmic ATP),
`o2_e` (extracellular oxygen).

If a query returns nothing, verify the ID format first:
```cypher
MATCH (m:Metabolite) RETURN m.id LIMIT 20;
```

---

## Important Notes

- Large path queries (`shortestPath` with no hop limit) can be slow on dense
  models. Add a bound to limit search depth: `-[*..10]-`.
- Load one model at a time unless you add a distinguishing property (e.g.
  `model_id`) to nodes during the Neo4JSBML import step.
- The Neo4J Browser (http://localhost:7474) is the fastest way to iterate
  on queries interactively before encoding them into agent tool calls.
- Neo4J MCP connection settings: URI `bolt://localhost:7687`,
  user `neo4j`, password from your `.env` file.
