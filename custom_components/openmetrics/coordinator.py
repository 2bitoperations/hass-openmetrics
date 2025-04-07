"""Coordinator for OpenMetrics."""

import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

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
    PROPERTY_DISK_SIZE,
    PROPERTY_NETWORK_SPEED,
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

            for resource, resource_info in self.resources.items():
                if resource_info.disk_size:
                    sensor_data[resource][PROPERTY_DISK_SIZE] = resource_info.disk_size
                if resource_info.network_speed:
                    sensor_data[resource][PROPERTY_NETWORK_SPEED] = (
                        resource_info.network_speed
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
