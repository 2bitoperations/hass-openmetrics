"""Base entity handling for OpenMetrics integration."""

from collections.abc import Callable
from typing import TypeVar

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .const import (
    DOMAIN,
    RESOURCE_TYPE_CONTAINER,
    RESOURCE_TYPE_NODE,
)
from .metrics.data import ResourceInfoData

T = TypeVar("T", bound=Entity)


def create_device_info(
    unique_id: str,
    resource: ResourceInfoData,
    via_device: tuple[str, str] | None = None,
) -> DeviceInfo:
    """Create a device info object for a resource."""
    # Create device info object with the minimal required fields (-> Generic provider)
    device_info = DeviceInfo(
        name=resource.name,
        identifiers={(DOMAIN, unique_id)},
    )
    # Set model if provided
    if resource.model:
        device_info["model"] = resource.model
    # Set serial number if provided
    if resource.serial_number:
        device_info["serial_number"] = resource.serial_number
    # Set via_device if provided
    if via_device:
        device_info["via_device"] = via_device
    # Set resource type related attributes
    if resource.type == RESOURCE_TYPE_CONTAINER:
        # Set software version
        device_info["sw_version"] = resource.version
        # Set entry type
        device_info["entry_type"] = DeviceEntryType.SERVICE
    elif resource.type == RESOURCE_TYPE_NODE:
        # Set software version
        if resource.software and resource.version:
            device_info["sw_version"] = f"{resource.software} {resource.version}"
        else:
            device_info["sw_version"] = resource.software
    # Return the device info object
    return device_info


class OpenMetricsBaseEntity(CoordinatorEntity):
    """Base class for all OpenMetrics entities."""

    _attr_has_entity_name = True
    device_info: DeviceInfo

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        device_info: DeviceInfo,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self.device_info = device_info
        identifier = next(iter(device_info.get("identifiers", {})))
        self._attr_unique_id = f"{identifier[1]}_{self.entity_description.key}"

    @property
    def translation_key(self) -> str | None:
        """Return the translation key to translate the entity's name and states."""
        return self.entity_description.translation_key

    @property
    def unique_id(self) -> str | None:
        """Return the unique ID."""
        return self._attr_unique_id


async def async_setup_entities[T: Entity](
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
    entity_factory: Callable[
        [ResourceInfoData, str, DataUpdateCoordinator, list[str]], list[T]
    ],
) -> None:
    """Set up OpenMetrics entities based on a config entry."""
    # Get coordinator
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    host = hass.data[DOMAIN][entry.entry_id]["host"]
    metric_keys = entry.data["metrics"]

    # Create entities
    entities = []
    for resource in coordinator.resources.values():
        # Create entities for each resource
        resource_entities = entity_factory(resource, host, coordinator, metric_keys)
        entities.extend(resource_entities)

    # Add entities to hass
    async_add_entities(entities)
