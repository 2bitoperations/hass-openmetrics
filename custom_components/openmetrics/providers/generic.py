"""Generic metrics provider."""

import re
from time import time

from ..const import (
    METRIC_CPU_USAGE_PCT,
    METRIC_DISK_USAGE_BYTES,
    METRIC_DISK_USAGE_PCT,
    METRIC_MEMORY_USAGE_BYTES,
    METRIC_MEMORY_USAGE_PCT,
    METRIC_NETWORK_RECEIVE_BYTES,
    METRIC_NETWORK_TRANSMIT_BYTES,
    METRIC_UPTIME_SECONDS,
    PROVIDER_NAME_GENERIC,
    RESOURCE_TYPE_GENERIC,
)
from ..lib.metrics_core import Metric
from ..lib.samples import Sample
from ..metrics.data import ProviderInfoData, ResourceInfoData
from ..metrics.filter import MetricFilter
from ..providers.base import MetricsProvider
from .cadvisor import PROVIDER_FILTERS as CADVISOR_PROVIDER_FILTERS
from .node_exporter import PROVIDER_FILTERS as NODE_EXPORTER_PROVIDER_FILTERS


class GenericProvider(MetricsProvider):
    """Generic metrics provider."""

    # Metric regexes
    CPU_CORES_REGEX = "^[^_]+_cpu_cores$"
    CPU_SECONDS_REGEX = "^(?!process)[^_]+_cpu(?:_usage)?_seconds$"
    MEMORY_BYTES_REGEX = "^[^_]+(?:_spec)?_memory(?:_(?:usage|limit|(?:MemFree|MemTotal|SwapTotal)))?_bytes$"
    DISK_BYTES_REGEX = "^[^_]+_(?:filesystem|fs)_(?:size|free|limit|usage)_bytes$"
    NETWORK_BYTES_REGEX = "^[^_]+(?:_spec)?_network_(?:receive|transmit)_bytes$"
    TIME_SECONDS_REGEX = "^(?!process)[^_]+(?:_start|_boot)?_time_seconds$"
    RESOURCE_REGEX = "^[^_]+_.*name_info$"
    RESOURCE_LABEL_REGEX = "^(?:node)?name$"

    metric_filters = [
        MetricFilter(
            metric_key=CPU_SECONDS_REGEX,
            label_filters={"mode": "idle"},
        ),
        MetricFilter(
            metric_key=CPU_SECONDS_REGEX,
            label_filters={"image": ".+", "name": ".+"},
            resource_label="name",
        ),
        MetricFilter(metric_key=CPU_CORES_REGEX, label_filters={"machine_id": ".+"}),
        MetricFilter(
            metric_key=MEMORY_BYTES_REGEX,
        ),
        MetricFilter(
            metric_key=MEMORY_BYTES_REGEX,
            label_filters={"image": ".+", "name": ".+"},
            resource_label="name",
        ),
        MetricFilter(
            metric_key=DISK_BYTES_REGEX,
            label_filters={"mountpoint": "/"},
        ),
        MetricFilter(
            metric_key=DISK_BYTES_REGEX,
            label_filters={"image": ".+", "name": ".+"},
            resource_label="name",
        ),
        MetricFilter(
            metric_key=NETWORK_BYTES_REGEX,
            label_filters={"device": "eth0"},
        ),
        MetricFilter(
            metric_key=NETWORK_BYTES_REGEX,
            label_filters={"image": ".+", "name": ".+", "interface": "eth0"},
            resource_label="name",
        ),
        MetricFilter(
            metric_key=TIME_SECONDS_REGEX,
        ),
        MetricFilter(
            metric_key=TIME_SECONDS_REGEX,
            label_filters={"image": ".+", "name": ".+"},
            resource_label="name",
        ),
    ]
    found_metrics = {
        "cpu_usage": False,
        "cpu_cores": False,
        "cpu_seconds": False,
        "memory_limit": False,
        "memory_bytes": False,
        "memory_usage": False,
        "memory_total": False,
        "memory_free": False,
        "filesystem_limit": False,
        "filesystem_usage": False,
        "filesystem_size": False,
        "filesystem_free": False,
        "network_receive": False,
        "network_transmit": False,
        "start_time": False,
        "boot_time": False,
    }

    def __init__(self):
        """Initialize generic provider."""
        super().__init__(PROVIDER_NAME_GENERIC, RESOURCE_TYPE_GENERIC)
        self.provider_filters: list[MetricFilter] = []
        self.provider_filters.extend(CADVISOR_PROVIDER_FILTERS)
        self.provider_filters.extend(NODE_EXPORTER_PROVIDER_FILTERS)

    def extract_provider_info(self, family: Metric, provider_info: ProviderInfoData):
        """Extract provider information."""

    def extract_resource_info(self, family: Metric, resources: dict):
        """Extract resource information."""
        if re.match(self.RESOURCE_REGEX, family.name, re.IGNORECASE):
            for sample in family.samples:
                for label in sample.labels:
                    if re.match(self.RESOURCE_LABEL_REGEX, label):
                        name = sample.labels.get(label)
                        if name is not None and name != "" and name not in resources:
                            resources[name] = ResourceInfoData(
                                type=RESOURCE_TYPE_GENERIC, name=name
                            )
                            self.resource_name = name
        elif re.match(self.TIME_SECONDS_REGEX, family.name, re.IGNORECASE):
            for sample in family.samples:
                for label in sample.labels:
                    if re.match(self.RESOURCE_LABEL_REGEX, label):
                        name = sample.labels.get(label)
                        if name is not None and name != "" and name not in resources:
                            resources[name] = ResourceInfoData(
                                type=RESOURCE_TYPE_GENERIC, name=name
                            )

    def collect_supported_metric(self, family: Metric, available_metrics: list[str]):
        """Collect supported metrics."""
        # CPU
        if re.match("(?i).+_cpu_usage", family.name):
            self.found_metrics["cpu_usage"] = True
        elif re.match("(?i).+_cpu_cores", family.name):
            self.found_metrics["cpu_cores"] = True
        elif re.match("(?i).+_cpu_seconds", family.name):
            self.found_metrics["cpu_seconds"] = True
            self._add_str_to_list_uniquely(METRIC_CPU_USAGE_PCT, available_metrics)
        # Memory
        elif re.match("(?i).+_memory_limit", family.name):
            self.found_metrics["memory_limit"] = True
        elif re.match("(?i).+_memory_bytes", family.name):
            self.found_metrics["memory_bytes"] = True
        elif re.match("(?i).+_memory_usage", family.name):
            self.found_metrics["memory_usage"] = True
        elif re.match("(?i).+_memory.*total", family.name):
            self.found_metrics["memory_total"] = True
        elif re.match("(?i).+memory.*free", family.name):
            self.found_metrics["memory_free"] = True
        # Filesystem
        elif re.match(".+_(?:fs|filesystem).*limit", family.name):
            self.found_metrics["filesystem_limit"] = True
        elif re.match(".+_(?:fs|filesystem).*usage", family.name):
            self.found_metrics["filesystem_usage"] = True
        elif re.match(".+_(?:fs|filesystem).*size", family.name):
            self.found_metrics["filesystem_size"] = True
        elif re.match(".+_(?:fs|filesystem).*free", family.name):
            self.found_metrics["filesystem_free"] = True
        # Network
        elif re.match(".+_network_receive.*", family.name):
            self.found_metrics["network_receive"] = True
            self._add_str_to_list_uniquely(
                METRIC_NETWORK_RECEIVE_BYTES, available_metrics
            )
        elif re.match(".+_network_transmit.*", family.name):
            self.found_metrics["network_transmit"] = True
            self._add_str_to_list_uniquely(
                METRIC_NETWORK_TRANSMIT_BYTES, available_metrics
            )
        # Uptime
        elif re.match(".+start_time.*", family.name):
            self.found_metrics["start_time"] = True
            self._add_str_to_list_uniquely(METRIC_UPTIME_SECONDS, available_metrics)
        elif re.match(".+_boot_time.*", family.name):
            self.found_metrics["boot_time"] = True
            self._add_str_to_list_uniquely(METRIC_UPTIME_SECONDS, available_metrics)

        # Add paired metrics after checking both components are present
        if self.found_metrics["cpu_usage"] and self.found_metrics["cpu_cores"]:
            self._add_str_to_list_uniquely(METRIC_CPU_USAGE_PCT, available_metrics)

        if (
            (self.found_metrics["memory_total"] and self.found_metrics["memory_free"])
            or (
                self.found_metrics["memory_limit"]
                and self.found_metrics["memory_usage"]
            )
            or (
                self.found_metrics["memory_bytes"]
                and self.found_metrics["memory_usage"]
            )
        ):
            self._add_str_to_list_uniquely(METRIC_MEMORY_USAGE_PCT, available_metrics)
        if (
            self.found_metrics["memory_total"] and self.found_metrics["memory_free"]
        ) or self.found_metrics["memory_usage"]:
            self._add_str_to_list_uniquely(METRIC_MEMORY_USAGE_BYTES, available_metrics)

        if (
            self.found_metrics["filesystem_size"]
            and self.found_metrics["filesystem_free"]
        ) or (
            self.found_metrics["filesystem_limit"]
            and self.found_metrics["filesystem_usage"]
        ):
            self._add_str_to_list_uniquely(METRIC_DISK_USAGE_PCT, available_metrics)
        if (
            self.found_metrics["filesystem_size"]
            and self.found_metrics["filesystem_free"]
        ) or self.found_metrics["filesystem_usage"]:
            self._add_str_to_list_uniquely(METRIC_DISK_USAGE_BYTES, available_metrics)

    def prepare_metric_value(self, metric_key: str, sample: Sample) -> float | dict:
        """Override: Collect metric value."""
        cpu = sample.labels.get("cpu")
        if cpu:
            return {cpu: sample.value}
        return sample.value

    def _share_common_metrics(self, metrics: dict):
        """Share common metrics between resources."""
        # Check if metrics are available
        if not metrics:
            return
        if self.RESOURCE_NAME in metrics:
            # Get machine related metrics
            for metric_key in metrics[self.RESOURCE_NAME]:
                if re.match(self.CPU_CORES_REGEX, metric_key):
                    cpu_cores = metrics[self.resource_name][metric_key]
                    cpu_cores_metric_key = metric_key
                    break
            # Share common metrics
            for metric_key, metric in metrics.items():
                if metric_key != self.RESOURCE_NAME:
                    # Share CPU cores
                    if cpu_cores is not None:
                        metric[cpu_cores_metric_key] = cpu_cores

    def _calculate_cpu_usage(
        self, resource: str, metrics: dict, update_interval: int
    ) -> tuple[float | None, dict[int, float] | None]:
        """Calculate CPU usage (pct, dict)."""
        # Check if metrics are available
        if not metrics:
            return None, None

        # Initialize variables
        prev_value = None
        current_value = None
        cpu_usage_pct = None
        cpu_usage_total_pct = None
        cpu_cores_key = None
        cpu_seconds_key = None
        cpu_core_usage = {}

        for metric_key in metrics:
            if re.match(self.CPU_SECONDS_REGEX, metric_key):
                cpu_seconds_key = metric_key
            if re.match(self.CPU_CORES_REGEX, metric_key):
                cpu_cores_key = metric_key

        # Calculate CPU usage
        if cpu_seconds_key and cpu_seconds_key in metrics:
            cpu_usage_metric = metrics[cpu_seconds_key]
            cpu_usage_total_pct = None

            for cpu in cpu_usage_metric:
                # Get current value
                current_value = cpu_usage_metric[cpu]
                # Get previous value
                if resource in self._previous_metrics:
                    if cpu_seconds_key in self._previous_metrics[resource]:
                        if cpu in self._previous_metrics[resource][cpu_seconds_key]:
                            prev_value = self._previous_metrics[resource][
                                cpu_seconds_key
                            ][cpu]
                else:
                    self._previous_metrics[resource] = {}
                    self._previous_metrics[resource][cpu_seconds_key] = {}
                # Set current value as previous value
                self._previous_metrics[resource][cpu_seconds_key][cpu] = current_value
                if prev_value is not None and current_value is not None:
                    # CPU usage seconds
                    if re.match(".*usage.*", cpu_seconds_key):
                        self.cpu_cores = int(metrics.get(cpu_cores_key, 1))
                        cpu_usage_time_delta = (
                            current_value - prev_value
                        )  # max = update interval * cores
                        # Calculate total CPU usage
                        cpu_cores_used = cpu_usage_time_delta / update_interval
                        cpu_usage_pct = cpu_cores_used / self.cpu_cores * 100
                        if cpu_usage_pct > 100:
                            cpu_usage_pct = 100
                        elif cpu_usage_pct < 0:
                            cpu_usage_pct = 0
                    # CPU idle seconds
                    else:
                        # Calculate CPU core usage
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
                        cpu_usage_total_pct += (
                            cpu_core_usage_pct  # max = 100% * cpu cores
                        )

            # Calculate total CPU usage
            if cpu_usage_total_pct is not None:
                self.cpu_cores = len(metrics[cpu_seconds_key])
                cpu_usage_pct = cpu_usage_total_pct / self.cpu_cores

        return (cpu_usage_pct, cpu_core_usage)

    def _calculate_memory_usage(
        self, resource: str, metrics: dict
    ) -> tuple[int | None, float | None]:
        """Calculate memory usage (used bytes, used pct)."""
        # Check if metrics are available
        if not metrics:
            return None, None

        # Initialize variables
        memory_total_bytes = None
        memory_free_bytes = None
        memory_usage_bytes = None
        memory_usage_pct = None
        memory_limit_key = None
        memory_usage_key = None
        memory_total_key = None
        memory_swap_key = None
        memory_free_key = None

        # Find relevant memory metric keys
        for metric_key in metrics:
            if re.match(".*memory.*limit.*", metric_key, re.IGNORECASE):
                memory_limit_key = metric_key
            elif re.match(".*memory.*usage.*", metric_key, re.IGNORECASE):
                memory_usage_key = metric_key
            elif re.match(".*memory(?!.*swap)(?=.*total).*", metric_key, re.IGNORECASE):
                memory_total_key = metric_key
            elif re.match(".*memory(?=.*swap)(?=.*total).*", metric_key, re.IGNORECASE):
                memory_swap_key = metric_key
            elif re.match(".*memory.*free.*", metric_key, re.IGNORECASE):
                memory_free_key = metric_key

        # Memory usage and limit
        if memory_usage_key and memory_usage_key in metrics:
            memory_usage_bytes = metrics[memory_usage_key]

            # Get total memory, preferring container limit if available
            if memory_limit_key and memory_limit_key in metrics:
                memory_total_bytes = metrics[memory_limit_key]
            elif memory_total_key and memory_total_key in metrics:
                memory_total_bytes = metrics[memory_total_key]

        # Total and free memory
        elif (
            memory_total_key
            and memory_free_key
            and memory_total_key in metrics
            and memory_free_key in metrics
        ):
            memory_total_bytes = metrics[memory_total_key]
            memory_free_bytes = metrics[memory_free_key]

            if memory_total_bytes is not None and memory_free_bytes is not None:
                memory_usage_bytes = memory_total_bytes - memory_free_bytes

        # Calculate memory usage
        if (
            memory_total_bytes
            and memory_total_bytes > 0
            and memory_usage_bytes
            and memory_usage_bytes > 0
        ):
            memory_usage_pct = memory_usage_bytes / memory_total_bytes * 100
            memory_usage_pct = min(memory_usage_pct, 100)

        # Set memory size
        if memory_total_bytes:
            self.memory_size = memory_total_bytes
        if memory_swap_key and memory_swap_key in metrics:
            memory_swap_size = metrics[memory_swap_key]
            self.memory_size += memory_swap_size

        # Return values
        return memory_usage_bytes, memory_usage_pct

    def _calculate_disk_usage(
        self, resource: str, metrics: dict
    ) -> tuple[int | None, float | None]:
        """Calculate disk usage (used bytes, used pct)."""
        # Check if metrics are available
        if not metrics:
            return None, None

        # Initialize variables
        disk_total_bytes = None
        disk_free_bytes = None
        disk_usage_bytes = None
        disk_usage_pct = None
        disk_limit_key = None
        disk_usage_key = None
        disk_size_key = None
        disk_free_key = None

        # Find relevant disk metric keys
        for metric_key in metrics:
            if re.match(".*(?:fs|filesystem).*limit.*", metric_key, re.IGNORECASE):
                disk_limit_key = metric_key
            elif re.match(".*(?:fs|filesystem).*usage.*", metric_key, re.IGNORECASE):
                disk_usage_key = metric_key
            elif re.match(".*(?:fs|filesystem).*size.*", metric_key, re.IGNORECASE):
                disk_size_key = metric_key
            elif re.match(".*(?:fs|filesystem).*free.*", metric_key, re.IGNORECASE):
                disk_free_key = metric_key

        # Direct disk usage and limit
        if (
            disk_usage_key
            and disk_limit_key
            and disk_usage_key in metrics
            and disk_limit_key in metrics
        ):
            disk_total_bytes = metrics[disk_limit_key]
            disk_usage_bytes = metrics[disk_usage_key]
        # Size and free space
        elif (
            disk_size_key
            and disk_free_key
            and disk_size_key in metrics
            and disk_free_key in metrics
        ):
            disk_total_bytes = metrics[disk_size_key]
            disk_free_bytes = metrics[disk_free_key]

            if disk_total_bytes is not None and disk_free_bytes is not None:
                disk_usage_bytes = disk_total_bytes - disk_free_bytes

        # Common calculation for disk usage percentage
        if (
            disk_total_bytes is not None
            and disk_total_bytes > 0
            and disk_usage_bytes is not None
        ):
            disk_usage_pct = disk_usage_bytes / disk_total_bytes * 100
            disk_usage_pct = min(disk_usage_pct, 100)

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
        prev_value_receive = None
        current_value_receive = None
        prev_value_transmit = None
        current_value_transmit = None
        network_receive_bytes_per_second = None
        network_transmit_bytes_per_second = None
        network_receive_key = None
        network_transmit_key = None

        # Find relevant network metric keys
        for metric_key in metrics:
            if re.match(".*network.*receive.*", metric_key, re.IGNORECASE):
                network_receive_key = metric_key
            elif re.match(".*network.*transmit.*", metric_key, re.IGNORECASE):
                network_transmit_key = metric_key

        # Calculate network receive
        if network_receive_key and network_receive_key in metrics:
            # Get current value
            current_value_receive = metrics[network_receive_key]
            # Get previous value
            if resource in self._previous_metrics:
                if network_receive_key in self._previous_metrics[resource]:
                    prev_value_receive = self._previous_metrics[resource][
                        network_receive_key
                    ]
            else:
                self._previous_metrics[resource] = {}
            # Set current value as previous value
            self._previous_metrics[resource][network_receive_key] = (
                current_value_receive
            )
            # Calculate network receive bytes per second
            if prev_value_receive is not None and current_value_receive is not None:
                network_receive_bytes_per_second = (
                    current_value_receive - prev_value_receive
                ) / update_interval
                network_receive_bytes_per_second = max(
                    network_receive_bytes_per_second, 0
                )

        # Calculate network transmit
        if network_transmit_key and network_transmit_key in metrics:
            # Get current value
            current_value_transmit = metrics[network_transmit_key]
            # Get previous value
            if resource in self._previous_metrics:
                if network_transmit_key in self._previous_metrics[resource]:
                    prev_value_transmit = self._previous_metrics[resource][
                        network_transmit_key
                    ]
            else:
                self._previous_metrics[resource] = {}
            # Set current value as previous value
            self._previous_metrics[resource][network_transmit_key] = (
                current_value_transmit
            )
            # Calculate network transmit bytes per second
            if prev_value_transmit is not None and current_value_transmit is not None:
                network_transmit_bytes_per_second = (
                    current_value_transmit - prev_value_transmit
                ) / update_interval
                network_transmit_bytes_per_second = max(
                    network_transmit_bytes_per_second, 0
                )

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
        start_time_key = None
        boot_time_key = None

        # Find relevant uptime metric keys
        for metric_key in metrics:
            if re.match(".*start_time.*", metric_key, re.IGNORECASE):
                start_time_key = metric_key
            elif re.match(".*boot_time.*", metric_key, re.IGNORECASE):
                boot_time_key = metric_key

        # Get start time (cAdvisor style or Node Exporter style)
        if start_time_key and start_time_key in metrics:
            start_time = metrics[start_time_key]
        elif boot_time_key and boot_time_key in metrics:
            start_time = metrics[boot_time_key]

        # Calculate uptime
        if start_time is not None:
            uptime_seconds = int(time()) - start_time
            uptime_seconds = max(uptime_seconds, 0)

        # Return values
        return uptime_seconds, start_time
