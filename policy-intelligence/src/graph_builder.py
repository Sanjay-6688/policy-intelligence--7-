"""
graph_builder.py
------------------
Step 5 of the pipeline: assemble the obligation knowledge graph.

Nodes = individual obligations (one per extracted clause)
Edges = relationships between obligations (CONFLICT / REDUNDANT / COMPLEMENTARY)
        UNRELATED pairs are kept in relationships.json for transparency but
        excluded from the graph to keep it readable.

Exported as a plain node-link JSON structure so the dashboard's D3 code
doesn't need a Python runtime.
"""
from __future__ import annotations

import networkx as nx

from .extraction import Obligation
from .classifier import Relationship

EDGE_COLORS = {
    "CONFLICT": "#B3261E",
    "REDUNDANT": "#B8923F",
    "COMPLEMENTARY": "#2F6F62",
}


def build_graph(obligations: list[Obligation], relationships: list[Relationship]) -> nx.Graph:
    g = nx.Graph()
    for o in obligations:
        g.add_node(
            o.obligation_id,
            policy_id=o.policy_id,
            policy_title=o.policy_title,
            section=o.section,
            text=o.text,
            topic=o.topic,
            scope=o.scope,
            strength=o.strength,
            polarity=o.polarity,
        )
    for r in relationships:
        if r.relationship == "UNRELATED":
            continue
        # Only add edge if both endpoint nodes exist (defensive)
        if r.obligation_a_id in g and r.obligation_b_id in g:
            g.add_edge(
                r.obligation_a_id,
                r.obligation_b_id,
                relationship=r.relationship,
                confidence=r.confidence,
                explanation=r.explanation,
                color=EDGE_COLORS.get(r.relationship, "#888888"),
            )
    return g


def graph_to_node_link(g: nx.Graph) -> dict:
    data = nx.node_link_data(g, edges="edges")
    # Drop isolated nodes (obligations with no flagged relationships) from the
    # visual graph to keep it focused on governance-relevant clusters, but
    # note the count so the dashboard can report full coverage.
    connected_ids = set()
    for e in data["edges"]:
        connected_ids.add(e["source"])
        connected_ids.add(e["target"])
    total_nodes = len(data["nodes"])
    data["nodes"] = [n for n in data["nodes"] if n["id"] in connected_ids]
    data["meta"] = {
        "total_obligations": total_nodes,
        "obligations_in_graph": len(data["nodes"]),
        "total_edges": len(data["edges"]),
    }
    return data
