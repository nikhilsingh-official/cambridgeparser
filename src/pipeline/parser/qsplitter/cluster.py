from typing import Any, Dict, List, Optional
from .type_definitions import Candidate


def cluster_candidates(candidates: List[Candidate], leeway: float, x_key: str = "x") -> List[Dict[str, Any]]:
    clusters: List[Dict[str, Any]] = []
    for candidate in sorted(candidates, key=lambda c: c[x_key]):
        for cluster in clusters:
            if abs(candidate[x_key] - cluster["x_mean"]) < leeway:
                cluster["members"].append(candidate)
                x_values = [c[x_key] for c in cluster["members"]]
                cluster["x_mean"] = sum(x_values) / len(x_values)
                break
        else:
            clusters.append({"members": [candidate], "x_mean": candidate[x_key]})

    for cluster_id, cluster in enumerate(clusters):
        x_values = [c[x_key] for c in cluster["members"]]
        mean = sum(x_values) / len(x_values)
        variance = sum((x - mean) ** 2 for x in x_values) / len(x_values)
        std_dev = variance ** 0.5
        cluster["id"] = cluster_id
        cluster["x_std"] = std_dev
        cluster["size"] = len(x_values)
        cluster["quality"] = cluster["size"] / (1 + std_dev)
        for candidate in cluster["members"]:
            candidate["cluster_id"] = cluster_id

    return clusters


def select_column_clusters(clusters: List[Dict[str, Any]]) -> (Optional[int], Optional[int]):
    if not clusters:
        return None, None
    ranked = sorted(clusters, key=lambda c: (c["size"], c["quality"]), reverse=True)
    if len(ranked) == 1:
        return ranked[0]["id"], None
    top_two = ranked[:2]
    left, right = sorted(top_two, key=lambda c: c["x_mean"])
    return left["id"], right["id"]


def select_marks_cluster(clusters: List[Dict[str, Any]]) -> Optional[int]:
    if not clusters:
        return None
    max_size = max(cluster["size"] for cluster in clusters)
    candidates = [cluster for cluster in clusters if cluster["size"] == max_size]
    return max(candidates, key=lambda c: c["x_mean"])["id"]
