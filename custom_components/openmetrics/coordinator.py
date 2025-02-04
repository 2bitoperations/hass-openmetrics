"""Coordinator for OpenMetrics."""

import logging
from datetime import datetime, timedelta
from time import time

from homeassistant.const import UnitOfInformation
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util
from homeassistant.util.unit_conversion import BaseUnitConverter

from .client import (
    CannotConnectError,
    ClientError,
    InvalidAuthError,
    OpenMetricsClient,
    RequestError,
)
from .const import (
    CONTAIENR_MEMORY_SWAP,
    CONTAINER_CPU_USAGE,
    CONTAINER_FS_LIMIT,
    CONTAINER_FS_USAGE,
    CONTAINER_MEMORY_LIMIT,
    CONTAINER_MEMORY_USAGE,
    CONTAINER_NETWORK_RECEIVE,
    CONTAINER_NETWORK_TRANSMIT,
    CONTAINER_START_TIME,
    DOMAIN,
    MACHINE_CPU_CORES,
    MACHINE_MEMORY,
    MACHINE_SWAP,
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
    NODE_FILESYSTEM_FREE,
    NODE_FILESYSTEM_SIZE,
    NODE_MEMORY_FREE,
    NODE_MEMORY_SWAP_TOTAL,
    NODE_MEMORY_TOTAL,
    NODE_NETWORK_RECEIVE,
    NODE_NETWORK_TRANSMIT,
)
from .sensor import SENSORS

_LOGGER = logging.getLogger(__name__)


class OpenMetricsDataUpdateCoordinator(DataUpdateCoordinator):
    """Define an object to manage OpenMetrics data update coordination."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: OpenMetricsClient,
        resources: list[str],
        update_interval: int,
    ) -> None:
        """Initialize the data update coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=update_interval),
        )
        self._client = client
        self._resources = resources
        self._previous_metrics = {}
        self.last_start_time = None
        self.cpu_cores = None
        self.memory_size = None
        self.disk_size = None

    async def _async_update_data(self):
        """Fetch OpenMetrics data."""
        try:
            # Get metrics
            metrics = await self._client.get_metrics(self._resources)
            # Process metrics for sensors
            sensor_data = self._process_data(metrics)
        except CannotConnectError as e:
            _LOGGER.error("Failed to connect: %s", str(e))
        except InvalidAuthError as e:
            _LOGGER.error("Authentication failed: %s", str(e))
        except RequestError as e:
            _LOGGER.error("Resources error: %s", str(e))
        except ClientError as e:
            _LOGGER.error("Processing error: %s", str(e))
        except ValueError as e:
            _LOGGER.error("Value error: %s", str(e))
        except Exception:
            _LOGGER.exception("Unexpected exception")
        else:
            # Return sensor data
            return sensor_data

    def _calculate_cpu_usage(self, resource, metrics):
        """Calculate CPU usage."""
        prev_value = None
        current_value = None
        cpu_usage_pct = None
        cpu_core_usage = {}
        if self.update_interval is None or self.update_interval.seconds <= 0:
            raise ValueError("Update interval must be positive")
        # Node Exporter
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
                        1 - cpu_core_idle_time_delta / self.update_interval.seconds
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
                cpu_cores = len(metrics[NODE_CPU_IDLE_SECONDS])
                cpu_usage_pct = cpu_usage_total_pct / cpu_cores
        # cAdvisor
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
                cpu_cores_used = cpu_usage_time_delta / self.update_interval.seconds
                cpu_usage_pct = cpu_cores_used / cpu_cores * 100
                if cpu_usage_pct > 100:
                    cpu_usage_pct = 100
                elif cpu_usage_pct < 0:
                    cpu_usage_pct = 0
        # Return values
        return (cpu_usage_pct, cpu_core_usage)

    def _calculate_memory_usage(self, resource, metrics):
        """Calculate memory usage."""
        memory_total_bytes = None
        memory_free_bytes = None
        memory_usage_bytes = None
        memory_usage_pct = None
        # Node Exporter
        if NODE_MEMORY_TOTAL in metrics:
            memory_total_bytes = metrics[NODE_MEMORY_TOTAL]
        if NODE_MEMORY_FREE in metrics:
            memory_free_bytes = metrics[NODE_MEMORY_FREE]
        # cAdvisor
        if CONTAINER_MEMORY_USAGE in metrics:
            memory_usage_bytes = metrics[CONTAINER_MEMORY_USAGE]
        if CONTAINER_MEMORY_LIMIT in metrics:
            memory_total_bytes = metrics[CONTAINER_MEMORY_LIMIT]
        if MACHINE_MEMORY in metrics and (
            memory_total_bytes is None or memory_total_bytes == 0
        ):
            memory_total_bytes = metrics[MACHINE_MEMORY]
        # Calculate memory usage
        if memory_total_bytes is not None and (
            memory_free_bytes is not None or memory_usage_bytes is not None
        ):
            if memory_usage_bytes is None:
                memory_usage_bytes = memory_total_bytes - memory_free_bytes
            if memory_total_bytes > 0:
                memory_usage_pct = memory_usage_bytes / memory_total_bytes * 100
        # Return values
        return (memory_usage_bytes, memory_usage_pct)

    def _calculate_disk_usage(self, resource, metrics):
        """Calculate disk usage."""
        disk_total_bytes = None
        disk_usage_bytes = None
        disk_usage_pct = None
        # Node Exporter
        if NODE_FILESYSTEM_SIZE in metrics:
            disk_total_bytes = metrics[NODE_FILESYSTEM_SIZE]
            disk_free_bytes = metrics[NODE_FILESYSTEM_FREE]
            disk_usage_bytes = disk_total_bytes - disk_free_bytes
        if CONTAINER_FS_LIMIT in metrics:
            disk_total_bytes = metrics[CONTAINER_FS_LIMIT]
            disk_usage_bytes = metrics[CONTAINER_FS_USAGE]
        # Calculate disk usage
        if disk_total_bytes is not None and disk_usage_bytes is not None:
            disk_usage_pct = disk_usage_bytes / disk_total_bytes * 100
        # Return values
        return (disk_usage_bytes, disk_usage_pct)

    def _calculate_network_io(self, resource, metrics):
        """Calculate network IO."""
        prev_value_receive = None
        current_value_receive = None
        prev_value_transmit = None
        current_value_transmit = None
        network_receive_bytes_per_second = None
        network_transmit_bytes_per_second = None
        if self.update_interval is None or self.update_interval.seconds <= 0:
            raise ValueError("Update interval must be positive")
        # Node Exporter
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
                ) / self.update_interval.seconds
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
                ) / self.update_interval.seconds
        # cAdvisor
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
                ) / self.update_interval.seconds
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
                ) / self.update_interval.seconds
        # Return values
        return (network_receive_bytes_per_second, network_transmit_bytes_per_second)

    def _calculate_uptime(self, resource, metrics):
        """Calculate uptime."""
        start_time = None
        uptime_seconds = None
        # Node Exporter
        if NODE_BOOT_TIME in metrics:
            start_time = metrics[NODE_BOOT_TIME]
        # cAdvisor
        if CONTAINER_START_TIME in metrics:
            start_time = metrics[CONTAINER_START_TIME]
        # Calculate uptime
        if start_time is not None:
            uptime_seconds = int(time()) - start_time
        # Return values
        return (uptime_seconds, start_time)

    def _process_data(self, data):
        """Process raw data into sensor values."""
        sensor_metrics = {}

        for resource in data:
            if resource not in sensor_metrics:
                sensor_metrics[resource] = {}

            # CPU usage
            cpu_usage_pct, cpu_core_usage_pct = self._calculate_cpu_usage(
                resource, data[resource]
            )
            sensor_metrics[resource][METRIC_CPU_USAGE_PCT] = cpu_usage_pct
            # CPU temperature
            if NODE_CPU_TEMP in data[resource]:
                sensor_metrics[resource][METRIC_CPU_TEMP] = data[resource][
                    NODE_CPU_TEMP
                ]
            # CPU cores
            if NODE_CPU_IDLE_SECONDS in data[resource]:
                self.cpu_cores = len(data[resource][NODE_CPU_IDLE_SECONDS])

            # Memory usage
            memory_usage_bytes, memory_usage_pct = self._calculate_memory_usage(
                resource, data[resource]
            )
            sensor_metrics[resource][METRIC_MEMORY_USAGE_BYTES] = memory_usage_bytes
            sensor_metrics[resource][METRIC_MEMORY_USAGE_PCT] = memory_usage_pct
            # Memory size
            memory_size = None
            swap_size = None
            if NODE_MEMORY_TOTAL in data[resource]:
                memory_size = data[resource][NODE_MEMORY_TOTAL]
                swap_size = data[resource][NODE_MEMORY_SWAP_TOTAL]
                # memory_size += swap_size
            elif CONTAINER_MEMORY_LIMIT in data[resource]:
                if data[resource][CONTAINER_MEMORY_LIMIT] > 0:
                    memory_size = data[resource][CONTAINER_MEMORY_LIMIT]
                    swap_size = data[resource][CONTAIENR_MEMORY_SWAP]
                elif MACHINE_MEMORY in data[resource]:
                    memory_size = data[resource][MACHINE_MEMORY]
                    swap_size = data[resource][MACHINE_SWAP]
                # memory_size += swap_size
            if memory_size is not None:
                if swap_size is not None:
                    memory_size += swap_size
                self.memory_size = self._convert_data_size(
                    memory_size, UnitOfInformation.GIBIBYTES
                )

            # Disk usage
            disk_usage_bytes, disk_usage_pct = self._calculate_disk_usage(
                resource, data[resource]
            )
            sensor_metrics[resource][METRIC_DISK_USAGE_BYTES] = disk_usage_bytes
            sensor_metrics[resource][METRIC_DISK_USAGE_PCT] = disk_usage_pct
            # Disk size
            disk_size = None
            if NODE_FILESYSTEM_SIZE in data[resource]:
                disk_size = data[resource][NODE_FILESYSTEM_SIZE]
            elif CONTAINER_FS_LIMIT in data[resource]:
                disk_size = data[resource][CONTAINER_FS_LIMIT]
            if disk_size is not None:
                self.disk_size = self._convert_data_size(
                    disk_size, UnitOfInformation.GIBIBYTES
                )

            # Network usage
            (
                network_receive_bytes_per_second,
                network_transmit_bytes_per_second,
            ) = self._calculate_network_io(resource, data[resource])
            sensor_metrics[resource][METRIC_NETWORK_RECEIVE_BYTES] = (
                network_receive_bytes_per_second
            )
            sensor_metrics[resource][METRIC_NETWORK_TRANSMIT_BYTES] = (
                network_transmit_bytes_per_second
            )

            # Uptime
            uptime_seconds, start_time_seconds = self._calculate_uptime(
                resource, data[resource]
            )
            sensor_metrics[resource][METRIC_UPTIME_SECONDS] = uptime_seconds
            if start_time_seconds is not None:
                last_start_time = datetime.fromtimestamp(
                    float(start_time_seconds), dt_util.UTC
                )
                self.last_start_time = last_start_time

            _LOGGER.debug(
                "Processed data for resource '%s': %s",
                resource,
                sensor_metrics[resource],
            )

        if len(sensor_metrics) == 0:
            raise ValueError("No metrics found")

        # Process data according to sensor type
        sensor_data = {}
        for sensor in SENSORS:
            for metrics in sensor_metrics.values():
                if sensor not in metrics:
                    continue
                sensor_data[sensor] = metrics[sensor]

        return sensor_data

    def _convert_data_size(self, data_size_bytes: int, target_unit: str) -> str:
        """Convert a data size in bytes to a specified target unit (GB, MB, KB, GiB, MiB, KiB, etc.).

        Args:
            data_size_bytes (int): The data size in bytes.
            target_unit (str): The target unit to convert to (e.g., 'GB', 'MB', 'KB', 'GiB', 'MiB', 'KiB').

        Returns:
            str: The converted data size as a string with the target unit.

        """
        # Convert data size to the target unit
        data_size_target_unit = DataSizeConverter.convert(
            data_size_bytes, UnitOfInformation.BYTES, target_unit
        )

        # Round the value based on the target unit
        if target_unit in (UnitOfInformation.GIGABYTES, UnitOfInformation.GIBIBYTES):
            # Round to the nearest quarter for GB and GiB
            data_size_rounded = round(data_size_target_unit * 8) / 8

            # Handle cases where the data size is not an exact multiple of 1 GB or 1 GiB
            if target_unit == UnitOfInformation.GIGABYTES:
                threshold = 0.05
            else:
                threshold = 0.05 / DataSizeConverter.get_unit_ratio(
                    UnitOfInformation.BYTES, UnitOfInformation.GIBIBYTES
                )

            if abs(data_size_target_unit - data_size_rounded) >= threshold:
                data_size_rounded = round(data_size_target_unit * 8) / 8
        else:
            # Round to the nearest integer for other units
            data_size_rounded = round(data_size_target_unit)

        # Format the result as a string with the target unit
        return f"{data_size_rounded:.2f} {target_unit}"


class DataSizeConverter(BaseUnitConverter):
    """Utility to convert data size values."""

    UNIT_CLASS = "data_size"
    NORMALIZED_UNIT = UnitOfInformation.BYTES
    # Units in terms of bytes
    _UNIT_CONVERSION: dict[str | None, float] = {
        UnitOfInformation.BYTES: 1,
        UnitOfInformation.KILOBYTES: 1 / 1e3,
        UnitOfInformation.MEGABYTES: 1 / 1e6,
        UnitOfInformation.GIGABYTES: 1 / 1e9,
        UnitOfInformation.TERABYTES: 1 / 1e12,
        UnitOfInformation.PETABYTES: 1 / 1e15,
        UnitOfInformation.EXABYTES: 1 / 1e18,
        UnitOfInformation.ZETTABYTES: 1 / 1e21,
        UnitOfInformation.YOTTABYTES: 1 / 1e24,
        UnitOfInformation.KIBIBYTES: 1 / 2**10,
        UnitOfInformation.MEBIBYTES: 1 / 2**20,
        UnitOfInformation.GIBIBYTES: 1 / 2**30,
        UnitOfInformation.TEBIBYTES: 1 / 2**40,
        UnitOfInformation.PEBIBYTES: 1 / 2**50,
        UnitOfInformation.EXBIBYTES: 1 / 2**60,
        UnitOfInformation.ZEBIBYTES: 1 / 2**70,
        UnitOfInformation.YOBIBYTES: 1 / 2**80,
    }
