"""Base class for metrics providers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

from homeassistant.util import dt as dt_util

from ..const import (
    METRIC_CPU_USAGE_PCT,
    METRIC_DISK_USAGE_BYTES,
    METRIC_DISK_USAGE_PCT,
    METRIC_MEMORY_USAGE_BYTES,
    METRIC_MEMORY_USAGE_PCT,
    METRIC_NETWORK_RECEIVE_BYTES,
    METRIC_NETWORK_TRANSMIT_BYTES,
    METRIC_UPTIME_SECONDS,
)
from ..lib.metrics_core import Metric
from ..lib.samples import Sample
from ..metrics import MetricFilter
from ..metrics.data import (
    MetadataData,
    ProviderInfoData,
)


@dataclass
class ProviderConfig:
    """Configuration for a metrics provider."""

    identifier_metric: str
    version_label: str
    resource_identifier: str
    metric_filters: list[MetricFilter]


class MetricsProvider(ABC):
    """Base class for metrics providers."""

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
            resources=[],
            available_metrics=[],
        )
        # Initialize metrics
        self._metrics: dict = {}
        self._previous_metrics: dict = {}
        # Initialize resource meta info
        self.last_start_time: datetime | None = None
        self.cpu_cores: int | None = None
        self.memory_size: int | None = None
        self.disk_size: int | None = None

    def get_metadata(self) -> MetadataData:
        """Return collected metadata."""
        return self._metadata

    def get_metrics(self) -> dict:
        """Return collected metrics."""
        return self._metrics

    @abstractmethod
    def get_config(self) -> ProviderConfig:
        """Return provider configuration."""
        raise NotImplementedError

    @abstractmethod
    def extract_provider_info(self, family: Metric) -> dict | None:
        """Extract provider information from metric family."""
        raise NotImplementedError

    @abstractmethod
    def extract_resource_info(self, family: Metric) -> dict | None:
        """Extract resource information from metric family."""
        raise NotImplementedError

    @abstractmethod
    def extract_available_metrics(self, family: Metric) -> list[str] | None:
        """Extract available metrics from metric family."""
        raise NotImplementedError

    def process_metrics(
        self, resource: str, metrics: dict, update_interval: int
    ) -> dict | None:
        """Process metrics and return sensor metrics."""
        sensor_metrics = {}
        # CPU
        cpu_usage_pct, cpu_core_usage_pct = self._calculate_cpu_usage(
            resource, metrics, update_interval
        )
        sensor_metrics[METRIC_CPU_USAGE_PCT] = cpu_usage_pct
        # Memory
        memory_usage_bytes, memory_usage_pct = self._calculate_memory_usage(
            resource, metrics
        )
        sensor_metrics[METRIC_MEMORY_USAGE_BYTES] = memory_usage_bytes
        sensor_metrics[METRIC_MEMORY_USAGE_PCT] = memory_usage_pct
        # Disk
        disk_usage_bytes, disk_usage_pct = self._calculate_disk_usage(resource, metrics)
        sensor_metrics[METRIC_DISK_USAGE_BYTES] = disk_usage_bytes
        sensor_metrics[METRIC_DISK_USAGE_PCT] = disk_usage_pct
        # Network
        network_receive_bytes_per_second, network_transmit_bytes_per_second = (
            self._calculate_network_io(resource, metrics, update_interval)
        )
        sensor_metrics[METRIC_NETWORK_RECEIVE_BYTES] = network_receive_bytes_per_second
        sensor_metrics[METRIC_NETWORK_TRANSMIT_BYTES] = (
            network_transmit_bytes_per_second
        )
        # Uptime
        uptime_seconds, start_time_seconds = self._calculate_uptime(resource, metrics)
        sensor_metrics[METRIC_UPTIME_SECONDS] = uptime_seconds
        if start_time_seconds is not None:
            last_start_time = datetime.fromtimestamp(
                float(start_time_seconds), dt_util.UTC
            )
            self.last_start_time = last_start_time
        # Return sensor metrics
        return sensor_metrics

    @abstractmethod
    def _calculate_cpu_usage(
        self, resource: str, metrics: dict, update_interval: int
    ) -> tuple[float, list[float]]:
        """Calculate CPU usage."""
        raise NotImplementedError

    @abstractmethod
    def _calculate_memory_usage(
        self, resource: str, metrics: dict
    ) -> tuple[int, float]:
        """Calculate memory usage."""
        raise NotImplementedError

    @abstractmethod
    def _calculate_disk_usage(self, resource: str, metrics: dict) -> tuple[int, float]:
        """Calculate disk usage."""
        raise NotImplementedError

    @abstractmethod
    def _calculate_network_io(
        self, resource: str, metrics: dict, update_interval: int
    ) -> tuple[int, int]:
        """Calculate network io."""
        raise NotImplementedError

    @abstractmethod
    def _calculate_uptime(self, resource: str, metrics: dict) -> tuple[int, float]:
        """Calculate uptime."""
        raise NotImplementedError

    def add_metric_value(
        self,
        resource_id: str,
        metric_key: str,
        sample: Sample,
    ):
        """Add metric value to metrics data."""
        if resource_id not in self._metrics:
            self._metrics[resource_id] = {}
        self._metrics[resource_id][metric_key] = sample.value
