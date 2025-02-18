"""Cadvisor metrics provider."""

from time import time

from ..const import (
    CADVISOR_RESOURCE_LABEL,
    CADVISOR_VERSION_INFO,
    CADVISOR_VERSION_LABEL,
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
from ..metrics.data import ResourceInfoData
from .base import MetricsProvider, ProviderConfig


class CadvisorProvider(MetricsProvider):
    """cAdvisor metrics provider."""

    def __init__(self):
        """Initialize cAdvisor provider."""
        super().__init__(PROVIDER_NAME_CADVISOR, RESOURCE_TYPE_CONTAINER)

    def get_config(self) -> ProviderConfig:
        """Return provider configuration."""
        return ProviderConfig(
            identifier_metric=CADVISOR_VERSION_INFO,
            version_label=CADVISOR_VERSION_LABEL,
            resource_identifier=CADVISOR_RESOURCE_LABEL,
            metric_filters=[
                MetricFilter(
                    metric_name=METRIC_UPTIME_SECONDS,
                    metric_key=CONTAINER_START_TIME,
                    label_filters={"image": "*", CADVISOR_RESOURCE_LABEL: "*"},
                ),
                MetricFilter(
                    metric_name=METRIC_CPU_USAGE_PCT, metric_key=MACHINE_CPU_CORES
                ),
                MetricFilter(
                    metric_name=METRIC_CPU_USAGE_PCT,
                    metric_key=CONTAINER_CPU_USAGE,
                    label_filters={"image": "*", CADVISOR_RESOURCE_LABEL: "*"},
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
                    label_filters={"image": "*", CADVISOR_RESOURCE_LABEL: "*"},
                ),
                MetricFilter(
                    metric_name=METRIC_MEMORY_USAGE_BYTES,
                    metric_key=CONTAINER_MEMORY_USAGE,
                    label_filters={"image": "*", CADVISOR_RESOURCE_LABEL: "*"},
                ),
                MetricFilter(
                    metric_name=METRIC_MEMORY_USAGE_BYTES,
                    metric_key=CONTAIENR_MEMORY_SWAP,
                    label_filters={"image": "*", CADVISOR_RESOURCE_LABEL: "*"},
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
                    label_filters={"image": "*", CADVISOR_RESOURCE_LABEL: "*"},
                ),
                MetricFilter(
                    metric_name=METRIC_MEMORY_USAGE_PCT,
                    metric_key=CONTAINER_MEMORY_USAGE,
                    label_filters={"image": "*", CADVISOR_RESOURCE_LABEL: "*"},
                ),
                MetricFilter(
                    metric_name=METRIC_MEMORY_USAGE_PCT,
                    metric_key=CONTAIENR_MEMORY_SWAP,
                    label_filters={"image": "*", CADVISOR_RESOURCE_LABEL: "*"},
                ),
                MetricFilter(
                    metric_name=METRIC_DISK_USAGE_BYTES,
                    metric_key=CONTAINER_FS_USAGE,
                    label_filters={"image": "*", CADVISOR_RESOURCE_LABEL: "*"},
                ),
                MetricFilter(
                    metric_name=METRIC_DISK_USAGE_BYTES,
                    metric_key=CONTAINER_FS_LIMIT,
                    label_filters={"image": "*", CADVISOR_RESOURCE_LABEL: "*"},
                ),
                MetricFilter(
                    metric_name=METRIC_DISK_USAGE_PCT,
                    metric_key=CONTAINER_FS_USAGE,
                    label_filters={"image": "*", CADVISOR_RESOURCE_LABEL: "*"},
                ),
                MetricFilter(
                    metric_name=METRIC_DISK_USAGE_PCT,
                    metric_key=CONTAINER_FS_LIMIT,
                    label_filters={"image": "*", CADVISOR_RESOURCE_LABEL: "*"},
                ),
                MetricFilter(
                    metric_name=METRIC_NETWORK_RECEIVE_BYTES,
                    metric_key=CONTAINER_NETWORK_RECEIVE,
                    label_filters={"image": "*", CADVISOR_RESOURCE_LABEL: "*"},
                ),
                MetricFilter(
                    metric_name=METRIC_NETWORK_TRANSMIT_BYTES,
                    metric_key=CONTAINER_NETWORK_TRANSMIT,
                    label_filters={"image": "*", CADVISOR_RESOURCE_LABEL: "*"},
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
        """Extract and store container resource information."""
        if family.name == CONTAINER_START_TIME:
            # Clear existing resources (to prevent duplicates in case of reconfiguration)
            self._metadata.resources.clear()
            for sample in family.samples:
                name = sample.labels.get("name", None)
                if name is not None and name != "":
                    self._metadata.resources.append(
                        ResourceInfoData(
                            type=RESOURCE_TYPE_CONTAINER,
                            name=name,
                            software=sample.labels.get("image", ""),
                            version=sample.labels.get(
                                "container_label_org_opencontainers_image_version", ""
                            ),
                        )
                    )

    def extract_available_metrics(self, family: Metric) -> None:
        """Extract and store available metrics."""
        for metric_filter in self.get_config().metric_filters:
            if (
                family.name == metric_filter.metric_key
                and metric_filter.metric_name not in self._metadata.available_metrics
            ):
                self._metadata.available_metrics.append(metric_filter.metric_name)

    def _calculate_cpu_usage(
        self, resource: str, metrics: dict, update_interval: int
    ) -> tuple[float | None, dict[int, float] | None]:
        """Calculate CPU usage."""
        # Check if metrics are available
        if not metrics:
            return None, None
        # Initialize variables
        prev_value = None
        current_value = None
        cpu_usage_pct = None
        cpu_core_usage = {}
        # Calculate CPU usage
        if CONTAINER_CPU_USAGE in metrics:
            # Get current value
            current_value = metrics[CONTAINER_CPU_USAGE]
            # Get previous value
            if resource in self._previous_metrics:
                if CONTAINER_CPU_USAGE in self._previous_metrics[resource]:
                    prev_value = self._previous_metrics[resource][CONTAINER_CPU_USAGE]
            else:
                self._previous_metrics[resource] = {}
            # Set current value as previous value
            self._previous_metrics[resource][CONTAINER_CPU_USAGE] = current_value
            # Calculate CPU usage
            if prev_value is not None and current_value is not None:
                cpu_cores = metrics.get(MACHINE_CPU_CORES, 1)
                cpu_usage_time_delta = (
                    current_value - prev_value
                )  # max = update interval * cores
                cpu_cores_used = cpu_usage_time_delta / update_interval
                cpu_usage_pct = cpu_cores_used / cpu_cores * 100
                if cpu_usage_pct > 100:
                    cpu_usage_pct = 100
                elif cpu_usage_pct < 0:
                    cpu_usage_pct = 0
        # Return values
        return (cpu_usage_pct, cpu_core_usage)

    def _calculate_memory_usage(
        self, resource: str, metrics: dict
    ) -> tuple[int | None, float | None]:
        """Calculate memory usage."""
        # Check if metrics are available
        if not metrics:
            return None, None
        # Initialize variables
        memory_total_bytes: int | None = None
        memory_usage_bytes: int | None = None
        memory_usage_pct: float | None = None
        # Get memory usage
        if CONTAINER_MEMORY_USAGE in metrics:
            memory_usage_bytes = metrics[CONTAINER_MEMORY_USAGE]
        # Get total memory, preferring container limit if available
        memory_total_bytes = metrics.get(CONTAINER_MEMORY_LIMIT) or metrics.get(
            MACHINE_MEMORY
        )
        # Calculate percentage if we have both values
        if memory_total_bytes and memory_usage_bytes and memory_total_bytes > 0:
            memory_usage_pct = memory_usage_bytes / memory_total_bytes * 100
        # Return values
        return memory_usage_bytes, memory_usage_pct

    def _calculate_disk_usage(
        self, resource: str, metrics: dict
    ) -> tuple[int | None, float | None]:
        """Calculate disk usage."""
        # Check if metrics are available
        if not metrics:
            return None, None
        # Initialize variables
        disk_total_bytes = None
        disk_usage_bytes = None
        disk_usage_pct = None
        # Get values
        if CONTAINER_FS_LIMIT in metrics:
            disk_total_bytes = metrics[CONTAINER_FS_LIMIT]
            disk_usage_bytes = metrics[CONTAINER_FS_USAGE]
        # Calculate disk usage
        if disk_total_bytes is not None and disk_usage_bytes is not None:
            disk_usage_pct = disk_usage_bytes / disk_total_bytes * 100
        # Set disk size
        self._set_disk_size(resource, metrics)
        # Return values
        return disk_usage_bytes, disk_usage_pct

    def _set_disk_size(self, resource: str, metrics: dict) -> None:
        """Set disk size."""
        if CONTAINER_FS_LIMIT in metrics:
            self.disk_size = metrics[CONTAINER_FS_LIMIT]

    def _calculate_network_io(
        self, resource: str, metrics: dict, update_interval: int
    ) -> tuple[float | None, float | None]:
        """Calculate network IO."""
        # Check if metrics are available
        if not metrics:
            return None, None
        # Check if update interval is valid
        if update_interval is None or update_interval <= 0:
            raise ValueError("Update interval must be positive")
        # Initialize variables
        prev_value_receive = None
        current_value_receive = None
        prev_value_transmit = None
        current_value_transmit = None
        network_receive_bytes_per_second = None
        network_transmit_bytes_per_second = None
        # Calculate network receive
        if CONTAINER_NETWORK_RECEIVE in metrics:
            # Get current value
            current_value_receive = metrics[CONTAINER_NETWORK_RECEIVE]
            # Get previous value
            if resource in self._previous_metrics:
                if CONTAINER_NETWORK_RECEIVE in self._previous_metrics[resource]:
                    prev_value_receive = self._previous_metrics[resource][
                        CONTAINER_NETWORK_RECEIVE
                    ]
            else:
                self._previous_metrics[resource] = {}
            # Set current value as previous value
            self._previous_metrics[resource][CONTAINER_NETWORK_RECEIVE] = (
                current_value_receive
            )
            # Calculate network receive bytes per second
            if prev_value_receive is not None and current_value_receive is not None:
                network_receive_bytes_per_second = (
                    current_value_receive - prev_value_receive
                ) / update_interval
        # Calculate network transmit
        if CONTAINER_NETWORK_TRANSMIT in metrics:
            # Get current value
            current_value_transmit = metrics[CONTAINER_NETWORK_TRANSMIT]
            # Get previous value
            if resource in self._previous_metrics:
                if CONTAINER_NETWORK_TRANSMIT in self._previous_metrics[resource]:
                    prev_value_transmit = self._previous_metrics[resource][
                        CONTAINER_NETWORK_TRANSMIT
                    ]
            else:
                self._previous_metrics[resource] = {}
            # Set current value as previous value
            self._previous_metrics[resource][CONTAINER_NETWORK_TRANSMIT] = (
                current_value_transmit
            )
            # Calculate network transmit bytes per second
            if prev_value_transmit is not None and current_value_transmit is not None:
                network_transmit_bytes_per_second = (
                    current_value_transmit - prev_value_transmit
                ) / update_interval
        # Return values
        return (network_receive_bytes_per_second, network_transmit_bytes_per_second)

    def _calculate_uptime(
        self, resource: str, metrics: dict
    ) -> tuple[int | None, int | None]:
        """Calculate uptime."""
        # Check if metrics are available
        if not metrics:
            return None, None
        # Initialize variables
        start_time = None
        uptime_seconds = None
        # Get values
        if CONTAINER_START_TIME in metrics:
            start_time = metrics[CONTAINER_START_TIME]
        # Calculate uptime
        if start_time is not None:
            uptime_seconds = int(time()) - start_time
        # Return values
        return uptime_seconds, start_time
