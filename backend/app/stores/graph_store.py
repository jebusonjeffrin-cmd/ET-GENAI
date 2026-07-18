from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class GraphNode:
    id: str
    label: str  # "Equipment" | "Document" | "Person" | "Unit" | ...
    properties: dict = field(default_factory=dict)


@dataclass
class GraphEdge:
    source_id: str
    target_id: str
    relationship: str  # "MENTIONS" | "PART_OF" | "PERFORMED_ON" | ...


class GraphStore(Protocol):
    def upsert_node(self, node: GraphNode) -> None: ...
    def upsert_edge(self, edge: GraphEdge) -> None: ...
    def get_equipment_360(self, tag: str) -> dict: ...
    def stats(self) -> dict: ...


class FakeGraphStore:
    """In-memory graph store. Backs every unit/integration test — no Neo4j
    required to run `pytest`."""

    def __init__(self) -> None:
        self.nodes: dict[str, GraphNode] = {}
        self.edges: list[GraphEdge] = []

    def upsert_node(self, node: GraphNode) -> None:
        self.nodes[node.id] = node

    def upsert_edge(self, edge: GraphEdge) -> None:
        self.edges.append(edge)

    def get_equipment_360(self, tag: str) -> dict:
        node_id = f"Equipment:{tag}"
        node = self.nodes.get(node_id)
        if not node:
            return {"equipment": None, "linked": []}
        linked = [
            {
                "relationship": e.relationship,
                "node": self.nodes.get(e.source_id if e.target_id == node_id else e.target_id),
            }
            for e in self.edges
            if e.source_id == node_id or e.target_id == node_id
        ]
        return {"equipment": node, "linked": linked}

    def stats(self) -> dict:
        by_label: dict[str, int] = {}
        for node in self.nodes.values():
            by_label[node.label] = by_label.get(node.label, 0) + 1
        return {"node_counts": by_label, "edge_count": len(self.edges)}


class Neo4jGraphStore:
    """Real adapter. Wire up once Neo4j is reachable (docker-compose, or the
    deployment machine) — not required for Phase 1 unit tests, which run
    entirely against FakeGraphStore."""

    def __init__(self, uri: str, user: str, password: str) -> None:
        from neo4j import GraphDatabase

        self._driver = GraphDatabase.driver(uri, auth=(user, password))

    def upsert_node(self, node: GraphNode) -> None:
        with self._driver.session() as session:
            session.run(
                f"MERGE (n:{node.label} {{id: $id}}) SET n += $props",
                id=node.id,
                props=node.properties,
            )

    def upsert_edge(self, edge: GraphEdge) -> None:
        with self._driver.session() as session:
            session.run(
                "MATCH (a {id: $source}), (b {id: $target}) "
                f"MERGE (a)-[:{edge.relationship}]->(b)",
                source=edge.source_id,
                target=edge.target_id,
            )

    def get_equipment_360(self, tag: str) -> dict:
        with self._driver.session() as session:
            result = session.run(
                "MATCH (e:Equipment {id: $id})-[r]-(n) RETURN e, type(r) AS rel, n",
                id=f"Equipment:{tag}",
            )
            linked = [{"relationship": rec["rel"], "node": dict(rec["n"])} for rec in result]
            return {"equipment": tag, "linked": linked}

    def stats(self) -> dict:
        with self._driver.session() as session:
            node_result = session.run("MATCH (n) RETURN labels(n)[0] AS label, count(*) AS c")
            node_counts = {rec["label"]: rec["c"] for rec in node_result}
            edge_result = session.run("MATCH ()-[r]->() RETURN count(r) AS c")
            edge_record = edge_result.single()
            edge_count = edge_record["c"] if edge_record is not None else 0
            return {"node_counts": node_counts, "edge_count": edge_count}
