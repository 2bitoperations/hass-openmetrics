"""Utilities for custom (arbitrary) metric mappings."""

import re
import uuid


def generate_custom_metric_id() -> str:
    """Generate a short unique ID for a custom metric config entry."""
    return str(uuid.uuid4()).replace("-", "")[:12]


def parse_metric_query(query: str) -> tuple[str, dict[str, str]]:
    """Parse a Prometheus metric selector into (metric_name, label_filters).

    Accepts: metric_name  or  metric_name{key="val", key2="val2"}
    """
    query = query.strip()
    match = re.match(r"^([a-zA-Z_:][a-zA-Z0-9_:]*)(\{([^}]*)\})?$", query)
    if not match:
        raise ValueError(f"Invalid metric query: {query!r}")
    metric_name = match.group(1)
    labels_str = match.group(3)
    labels: dict[str, str] = {}
    if labels_str:
        for m in re.finditer(r'(\w+)="([^"]*)"', labels_str):
            labels[m.group(1)] = m.group(2)
    return metric_name, labels


def extract_custom_metric_value(
    families: list, metric_name: str, label_filters: dict[str, str]
) -> float | None:
    """Return the first sample value that matches metric_name and all label_filters."""
    for family in families:
        if family.name == metric_name:
            for sample in family.samples:
                if all(sample.labels.get(k) == v for k, v in label_filters.items()):
                    return sample.value
    return None
