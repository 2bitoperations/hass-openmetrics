"""Node Exporter provider."""

from custom_components.openmetrics.metrics.data import (
    ResourceInfoData,
)

from ..const import (
    METRIC_CPU_TEMP,
    METRIC_CPU_USAGE_PCT,
    METRIC_DISK_USAGE_BYTES,
    METRIC_DISK_USAGE_PCT,
    METRIC_MEMORY_USAGE_BYTES,
    METRIC_MEMORY_USAGE_PCT,
    METRIC_NETWORK_RECEIVE_BYTES,
    METRIC_NETWORK_TRANSMIT_BYTES,
    METRIC_UPTIME_SECONDS,
    NODE_BOOT_TIME,
    NODE_CPU_IDLE_SECONDS,
    NODE_CPU_TEMP,
    NODE_EXPORTER_BUILD_INFO,
    NODE_FILESYSTEM_FREE,
    NODE_FILESYSTEM_SIZE,
    NODE_MEMORY_FREE,
    NODE_MEMORY_SWAP_TOTAL,
    NODE_MEMORY_TOTAL,
    NODE_NETWORK_RECEIVE,
    NODE_NETWORK_TRANSMIT,
    NODE_OS_INFO,
    NODE_TIME,
    NODE_UNAME_INFO,
    PROVIDER_NAME_NODE_EXPORTER,
    RESOURCE_TYPE_NODE,
)
from ..lib.metrics_core import Metric
from ..metrics import MetricFilter
from .base import MetricsProvider, ProviderConfig


class NodeExporterProvider(MetricsProvider):
    """Node Exporter metrics provider."""

    def __init__(self):
        """Initialize node exporter provider."""
        super().__init__()
        self.resource_info = ResourceInfoData(
            type=RESOURCE_TYPE_NODE, name=None, software=None, version=None
        )
        self._metadata.resources.append(self.resource_info)

    def get_config(self) -> ProviderConfig:
        """Return provider configuration."""
        return ProviderConfig(
            identifier_metric=NODE_EXPORTER_BUILD_INFO,
            resource_identifier="nodename",
            version_label="version",
            resource_type=RESOURCE_TYPE_NODE,
            provider_name=PROVIDER_NAME_NODE_EXPORTER,
            metric_filters=[
                MetricFilter(metric_name=METRIC_UPTIME_SECONDS, metric_key=NODE_TIME),
                MetricFilter(
                    metric_name=METRIC_UPTIME_SECONDS, metric_key=NODE_BOOT_TIME
                ),
                MetricFilter(
                    metric_name=METRIC_CPU_TEMP,
                    metric_key=NODE_CPU_TEMP,
                    label_filters={"type": "cpu-thermal"},
                ),
                MetricFilter(
                    metric_name=METRIC_CPU_USAGE_PCT,
                    metric_key=NODE_CPU_IDLE_SECONDS,
                    label_filters={"mode": "idle"},
                ),
                MetricFilter(
                    metric_name=METRIC_MEMORY_USAGE_BYTES,
                    metric_key=NODE_MEMORY_FREE,
                ),
                MetricFilter(
                    metric_name=METRIC_MEMORY_USAGE_BYTES,
                    metric_key=NODE_MEMORY_TOTAL,
                ),
                MetricFilter(
                    metric_name=METRIC_MEMORY_USAGE_BYTES,
                    metric_key=NODE_MEMORY_SWAP_TOTAL,
                ),
                MetricFilter(
                    metric_name=METRIC_MEMORY_USAGE_PCT, metric_key=NODE_MEMORY_FREE
                ),
                MetricFilter(
                    metric_name=METRIC_MEMORY_USAGE_PCT,
                    metric_key=NODE_MEMORY_TOTAL,
                ),
                MetricFilter(
                    metric_name=METRIC_MEMORY_USAGE_PCT,
                    metric_key=NODE_MEMORY_SWAP_TOTAL,
                ),
                MetricFilter(
                    metric_name=METRIC_DISK_USAGE_BYTES,
                    metric_key=NODE_FILESYSTEM_SIZE,
                    label_filters={"mountpoint": "/"},
                ),
                MetricFilter(
                    metric_name=METRIC_DISK_USAGE_BYTES,
                    metric_key=NODE_FILESYSTEM_FREE,
                    label_filters={"mountpoint": "/"},
                ),
                MetricFilter(
                    metric_name=METRIC_DISK_USAGE_PCT,
                    metric_key=NODE_FILESYSTEM_SIZE,
                    label_filters={"mountpoint": "/"},
                ),
                MetricFilter(
                    metric_name=METRIC_DISK_USAGE_PCT,
                    metric_key=NODE_FILESYSTEM_FREE,
                    label_filters={"mountpoint": "/"},
                ),
                MetricFilter(
                    metric_name=METRIC_NETWORK_RECEIVE_BYTES,
                    metric_key=NODE_NETWORK_RECEIVE,
                    label_filters={"device": "eth0"},
                ),
                MetricFilter(
                    metric_name=METRIC_NETWORK_TRANSMIT_BYTES,
                    metric_key=NODE_NETWORK_TRANSMIT,
                    label_filters={"device": "eth0"},
                ),
            ],
        )

    def extract_provider_info(self, family: Metric) -> None:
        """Extract and store provider information."""
        if family.name == self.get_config().identifier_metric and family.samples:
            self._metadata.provider_info.version = family.samples[0].labels[
                self.get_config().version_label
            ]

    def extract_resource_info(self, family: Metric) -> None:
        """Extract and store node resource information."""
        if family.name == NODE_UNAME_INFO:
            for sample in family.samples:
                nodename = sample.labels.get("nodename", None)
                if nodename:
                    self.resource_info.name = nodename
        elif family.name == NODE_OS_INFO:
            for sample in family.samples:
                self.resource_info.software = sample.labels.get("pretty_name", "")
                self.resource_info.version = sample.labels.get("version", "")

    def extract_available_metrics(self, family: Metric) -> None:
        """Extract and store available metrics."""
        for metric_filter in self.get_config().metric_filters:
            if (
                family.name == metric_filter.metric_key
                and metric_filter.metric_name not in self._metadata.available_metrics
            ):
                self._metadata.available_metrics.append(metric_filter.metric_name)
