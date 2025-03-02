"""Processor for metrics."""

import logging
from datetime import datetime

from homeassistant.exceptions import HomeAssistantError

from ..const import (
    CONTENT_TYPE_OPENMETRICS,
    CONTENT_TYPE_TEXT,
)
from ..lib import parser, prom_parser
from ..lib.metrics_core import Metric
from ..metrics.data import MetadataData, ProviderInfoData
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
        # Create collector for metadata extraction
        metadata = MetadataData(
            provider_info=ProviderInfoData(
                name=self._provider.name,
                type=self._provider.resource_type,
                version=None,
            ),
            resources={},
            available_metrics=[],
        )
        # Extract provider related metadata from metric families
        for family in families:
            self._provider.extract_provider_info(family, metadata)
            self._provider.extract_resource_info(family, metadata)
            self._provider.extract_available_metrics(family, metadata)
        # Cleanup metadata resources dict
        if self._provider.name in metadata.resources:
            main_resource = metadata.resources[self._provider.name]
            if main_resource.name:
                metadata.resources[main_resource.name] = main_resource
                del metadata.resources[self._provider.name]
                for resource in metadata.resources.values():
                    if resource.name != main_resource.name:
                        resource.via_resource = main_resource.name
        # Collect and return provider related metadata
        _LOGGER.debug("Metadata successfully extracted")
        return metadata

    def extract_metrics(self, families: list[Metric], resources: list[str]) -> dict:
        """Extract metrics for specified resources."""
        extracted_metrics = {}
        # Ensure provider is defined
        self._ensure_provider(families)
        # Extract metrics of all relevant metric families
        for family in families:
            for metric_filter in self._config.metric_filters:
                if family.name == metric_filter.metric_key:
                    for sample in family.samples:
                        # Check if metric is relevant
                        is_relevant, resource = metric_filter.matches(sample)
                        # Set resource according to provider resource
                        if not resource and self._provider.resource_name:
                            resource = self._provider.resource_name
                        if is_relevant:
                            # Check if resource is relevant
                            if resource in resources:
                                # Initialize resource dictionary
                                if resource not in extracted_metrics:
                                    extracted_metrics[resource] = {}
                                # Initialize metric dictionary
                                if (
                                    metric_filter.metric_key
                                    not in extracted_metrics[resource]
                                ):
                                    extracted_metrics[resource][
                                        metric_filter.metric_key
                                    ] = {}
                                # Prepare metric value
                                metric_value = self._provider.prepare_metric_value(
                                    metric_filter.metric_key, sample
                                )
                                # Add metric value to dictionary
                                if isinstance(metric_value, dict):
                                    extracted_metrics[resource][
                                        metric_filter.metric_key
                                    ].update(metric_value)
                                else:
                                    extracted_metrics[resource][
                                        metric_filter.metric_key
                                    ] = metric_value
        if extracted_metrics:
            _LOGGER.debug("Metrics successfully extracted")
        else:
            _LOGGER.debug("No metrics extracted")
        # Collect and return provider related metrics
        return extracted_metrics

    def process_metrics(self, metrics: dict, update_interval: int) -> dict:
        """Process metrics."""
        sensor_metrics = self._provider.process_metrics(metrics, update_interval)
        if sensor_metrics:
            # Return provider related metrics
            _LOGGER.debug("Metrics successfully processed")
            return sensor_metrics
        _LOGGER.debug("No metrics processed")
        return {}

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
