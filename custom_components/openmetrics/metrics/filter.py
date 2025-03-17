"""Filter metrics."""

import logging
import re
from dataclasses import dataclass

from homeassistant.exceptions import HomeAssistantError

from ..lib.metrics_core import Sample

_LOGGER = logging.getLogger(__name__)


class ProcessingError(HomeAssistantError):
    """Error to indicate a client processing error."""


@dataclass
class MetricFilter:
    """Configuration for filtering metrics."""

    metric_key: str
    resource_label: str | None = None
    label_filters: dict[str, str] | None = None

    def matches_metric(self, metric_name: str) -> bool:
        """Check if metric matches the filter criteria."""
        # Check if metric name matches
        if self.metric_key == metric_name:
            return True
        # Check if metric name matches regex pattern
        try:
            if re.match(self.metric_key, metric_name, re.IGNORECASE):
                return True
        except re.error:
            _LOGGER.warning("Skipping invalid regex pattern: %s", self.metric_key)
        # Return False if no match
        return False

    def matches_labels(self, sample: Sample) -> bool:
        """Check if sample matches the filter criteria and return matching status."""
        # Check labels if label filters not empty
        if self.label_filters:
            # Check all required labels exist and match
            for label_key, label_value in self.label_filters.items():
                # Check if required label exists
                if label_key not in sample.labels:
                    return False
                if not re.match(label_value, sample.labels[label_key], re.IGNORECASE):
                    return False
        elif sample.labels:
            return False
        # Return result
        return True
