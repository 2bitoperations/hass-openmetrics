"""Filter metrics."""

from dataclasses import dataclass

from homeassistant.exceptions import HomeAssistantError

from ..lib.metrics_core import Sample


class ProcessingError(HomeAssistantError):
    """Error to indicate a client processing error."""


@dataclass
class MetricFilter:
    """Configuration for filtering metrics."""

    metric_name: str
    metric_key: str
    resource_label: str | None = None
    label_filters: dict[str, str] | None = None

    def matches(self, sample: Sample) -> tuple[bool, str | None]:
        """Check if sample matches filter criteria."""
        resource_id = None
        # Check resource label
        if self.resource_label:
            if self.resource_label not in sample.labels:
                return False, None
            resource_id = sample.labels[self.resource_label]
        # Check label filters
        if not self.label_filters:
            return True, resource_id
        matches = all(
            key in sample.labels
            and (value == "*" and sample.labels[key] or sample.labels[key] == value)
            for key, value in self.label_filters.items()
        )
        # Return result
        return matches, resource_id
