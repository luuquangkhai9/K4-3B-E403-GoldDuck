"""Deterministic reciprocal rank fusion (ranks start at one)."""


def reciprocal_rank_fusion(
    rankings: list[list[tuple[int, float]]], limit: int = 5, k: int = 60
) -> list[tuple[int, float]]:
    scores: dict[int, float] = {}
    for ranking in rankings:
        seen = set()
        for rank, (index, _) in enumerate(ranking, start=1):
            if index in seen:
                continue
            seen.add(index)
            scores[index] = scores.get(index, 0.0) + 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda item: (-item[1], item[0]))[:limit]
