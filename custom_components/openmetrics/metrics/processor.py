"""Processor for metrics."""

import logging
from datetime import datetime

from homeassistant.exceptions import HomeAssistantError

from custom_components.openmetrics.providers.base import MetricsProvider

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
        self._provider = self._registry.get_default_provider()

    def parse_data(self, response_text: str, content_type: str | None) -> list[Metric]:
        """Parse metrics provider data."""
        try:
            _LOGGER.debug("Metrics provider: %s", self._provider.name)
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
            # Return metrics
            _LOGGER.debug("Metrics successfully parsed")
            return list(families)

    def __detect_provider(self, families: list[Metric]) -> MetricsProvider | None:
        """Filter relevant metrics."""
        relevant_families = []
        provider = None
        for family in families:
            # Get provider info metric
            provider_info = self._provider.search_provider_info_metric(family)
            if provider_info:
                relevant_families.append(provider_info)
                provider = self._registry.get_provider(family.name)
                if provider:
                    _LOGGER.debug("Metrics provider detected: %s", provider.name)
                    break
        # Return provider
        return provider

    def __filter_relevant_resource_metrics(
        self, families: list[Metric]
    ) -> list[Metric]:
        """Filter relevant metrics."""
        relevant_families = []
        provider = None
        for family in families:
            # Get resource metric
            metric = self._provider.search_resource_metric(family)
            if metric:
                relevant_families.append(metric)
                continue
        # Set provider if found
        if provider:
            self._provider = provider
        # Return relevant metrics
        _LOGGER.debug("Metrics successfully filtered")
        return relevant_families

    def extract_metadata(self, families: list[Metric]) -> MetadataData:
        """Extract provider metadata and available metrics."""
        # Detect and set provider
        provider = self.__detect_provider(families)
        if provider:
            self._provider = provider
        # Define provider related metadata
        provider_info = ProviderInfoData(
            name=self._provider.name,
            type=self._provider.resource_type,
            version=None,
        )
        resources = {}
        available_metrics = []
        # Extract provider related metadata from metric families
        for family in families:
            self._provider.extract_provider_info(family, provider_info)
            self._provider.extract_resource_info(family, resources)
            self._provider.collect_supported_metric(family, available_metrics)
        # Post process resources
        resources = self._provider.post_process_resources(resources)
        # Return provider related metadata
        _LOGGER.debug("Metadata successfully extracted")
        return MetadataData(
            provider_info=provider_info,
            resources=resources,
            available_metrics=available_metrics,
        )

    def extract_metrics(self, families: list[Metric], resources: list[str]) -> dict:
        """Extract metrics for specified resources."""
        extracted_metrics = {}
        # Filter relevant metrics
        relevant_families = self.__filter_relevant_resource_metrics(families)
        # Extract metrics of all relevant metric families
        for family in relevant_families:
            for metric_filter in self._provider.get_metric_filters():
                # Check if metric family is relevant
                if metric_filter.matches_metric(family.name):
                    for sample in family.samples:
                        # Check if metric sample is relevant
                        if metric_filter.matches_labels(sample):
                            # Set metric key without "_total" suffix
                            if sample.name.endswith("_total"):
                                metric_key = sample.name.replace("_total", "")
                            else:
                                metric_key = sample.name
                            # Set resource according to provider
                            if (
                                metric_filter.resource_label
                                and metric_filter.resource_label in sample.labels
                            ):
                                resource = sample.labels[metric_filter.resource_label]
                            elif self._provider.resource_name:
                                resource = self._provider.resource_name
                            else:
                                resource = self._provider.name
                            # Initialize resource dictionary
                            if resource not in extracted_metrics:
                                extracted_metrics[resource] = {}
                            # Initialize metric dictionary
                            if metric_key not in extracted_metrics[resource]:
                                extracted_metrics[resource][metric_key] = {}
                            # Prepare metric value
                            metric_value = self._provider.prepare_metric_value(
                                metric_key, sample
                            )
                            # Add metric value to dictionary
                            if isinstance(metric_value, dict):
                                extracted_metrics[resource][metric_key].update(
                                    metric_value
                                )
                            else:
                                extracted_metrics[resource][metric_key] = metric_value
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
