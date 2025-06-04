"""Node Exporter provider."""

import re
from datetime import datetime
from math import floor
from time import time
from typing import Any

from homeassistant.const import UnitOfDataRate, UnitOfInformation
from homeassistant.util import dt as dt_util

from ..const import (
    METRIC_CPU_TEMP,
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
    PROPERTY_NETWORK_SPEED,
    PROVIDER_NAME_NODE_EXPORTER,
    RESOURCE_TYPE_CONTAINER,
    RESOURCE_TYPE_NODE,
)
from ..lib.metrics_core import Metric
from ..lib.samples import Sample
from ..metrics import MetricFilter
from ..metrics.data import (
    ProviderInfoData,
    ResourceInfoData,
)
from ..unit_converters import (
    convert_data_rate,
    convert_data_size,
    get_appropriate_unit,
)
from .base import MetricsProvider

# Metrics
NODE_EXPORTER_BUILD_INFO = "node_exporter_build_info"
NODE_DEVICE_INFO = "node_device_info"
NODE_UNAME_INFO = "node_uname_info"
NODE_OS_INFO = "node_os_info"
NODE_TIME = "node_time_seconds"
NODE_BOOT_TIME = "node_boot_time_seconds"
NODE_HWMON_TEMP = "node_hwmon_temp_celsius"
NODE_CPU_TEMP = "node_thermal_zone_temp"
NODE_CPU_IDLE_SECONDS = "node_cpu_seconds"
NODE_MEMORY_AVAILABLE = "node_memory_MemAvailable_bytes"
NODE_MEMORY_TOTAL = "node_memory_MemTotal_bytes"
NODE_MEMORY_SWAP_TOTAL = "node_memory_SwapTotal_bytes"
NODE_FILESYSTEM_SIZE = "node_filesystem_size_bytes"
NODE_FILESYSTEM_FREE = "node_filesystem_free_bytes"
NODE_NETWORK_RECEIVE = "node_network_receive_bytes"
NODE_NETWORK_TRANSMIT = "node_network_transmit_bytes"
NODE_NETWORK_INTERFACE_SPEED = "node_network_speed_bytes"
NODE_OS_UPDATE_INFO = "node_os_update_info"
NODE_CONTAINER_STATE_HEALTH_STATUS = "container_state_health_status"
NODE_CONTAINER_STATE_STATUS = "container_state_status"
NODE_CONTAINER_STATE_OOMKILLED = "container_state_oomkilled"
NODE_CONTAINER_STATE_STARTEDAT = "container_state_startedat"
NODE_CONTAINER_STATE_FINISHEDAT = "container_state_finishedat"
NODE_CONTAINER_RESTARTCOUNT = "container_restartcount"
NODE_CONTAINER_IMAGE_UPDATE_INFO = "container_image_update_info"
# Labels
NODE_EXPORTER_VERSION_LABEL = "version"
NODE_EXPORTER_RESOURCE_LABEL = "nodename"
NODE_EXPORTER_OS_NAME_LABEL = "name"
NODE_EXPORTER_OS_VERSION_LABEL = "version"
NODE_EXPORTER_DEVICE_MODEL_LABEL = "model"
NODE_EXPORTER_DEVICE_SERIAL_LABEL = "serial"
NODE_EXPORTER_DEVICE_DISK_SIZE_LABEL = "disk_size"
NODE_CPU_CORE_LABEL = "cpu"
NODE_CPU_IDLE_SECONDS_LABEL = "mode"
NODE_CPU_TEMP_LABEL = "type"
NODE_FILESYSTEM_MOUNTPOINT_LABEL = "mountpoint"
NODE_NETWORK_INTERFACE_LABEL = "device"
NODE_OS_INSTALLED_VERSION_LABEL = "installed_version"
NODE_OS_LATEST_VERSION_LABEL = "latest_version"
NODE_CONTAINER_IMAGE_USED_VERSION_LABEL = "used_version"
NODE_CONTAINER_IMAGE_LATEST_VERSION_LABEL = "latest_version"
NODE_CONTAINER_RESOURCE_LABEL = "name"
NODE_CONTAINER_IMAGE_LABEL = "image"
NODE_CONTAINER_STATE_STATUS_LABEL = "status"
# Regex
NODE_AT_LEAST_ONE_CHARACTER_REGEX = ".+"
NODE_CPU_IDLE_SECONDS_LABEL_REGEX = "^idle$"
NODE_CPU_TEMP_LABEL_REGEX = "^cpu-thermal$"
NODE_FILESYSTEM_MOUNTPOINT_LABEL_REGEX = "^\\/$"
NODE_NETWORK_INTERFACE_LABEL_REGEX = "^eth[0-9]+|wlan[0-9]+$"
# Textfile collector metrics
METRIC_NODE_OS_UPDATE_INFO = "os_update_info"
METRIC_VIRTUAL_RESOURCES = "virtual_resources"
METRIC_VIRTUAL_RESOURCE_IMAGE_UPDATE_INFO = "virtual_resource_image_update_info"
METRIC_VIRTUAL_RESOURCE_STATUS = "virtual_resource_status"
METRIC_VIRTUAL_RESOURCE_STATUS_CREATED = "virtual_resource_status_created"
METRIC_VIRTUAL_RESOURCE_STATUS_RUNNING = "virtual_resource_status_running"
METRIC_VIRTUAL_RESOURCE_STATUS_PAUSED = "virtual_resource_status_paused"
METRIC_VIRTUAL_RESOURCE_STATUS_RESTARTING = "virtual_resource_status_restarting"
METRIC_VIRTUAL_RESOURCE_STATUS_REMOVING = "virtual_resource_status_removing"
METRIC_VIRTUAL_RESOURCE_STATUS_EXITED = "virtual_resource_status_exited"
METRIC_VIRTUAL_RESOURCE_STATUS_DEAD = "virtual_resource_status_dead"
METRIC_VIRTUAL_RESOURCE_UPTIME = "virtual_resource_uptime"
# Properties
PROPERTY_CURRENTLY_INSTALLED_OS_VERSION = "os_version_currently_installed"
PROPERTY_LATEST_AVAILABLE_OS_VERSION = "os_version_latest_available"
PROPERTY_CURRENTLY_USED_IMAGE_VERSION = "image_version_currently_used"
PROPERTY_LATEST_AVAILABLE_IMAGE_VERSION = "image_version_latest_available"


PROVIDER_FILTERS = [
    MetricFilter(
        metric_key=NODE_EXPORTER_BUILD_INFO,
        label_filters={NODE_EXPORTER_VERSION_LABEL: NODE_AT_LEAST_ONE_CHARACTER_REGEX},
    ),
    MetricFilter(
        metric_key=NODE_UNAME_INFO,
        label_filters={NODE_EXPORTER_RESOURCE_LABEL: NODE_AT_LEAST_ONE_CHARACTER_REGEX},
    ),
    MetricFilter(
        metric_key=NODE_OS_INFO,
        label_filters={
            NODE_EXPORTER_OS_NAME_LABEL: NODE_AT_LEAST_ONE_CHARACTER_REGEX,
            NODE_EXPORTER_OS_VERSION_LABEL: NODE_AT_LEAST_ONE_CHARACTER_REGEX,
        },
    ),
    MetricFilter(
        metric_key=NODE_DEVICE_INFO,
        label_filters={
            NODE_EXPORTER_DEVICE_MODEL_LABEL: NODE_AT_LEAST_ONE_CHARACTER_REGEX,
            NODE_EXPORTER_DEVICE_SERIAL_LABEL: NODE_AT_LEAST_ONE_CHARACTER_REGEX,
        },
    ),
]


class NodeExporterProvider(MetricsProvider):
    """Node Exporter metrics provider."""

    metric_filters = [
        MetricFilter(metric_key=NODE_TIME),
        MetricFilter(metric_key=NODE_BOOT_TIME),
        MetricFilter(
            metric_key=NODE_CPU_TEMP,
            label_filters={NODE_CPU_TEMP_LABEL: NODE_CPU_TEMP_LABEL_REGEX},
        ),
        MetricFilter(
            metric_key=NODE_CPU_IDLE_SECONDS,
            label_filters={
                NODE_CPU_IDLE_SECONDS_LABEL: NODE_CPU_IDLE_SECONDS_LABEL_REGEX
            },
        ),
        MetricFilter(
            metric_key=NODE_MEMORY_AVAILABLE,
        ),
        MetricFilter(
            metric_key=NODE_MEMORY_TOTAL,
        ),
        MetricFilter(
            metric_key=NODE_MEMORY_SWAP_TOTAL,
        ),
        MetricFilter(
            metric_key=NODE_FILESYSTEM_SIZE,
            label_filters={
                NODE_FILESYSTEM_MOUNTPOINT_LABEL: NODE_FILESYSTEM_MOUNTPOINT_LABEL_REGEX
            },
        ),
        MetricFilter(
            metric_key=NODE_FILESYSTEM_FREE,
            label_filters={
                NODE_FILESYSTEM_MOUNTPOINT_LABEL: NODE_FILESYSTEM_MOUNTPOINT_LABEL_REGEX
            },
        ),
        MetricFilter(
            metric_key=NODE_NETWORK_RECEIVE,
            label_filters={
                NODE_NETWORK_INTERFACE_LABEL: NODE_NETWORK_INTERFACE_LABEL_REGEX
            },
        ),
        MetricFilter(
            metric_key=NODE_NETWORK_TRANSMIT,
            label_filters={
                NODE_NETWORK_INTERFACE_LABEL: NODE_NETWORK_INTERFACE_LABEL_REGEX
            },
        ),
        MetricFilter(
            metric_key=NODE_NETWORK_INTERFACE_SPEED,
            label_filters={
                NODE_NETWORK_INTERFACE_LABEL: NODE_NETWORK_INTERFACE_LABEL_REGEX
            },
        ),
        MetricFilter(
            metric_key=NODE_DEVICE_INFO,
            label_filters={
                NODE_EXPORTER_DEVICE_DISK_SIZE_LABEL: NODE_AT_LEAST_ONE_CHARACTER_REGEX
            },
        ),
        MetricFilter(
            metric_key=NODE_OS_UPDATE_INFO,
            label_filters={
                NODE_OS_INSTALLED_VERSION_LABEL: NODE_AT_LEAST_ONE_CHARACTER_REGEX,
                NODE_OS_LATEST_VERSION_LABEL: NODE_AT_LEAST_ONE_CHARACTER_REGEX,
            },
        ),
        MetricFilter(
            metric_key=NODE_CONTAINER_IMAGE_UPDATE_INFO,
            label_filters={
                NODE_CONTAINER_IMAGE_LABEL: NODE_AT_LEAST_ONE_CHARACTER_REGEX,
                NODE_CONTAINER_IMAGE_USED_VERSION_LABEL: NODE_AT_LEAST_ONE_CHARACTER_REGEX,
                NODE_CONTAINER_IMAGE_LATEST_VERSION_LABEL: NODE_AT_LEAST_ONE_CHARACTER_REGEX,
            },
            resource_label=NODE_CONTAINER_RESOURCE_LABEL,
        ),
        MetricFilter(
            metric_key=NODE_CONTAINER_STATE_STATUS,
            label_filters={
                NODE_CONTAINER_STATE_STATUS_LABEL: NODE_AT_LEAST_ONE_CHARACTER_REGEX
            },
            resource_label=NODE_CONTAINER_RESOURCE_LABEL,
        ),
        MetricFilter(
            metric_key=NODE_CONTAINER_STATE_STARTEDAT,
            label_filters={
                NODE_CONTAINER_RESOURCE_LABEL: NODE_AT_LEAST_ONE_CHARACTER_REGEX
            },
            resource_label=NODE_CONTAINER_RESOURCE_LABEL,
        ),
    ]
    found_metrics = {
        NODE_CPU_IDLE_SECONDS: False,
        NODE_CPU_TEMP: False,
        NODE_MEMORY_TOTAL: False,
        NODE_MEMORY_AVAILABLE: False,
        NODE_FILESYSTEM_SIZE: False,
        NODE_FILESYSTEM_FREE: False,
        NODE_NETWORK_RECEIVE: False,
        NODE_NETWORK_TRANSMIT: False,
        NODE_BOOT_TIME: False,
        NODE_OS_UPDATE_INFO: False,
        NODE_CONTAINER_IMAGE_UPDATE_INFO: False,
        NODE_CONTAINER_STATE_STATUS: False,
        NODE_CONTAINER_STATE_STARTEDAT: False,
    }

    def __init__(self):
        """Initialize node exporter provider."""
        super().__init__(PROVIDER_NAME_NODE_EXPORTER, RESOURCE_TYPE_NODE)
        self.provider_filters = PROVIDER_FILTERS
        self.__process_virtual_resource_metrics()

    def __process_virtual_resource_metrics(self):
        virtual_resource_metric_keys = []
        for metric_filter in self.metric_filters:
            if metric_filter.resource_label is not None:
                if metric_filter.metric_key not in virtual_resource_metric_keys:
                    virtual_resource_metric_keys.append(metric_filter.metric_key)
        self.__virtual_resource_metric_keys = virtual_resource_metric_keys

    def extract_provider_info(self, family: Metric, provider_info: ProviderInfoData):
        """Extract and store provider information."""
        if family.name == NODE_EXPORTER_BUILD_INFO and family.samples:
            provider_info.version = family.samples[0].labels[
                NODE_EXPORTER_VERSION_LABEL
            ]

    def extract_resource_info(self, family: Metric, resources: dict):
        """Extract and store node resource information."""
        # Initialize resource info for main resource (if not yet initialized)
        if self.resource_name not in resources:
            resource_info = ResourceInfoData(type=RESOURCE_TYPE_NODE)
            resources[self.resource_name] = resource_info
        else:
            resource_info = resources[self.resource_name]
        # Extract resource info
        if family.name == NODE_UNAME_INFO:
            for sample in family.samples:
                nodename = sample.labels.get(NODE_EXPORTER_RESOURCE_LABEL, None)
                if nodename:
                    resource_info.name = nodename
                    self.resource_name = nodename
        # Extract software
        elif family.name == NODE_OS_INFO:
            for sample in family.samples:
                if sample.labels.get(NODE_EXPORTER_OS_NAME_LABEL):
                    resource_info.software = sample.labels[NODE_EXPORTER_OS_NAME_LABEL]
                if sample.labels.get(NODE_EXPORTER_OS_VERSION_LABEL):
                    resource_info.version = sample.labels[
                        NODE_EXPORTER_OS_VERSION_LABEL
                    ]
        # Extract model and serial number
        elif family.name == NODE_DEVICE_INFO:
            for sample in family.samples:
                # Get model
                if sample.labels.get(NODE_EXPORTER_DEVICE_MODEL_LABEL):
                    resource_info.model = sample.labels[
                        NODE_EXPORTER_DEVICE_MODEL_LABEL
                    ]
                # Get serial number
                if sample.labels.get(NODE_EXPORTER_DEVICE_SERIAL_LABEL):
                    resource_info.serial_number = sample.labels[
                        NODE_EXPORTER_DEVICE_SERIAL_LABEL
                    ]
        # Extract network interfaces
        elif family.name == NODE_NETWORK_INTERFACE_SPEED:
            for sample in family.samples:
                interface_name = sample.labels.get(NODE_NETWORK_INTERFACE_LABEL)
                if interface_name:
                    if not resource_info.network_interfaces:
                        resource_info.network_interfaces = set()
                    # Add interface name to network interfaces list
                    if re.match(NODE_NETWORK_INTERFACE_LABEL_REGEX, interface_name):
                        resource_info.network_interfaces.add(interface_name)
        # Extract virtual resources and create resource info
        elif family.name in self.__virtual_resource_metric_keys:
            for sample in family.samples:
                v_resource_name = sample.labels.get(NODE_CONTAINER_RESOURCE_LABEL)
                v_resource_image = sample.labels.get(NODE_CONTAINER_IMAGE_LABEL)
                if v_resource_image:
                    v_resource_software = self._get_application_from_image(
                        v_resource_image
                    )
                    v_resource_model = self._get_model_from_image(v_resource_image)
                    v_resource_version = self._get_version_from_image(v_resource_image)
                if v_resource_name and v_resource_name not in resources:
                    v_resource_info = ResourceInfoData(
                        type=RESOURCE_TYPE_CONTAINER,
                        name=v_resource_name,
                        software=v_resource_software,
                        version=v_resource_version,
                        model=v_resource_model,
                        is_virtual=True,
                    )
                    resources[v_resource_name] = v_resource_info

    def collect_supported_metric(self, family: Metric, available_metrics: list[str]):
        """Collect supported metric."""
        # Add metric to list if not already added
        if family.name in self.found_metrics:
            self.found_metrics[family.name] = True
            if family.name == NODE_CPU_IDLE_SECONDS:
                self._add_str_to_list_uniquely(METRIC_CPU_USAGE_PCT, available_metrics)
            elif family.name == NODE_CPU_TEMP:
                self._add_str_to_list_uniquely(METRIC_CPU_TEMP, available_metrics)
            elif family.name == NODE_BOOT_TIME:
                self._add_str_to_list_uniquely(METRIC_UPTIME_SECONDS, available_metrics)
            elif family.name == NODE_OS_UPDATE_INFO:
                self._add_str_to_list_uniquely(
                    METRIC_NODE_OS_UPDATE_INFO, available_metrics
                )
            elif family.name == NODE_CONTAINER_IMAGE_UPDATE_INFO:
                self._add_str_to_list_uniquely(
                    METRIC_VIRTUAL_RESOURCE_IMAGE_UPDATE_INFO, available_metrics
                )
                self._add_str_to_list_uniquely(
                    METRIC_VIRTUAL_RESOURCES, available_metrics
                )
            elif family.name == NODE_CONTAINER_STATE_STATUS:
                self._add_str_to_list_uniquely(
                    METRIC_VIRTUAL_RESOURCE_STATUS, available_metrics
                )
                self._add_str_to_list_uniquely(
                    METRIC_VIRTUAL_RESOURCES, available_metrics
                )
            elif family.name == NODE_CONTAINER_STATE_STARTEDAT:
                self._add_str_to_list_uniquely(
                    METRIC_VIRTUAL_RESOURCE_UPTIME, available_metrics
                )
                self._add_str_to_list_uniquely(
                    METRIC_VIRTUAL_RESOURCES, available_metrics
                )
        # Add name metric
        self._add_str_to_list_uniquely(METRIC_DEVICE_NAME, available_metrics)
        # Add paired metrics after checking both components are present
        if (
            self.found_metrics[NODE_MEMORY_TOTAL]
            and self.found_metrics[NODE_MEMORY_AVAILABLE]
        ):
            self._add_str_to_list_uniquely(METRIC_MEMORY_USAGE_BYTES, available_metrics)
            self._add_str_to_list_uniquely(METRIC_MEMORY_USAGE_PCT, available_metrics)

        if (
            self.found_metrics[NODE_FILESYSTEM_SIZE]
            and self.found_metrics[NODE_FILESYSTEM_FREE]
        ):
            self._add_str_to_list_uniquely(METRIC_DISK_USAGE_BYTES, available_metrics)
            self._add_str_to_list_uniquely(METRIC_DISK_USAGE_PCT, available_metrics)

        if (
            self.found_metrics[NODE_NETWORK_RECEIVE]
            and self.found_metrics[NODE_NETWORK_TRANSMIT]
        ):
            self._add_str_to_list_uniquely(
                METRIC_NETWORK_RECEIVE_BYTES, available_metrics
            )
            self._add_str_to_list_uniquely(
                METRIC_NETWORK_TRANSMIT_BYTES, available_metrics
            )

    def prepare_metric_value(self, metric_key: str, sample: Sample) -> float | dict:
        """Override: Collect metric value."""
        # CPU
        if metric_key == NODE_CPU_IDLE_SECONDS:
            cpu = sample.labels[NODE_CPU_CORE_LABEL]
            return {cpu: sample.value}
        # Network
        if metric_key in (
            NODE_NETWORK_RECEIVE,
            NODE_NETWORK_TRANSMIT,
            NODE_NETWORK_INTERFACE_SPEED,
        ):
            interface = sample.labels[NODE_NETWORK_INTERFACE_LABEL]
            return {interface: sample.value}
        # Storage
        if metric_key == NODE_DEVICE_INFO:
            disk_size = sample.labels.get(NODE_EXPORTER_DEVICE_DISK_SIZE_LABEL)
            if disk_size:
                return round(convert_data_size(disk_size, UnitOfInformation.BYTES))
        # OS update
        if metric_key == NODE_OS_UPDATE_INFO:
            return {
                NODE_OS_UPDATE_INFO: sample.value,
                NODE_OS_INSTALLED_VERSION_LABEL: sample.labels.get(
                    NODE_OS_INSTALLED_VERSION_LABEL
                ),
                NODE_OS_LATEST_VERSION_LABEL: sample.labels.get(
                    NODE_OS_LATEST_VERSION_LABEL
                ),
            }
        # Container
        if metric_key == NODE_CONTAINER_IMAGE_UPDATE_INFO:
            return {
                NODE_CONTAINER_IMAGE_UPDATE_INFO: sample.value,
                NODE_CONTAINER_IMAGE_USED_VERSION_LABEL: sample.labels.get(
                    NODE_CONTAINER_IMAGE_USED_VERSION_LABEL
                ),
                NODE_CONTAINER_IMAGE_LATEST_VERSION_LABEL: sample.labels.get(
                    NODE_CONTAINER_IMAGE_LATEST_VERSION_LABEL
                ),
            }
        if metric_key == NODE_CONTAINER_STATE_STATUS:
            status = sample.labels[NODE_CONTAINER_STATE_STATUS_LABEL]
            return {status: sample.value}
        # Other
        return sample.value

    def _pre_process_metrics(self, metrics: dict):
        """Pre-process metrics."""
        # Add number of containers to main resource metrics
        for resource, resource_metrics in metrics.items():
            if resource == self.resource_name:
                resource_metrics[METRIC_VIRTUAL_RESOURCES] = len(metrics) - 1
                break

    def _calculate_resource_metrics(
        self, resource: str, metrics: dict, update_interval: int
    ) -> dict | None:
        """Process resource metrics and return sensor metrics."""
        if resource == self.resource_name:
            sensor_metrics = super()._calculate_resource_metrics(
                resource, metrics, update_interval
            )
            # CPU temperature
            if NODE_CPU_TEMP in metrics and sensor_metrics:
                sensor_metrics[METRIC_CPU_TEMP] = metrics[NODE_CPU_TEMP]

            # OS update
            if NODE_OS_UPDATE_INFO in metrics and sensor_metrics:
                sensor_metrics[METRIC_NODE_OS_UPDATE_INFO] = metrics[
                    NODE_OS_UPDATE_INFO
                ][NODE_OS_UPDATE_INFO]
                sensor_metrics[PROPERTY_CURRENTLY_INSTALLED_OS_VERSION] = metrics[
                    NODE_OS_UPDATE_INFO
                ][NODE_OS_INSTALLED_VERSION_LABEL]
                sensor_metrics[PROPERTY_LATEST_AVAILABLE_OS_VERSION] = metrics[
                    NODE_OS_UPDATE_INFO
                ][NODE_OS_LATEST_VERSION_LABEL]

            # Virtual resources
            if METRIC_VIRTUAL_RESOURCES in metrics and sensor_metrics:
                sensor_metrics[METRIC_VIRTUAL_RESOURCES] = metrics[
                    METRIC_VIRTUAL_RESOURCES
                ]
        else:
            # Process virtual resource metrics
            sensor_metrics = self._calculate_virtual_resource_metrics(resource, metrics)
        # Return sensor metrics
        return sensor_metrics

    def _calculate_virtual_resource_metrics(
        self, resource: str, metrics: dict
    ) -> dict | None:
        """Process virtual resource metrics and return sensor metrics."""
        sensor_metrics = {}
        # Calculate container image update
        if NODE_CONTAINER_IMAGE_UPDATE_INFO in metrics:
            sensor_metrics[METRIC_VIRTUAL_RESOURCE_IMAGE_UPDATE_INFO] = metrics[
                NODE_CONTAINER_IMAGE_UPDATE_INFO
            ][NODE_CONTAINER_IMAGE_UPDATE_INFO]
            sensor_metrics[PROPERTY_CURRENTLY_USED_IMAGE_VERSION] = metrics[
                NODE_CONTAINER_IMAGE_UPDATE_INFO
            ][NODE_CONTAINER_IMAGE_USED_VERSION_LABEL]
            sensor_metrics[PROPERTY_LATEST_AVAILABLE_IMAGE_VERSION] = metrics[
                NODE_CONTAINER_IMAGE_UPDATE_INFO
            ][NODE_CONTAINER_IMAGE_LATEST_VERSION_LABEL]
        # Calculate container status
        if NODE_CONTAINER_STATE_STATUS in metrics:
            sensor_metrics[METRIC_VIRTUAL_RESOURCE_STATUS] = (
                self._calculate_virtual_resource_status(
                    resource, metrics[NODE_CONTAINER_STATE_STATUS]
                )
            )
        # Calculate container uptime
        if NODE_CONTAINER_STATE_STARTEDAT in metrics:
            sensor_metrics.update(
                self._calculate_virtual_resource_uptime(
                    resource, metrics[NODE_CONTAINER_STATE_STARTEDAT]
                )
            )
        return sensor_metrics

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
        cpu_usage_pct: float | None = None
        cpu_core_usage: dict = {}
        # Calculate CPU usage
        if NODE_CPU_IDLE_SECONDS in metrics:
            cpu_usage_total_pct = None
            for cpu in metrics[NODE_CPU_IDLE_SECONDS]:
                # Get current value
                current_value = metrics[NODE_CPU_IDLE_SECONDS][cpu]
                # Get previous value
                if resource in self._previous_metrics:
                    if NODE_CPU_IDLE_SECONDS in self._previous_metrics[resource]:
                        if (
                            cpu
                            in self._previous_metrics[resource][NODE_CPU_IDLE_SECONDS]
                        ):
                            prev_value = self._previous_metrics[resource][
                                NODE_CPU_IDLE_SECONDS
                            ][cpu]
                else:
                    self._previous_metrics[resource] = {}
                    self._previous_metrics[resource][NODE_CPU_IDLE_SECONDS] = {}
                # Set current value as previous value
                self._previous_metrics[resource][NODE_CPU_IDLE_SECONDS][cpu] = (
                    current_value
                )
                # Calculate CPU core usage
                if prev_value is not None and current_value is not None:
                    cpu_core_idle_time_delta = current_value - prev_value
                    cpu_core_usage_pct = (
                        1 - cpu_core_idle_time_delta / update_interval
                    ) * 100
                    if cpu_core_usage_pct > 100:
                        cpu_core_usage_pct = 100
                    elif cpu_core_usage_pct < 0:
                        cpu_core_usage_pct = 0
                    cpu_core_usage[cpu] = cpu_core_usage_pct
                    if cpu_usage_total_pct is None:
                        cpu_usage_total_pct = 0
                    cpu_usage_total_pct += cpu_core_usage_pct  # max = 100% * cpu cores
            # Calculate total CPU usage
            if cpu_usage_total_pct is not None:
                # Set CPU cores
                cpu_cores = len(metrics[NODE_CPU_IDLE_SECONDS])
                sensor_metrics[PROPERTY_CPU_CORES] = cpu_cores
                # Set CPU usage
                cpu_usage_pct = cpu_usage_total_pct / cpu_cores
                sensor_metrics[METRIC_CPU_USAGE_PCT] = cpu_usage_pct
        # Return values
        return sensor_metrics

    def _calculate_memory_usage(
        self,
        resource: str,
        metrics: dict[str, int],
    ) -> dict[str, Any]:
        """Calculate memory usage (used bytes, used pct)."""
        sensor_metrics = {}
        # Check if metrics are available
        if not metrics:
            return sensor_metrics
        # Get values
        memory_total_bytes = metrics.get(NODE_MEMORY_TOTAL)
        if memory_total_bytes is None or memory_total_bytes == 0:
            return sensor_metrics
        memory_free_bytes = metrics.get(NODE_MEMORY_AVAILABLE)
        if memory_free_bytes is None:
            return sensor_metrics
        # Calculate memory usage
        memory_usage_bytes = memory_total_bytes - memory_free_bytes
        memory_usage_pct = (memory_usage_bytes / memory_total_bytes) * 100
        # Set memory usage
        sensor_metrics[METRIC_MEMORY_USAGE_BYTES] = memory_usage_bytes
        sensor_metrics[METRIC_MEMORY_USAGE_PCT] = memory_usage_pct
        # Set memory size
        if NODE_MEMORY_TOTAL in metrics:
            memory_size_bytes: int = metrics[NODE_MEMORY_TOTAL]
        if memory_size_bytes and NODE_MEMORY_SWAP_TOTAL in metrics:
            memory_size_bytes += int(metrics[NODE_MEMORY_SWAP_TOTAL])
            # Convert memory size to appropriate unit
            target_unit = get_appropriate_unit(memory_size_bytes)
            sensor_metrics[PROPERTY_MEMORY_SIZE] = (
                f"{floor(convert_data_size(memory_size_bytes, target_unit))} {target_unit}"
            )
        # Return values
        return sensor_metrics

    def _calculate_disk_usage(self, resource, metrics) -> dict[str, Any]:
        """Calculate disk usage (used bytes, used pct)."""
        sensor_metrics = {}
        # Check if metrics are available
        if not metrics:
            return sensor_metrics
        # Initialize variables
        disk_total_bytes: int | None = None
        disk_usage_bytes: int | None = None
        # Get values
        if NODE_FILESYSTEM_SIZE in metrics:
            disk_total_bytes = metrics[NODE_FILESYSTEM_SIZE]
            disk_free_bytes = metrics[NODE_FILESYSTEM_FREE]
            disk_usage_bytes = disk_total_bytes - disk_free_bytes
        # Calculate disk usage
        if (
            disk_total_bytes is not None
            and disk_total_bytes > 0
            and disk_usage_bytes is not None
        ):
            sensor_metrics[METRIC_DISK_USAGE_BYTES] = disk_usage_bytes
            sensor_metrics[METRIC_DISK_USAGE_PCT] = (
                disk_usage_bytes / disk_total_bytes * 100
            )
        # Set disk size
        if disk_total_bytes:
            target_unit = get_appropriate_unit(disk_total_bytes)
            sensor_metrics[PROPERTY_DISK_SIZE] = (
                f"{floor(convert_data_size(disk_total_bytes, target_unit))} {target_unit}"
            )
        if NODE_DEVICE_INFO in metrics:
            disk_size = metrics[NODE_DEVICE_INFO]
            target_unit = get_appropriate_unit(disk_size)
            sensor_metrics[PROPERTY_DISK_SIZE] = (
                f"{floor(convert_data_size(disk_size, target_unit))} {target_unit}"
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
        prev_value_receive: int | None = None
        current_value_receive: int | None = None
        prev_value_transmit: int | None = None
        current_value_transmit: int | None = None
        # Calculate network receive
        if NODE_NETWORK_RECEIVE in metrics:
            for interface in metrics[NODE_NETWORK_RECEIVE]:
                # Get current value
                current_value_receive = metrics[NODE_NETWORK_RECEIVE][interface]
                # Get previous value
                if resource in self._previous_metrics:
                    if NODE_NETWORK_RECEIVE in self._previous_metrics[resource]:
                        if (
                            interface
                            in self._previous_metrics[resource][NODE_NETWORK_RECEIVE]
                        ):
                            prev_value_receive = self._previous_metrics[resource][
                                NODE_NETWORK_RECEIVE
                            ][interface]
                    else:
                        self._previous_metrics[resource][NODE_NETWORK_RECEIVE] = {}
                else:
                    self._previous_metrics[resource] = {NODE_NETWORK_RECEIVE: {}}
                # Set current value as previous value
                self._previous_metrics[resource][NODE_NETWORK_RECEIVE][interface] = (
                    current_value_receive
                )
                # Calculate network receive bytes per second
                if prev_value_receive is not None and current_value_receive is not None:
                    metric_key = f"{METRIC_NETWORK_RECEIVE_BYTES}_{interface}"
                    sensor_metrics[metric_key] = (
                        current_value_receive - prev_value_receive
                    ) / update_interval
        # Calculate network transmit
        if NODE_NETWORK_TRANSMIT in metrics:
            for interface in metrics[NODE_NETWORK_TRANSMIT]:
                # Get current value
                current_value_transmit = metrics[NODE_NETWORK_TRANSMIT][interface]
                # Get previous value
                if resource in self._previous_metrics:
                    if NODE_NETWORK_TRANSMIT in self._previous_metrics[resource]:
                        if (
                            interface
                            in self._previous_metrics[resource][NODE_NETWORK_TRANSMIT]
                        ):
                            prev_value_transmit = self._previous_metrics[resource][
                                NODE_NETWORK_TRANSMIT
                            ][interface]
                    else:
                        self._previous_metrics[resource][NODE_NETWORK_TRANSMIT] = {}
                else:
                    self._previous_metrics[resource] = {NODE_NETWORK_TRANSMIT: {}}
                # Set current value as previous value
                self._previous_metrics[resource][NODE_NETWORK_TRANSMIT][interface] = (
                    current_value_transmit
                )
                # Calculate network transmit bytes per second
                if (
                    prev_value_transmit is not None
                    and current_value_transmit is not None
                ):
                    metric_key = f"{METRIC_NETWORK_TRANSMIT_BYTES}_{interface}"
                    sensor_metrics[metric_key] = (
                        current_value_transmit - prev_value_transmit
                    ) / update_interval
        # Set network speed
        if NODE_NETWORK_INTERFACE_SPEED in metrics:
            network_speed = metrics[NODE_NETWORK_INTERFACE_SPEED]
            sensor_metrics[PROPERTY_NETWORK_SPEED] = {}
            for interface, speed in network_speed.items():
                target_unit = UnitOfDataRate.MEGABITS_PER_SECOND
                sensor_metrics[PROPERTY_NETWORK_SPEED][interface] = (
                    f"{round(convert_data_rate(speed, target_unit))} {target_unit}"
                )
        # Return values
        return sensor_metrics

    def _calculate_uptime(self, resource: str, metrics: dict) -> dict[str, Any]:
        """Calculate uptime."""
        sensor_metrics = {}
        # Check if metrics are available
        if not metrics:
            return sensor_metrics
        # Initialize variables
        start_time: int | None = None
        # Get values
        if NODE_BOOT_TIME in metrics:
            start_time = metrics[NODE_BOOT_TIME]
        # Calculate uptime
        if start_time is not None:
            sensor_metrics[PROPERTY_LAST_START_TIME] = datetime.fromtimestamp(
                float(start_time), dt_util.UTC
            )
            sensor_metrics[METRIC_UPTIME_SECONDS] = int(time()) - start_time
        # Return values
        return sensor_metrics

    def _calculate_virtual_resource_uptime(
        self, resource: str, start_time: int
    ) -> dict[str, Any]:
        """Calculate uptime."""
        sensor_metrics = {}
        # Check if metrics are available
        if not start_time:
            return sensor_metrics
        # Calculate uptime
        if start_time is not None:
            sensor_metrics[PROPERTY_LAST_START_TIME] = datetime.fromtimestamp(
                float(start_time), dt_util.UTC
            )
            sensor_metrics[METRIC_VIRTUAL_RESOURCE_UPTIME] = int(time()) - start_time
        # Return values
        return sensor_metrics

    def _calculate_virtual_resource_status(
        self, resource: str, container_states: dict
    ) -> str | None:
        """Get container state as string from state values."""
        # Check if metrics are available
        if not container_states:
            return None
        for status, value in container_states.items():
            if value == 1.0:
                return status
        return "unknown"
