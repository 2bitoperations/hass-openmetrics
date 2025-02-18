"""Coordinator for OpenMetrics."""

import logging
from datetime import timedelta

from homeassistant.const import UnitOfInformation
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util.unit_conversion import BaseUnitConverter

from custom_components.openmetrics.metrics.data import ResourceInfoData

from .client import (
    CannotConnectError,
    ClientError,
    InvalidAuthError,
    OpenMetricsClient,
    RequestError,
)
from .const import (
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class OpenMetricsDataUpdateCoordinator(DataUpdateCoordinator):
    """Define an object to manage OpenMetrics data update coordination."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: OpenMetricsClient,
        resources: dict[str, ResourceInfoData],
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
        self.resources = resources
        self._previous_metrics = {}
        self.last_start_time = None
        self.cpu_cores = None
        self.memory_size = None
        self.disk_size = None

    async def _async_update_data(self):
        """Fetch OpenMetrics data."""
        try:
            _LOGGER.debug(
                "Started fetching %s data from %s", self.name, self._client.url
            )
            # Get metrics
            metrics = await self._client.get_metrics(list(self.resources.keys()))
            # Process metrics for sensors
            sensor_data = self._client.process_metrics(metrics, self.update_interval)
            # Update meta info
            self.last_start_time = self._client.processor.last_start_time
            self.cpu_cores = self._client.processor.cpu_cores
            memory_size = self._client.processor.memory_size
            if memory_size is not None:
                self.memory_size = self._convert_data_size(
                    memory_size, UnitOfInformation.GIBIBYTES
                )
            disk_size = self._client.processor.disk_size
            if disk_size is not None:
                self.disk_size = self._convert_data_size(
                    disk_size, UnitOfInformation.GIBIBYTES
                )

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
