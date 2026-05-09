"""Utilities for custom (arbitrary) metric mappings."""

import re
import uuid
from dataclasses import dataclass
from enum import Enum


class LabelMatchType(str, Enum):
    EXACT = "="
    NOT_EXACT = "!="
    REGEX = "=~"
    NOT_REGEX = "!~"


@dataclass
class LabelFilter:
    label: str
    value: str
    match_type: LabelMatchType = LabelMatchType.EXACT

    def matches(self, sample_labels: dict[str, str]) -> bool:
        actual = sample_labels.get(self.label, "")
        if self.match_type == LabelMatchType.EXACT:
            return actual == self.value
        if self.match_type == LabelMatchType.NOT_EXACT:
            return actual != self.value
        if self.match_type == LabelMatchType.REGEX:
            return bool(re.fullmatch(self.value, actual))
        if self.match_type == LabelMatchType.NOT_REGEX:
            return not bool(re.fullmatch(self.value, actual))
        return False


def generate_custom_metric_id() -> str:
    """Generate a short unique ID for a custom metric config entry."""
    return str(uuid.uuid4()).replace("-", "")[:12]


def parse_metric_query(query: str) -> tuple[str, list[LabelFilter]]:
    """Parse a Prometheus metric selector into (metric_name, filters).

    Supports:
      metric_name
      metric_name{label="value"}       exact match
      metric_name{label!="value"}      exact non-match
      metric_name{label=~"pattern"}    regex match  (re.fullmatch)
      metric_name{label!~"pattern"}    regex non-match
    Multiple filters may be combined: metric{a="x",b=~"y.*"}
    """
    query = query.strip()
    m = re.match(r"^([a-zA-Z_:][a-zA-Z0-9_:]*)(\{([^}]*)\})?$", query)
    if not m:
        raise ValueError(f"Invalid metric query: {query!r}")
    metric_name = m.group(1)
    labels_str = m.group(3)
    filters: list[LabelFilter] = []
    if labels_str:
        _OP_MAP = {
            "=~": LabelMatchType.REGEX,
            "!~": LabelMatchType.NOT_REGEX,
            "!=": LabelMatchType.NOT_EXACT,
            "=": LabelMatchType.EXACT,
        }
        for fm in re.finditer(r'(\w+)(=~|!~|!=|=)"([^"]*)"', labels_str):
            filters.append(
                LabelFilter(
                    label=fm.group(1),
                    value=fm.group(3),
                    match_type=_OP_MAP[fm.group(2)],
                )
            )
    return metric_name, filters


def find_matching_samples(
    families: list,
    metric_name: str,
    filters: list[LabelFilter],
) -> list[tuple[float, dict[str, str]]]:
    """Return (value, all_sample_labels) for every sample matching name and filters."""
    results = []
    for family in families:
        if family.name != metric_name:
            continue
        for sample in family.samples:
            if all(f.matches(sample.labels) for f in filters):
                results.append((sample.value, dict(sample.labels)))
    return results


def compute_fingerprint(labels: dict[str, str], group_by: list[str]) -> str:
    """Build a stable, filesystem-safe fingerprint from the specified label values."""
    parts = [re.sub(r"[^a-zA-Z0-9]", "_", labels.get(k, "")) for k in group_by]
    return "__".join(parts)


def extract_custom_metric_value(
    families: list, metric_name: str, filters: list[LabelFilter]
) -> float | None:
    """Return the first matching sample value, or None."""
    matches = find_matching_samples(families, metric_name, filters)
    return matches[0][0] if matches else None
