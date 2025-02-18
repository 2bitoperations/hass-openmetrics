"""Processor for metrics."""

import logging
from datetime import datetime

from homeassistant.exceptions import HomeAssistantError

from ..const import CONTENT_TYPE_OPENMETRICS, CONTENT_TYPE_TEXT, PROVIDER_TYPE_NODE
from ..lib import parser, prom_parser
from ..lib.metrics_core import Metric
from ..metrics.data import MetadataData
from ..providers.registry import ProviderRegistry

_LOGGER = logging.getLogger(__name__)


class ProcessingError(HomeAssistantError):
    """Error to indicate issues related to processing."""


class ProviderError(ProcessingError):
    """Error to indicate issues related to provider."""


class ResourcesError(ProcessingError):
    """Error to indicate issues related to resources."""


class MetricsError(ProcessingError):
    """Error to indicate issues related to metrics."""


class OpenMetricsProcessor:
    """Process metrics based on provider configuration."""

    def __init__(self):
        """Initialize metrics processor."""
        self._registry = ProviderRegistry()
        self._previous_metrics = {}

    def _ensure_provider(self, families: list[Metric]):
        """Ensure provider is detected and configured."""
        # Check if any metrics are available
        if not families:
            _LOGGER.error("No metrics found in provided families")
            raise MetricsError("No metrics found")
        # Search metrics for provider
        if not hasattr(self, "_provider"):
            for family in families:
                provider = self._registry.get_provider(family.name)
                if provider:
                    # Set provider
                    self._provider = provider
                    # Set provider config
                    self._config = self._provider.get_config()
                    _LOGGER.info(
                        "Provider detected and configured: %s", self._provider.name
                    )
                    break
        # If no provider is found, raise an error
        if not hasattr(self, "_provider"):
            _LOGGER.error("No matching provider found in provided metrics")
            raise ProviderError("No supported provider found")

    def parse_data(self, response_text: str, content_type: str | None) -> list[Metric]:
        """Parse metrics provider data."""
        try:
            # Parse prometheus text format
            if content_type and CONTENT_TYPE_TEXT in content_type:
                families = prom_parser.text_string_to_metric_families(response_text)
            # Parse OpenMetrics text format
            elif content_type and CONTENT_TYPE_OPENMETRICS in content_type:
                families = parser.text_string_to_metric_families(response_text)
            else:
                _LOGGER.error("Content type '%s' not supported", content_type)
                raise ProcessingError(f"Content type '{content_type}' not supported")
        except Exception as e:
            raise ProcessingError(str(e)) from e
        else:
            _LOGGER.debug("Metrics successfully parsed")
            return list(families)

    def extract_metadata(self, families: list[Metric]) -> MetadataData:
        """Extract provider metadata and available metrics."""
        # Ensure provider is defined
        self._ensure_provider(families)
        # Process all metric families
        for family in families:
            self._provider.extract_provider_info(family)
            self._provider.extract_resource_info(family)
            self._provider.extract_available_metrics(family)
        # Collect and return provider related metadata
        _LOGGER.debug("Metadata successfully extracted")
        return self._provider.get_metadata()

    def extract_metrics(self, families: list[Metric], resources: list[str]) -> dict:
        """Extract metrics for specified resources."""
        # Ensure provider is defined
        self._ensure_provider(families)
        # Extract metrics of all relevant metric families
        for family in families:
            for metric_filter in self._config.metric_filters:
                if family.name == metric_filter.metric_key:
                    for sample in family.samples:
                        # Get resource identifier
                        if self._provider.resource_type == PROVIDER_TYPE_NODE:
                            resource_id = resources[0]
                        elif self._config.resource_identifier in sample.labels:
                            resource_id = sample.labels[
                                self._config.resource_identifier
                            ]
                        # Check if resource is relevant
                        matches, _ = metric_filter.matches(sample)
                        if matches:
                            # Add metric value
                            self._provider.add_metric_value(
                                resource_id,
                                metric_filter.metric_key,
                                sample,
                            )
        # Collect and return provider related metrics
        _LOGGER.debug("Metrics successfully extracted")
        return self._provider.get_metrics()

    def process_metrics(self, metrics: dict, update_interval: int) -> dict:
        """Process metrics."""
        sensor_metrics = {}
        # Process metrics for each resource
        for resource in metrics:
            if resource not in sensor_metrics:
                sensor_metrics[resource] = {}
            sensor_metrics[resource].update(
                self._provider.process_metrics(
                    resource, metrics[resource], update_interval
                )
            )
        # Return provider related metrics
        _LOGGER.debug("Metrics successfully processed")
        return sensor_metrics

    @property
    def last_start_time(self) -> datetime | None:
        """Return last start time."""
        if not hasattr(self, "_provider"):
            return None
        return self._provider.last_start_time

    @property
    def cpu_cores(self) -> int | None:
        """Return number of CPU cores."""
        if not hasattr(self, "_provider"):
            return None
        return self._provider.cpu_cores

    @property
    def memory_size(self) -> int | None:
        """Return memory size in bytes."""
        if not hasattr(self, "_provider"):
            return None
        return self._provider.memory_size

    @property
    def disk_size(self) -> int | None:
        """Return disk size in bytes."""
        if not hasattr(self, "_provider"):
            return None
        return self._provider.disk_size
