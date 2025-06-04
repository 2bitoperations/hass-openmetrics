"""The openmetrics integration."""

from __future__ import annotations

import logging
import urllib.parse

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_URL,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
    Platform,
)
from homeassistant.core import HomeAssistant

from .client import (
    CannotConnectError,
    ClientError,
    InvalidAuthError,
    OpenMetricsClient,
    RequestError,
)
from .const import CONF_RESOURCES, DOMAIN
from .coordinator import OpenMetricsDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.UPDATE,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up openmetrics from a config entry."""
    try:
        hass.data.setdefault(DOMAIN, {})
        # Extract entry data
        url = entry.data[CONF_URL]
        username = entry.data.get(CONF_USERNAME)
        password = entry.data.get(CONF_PASSWORD)
        verify_ssl = entry.data[CONF_VERIFY_SSL]
        # Create an instance of the OpenMetricsClient
        client = OpenMetricsClient(url, verify_ssl, username, password)
        # Validate the OpenMetrics connection (and authentication)
        metadata = await client.get_metadata()
        # Create domain data if it does not exist
        if DOMAIN not in hass.data:
            hass.data[DOMAIN] = {}
        # Create the coordinator and add configured resources
        coordinator = OpenMetricsDataUpdateCoordinator(
            hass,
            client=client,
            resources={
                resource_key: resource
                for resource_key, resource in metadata.resources.items()
                if resource_key in entry.data[CONF_RESOURCES] or resource.is_virtual
            },
            update_interval=int(entry.data[CONF_SCAN_INTERVAL]),
        )
        # Get the host name from the URL
        host = urllib.parse.urlparse(url).netloc
        # Store required entry data in hass domain entry object
        hass.data[DOMAIN][entry.entry_id] = {
            "client": client,
            "coordinator": coordinator,
            "host": host,
        }
        # Forward setup to used platforms
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    except CannotConnectError as e:
        _LOGGER.error("Failed to connect: %s", str(e))
        return False
    except InvalidAuthError as e:
        _LOGGER.error("Authentication failed: %s", str(e))
        return False
    except RequestError as e:
        _LOGGER.error("Resources error: %s", str(e))
        return False
    except ClientError as e:
        _LOGGER.error("Processing error: %s", str(e))
        return False
    except ValueError as e:
        _LOGGER.error("Value error: %s", str(e))
        return False
    except Exception:
        _LOGGER.exception("Unexpected exception")
        return False
    else:
        # Initial sensor data refresh
        await coordinator.async_refresh()
        return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate old entry."""
    _LOGGER.info(
        "Migrating configuration from version %s.%s",
        entry.version,
        entry.minor_version,
    )
    _LOGGER.debug("Starting migration process for entry ID: %s", entry.entry_id)

    # Skip migration if not needed
    if entry.version > 1:
        # This means the user has downgraded from a future version
        _LOGGER.debug("Migration skipped - entry version > 1")
        return False

    # Extract the connection data from the config entry
    url = entry.data[CONF_URL]
    username = entry.data.get(CONF_USERNAME)
    password = entry.data.get(CONF_PASSWORD)
    verify_ssl = entry.data[CONF_VERIFY_SSL]

    # Get metaadata of the configured OpenMetrics provider
    client = OpenMetricsClient(url, verify_ssl, username, password)
    metadata = await client.get_metadata()

    # Create a copy of the entry data
    data = {**entry.data}
    _LOGGER.debug("Created copy of entry data: %s", data)

    # Version 1 migration
    if entry.version == 1:
        _LOGGER.debug("Starting version 1 migration")
        version = 2
        minor_version = 1
        # Extract provider info
        provider_name = metadata.provider_info.name
        provider_version = metadata.provider_info.version
        # Extract metadata
        available_metrics = metadata.available_metrics
        # Upgrade title
        host = urllib.parse.urlparse(url).netloc
        title = host
        if provider_name:
            title += f" ({provider_name}"
            if provider_version:
                title += f" {provider_version}"
            title += ")"
        # Updgrade data
        data["metrics"] = available_metrics

        _LOGGER.debug("Updating entry data with new configuration")
        hass.config_entries.async_update_entry(
            entry,
            title=title,
            data=data,
            version=version,
            minor_version=minor_version,
        )
        _LOGGER.debug("Updated config entry with new data")

    # Version 2 migration
    if entry.version == 2:
        _LOGGER.debug("Starting version 2 migration")
        version = 3
        minor_version = 1
        # Extract provider info
        provider_name = metadata.provider_info.name
        # Upgrade title
        host = urllib.parse.urlparse(url).netloc
        title = host
        if provider_name:
            title += f" ({provider_name})"

        _LOGGER.debug("Updating entry data with new configuration")
        hass.config_entries.async_update_entry(
            entry,
            title=title,
            data=data,
            version=version,
            minor_version=minor_version,
        )
        _LOGGER.debug("Updated config entry with new data")

    _LOGGER.info(
        "Migration to configuration version %s.%s successful",
        entry.version,
        entry.minor_version,
    )

    return True
