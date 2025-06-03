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
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN
from .entity import OpenMetricsBaseEntity, async_setup_entities, create_device_info
from .metrics.data import ResourceInfoData
from .providers.node_exporter import (
    METRIC_NODE_OS_UPDATE_INFO,
    METRIC_VIRTUAL_RESOURCE_IMAGE_UPDATE_INFO,
    PROPERTY_CURRENTLY_INSTALLED_OS_VERSION,
    PROPERTY_CURRENTLY_USED_IMAGE_VERSION,
    PROPERTY_LATEST_AVAILABLE_IMAGE_VERSION,
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

VIRTUAL_UPDATE_ENTITIES: dict[str, UpdateEntityDescription] = {
    METRIC_VIRTUAL_RESOURCE_IMAGE_UPDATE_INFO: UpdateEntityDescription(
        key=METRIC_VIRTUAL_RESOURCE_IMAGE_UPDATE_INFO,
        icon="mdi:update",
        translation_key=METRIC_VIRTUAL_RESOURCE_IMAGE_UPDATE_INFO,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up OpenMetrics update entities based on a config entry."""
    await async_setup_entities(
        hass, entry, async_add_entities, create_resource_update_entities
    )


def create_resource_update_entities(
    resource: ResourceInfoData,
    host: str,
    coordinator: DataUpdateCoordinator,
    metric_keys: list[str],
) -> list[Any]:
    """Create update entities for the given resource."""
    entities = []
    unique_id = f"{host}_{resource.name}"
    if resource.is_virtual:
        via_device = (DOMAIN, f"{host}_{resource.via_resource}")
        device_info = create_device_info(unique_id, resource, via_device)
        update_entity_descriptions = VIRTUAL_UPDATE_ENTITIES
    else:
        device_info = create_device_info(unique_id, resource)
        update_entity_descriptions = UPDATE_ENTITIES

    # Create update entities
    for key, description in update_entity_descriptions.items():
        if key in metric_keys:
            entity = OpenMetricsUpdateEntity(
                coordinator, description, device_info, resource
            )
            entities.append(entity)

    return entities


class OpenMetricsUpdateEntity(OpenMetricsBaseEntity, UpdateEntity):
    """Representation of an OpenMetrics update entity."""

    _attr_device_class = UpdateDeviceClass.FIRMWARE
    entity_description: UpdateEntityDescription

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        description: UpdateEntityDescription,
        device_info: DeviceInfo,
        resource: ResourceInfoData,
    ) -> None:
        """Initialize the update entity."""
        self.entity_description = description
        self.resource = resource
        super().__init__(coordinator, device_info)

        self._attr_title = resource.software

        if self._attr_unique_id:
            # Replace invalid characters in the unique ID with underscores
            self.entity_id = f"update.{self._attr_unique_id.replace('.', '_').replace(':', '_').replace('/', '_')}"

    @property
    def installed_version(self) -> str | None:
        """Return the installed version."""
        if not self.coordinator.data:
            return None
        resource = self.resource.name
        if not resource:
            return None
        if self.resource.is_virtual:
            property_name = PROPERTY_CURRENTLY_USED_IMAGE_VERSION
        else:
            property_name = PROPERTY_CURRENTLY_INSTALLED_OS_VERSION
        self._attr_installed_version = self.coordinator.data.get(resource, {}).get(
            property_name
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
        if self.resource.is_virtual:
            property_name = PROPERTY_LATEST_AVAILABLE_IMAGE_VERSION
        else:
            property_name = PROPERTY_LATEST_AVAILABLE_OS_VERSION
        self._attr_latest_version = self.coordinator.data.get(resource, {}).get(
            property_name
        )
        return self._attr_latest_version
