"""Filter metrics."""

from dataclasses import dataclass

from homeassistant.exceptions import HomeAssistantError

from ..const import CADVISOR_RESOURCE_LABEL
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
        """Check if sample matches the filter criteria and return matching status with resource id."""
        # Get resource id if resource label is specified
        resource_id = None
        if self.resource_label and self.resource_label in sample.labels:
            resource_id = sample.labels[self.resource_label]

        # Check if sample has no labels
        if len(sample.labels) == 0:
            return True, resource_id
        # Check if label filters are empty
        if not self.label_filters:
            return True, resource_id

        # Check all required labels exist and match
        for label_key, label_value in self.label_filters.items():
            # Check if required label exists
            if label_key not in sample.labels:
                return False, None
            # If label value is "*", any non-empty value matches
            if label_value == "*":
                if not sample.labels[label_key]:
                    return False, None
            # Otherwise exact match required
            elif sample.labels[label_key] != label_value:
                return False, None
            # Get resource id if resource label is specified
            if label_key == CADVISOR_RESOURCE_LABEL:
                resource_id = sample.labels[CADVISOR_RESOURCE_LABEL]

        # Return result
        return True, resource_id
