"""Base class for metrics providers."""

from abc import ABC, abstractmethod
from typing import Any

from ..lib.metrics_core import Metric
from ..lib.samples import Sample
from ..metrics import MetricFilter
from ..metrics.data import (
    MetadataData,
    ProviderInfoData,
    ResourceInfoData,
)


class MetricsProvider(ABC):
    """Base class for metrics providers."""

    RESOURCE_NAME = "unknown"
    provider_filters: list[MetricFilter]
    metric_filters: list[MetricFilter]

    def __init__(
        self,
        name,
        resource_type,
    ):
        """Initialize metrics provider."""
        self.name = name
        self.resource_type = resource_type
        # Initialize metadata
        self._metadata = MetadataData(
            provider_info=ProviderInfoData(
                name=name,
                type=resource_type,
                version=None,
            ),
            resources={},
            available_metrics=[],
        )
        self.resource_name = self.RESOURCE_NAME
        # Initialize metrics
        self._previous_metrics: dict = {}

    def search_provider_info_metric(self, family: Metric) -> Metric | None:
        """Search provider information metric."""
        for metric_filter in self.provider_filters:
            if metric_filter.matches_metric(family.name):
                return family

    def search_resource_metric(self, family: Metric) -> Metric | None:
        """Search resource metric."""
        for metric_filter in self.metric_filters:
            if metric_filter.matches_metric(family.name):
                return family

    @abstractmethod
    def extract_provider_info(self, family: Metric, provider_info: ProviderInfoData):
        """Extract provider information from metric family."""
        raise NotImplementedError

    @abstractmethod
    def extract_resource_info(self, family: Metric, resources: dict):
        """Extract resource information from metric family."""
        raise NotImplementedError

    def post_process_resources(self, resources: dict) -> dict[str, ResourceInfoData]:
        """Handle resources - Rename, reorder and link resources."""
        # Reoder and link resources
        if self.name in resources:
            res = {}
            main_resource = resources[self.name]
            # Rename and add main resource
            if main_resource.name and not main_resource.is_virtual:
                res[main_resource.name] = main_resource
            # Add and link resources
            for resource_key, resource_info in resources.items():
                if resource_info.is_virtual:
                    resource_info.via_resource = main_resource.name
                if resource_key != self.name:
                    res[resource_info.name] = resource_info
            return res
        return resources

    @abstractmethod
    def collect_supported_metric(self, family: Metric, available_metrics: list[str]):
        """Collect supported metric."""
        raise NotImplementedError

    def get_metadata(self) -> MetadataData:
        """Return collected metadata."""
        return self._metadata

    def get_metric_filters(self) -> list[MetricFilter]:
        """Return metric filters."""
        return self.metric_filters

    def process_metrics(self, metrics: dict, update_interval: int) -> dict | None:
        """Process metrics and return sensor metrics."""
        sensor_metrics = {}
        # Pre-process metrics
        self._pre_process_metrics(metrics)
        # Calculate resource metrics
        for resource, resource_metrics in metrics.items():
            if resource not in sensor_metrics:
                sensor_metrics[resource] = {}
            sensor_metrics[resource].update(
                self._calculate_resource_metrics(
                    resource, resource_metrics, update_interval
                )
            )
        # Return sensor metrics
        return sensor_metrics

    def prepare_metric_value(self, metric_key: str, sample: Sample) -> float | dict:
        """Collect metric values."""
        return sample.value

    @abstractmethod
    def _pre_process_metrics(self, metrics: dict):
        """Pre-process metrics."""
        raise NotImplementedError

    @abstractmethod
    def _calculate_cpu_usage(
        self, resource: str, metrics: dict, update_interval: int
    ) -> dict[str, Any]:
        """Calculate CPU usage."""
        raise NotImplementedError

    @abstractmethod
    def _calculate_memory_usage(self, resource: str, metrics: dict) -> dict[str, Any]:
        """Calculate memory usage (used bytes, used pct)."""
        raise NotImplementedError

    @abstractmethod
    def _calculate_disk_usage(self, resource: str, metrics: dict) -> dict[str, Any]:
        """Calculate disk usage (used bytes, used pct)."""
        raise NotImplementedError

    @abstractmethod
    def _calculate_network_io(
        self, resource: str, metrics: dict, update_interval: int
    ) -> dict[str, Any]:
        """Calculate network io (receive bytes, transmit bytes)."""
        raise NotImplementedError

    @abstractmethod
    def _calculate_uptime(self, resource: str, metrics: dict) -> dict[str, Any]:
        """Calculate uptime."""
        raise NotImplementedError

    def _add_str_to_list_uniquely(self, string: str, list: list[str]):
        if string not in list:
            list.append(string)

    def _calculate_resource_metrics(
        self, resource: str, metrics: dict, update_interval: int
    ) -> dict | None:
        """Process resource metrics and return sensor metrics."""
        # CPU
        sensor_metrics = self._calculate_cpu_usage(resource, metrics, update_interval)
        # Memory
        sensor_metrics.update(self._calculate_memory_usage(resource, metrics))
        # Disk
        sensor_metrics.update(self._calculate_disk_usage(resource, metrics))
        # Network
        sensor_metrics.update(
            self._calculate_network_io(resource, metrics, update_interval)
        )
        # Uptime
        sensor_metrics.update(self._calculate_uptime(resource, metrics))
        # Return sensor metrics
        return sensor_metrics
