"""Definition for OpenMetrics update entity."""

from typing import Any

from homeassistant.components.update import (
    UpdateDeviceClass,
    UpdateEntity,
    UpdateEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    EntityCategory,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
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
from .providers.node_exporter import (
    METRIC_NODE_OS_UPDATE_INFO,
    PROPERTY_CURRENTLY_INSTALLED_OS_VERSION,
    PROPERTY_LATEST_AVAILABLE_OS_VERSION,
)

UPDATE_ENTITIES: dict[str, UpdateEntityDescription] = {
    METRIC_NODE_OS_UPDATE_INFO: UpdateEntityDescription(
        key=METRIC_NODE_OS_UPDATE_INFO,
        icon="mdi:update",
        translation_key=METRIC_NODE_OS_UPDATE_INFO,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up OpenMetrics sensors based on a config entry."""
    # Get coordinator
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    host = hass.data[DOMAIN][entry.entry_id]["host"]
    metric_keys = entry.data["metrics"]
    # Create sensors
    for resource in coordinator.resources.values():
        # Create entities for each resource
        entities = create_resource_entities(resource, host, coordinator, metric_keys)
        # Add entities to hass
        async_add_entities(entities)


def create_resource_entities(
    resource: ResourceInfoData,
    host: str,
    coordinator,
    metric_keys: list[str],
) -> list[Any]:
    """Create entities for the given resource."""
    entities = []
    unique_id = f"{host}_{resource.name}"
    if resource.is_virtual:
        via_device = (DOMAIN, f"{host}_{resource.via_resource}")
        device_info = create_device_info(unique_id, resource, via_device)
    else:
        device_info = create_device_info(unique_id, resource)
    # Create update entities
    for key, description in UPDATE_ENTITIES.items():
        if key in metric_keys:
            entity = OpenMetricsUpdateEntity(
                coordinator, description, device_info, resource
            )
            entities.append(entity)
    # Return created entities
    return entities


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
        if resource.software and resource.version:
            device_info["sw_version"] = f"{resource.software} {resource.version}"
        else:
            device_info["sw_version"] = resource.software
    # Return the device info object
    return device_info


class OpenMetricsUpdateEntity(CoordinatorEntity, UpdateEntity):
    """Representation of an OpenMetrics update entity."""

    _attr_has_entity_name = True
    _attr_device_class = UpdateDeviceClass.FIRMWARE
    entity_description: UpdateEntityDescription
    device_info: DeviceInfo

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        description: UpdateEntityDescription,
        device_info: DeviceInfo,
        resource: ResourceInfoData,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self.device_info = device_info
        identifier = next(iter(device_info.get("identifiers", {})))
        self._attr_unique_id = f"{identifier[1]}_{description.key}"
        self.entity_id = f"sensor.{self._attr_unique_id.replace('.', '_').replace(':', '_').replace('/', '_')}"
        self._attr_title = resource.software
        self.resource = resource

    @property
    def translation_key(self) -> str | None:
        """Return the translation key to translate the entity's name and states."""
        return self.entity_description.translation_key

    @property
    def unique_id(self) -> str | None:
        """Return the unique ID."""
        return self._attr_unique_id

    @property
    def installed_version(self) -> str | None:
        """Return the installed version."""
        if not self.coordinator.data:
            return None
        resource = self.resource.name
        if not resource:
            return None
        self._attr_installed_version = self.coordinator.data.get(resource, {}).get(
            PROPERTY_CURRENTLY_INSTALLED_OS_VERSION
        )
        return self._attr_installed_version

    @property
    def latest_version(self) -> str | None:
        """Return the latest version."""
        if not self.coordinator.data:
            return None
        resource = self.resource.name
        if not resource:
            return None
        self._attr_latest_version = self.coordinator.data.get(resource, {}).get(
            PROPERTY_LATEST_AVAILABLE_OS_VERSION
        )
        return self._attr_latest_version
