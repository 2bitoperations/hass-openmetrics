"""Processor for metrics."""

from homeassistant.exceptions import HomeAssistantError

from ..const import (
    NODE_CPU_IDLE_SECONDS,
    PROVIDER_TYPE_NODE,
)
from ..lib.metrics_core import Metric, Sample
from ..providers.base import MetricsProvider, ProviderConfig
from ..providers.registry import ProviderRegistry


class ProcessingError(HomeAssistantError):
    """Error to indicate a client processing error."""


class MetricsProcessor:
    """Process metrics based on provider configuration."""

    def __init__(self):
        """Initialize metrics processor."""
        self.registry = ProviderRegistry()
        self._provider: MetricsProvider | None = None
        self._config: ProviderConfig | None = None

    def _ensure_provider(self, families: list[Metric]) -> None:
        """Ensure provider is detected and configured."""
        if self._provider is None:
            if not families:
                raise ProcessingError("No metrics found")

            for family in families:
                self._provider = self.registry.get_provider(family.name)
                if self._provider:
                    self._config = self._provider.get_config()
                    break

            if not self._provider:
                raise ProcessingError("No supported provider found")

    def extract_metadata(self, families: list[Metric]) -> dict:
        """Extract provider metadata and available metrics."""
        self._ensure_provider(families)
        if not self._provider:
            raise ProcessingError("No provider configuration available")

        # Process all metric families
        for family in families:
            self._provider.extract_provider_info(family)
            self._provider.extract_resource_info(family)
            self._provider.extract_available_metrics(family)

        # Get collected metadata from provider
        return self._provider.get_metadata()

    def extract_metrics(self, families: list[Metric], resources: list[str]) -> dict:
        """Extract metrics for specified resources."""
        self._ensure_provider(families)
        if not self._config:
            raise ProcessingError("No provider configuration available")

        result = {}

        for family in families:
            for metric_filter in self._config.metric_filters:
                if family.name == metric_filter.metric_key:
                    for sample in family.samples:
                        if self._config.resource_type == PROVIDER_TYPE_NODE:
                            resource_id = resources[0]
                        elif self._config.resource_identifier in sample.labels:
                            resource_id = sample.labels[
                                self._config.resource_identifier
                            ]
                        if resource_id in resources:
                            matches, _ = metric_filter.matches(sample)
                            if matches:
                                if resource_id not in result:
                                    result[resource_id] = {}
                                self._add_metric_value(
                                    result[resource_id],
                                    metric_filter.metric_key,
                                    metric_filter.resource_label,
                                    sample,
                                )
        return result

    def _add_metric_value(
        self, metrics: dict, metric_key: str, resource_label: str | None, sample: Sample
    ) -> None:
        """Add metric value with special handling for specific metrics."""
        if metric_key not in metrics:
            metrics[metric_key] = {}

        if metric_key == NODE_CPU_IDLE_SECONDS:
            key = sample.labels["cpu"]
            if key not in metrics[metric_key]:
                metrics[metric_key][key] = {}
            metrics[metric_key][key] = sample.value
        else:
            metrics[metric_key] = sample.value
