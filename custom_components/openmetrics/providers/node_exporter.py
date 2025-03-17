"""Node Exporter provider."""

from time import time

from ..const import (
    METRIC_CONTAINER_STATUS,
    METRIC_CONTAINER_UPTIME,
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
NODE_MEMORY_FREE = "node_memory_MemFree_bytes"
NODE_MEMORY_TOTAL = "node_memory_MemTotal_bytes"
NODE_MEMORY_SWAP_TOTAL = "node_memory_SwapTotal_bytes"
NODE_FILESYSTEM_SIZE = "node_filesystem_size_bytes"
NODE_FILESYSTEM_FREE = "node_filesystem_free_bytes"
NODE_NETWORK_RECEIVE = "node_network_receive_bytes"
NODE_NETWORK_TRANSMIT = "node_network_transmit_bytes"
NODE_CONTAINER_STATE_HEALTH_STATUS = "container_state_health_status"
NODE_CONTAINER_STATE_STATUS = "container_state_status"
NODE_CONTAINER_STATE_OOMKILLED = "container_state_oomkilled"
NODE_CONTAINER_STATE_STARTEDAT = "container_state_startedat"
NODE_CONTAINER_STATE_FINISHEDAT = "container_state_finishedat"
NODE_CONTAINER_RESTARTCOUNT = "container_restartcount"
# Labels
NODE_EXPORTER_VERSION_LABEL = "version"
NODE_EXPORTER_RESOURCE_LABEL = "nodename"
NODE_EXPORTER_OS_NAME_LABEL = "pretty_name"
NODE_EXPORTER_OS_VERSION_LABEL = "version"
NODE_EXPORTER_DEVICE_MODEL_LABEL = "model"
NODE_EXPORTER_DEVICE_SERIAL_LABEL = "serial"
NODE_EXPORTER_CPU_CORE_LABEL = "cpu"
NODE_CONTAINER_RESOURCE_LABEL = "name"
NODE_CONTAINER_IMAGE_LABEL = "image"
NODE_CONTAINER_STATE_STATUS_LABEL = "status"

PROVIDER_FILTERS = [
    MetricFilter(
        metric_key=NODE_EXPORTER_BUILD_INFO,
        label_filters={NODE_EXPORTER_VERSION_LABEL: ".+"},
    ),
    MetricFilter(
        metric_key=NODE_UNAME_INFO,
        label_filters={NODE_EXPORTER_RESOURCE_LABEL: ".+"},
    ),
    MetricFilter(
        metric_key=NODE_OS_INFO,
        label_filters={
            NODE_EXPORTER_OS_NAME_LABEL: ".+",
            NODE_EXPORTER_OS_VERSION_LABEL: ".+",
        },
    ),
    MetricFilter(
        metric_key=NODE_DEVICE_INFO,
        label_filters={
            NODE_EXPORTER_DEVICE_MODEL_LABEL: ".+",
            NODE_EXPORTER_DEVICE_SERIAL_LABEL: ".+",
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
            label_filters={"type": "cpu-thermal"},
        ),
        MetricFilter(
            metric_key=NODE_CPU_IDLE_SECONDS,
            label_filters={"mode": "idle"},
        ),
        MetricFilter(
            metric_key=NODE_MEMORY_FREE,
        ),
        MetricFilter(
            metric_key=NODE_MEMORY_TOTAL,
        ),
        MetricFilter(
            metric_key=NODE_MEMORY_SWAP_TOTAL,
        ),
        MetricFilter(
            metric_key=NODE_FILESYSTEM_SIZE,
            label_filters={"mountpoint": "^\\/$"},
        ),
        MetricFilter(
            metric_key=NODE_FILESYSTEM_FREE,
            label_filters={"mountpoint": "^\\/$"},
        ),
        MetricFilter(
            metric_key=NODE_NETWORK_RECEIVE,
            label_filters={"device": "eth0"},
        ),
        MetricFilter(
            metric_key=NODE_NETWORK_TRANSMIT,
            label_filters={"device": "eth0"},
        ),
        MetricFilter(
            metric_key=NODE_CONTAINER_STATE_STATUS,
            label_filters={"status": ".+"},
            resource_label=NODE_CONTAINER_RESOURCE_LABEL,
        ),
        MetricFilter(
            metric_key=NODE_CONTAINER_STATE_STARTEDAT,
            label_filters={"name": ".+"},
            resource_label=NODE_CONTAINER_RESOURCE_LABEL,
        ),
    ]
    found_metrics = {
        NODE_CPU_IDLE_SECONDS: False,
        NODE_CPU_TEMP: False,
        NODE_MEMORY_TOTAL: False,
        NODE_MEMORY_FREE: False,
        NODE_FILESYSTEM_SIZE: False,
        NODE_FILESYSTEM_FREE: False,
        NODE_NETWORK_RECEIVE: False,
        NODE_NETWORK_TRANSMIT: False,
        NODE_BOOT_TIME: False,
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
        # Initialize resource info if not yet initialized
        if self.name not in resources:
            resource_info = ResourceInfoData(type=RESOURCE_TYPE_NODE)
            resources[self.name] = resource_info
        else:
            resource_info = resources[self.name]
        # Extract resource info
        if family.name == NODE_UNAME_INFO:
            for sample in family.samples:
                nodename = sample.labels.get(NODE_EXPORTER_RESOURCE_LABEL, None)
                if nodename:
                    resource_info.name = nodename
                    self.resource_name = nodename
        elif family.name == NODE_OS_INFO:
            for sample in family.samples:
                resource_info.software = sample.labels.get(NODE_EXPORTER_OS_NAME_LABEL)
                resource_info.version = sample.labels.get(
                    NODE_EXPORTER_OS_VERSION_LABEL
                )
        elif family.name == NODE_DEVICE_INFO:
            for sample in family.samples:
                resource_info.model = sample.labels.get(
                    NODE_EXPORTER_DEVICE_MODEL_LABEL
                )
                resource_info.serial_number = sample.labels.get(
                    NODE_EXPORTER_DEVICE_SERIAL_LABEL
                )
        elif family.name in self.__virtual_resource_metric_keys:
            for sample in family.samples:
                v_resource_name = sample.labels.get(NODE_CONTAINER_RESOURCE_LABEL)
                if v_resource_name and v_resource_name not in resources:
                    v_resource_info = ResourceInfoData(
                        type=RESOURCE_TYPE_CONTAINER,
                        name=v_resource_name,
                        software=sample.labels.get(NODE_CONTAINER_IMAGE_LABEL),
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
            elif family.name == NODE_CONTAINER_STATE_STATUS:
                self._add_str_to_list_uniquely(
                    METRIC_CONTAINER_STATUS, available_metrics
                )
            elif family.name == NODE_CONTAINER_STATE_STARTEDAT:
                self._add_str_to_list_uniquely(
                    METRIC_CONTAINER_UPTIME, available_metrics
                )
        # Add name metric
        self._add_str_to_list_uniquely(METRIC_DEVICE_NAME, available_metrics)
        # Add paired metrics after checking both components are present
        if (
            self.found_metrics[NODE_MEMORY_TOTAL]
            and self.found_metrics[NODE_MEMORY_FREE]
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
        if metric_key == NODE_CPU_IDLE_SECONDS:
            cpu = sample.labels[NODE_EXPORTER_CPU_CORE_LABEL]
            return {cpu: sample.value}
        if metric_key == NODE_CONTAINER_STATE_STATUS:
            status = sample.labels[NODE_CONTAINER_STATE_STATUS_LABEL]
            return {status: sample.value}
        return sample.value

    def _share_common_metrics(self, metrics: dict):
        """Share common metrics between resources."""
        # Not needed for node exporter
        return

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
        # Calculate container status
        if NODE_CONTAINER_STATE_STATUS in metrics:
            sensor_metrics[METRIC_CONTAINER_STATUS] = self._calculate_container_status(
                resource, metrics[NODE_CONTAINER_STATE_STATUS]
            )
        # Calculate container uptime
        if NODE_CONTAINER_STATE_STARTEDAT in metrics:
            uptime_seconds, start_time = self._calculate_container_uptime(
                resource, metrics[NODE_CONTAINER_STATE_STARTEDAT]
            )
            sensor_metrics[METRIC_CONTAINER_UPTIME] = uptime_seconds
        return sensor_metrics

    def _calculate_cpu_usage(
        self, resource: str, metrics: dict, update_interval: int
    ) -> tuple[float | None, dict[int, float] | None]:
        """Calculate CPU usage (pct, dict)."""
        # Check if metrics are available
        if not metrics:
            return None, None
        # Initialize variables
        prev_value: float | None = None
        current_value: float | None = None
        cpu_usage_pct: float | None = None
        cpu_core_usage: dict = {}
        # Calculate CPU usage
        if NODE_CPU_IDLE_SECONDS in metrics:
            cpu_usage_pct = None
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
                self.cpu_cores = len(metrics[NODE_CPU_IDLE_SECONDS])
                cpu_usage_pct = cpu_usage_total_pct / self.cpu_cores
        # Return values
        return cpu_usage_pct, cpu_core_usage

    def _calculate_memory_usage(
        self, resource: str, metrics: dict[str, int]
    ) -> tuple[int | None, float | None]:
        """Calculate memory usage (used bytes, used pct)."""
        # Check if metrics are available
        if not metrics:
            return None, None
        # Get values
        memory_total_bytes = metrics.get(NODE_MEMORY_TOTAL)
        if memory_total_bytes is None or memory_total_bytes == 0:
            return None, None
        memory_free_bytes = metrics.get(NODE_MEMORY_FREE)
        if memory_free_bytes is None:
            return None, None
        # Calculate memory usage
        memory_usage_bytes = memory_total_bytes - memory_free_bytes
        memory_usage_pct = (memory_usage_bytes / memory_total_bytes) * 100
        # Set memory size
        if NODE_MEMORY_TOTAL in metrics:
            self.memory_size: int = metrics[NODE_MEMORY_TOTAL]
        if self.memory_size and NODE_MEMORY_SWAP_TOTAL in metrics:
            self.memory_size += int(metrics[NODE_MEMORY_SWAP_TOTAL])
        # Return values
        return memory_usage_bytes, memory_usage_pct

    def _calculate_disk_usage(
        self, resource, metrics
    ) -> tuple[int | None, float | None]:
        """Calculate disk usage (used bytes, used pct)."""
        # Check if metrics are available
        if not metrics:
            return None, None
        # Initialize variables
        disk_total_bytes: int | None = None
        disk_usage_bytes: int | None = None
        disk_usage_pct: float | None = None
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
            disk_usage_pct = disk_usage_bytes / disk_total_bytes * 100
        # Set disk size
        if disk_total_bytes:
            self.disk_size = disk_total_bytes
        # Return values
        return disk_usage_bytes, disk_usage_pct

    def _calculate_network_io(
        self, resource: str, metrics: dict, update_interval: int
    ) -> tuple[float | None, float | None]:
        """Calculate network IO (receive bytes, transmit bytes)."""
        # Check if metrics are available
        if not metrics:
            return None, None
        # Check if update interval is valid
        if update_interval is None or update_interval <= 0:
            raise ValueError("Update interval must be positive")
        # Initialize variables
        prev_value_receive: int | None = None
        current_value_receive: int | None = None
        prev_value_transmit: int | None = None
        current_value_transmit: int | None = None
        network_receive_bytes_per_second: float | None = None
        network_transmit_bytes_per_second: float | None = None
        # Calculate network receive
        if NODE_NETWORK_RECEIVE in metrics:
            # Get current value
            current_value_receive = metrics[NODE_NETWORK_RECEIVE]
            # Get previous value
            if resource in self._previous_metrics:
                if NODE_NETWORK_RECEIVE in self._previous_metrics[resource]:
                    prev_value_receive = self._previous_metrics[resource][
                        NODE_NETWORK_RECEIVE
                    ]
            else:
                self._previous_metrics[resource] = {}
            # Set current value as previous value
            self._previous_metrics[resource][NODE_NETWORK_RECEIVE] = (
                current_value_receive
            )
            # Calculate network receive bytes per second
            if prev_value_receive is not None and current_value_receive is not None:
                network_receive_bytes_per_second = (
                    current_value_receive - prev_value_receive
                ) / update_interval
        # Calculate network transmit
        if NODE_NETWORK_TRANSMIT in metrics:
            # Get current value
            current_value_transmit = metrics[NODE_NETWORK_TRANSMIT]
            # Get previous value
            if resource in self._previous_metrics:
                if NODE_NETWORK_TRANSMIT in self._previous_metrics[resource]:
                    prev_value_transmit = self._previous_metrics[resource][
                        NODE_NETWORK_TRANSMIT
                    ]
            else:
                self._previous_metrics[resource] = {}
            # Set current value as previous value
            self._previous_metrics[resource][NODE_NETWORK_TRANSMIT] = (
                current_value_transmit
            )
            # Calculate network transmit bytes per second
            if prev_value_transmit is not None and current_value_transmit is not None:
                network_transmit_bytes_per_second = (
                    current_value_transmit - prev_value_transmit
                ) / update_interval
        # Return values
        return network_receive_bytes_per_second, network_transmit_bytes_per_second

    def _calculate_uptime(
        self, resource: str, metrics: dict
    ) -> tuple[int | None, int | None]:
        """Calculate uptime."""
        # Check if metrics are available
        if not metrics:
            return None, None
        # Initialize variables
        start_time: int | None = None
        uptime_seconds: int | None = None
        # Get values
        if NODE_BOOT_TIME in metrics:
            start_time = metrics[NODE_BOOT_TIME]
        # Calculate uptime
        if start_time is not None:
            uptime_seconds = int(time()) - start_time
        # Return values
        return uptime_seconds, start_time

    def _calculate_container_status(
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

    def _calculate_container_uptime(
        self, resource: str, start_time: int
    ) -> tuple[int | None, int | None]:
        """Calculate uptime."""
        # Check if metrics are available
        if not start_time:
            return None, None
        # Initialize variables
        uptime_seconds: int | None = None
        # Calculate uptime
        if start_time is not None:
            uptime_seconds = int(time()) - start_time
        # Return values
        return uptime_seconds, start_time
