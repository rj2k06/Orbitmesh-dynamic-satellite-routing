# DAA report guide

## Problem

Model a satellite constellation as a dynamic weighted graph. Find routes between a source satellite and a ground station while optimizing multiple criteria and recovering from topology failures.

## Graph model

Vertex:
- Satellite or ground station

Edge:
- Communication link

Edge attributes:
- latency
- bandwidth
- congestion
- energy
- reliability

Weighted cost:

C(e) = wL * latency + wC * congestion_penalty + wE * energy

## Algorithms

### Dijkstra
Exact shortest path for non-negative edge weights.
Typical binary-heap complexity: O((V+E) log V).

### A*
Uses f(n) = g(n) + h(n), where h estimates remaining cost.
Worst-case can approach Dijkstra; practical performance depends on the heuristic.

### Bellman-Ford
O(VE). Useful as a baseline and for demonstrating repeated relaxation.

### Floyd-Warshall
O(V^3), useful when all-pairs shortest paths are required.

### Genetic heuristic
Metaheuristic comparison point. It trades exactness guarantees for search flexibility.

## Experiments

1. Algorithm runtime vs graph size.
2. Route cost vs congestion weight.
3. Route reliability before/after failures.
4. Recovery behavior after node failures.
5. Bottleneck bandwidth under congestion.
6. Number of hops and weighted cost.

## Viva explanation

A strong explanation is:

"Every satellite is represented as a graph vertex and every available communication link as a weighted edge. The edge weight is a multi-objective function combining latency, congestion and energy. Dijkstra and A* find routes, Bellman-Ford and Floyd-Warshall provide comparison baselines, and a heuristic provides an optimization comparison. Because the constellation is dynamic, node/link failures modify the graph and force re-optimization."

## Important limitation

The orbital motion in this version is simulated. For a research/industry extension, use real orbital propagation such as SGP4 from TLE/OMM data and a contact-plan routing model.


## Dynamic rerouting demonstration

The simulator recomputes link latency, energy and bandwidth from the current satellite geometry on every simulation tick. It also applies a geometry-derived orbital signal-quality factor. Therefore satellite motion changes graph edge weights, and Dijkstra/A*/Bellman-Ford/Floyd-Warshall may select a different route when another path becomes cheaper. The UI recalculates the route after every movement step and shows a ROUTE CHANGED notification when the selected path changes.

## Implementation notes for accurate reporting

- The current Dijkstra implementation selects the next node with a linear scan, so describe its implementation-level complexity as approximately O(V² + E), not the binary-heap bound.
- The A* heuristic is geometry-based, but its admissibility for the combined latency/congestion/energy score is not proven.
- The UI's “Genetic Heuristic” is a deterministic candidate-path comparison over fixed weight configurations. It does not currently use genetic selection, crossover, or mutation.
- Latency, congestion, energy, bandwidth, reliability, and movement are simulated values. They are not calibrated to real spacecraft or communications hardware.
