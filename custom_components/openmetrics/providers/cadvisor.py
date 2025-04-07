"""Cadvisor metrics provider."""

from datetime import datetime
from math import floor
from time import time
from typing import Any

from homeassistant.util import dt as dt_util

from ..const import (
    METRIC_CPU_USAGE_PCT,
    METRIC_DEVICE_NAME,
    METRIC_DISK_USAGE_BYTES,
    METRIC_DISK_USAGE_PCT,
    METRIC_MEMORY_USAGE_BYTES,
    METRIC_MEMORY_USAGE_PCT,
    METRIC_NETWORK_RECEIVE_BYTES,
    METRIC_NETWORK_TRANSMIT_BYTES,
    METRIC_UPTIME_SECONDS,
    PROPERTY_CPU_CORES,
    PROPERTY_DISK_SIZE,
    PROPERTY_LAST_START_TIME,
    PROPERTY_MEMORY_SIZE,
    PROVIDER_NAME_CADVISOR,
    RESOURCE_TYPE_CONTAINER,
)
from ..lib.metrics_core import Metric
from ..metrics import MetricFilter
from ..metrics.data import ProviderInfoData, ResourceInfoData
from ..unit_converters import convert_bytes, get_appropriate_unit
from .base import MetricsProvider

# Metrics
CADVISOR_VERSION_INFO = "cadvisor_version_info"
MACHINE_CPU_CORES = "machine_cpu_cores"
MACHINE_MEMORY = "machine_memory_bytes"
MACHINE_SWAP = "machine_swap_bytes"
CONTAINER_START_TIME = "container_start_time_seconds"
CONTAINER_CPU_USAGE = "container_cpu_usage_seconds"
CONTAINER_MEMORY_LIMIT = "container_spec_memory_limit_bytes"
CONTAINER_MEMORY_USAGE = "container_memory_usage_bytes"
CONTAIENR_MEMORY_SWAP = "container_memory_swap"
CONTAINER_FS_USAGE = "container_fs_usage_bytes"
CONTAINER_FS_LIMIT = "container_fs_limit_bytes"
CONTAINER_NETWORK_RECEIVE = "container_network_receive_bytes"
CONTAINER_NETWORK_TRANSMIT = "container_network_transmit_bytes"
# Labels
CADVISOR_VERSION_LABEL = "cadvisorVersion"
CADVISOR_RESOURCE_LABEL = "name"
CONTAINER_IMAGE_NAME_LABEL = "image"
CONTAINER_IMAGE_VERSION_LABEL = "container_label_org_opencontainers_image_version"
CONTAINER_IMAGE_SERIAL_LABEL = "container_label_org_opencontainers_image_revision"
CONTAINER_NETWORK_INTERFACE_LABEL = "interface"
MACHINE_ID_LABEL = "machine_id"

PROVIDER_FILTERS = [
    MetricFilter(
        metric_key=CADVISOR_VERSION_INFO,
        label_filters={CADVISOR_VERSION_LABEL: ".+"},
    )
]


class CadvisorProvider(MetricsProvider):
    """cAdvisor metrics provider."""

    metric_filters = [
        MetricFilter(
            metric_key=CONTAINER_START_TIME,
            label_filters={
                CONTAINER_IMAGE_NAME_LABEL: ".+",
                CADVISOR_RESOURCE_LABEL: ".+",
            },
            resource_label=CADVISOR_RESOURCE_LABEL,
        ),
        MetricFilter(
            metric_key=MACHINE_CPU_CORES, label_filters={MACHINE_ID_LABEL: ".+"}
        ),
        MetricFilter(
            metric_key=CONTAINER_CPU_USAGE,
            label_filters={
                CONTAINER_IMAGE_NAME_LABEL: ".+",
                CADVISOR_RESOURCE_LABEL: ".+",
            },
            resource_label=CADVISOR_RESOURCE_LABEL,
        ),
        MetricFilter(metric_key=MACHINE_MEMORY, label_filters={MACHINE_ID_LABEL: ".+"}),
        MetricFilter(metric_key=MACHINE_SWAP, label_filters={MACHINE_ID_LABEL: ".+"}),
        MetricFilter(
            metric_key=CONTAINER_MEMORY_LIMIT,
            label_filters={
                CONTAINER_IMAGE_NAME_LABEL: ".+",
                CADVISOR_RESOURCE_LABEL: ".+",
            },
            resource_label=CADVISOR_RESOURCE_LABEL,
        ),
        MetricFilter(
            metric_key=CONTAINER_MEMORY_USAGE,
            label_filters={
                CONTAINER_IMAGE_NAME_LABEL: ".+",
                CADVISOR_RESOURCE_LABEL: ".+",
            },
            resource_label=CADVISOR_RESOURCE_LABEL,
        ),
        MetricFilter(
            metric_key=CONTAIENR_MEMORY_SWAP,
            label_filters={
                CONTAINER_IMAGE_NAME_LABEL: ".+",
                CADVISOR_RESOURCE_LABEL: ".+",
            },
            resource_label=CADVISOR_RESOURCE_LABEL,
        ),
        MetricFilter(
            metric_key=CONTAINER_FS_USAGE,
            label_filters={
                CONTAINER_IMAGE_NAME_LABEL: ".+",
                CADVISOR_RESOURCE_LABEL: ".+",
            },
            resource_label=CADVISOR_RESOURCE_LABEL,
        ),
        MetricFilter(
            metric_key=CONTAINER_FS_LIMIT,
            label_filters={
                CONTAINER_IMAGE_NAME_LABEL: ".+",
                CADVISOR_RESOURCE_LABEL: ".+",
            },
            resource_label=CADVISOR_RESOURCE_LABEL,
        ),
        MetricFilter(
            metric_key=CONTAINER_NETWORK_RECEIVE,
            label_filters={
                CONTAINER_IMAGE_NAME_LABEL: ".+",
                CADVISOR_RESOURCE_LABEL: ".+",
                CONTAINER_NETWORK_INTERFACE_LABEL: "eth0",
            },
            resource_label=CADVISOR_RESOURCE_LABEL,
        ),
        MetricFilter(
            metric_key=CONTAINER_NETWORK_TRANSMIT,
            label_filters={
                CONTAINER_IMAGE_NAME_LABEL: ".+",
                CADVISOR_RESOURCE_LABEL: ".+",
                CONTAINER_NETWORK_INTERFACE_LABEL: "eth0",
            },
            resource_label=CADVISOR_RESOURCE_LABEL,
        ),
    ]
    found_metrics = {
        CONTAINER_CPU_USAGE: False,
        CONTAINER_MEMORY_LIMIT: False,
        CONTAINER_MEMORY_USAGE: False,
        MACHINE_MEMORY: False,
        CONTAINER_FS_LIMIT: False,
        CONTAINER_FS_USAGE: False,
        CONTAINER_NETWORK_RECEIVE: False,
        CONTAINER_NETWORK_TRANSMIT: False,
        CONTAINER_START_TIME: False,
    }

    def __init__(self):
        """Initialize cAdvisor provider."""
        super().__init__(PROVIDER_NAME_CADVISOR, RESOURCE_TYPE_CONTAINER)
        self.provider_filters = PROVIDER_FILTERS

    def extract_provider_info(self, family: Metric, provider_info: ProviderInfoData):
        """Extract and store provider information."""
        if family.name == CADVISOR_VERSION_INFO and family.samples:
            provider_info.version = family.samples[0].labels[CADVISOR_VERSION_LABEL]

    def extract_resource_info(self, family: Metric, resources: dict):
        """Extract and store container resource information."""
        if family.name == CONTAINER_START_TIME:
            for sample in family.samples:
                name = sample.labels.get(CADVISOR_RESOURCE_LABEL, None)
                if name is not None and name != "" and name not in resources:
                    model = None
                    software = name
                    version = None
                    serial_number = None
                    # Get model
                    if sample.labels.get(CONTAINER_IMAGE_NAME_LABEL):
                        model = sample.labels[CONTAINER_IMAGE_NAME_LABEL]
                    # Get version
                    if sample.labels.get(CONTAINER_IMAGE_VERSION_LABEL):
                        version = sample.labels[CONTAINER_IMAGE_VERSION_LABEL]
                    # Get serial number
                    if sample.labels.get(CONTAINER_IMAGE_SERIAL_LABEL):
                        serial_number = sample.labels[CONTAINER_IMAGE_SERIAL_LABEL]
                    # Create resource info
                    resources[name] = ResourceInfoData(
                        type=RESOURCE_TYPE_CONTAINER,
                        name=name,
                        model=model,
                        software=software,
                        version=version,
                        serial_number=serial_number,
                    )

    def collect_supported_metric(self, family: Metric, available_metrics: list[str]):
        """Collect supported metrics."""
        # Add metric to list if not already added
        if family.name in self.found_metrics:
            self.found_metrics[family.name] = True
            if family.name == CONTAINER_CPU_USAGE:
                self._add_str_to_list_uniquely(METRIC_CPU_USAGE_PCT, available_metrics)
            elif family.name == CONTAINER_START_TIME:
                self._add_str_to_list_uniquely(METRIC_UPTIME_SECONDS, available_metrics)
        # Add name metric
        self._add_str_to_list_uniquely(METRIC_DEVICE_NAME, available_metrics)
        # Add paired metrics after checking both components are present
        if (
            self.found_metrics[CONTAINER_MEMORY_LIMIT]
            or self.found_metrics[MACHINE_MEMORY]
        ) and self.found_metrics[CONTAINER_MEMORY_USAGE]:
            self._add_str_to_list_uniquely(METRIC_MEMORY_USAGE_BYTES, available_metrics)
            self._add_str_to_list_uniquely(METRIC_MEMORY_USAGE_PCT, available_metrics)

        if (
            self.found_metrics[CONTAINER_FS_LIMIT]
            and self.found_metrics[CONTAINER_FS_USAGE]
        ):
            self._add_str_to_list_uniquely(METRIC_DISK_USAGE_BYTES, available_metrics)
            self._add_str_to_list_uniquely(METRIC_DISK_USAGE_PCT, available_metrics)

        if (
            self.found_metrics[CONTAINER_NETWORK_RECEIVE]
            and self.found_metrics[CONTAINER_NETWORK_TRANSMIT]
        ):
            self._add_str_to_list_uniquely(
                METRIC_NETWORK_RECEIVE_BYTES, available_metrics
            )
            self._add_str_to_list_uniquely(
                METRIC_NETWORK_TRANSMIT_BYTES, available_metrics
            )

    def _pre_process_metrics(self, metrics: dict):
        """Pre-process metrics."""
        # Check if metrics are available
        if not metrics:
            return
        if self.RESOURCE_NAME in metrics:
            # Get machine related metrics
            for metric_key in metrics[self.RESOURCE_NAME]:
                if metric_key == MACHINE_CPU_CORES:
                    cpu_cores = metrics[self.RESOURCE_NAME][metric_key]
                    cpu_cores_metric_key = metric_key
                elif metric_key == MACHINE_MEMORY:
                    memory_bytes = metrics[self.RESOURCE_NAME][metric_key]
                    memory_bytes_metric_key = metric_key
                elif metric_key == MACHINE_SWAP:
                    swap_bytes = metrics[self.RESOURCE_NAME][metric_key]
                    swap_bytes_metric_key = metric_key
            # Share common metrics
            for metric_key, metric in metrics.items():
                if metric_key != self.RESOURCE_NAME:
                    # Share CPU cores
                    if cpu_cores is not None:
                        metric[cpu_cores_metric_key] = cpu_cores
                    # Share memory
                    if memory_bytes is not None:
                        metric[memory_bytes_metric_key] = memory_bytes
                    # Share swap
                    if swap_bytes is not None:
                        metric[swap_bytes_metric_key] = swap_bytes
            # Remove machine metrics key
            metrics.pop(self.RESOURCE_NAME)

    def _calculate_cpu_usage(
        self,
        resource: str,
        metrics: dict,
        update_interval: int,
    ) -> dict[str, Any]:
        """Calculate CPU usage (pct, dict)."""
        sensor_metrics = {}
        # Check if metrics are available
        if not metrics:
            return sensor_metrics
        # Initialize variables
        prev_value: float | None = None
        current_value: float | None = None
        cpu_usage_pct_core: float | None = None
        cpu_usage_pct: float | None = None
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
                # Calculate CPU usage
                cpu_seconds_delta = (
                    current_value - prev_value
                )  # max = update interval * cores
                cpu_usage_pct = cpu_seconds_delta / update_interval * 100
                if cpu_usage_pct and cpu_usage_pct > 100:
                    cpu_usage_pct = 100
                elif cpu_usage_pct and cpu_usage_pct < 0:
                    cpu_usage_pct = 0
                # Set CPU usage
                sensor_metrics[METRIC_CPU_USAGE_PCT] = cpu_usage_pct
                # Get CPU cores
                cpu_cores = metrics.get(MACHINE_CPU_CORES, 1)
                # Set CPU cores
                sensor_metrics[PROPERTY_CPU_CORES] = cpu_cores
                # Calculate CPU usage per core
                if cpu_usage_pct > 0 and cpu_cores:
                    cpu_usage_pct_core = cpu_usage_pct / cpu_cores
                else:
                    cpu_usage_pct_core = cpu_usage_pct
                if cpu_cores:
                    for cpu_core in range(int(cpu_cores)):
                        cpu_core_usage[cpu_core] = cpu_usage_pct_core
        # Return values
        return sensor_metrics

    def _calculate_memory_usage(
        self,
        resource: str,
        metrics: dict,
    ) -> dict[str, Any]:
        """Calculate memory usage (used bytes, used pct)."""
        sensor_metrics = {}
        # Check if metrics are available
        if not metrics:
            return sensor_metrics
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
        # Set memory usage
        sensor_metrics[METRIC_MEMORY_USAGE_BYTES] = memory_usage_bytes
        sensor_metrics[METRIC_MEMORY_USAGE_PCT] = memory_usage_pct
        # Set memory size
        if memory_total_bytes:
            # Convert memory size to appropriate unit
            target_unit = get_appropriate_unit(memory_total_bytes)
            sensor_metrics[PROPERTY_MEMORY_SIZE] = (
                f"{floor(convert_bytes(memory_total_bytes, target_unit))} {target_unit}"
            )
        # Return values
        return sensor_metrics

    def _calculate_disk_usage(self, resource: str, metrics: dict) -> dict[str, Any]:
        """Calculate disk usage (used bytes, used pct)."""
        sensor_metrics = {}
        # Check if metrics are available
        if not metrics:
            return sensor_metrics
        # Initialize variables
        disk_total_bytes: int | None = None
        disk_usage_bytes: int | None = None
        # Get values
        if CONTAINER_FS_LIMIT in metrics:
            disk_total_bytes = metrics[CONTAINER_FS_LIMIT]
            disk_usage_bytes = metrics[CONTAINER_FS_USAGE]
        # Calculate disk usage
        if disk_total_bytes is not None and disk_usage_bytes is not None:
            sensor_metrics[METRIC_DISK_USAGE_BYTES] = disk_usage_bytes
            sensor_metrics[METRIC_DISK_USAGE_PCT] = (
                disk_usage_bytes / disk_total_bytes * 100
            )
        # Set disk size
        if disk_total_bytes:
            target_unit = get_appropriate_unit(disk_total_bytes)
            sensor_metrics[PROPERTY_DISK_SIZE] = (
                f"{floor(convert_bytes(disk_total_bytes, target_unit))} {target_unit}"
            )
        # Return values
        return sensor_metrics

    def _calculate_network_io(
        self, resource: str, metrics: dict, update_interval: int
    ) -> dict[str, Any]:
        """Calculate network IO (receive bytes, transmit bytes)."""
        sensor_metrics = {}
        # Check if metrics are available
        if not metrics:
            return sensor_metrics
        # Check if update interval is valid
        if update_interval is None or update_interval <= 0:
            raise ValueError("Update interval must be positive")
        # Initialize variables
        prev_value_receive: float | None = None
        current_value_receive: float | None = None
        prev_value_transmit: float | None = None
        current_value_transmit: float | None = None
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
                sensor_metrics[METRIC_NETWORK_RECEIVE_BYTES] = (
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
                sensor_metrics[METRIC_NETWORK_TRANSMIT_BYTES] = (
                    current_value_transmit - prev_value_transmit
                ) / update_interval

        # Return values
        return sensor_metrics

    def _calculate_uptime(self, resource: str, metrics: dict) -> dict[str, Any]:
        """Calculate uptime."""
        sensor_metrics = {}
        # Check if metrics are available
        if not metrics:
            return sensor_metrics
        # Get values
        if CONTAINER_START_TIME in metrics:
            start_time = int(metrics[CONTAINER_START_TIME])
            sensor_metrics[PROPERTY_LAST_START_TIME] = datetime.fromtimestamp(
                float(start_time), dt_util.UTC
            )
        # Calculate uptime
        if start_time is not None:
            sensor_metrics[METRIC_UPTIME_SECONDS] = int(time()) - start_time
        # Return values
        return sensor_metrics
