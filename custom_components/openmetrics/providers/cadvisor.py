"""Cadvisor metrics provider."""

from ..const import (
    CADVISOR_VERSION_INFO,
    CONTAIENR_MEMORY_SWAP,
    CONTAINER_CPU_USAGE,
    CONTAINER_FS_LIMIT,
    CONTAINER_FS_USAGE,
    CONTAINER_MEMORY_LIMIT,
    CONTAINER_MEMORY_USAGE,
    CONTAINER_NETWORK_RECEIVE,
    CONTAINER_NETWORK_TRANSMIT,
    CONTAINER_START_TIME,
    MACHINE_CPU_CORES,
    MACHINE_MEMORY,
    MACHINE_SWAP,
    METRIC_CPU_USAGE_PCT,
    METRIC_DISK_USAGE_BYTES,
    METRIC_DISK_USAGE_PCT,
    METRIC_MEMORY_USAGE_BYTES,
    METRIC_MEMORY_USAGE_PCT,
    METRIC_NETWORK_RECEIVE_BYTES,
    METRIC_NETWORK_TRANSMIT_BYTES,
    METRIC_UPTIME_SECONDS,
    PROVIDER_NAME_CADVISOR,
    RESOURCE_TYPE_CONTAINER,
)
from ..lib.metrics_core import Metric
from ..metrics import MetricFilter
from .base import MetricsProvider, ProviderConfig


class CadvisorProvider(MetricsProvider):
    """cAdvisor metrics provider."""

    def __init__(self):
        """Initialize cAdvisor provider."""
        super().__init__()
        self._provider_info = {}
        self._resources = {}
        self._available_metrics = set()

    def get_config(self) -> ProviderConfig:
        """Return provider configuration."""
        return ProviderConfig(
            identifier_metric=CADVISOR_VERSION_INFO,
            resource_identifier="name",
            version_label="cadvisorVersion",
            resource_type=RESOURCE_TYPE_CONTAINER,
            provider_name=PROVIDER_NAME_CADVISOR,
            metric_filters=[
                MetricFilter(
                    metric_name=METRIC_UPTIME_SECONDS,
                    metric_key=CONTAINER_START_TIME,
                    label_filters={"image": "*", "name": "*"},
                ),
                MetricFilter(
                    metric_name=METRIC_CPU_USAGE_PCT, metric_key=MACHINE_CPU_CORES
                ),
                MetricFilter(
                    metric_name=METRIC_CPU_USAGE_PCT,
                    metric_key=CONTAINER_CPU_USAGE,
                    label_filters={"image": "*", "name": "*"},
                ),
                MetricFilter(
                    metric_name=METRIC_MEMORY_USAGE_BYTES, metric_key=MACHINE_MEMORY
                ),
                MetricFilter(
                    metric_name=METRIC_MEMORY_USAGE_BYTES, metric_key=MACHINE_SWAP
                ),
                MetricFilter(
                    metric_name=METRIC_MEMORY_USAGE_BYTES,
                    metric_key=CONTAINER_MEMORY_LIMIT,
                    label_filters={"image": "*", "name": "*"},
                ),
                MetricFilter(
                    metric_name=METRIC_MEMORY_USAGE_BYTES,
                    metric_key=CONTAINER_MEMORY_USAGE,
                    label_filters={"image": "*", "name": "*"},
                ),
                MetricFilter(
                    metric_name=METRIC_MEMORY_USAGE_BYTES,
                    metric_key=CONTAIENR_MEMORY_SWAP,
                    label_filters={"image": "*", "name": "*"},
                ),
                MetricFilter(
                    metric_name=METRIC_MEMORY_USAGE_PCT, metric_key=MACHINE_MEMORY
                ),
                MetricFilter(
                    metric_name=METRIC_MEMORY_USAGE_PCT, metric_key=MACHINE_SWAP
                ),
                MetricFilter(
                    metric_name=METRIC_MEMORY_USAGE_PCT,
                    metric_key=CONTAINER_MEMORY_LIMIT,
                    label_filters={"image": "*", "name": "*"},
                ),
                MetricFilter(
                    metric_name=METRIC_MEMORY_USAGE_PCT,
                    metric_key=CONTAINER_MEMORY_USAGE,
                    label_filters={"image": "*", "name": "*"},
                ),
                MetricFilter(
                    metric_name=METRIC_MEMORY_USAGE_PCT,
                    metric_key=CONTAIENR_MEMORY_SWAP,
                    label_filters={"image": "*", "name": "*"},
                ),
                MetricFilter(
                    metric_name=METRIC_DISK_USAGE_BYTES,
                    metric_key=CONTAINER_FS_USAGE,
                    label_filters={"image": "*", "name": "*"},
                ),
                MetricFilter(
                    metric_name=METRIC_DISK_USAGE_BYTES,
                    metric_key=CONTAINER_FS_LIMIT,
                    label_filters={"image": "*", "name": "*"},
                ),
                MetricFilter(
                    metric_name=METRIC_DISK_USAGE_PCT,
                    metric_key=CONTAINER_FS_USAGE,
                    label_filters={"image": "*", "name": "*"},
                ),
                MetricFilter(
                    metric_name=METRIC_DISK_USAGE_PCT,
                    metric_key=CONTAINER_FS_LIMIT,
                    label_filters={"image": "*", "name": "*"},
                ),
                MetricFilter(
                    metric_name=METRIC_NETWORK_RECEIVE_BYTES,
                    metric_key=CONTAINER_NETWORK_RECEIVE,
                    label_filters={"image": "*", "name": "*"},
                ),
                MetricFilter(
                    metric_name=METRIC_NETWORK_TRANSMIT_BYTES,
                    metric_key=CONTAINER_NETWORK_TRANSMIT,
                    label_filters={"image": "*", "name": "*"},
                ),
            ],
        )

    def extract_provider_info(self, family: Metric) -> None:
        """Extract and store provider information."""
        if family.name == self.get_config().identifier_metric and family.samples:
            self._provider_info = {
                "name": self.get_config().provider_name,
                "type": self.get_config().resource_type,
                "version": family.samples[0].labels[self.get_config().version_label],
            }

    def extract_resource_info(self, family: Metric) -> None:
        """Extract and store container resource information."""
        if family.name == CONTAINER_START_TIME:
            for sample in family.samples:
                name = sample.labels.get("name", None)
                if name is not None and name != "":
                    self._resources[name] = {
                        "type": RESOURCE_TYPE_CONTAINER,
                        "name": name,
                        "software": sample.labels.get("image", ""),
                        "version": sample.labels.get(
                            "container_label_org_opencontainers_image_version", ""
                        ),
                    }

    def extract_available_metrics(self, family: Metric) -> None:
        """Extract and store available metrics."""
        for metric_filter in self.get_config().metric_filters:
            if family.name == metric_filter.metric_key:
                self._available_metrics.add(metric_filter.metric_name)
