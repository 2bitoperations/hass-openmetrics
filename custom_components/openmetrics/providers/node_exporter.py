"""Node Exporter provider."""

from time import time

from ..const import (
    CONTAINER_STATE_STARTEDAT,
    CONTAINER_STATE_STATUS,
    METRIC_CONTAINER_STATUS,
    METRIC_CONTAINER_STATUS_CREATED,
    METRIC_CONTAINER_STATUS_DEAD,
    METRIC_CONTAINER_STATUS_EXITED,
    METRIC_CONTAINER_STATUS_PAUSED,
    METRIC_CONTAINER_STATUS_REMOVING,
    METRIC_CONTAINER_STATUS_RESTARTING,
    METRIC_CONTAINER_STATUS_RUNNING,
    METRIC_CONTAINER_UPTIME,
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
    NODE_CONTAINER_RESOURCE_LABEL,
    NODE_CPU_IDLE_SECONDS,
    NODE_CPU_TEMP,
    NODE_DEVICE_INFO,
    NODE_EXPORTER_BUILD_INFO,
    NODE_EXPORTER_RESOURCE_LABEL,
    NODE_EXPORTER_VERSION_LABEL,
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
    RESOURCE_TYPE_CONTAINER,
    RESOURCE_TYPE_NODE,
)
from ..lib.metrics_core import Metric
from ..lib.samples import Sample
from ..metrics import MetricFilter
from ..metrics.data import (
    MetadataData,
    ResourceInfoData,
)
from .base import MetricsProvider, ProviderConfig


class NodeExporterProvider(MetricsProvider):
    """Node Exporter metrics provider."""

    def __init__(self):
        """Initialize node exporter provider."""
        super().__init__(PROVIDER_NAME_NODE_EXPORTER, RESOURCE_TYPE_NODE)

    def get_config(self) -> ProviderConfig:
        """Return provider configuration."""
        provider_config = ProviderConfig(
            identifier_metric=NODE_EXPORTER_BUILD_INFO,
            version_label=NODE_EXPORTER_VERSION_LABEL,
            resource_identifier=NODE_EXPORTER_RESOURCE_LABEL,
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
                MetricFilter(
                    metric_name=METRIC_CONTAINER_STATUS_CREATED,
                    metric_key=CONTAINER_STATE_STATUS,
                    label_filters={"status": "created"},
                    resource_label=NODE_CONTAINER_RESOURCE_LABEL,
                ),
                MetricFilter(
                    metric_name=METRIC_CONTAINER_STATUS_DEAD,
                    metric_key=CONTAINER_STATE_STATUS,
                    label_filters={"status": "dead"},
                    resource_label=NODE_CONTAINER_RESOURCE_LABEL,
                ),
                MetricFilter(
                    metric_name=METRIC_CONTAINER_STATUS_EXITED,
                    metric_key=CONTAINER_STATE_STATUS,
                    label_filters={"status": "exited"},
                    resource_label=NODE_CONTAINER_RESOURCE_LABEL,
                ),
                MetricFilter(
                    metric_name=METRIC_CONTAINER_STATUS_PAUSED,
                    metric_key=CONTAINER_STATE_STATUS,
                    label_filters={"status": "paused"},
                    resource_label=NODE_CONTAINER_RESOURCE_LABEL,
                ),
                MetricFilter(
                    metric_name=METRIC_CONTAINER_STATUS_REMOVING,
                    metric_key=CONTAINER_STATE_STATUS,
                    label_filters={"status": "removing"},
                    resource_label=NODE_CONTAINER_RESOURCE_LABEL,
                ),
                MetricFilter(
                    metric_name=METRIC_CONTAINER_STATUS_RESTARTING,
                    metric_key=CONTAINER_STATE_STATUS,
                    label_filters={"status": "restarting"},
                    resource_label=NODE_CONTAINER_RESOURCE_LABEL,
                ),
                MetricFilter(
                    metric_name=METRIC_CONTAINER_STATUS_RUNNING,
                    metric_key=CONTAINER_STATE_STATUS,
                    label_filters={"status": "running"},
                    resource_label=NODE_CONTAINER_RESOURCE_LABEL,
                ),
                MetricFilter(
                    metric_name=METRIC_CONTAINER_UPTIME,
                    metric_key=CONTAINER_STATE_STARTEDAT,
                    resource_label=NODE_CONTAINER_RESOURCE_LABEL,
                ),
            ],
        )
        # Extract virtual resource keys and names
        virtual_resource_metric_keys = []
        virtual_resource_metric_names = []
        for metric_filter in provider_config.metric_filters:
            if metric_filter.resource_label is not None:
                if metric_filter.metric_key not in virtual_resource_metric_keys:
                    virtual_resource_metric_keys.append(metric_filter.metric_key)
                if metric_filter.metric_name not in virtual_resource_metric_names:
                    virtual_resource_metric_names.append(metric_filter.metric_name)
        self.__virtual_resource_metric_keys = virtual_resource_metric_keys
        self.__virtual_resource_metric_names = virtual_resource_metric_names
        # Return provider config
        return provider_config

    def extract_provider_info(self, family: Metric, metadata: MetadataData):
        """Extract and store provider information."""
        if family.name == self.get_config().identifier_metric and family.samples:
            metadata.provider_info.version = family.samples[0].labels[
                self.get_config().version_label
            ]

    def extract_resource_info(self, family: Metric, metadata: MetadataData):
        """Extract and store node resource information."""
        # Initialize resource info if not yet initialized
        if self.name not in metadata.resources:
            resource_info = ResourceInfoData(type=RESOURCE_TYPE_NODE)
            metadata.resources[self.name] = resource_info
        else:
            resource_info = metadata.resources[self.name]
        # Extract resource info
        if family.name == NODE_UNAME_INFO:
            for sample in family.samples:
                nodename = sample.labels.get("nodename", None)
                if nodename:
                    resource_info.name = nodename
                    self.resource_name = nodename
        elif family.name == NODE_OS_INFO:
            for sample in family.samples:
                resource_info.software = sample.labels.get("pretty_name")
                resource_info.version = sample.labels.get("version")
        elif family.name == NODE_DEVICE_INFO:
            for sample in family.samples:
                resource_info.model = sample.labels.get("model")
                resource_info.serial_number = sample.labels.get("serial")
        elif family.name in self.__virtual_resource_metric_keys:
            for sample in family.samples:
                v_resource_name = sample.labels.get(NODE_CONTAINER_RESOURCE_LABEL)
                if v_resource_name and v_resource_name not in metadata.resources:
                    v_resource_info = ResourceInfoData(
                        type=RESOURCE_TYPE_CONTAINER,
                        name=v_resource_name,
                        software=sample.labels.get("image"),
                        is_virtual=True,
                    )
                    metadata.resources[v_resource_name] = v_resource_info

    def extract_available_metrics(self, family: Metric, metadata: MetadataData):
        """Extract and store available metrics."""
        for metric_filter in self.get_config().metric_filters:
            # Check if metric is available
            if family.name == metric_filter.metric_key:
                # In case of metric_key is a container status metric,
                if (
                    metric_filter.metric_name in self.__virtual_resource_metric_names
                    and metric_filter.metric_name.startswith(METRIC_CONTAINER_STATUS)
                ):
                    metric = METRIC_CONTAINER_STATUS
                # Otherwise, use metric_name
                else:
                    metric = metric_filter.metric_name
                # Add metric to available metrics if not already present
                if metric not in metadata.available_metrics:
                    metadata.available_metrics.append(metric)
                    if metric == METRIC_MEMORY_USAGE_BYTES:
                        metadata.available_metrics.append(METRIC_MEMORY_USAGE_PCT)
                    if metric == METRIC_DISK_USAGE_BYTES:
                        metadata.available_metrics.append(METRIC_DISK_USAGE_PCT)
                break

    def prepare_metric_value(self, metric_key: str, sample: Sample) -> float | dict:
        """Override: Collect metric value."""
        if metric_key == NODE_CPU_IDLE_SECONDS:
            cpu = sample.labels["cpu"]
            return {cpu: sample.value}
        if metric_key == CONTAINER_STATE_STATUS:
            status = sample.labels["status"]
            return {status: sample.value}
        return sample.value

    def process_metrics(self, metrics: dict, update_interval: int) -> dict | None:
        """Process metrics and return sensor metrics."""
        sensor_metrics = {}
        for resource, resource_metrics in metrics.items():
            # Create resource sensor metrics if not existing
            if resource not in sensor_metrics:
                sensor_metrics[resource] = {}
            # Process resource metrics
            res_metrics = self._process_resource_metrics(
                resource, resource_metrics, update_interval
            )
            if res_metrics:
                sensor_metrics[resource].update(res_metrics)
            # Process virtual resource metrics
            v_res_metrics = self._process_virtual_resource_metrics(
                resource, resource_metrics
            )
            if v_res_metrics:
                sensor_metrics[resource].update(v_res_metrics)
        # Return sensor metrics
        return sensor_metrics

    def _process_resource_metrics(
        self, resource: str, metrics: dict, update_interval: int
    ) -> dict | None:
        """Process resource metrics and return sensor metrics."""
        if resource == self.resource_name:
            sensor_metrics = super()._process_resource_metrics(
                resource, metrics, update_interval
            )
            # CPU temperature
            if NODE_CPU_TEMP in metrics and sensor_metrics:
                sensor_metrics[METRIC_CPU_TEMP] = metrics[NODE_CPU_TEMP]
        else:
            sensor_metrics = None
        # Return sensor metrics
        return sensor_metrics

    def _process_virtual_resource_metrics(
        self, resource: str, metrics: dict
    ) -> dict | None:
        """Process virtual resource metrics and return sensor metrics."""
        sensor_metrics = {}
        # Calculate container status
        if CONTAINER_STATE_STATUS in metrics:
            sensor_metrics[METRIC_CONTAINER_STATUS] = self._calculate_container_status(
                resource, metrics[CONTAINER_STATE_STATUS]
            )
        # Calculate container uptime
        if CONTAINER_STATE_STARTEDAT in metrics:
            uptime_seconds, start_time = self._calculate_container_uptime(
                resource, metrics[CONTAINER_STATE_STARTEDAT]
            )
            sensor_metrics[METRIC_CONTAINER_UPTIME] = uptime_seconds
        return sensor_metrics

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
        return (cpu_usage_pct, cpu_core_usage)

    def _calculate_memory_usage(
        self, resource: str, metrics: dict[str, int]
    ) -> tuple[int | None, float | None]:
        """Calculate memory usage."""
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
        self._set_memory_size(resource, metrics)
        # Return values
        return memory_usage_bytes, memory_usage_pct

    def _set_memory_size(self, resource: str, metrics: dict[str, int]) -> None:
        """Set memory size."""
        if NODE_MEMORY_TOTAL in metrics:
            self.memory_size: int = metrics[NODE_MEMORY_TOTAL]
        if self.memory_size and NODE_MEMORY_SWAP_TOTAL in metrics:
            self.memory_size += int(metrics[NODE_MEMORY_SWAP_TOTAL])

    def _calculate_disk_usage(
        self, resource, metrics
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
        self._set_disk_size(resource, metrics)
        # Return values
        return disk_usage_bytes, disk_usage_pct

    def _set_disk_size(self, resource: str, metrics: dict[str, int]) -> None:
        """Set disk size."""
        if NODE_FILESYSTEM_SIZE in metrics:
            self.disk_size: int = metrics[NODE_FILESYSTEM_SIZE]

    def _calculate_network_io(
        self, resource: str, metrics: dict, update_interval: int
    ) -> tuple[int | None, int | None]:
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
        start_time = None
        uptime_seconds = None
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
        uptime_seconds = None
        # Calculate uptime
        if start_time is not None:
            uptime_seconds = int(time()) - start_time
        # Return values
        return uptime_seconds, start_time
