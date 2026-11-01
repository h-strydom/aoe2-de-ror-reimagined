"""Source terrain clean-up applied before the terrain swap.

Stray road tiles: AoE DE maps sometimes dab single road tiles or tiny clusters beside forests and
cliffs (Ascent of Egypt 4 has 26). AoE DE blends them into faint pale patches, but RoR draws its
road terrain as crisp cobblestone (proof-of-concept playtest: "roads instead of some kind of
terrain"). A road cluster (8-connected) smaller than rules.min_road_cluster takes the most common
non-road terrain around each tile; real roads, which are long connected runs, are kept.
"""
from __future__ import annotations

from collections import Counter

_NEIGHBOURS = ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1))


def _road_clusters(terrain: list[int], w: int, h: int, roads: frozenset[int]) -> list[list[int]]:
    seen: set[int] = set()
    clusters = []
    for i, t in enumerate(terrain):
        if t not in roads or i in seen:
            continue
        stack, cluster = [i], []
        seen.add(i)
        while stack:
            j = stack.pop()
            cluster.append(j)
            x, y = j % w, j // w
            for dx, dy in _NEIGHBOURS:
                nx, ny = x + dx, y + dy
                if 0 <= nx < w and 0 <= ny < h:
                    k = ny * w + nx
                    if k not in seen and terrain[k] in roads:
                        seen.add(k)
                        stack.append(k)
        clusters.append(cluster)
    return clusters


def _surrounding(terrain: list[int], w: int, h: int, i: int, roads: frozenset[int]) -> int:
    x, y = i % w, i // w
    for r in (1, 2, 3):
        around = Counter(terrain[ny * w + nx]
                         for ny in range(max(0, y - r), min(h, y + r + 1))
                         for nx in range(max(0, x - r), min(w, x + r + 1))
                         if terrain[ny * w + nx] not in roads)
        if around:
            return around.most_common(1)[0][0]
    return 0  # grass


def clean_terrain(terrain: list[int], w: int, h: int, roads: frozenset[int], min_cluster: int) -> list[int]:
    """AoE DE terrain ids with stray road clusters replaced (still AoE DE ids)."""
    out = list(terrain)
    for cluster in _road_clusters(terrain, w, h, roads):
        if len(cluster) < min_cluster:
            for i in cluster:
                out[i] = _surrounding(terrain, w, h, i, roads)
    return out
