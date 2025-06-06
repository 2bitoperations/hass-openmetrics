"""Entity management for OpenMetrics integration."""

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.device_registry import DeviceEntry
from homeassistant.helpers.entity_platform import EntityPlatform

from .const import CONF_METRICS, CONF_RESOURCES, DOMAIN
from .coordinator import OpenMetricsDataUpdateCoordinator
from .metrics.data import MetadataData
from .sensor import create_resource_sensors
from .update import create_resource_update_entities

_LOGGER = logging.getLogger(__name__)


class OpenMetricsEntityManager:
    """Manages entity lifecycle for OpenMetrics integration."""

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry):
        """Initialize the entity manager."""
        self.hass = hass
        self.config_entry = config_entry
        self._platforms: dict[str, EntityPlatform] = {}
        self._coordinator: OpenMetricsDataUpdateCoordinator | None = None
        self._host: str | None = None

    @property
    def coordinator(self) -> OpenMetricsDataUpdateCoordinator:
        """Get the coordinator instance."""
        if self._coordinator is None:
            self._coordinator = self.hass.data[DOMAIN][self.config_entry.entry_id][
                "coordinator"
            ]
        if self._coordinator is None:
            raise HomeAssistantError("Coordinator is not set for this config entry")
        return self._coordinator

    @property
    def host(self) -> str:
        """Get the host identifier."""
        if self._host is None:
            self._host = self.hass.data[DOMAIN][self.config_entry.entry_id]["host"]
        if self._host is None:
            raise HomeAssistantError("Host is not set for this config entry")
        return self._host

    def get_platform(self, platform_type: str) -> EntityPlatform:
        """Get platform instance for the given type."""
        if platform_type not in self._platforms:
            platforms = self.hass.data["entity_platform"][DOMAIN]
            for platform in platforms:
                if (
                    platform.config_entry.entry_id == self.config_entry.entry_id
                    and platform.domain == platform_type
                ):
                    self._platforms[platform_type] = platform
                    break
            else:
                raise HomeAssistantError(
                    f"No {platform_type} platform found for config entry {self.config_entry.entry_id}"
                )
        return self._platforms[platform_type]

    def get_integration_device_entries(self) -> list[DeviceEntry]:
        """Get all device entries for this integration."""
        device_registry = self.hass.data[dr.DATA_REGISTRY]
        device_entries = [
            device_entry
            for device_entry in device_registry.devices.data.values()
            if self.config_entry.entry_id in device_entry.config_entries
        ]
        if not device_entries:
            _LOGGER.warning(
                "No devices found for config entry %s",
                self.config_entry.entry_id,
            )
        return device_entries

    async def update_resources(
        self, new_resources: list[str], metadata: MetadataData
    ) -> None:
        """Update resources by adding new ones and removing unselected ones."""
        current_resources = self.config_entry.data[CONF_RESOURCES]
        current_metrics = self.config_entry.data[CONF_METRICS]
        # Remove unselected resources
        resources_to_remove = [r for r in current_resources if r not in new_resources]
        await self._remove_resources(resources_to_remove)
        # Add new resources
        resources_to_add = [r for r in new_resources if r not in current_resources]
        await self._add_resources(resources_to_add, metadata, current_metrics)

    async def update_metrics(self, new_metrics: list[str]) -> None:
        """Update metrics by adding new ones and removing unselected ones."""
        current_metrics = self.config_entry.data[CONF_METRICS]
        device_entries = self.get_integration_device_entries()
        # Determine metrics to add and remove
        metrics_to_remove = [m for m in current_metrics if m not in new_metrics]
        metrics_to_add = [m for m in new_metrics if m not in current_metrics]
        # Loop through all device entries to update metrics
        for device in device_entries:
            # Remove unselected metrics
            await self._remove_metrics_from_device(device, metrics_to_remove)
            # Add new metrics
            await self._add_metrics_to_device(device, metrics_to_add)

    async def remove_orphaned_resources(self, metadata: MetadataData) -> None:
        """Remove orphaned resources."""
        # Loop through all device entries
        removed_resources = []
        for device in self.get_integration_device_entries():
            if device.name and device.name not in metadata.resources:
                if await self._remove_single_resource(device, device.name):
                    removed_resources.append(device.name)
        # Log removed resources
        if removed_resources == 0:
            _LOGGER.debug("No obsolote resources removed from Home Assistant")

    # Private helper methods
    async def _add_resources(
        self, resource_names: list[str], metadata: MetadataData, metrics: list[str]
    ) -> None:
        """Add multiple resources."""
        added_resources = [
            resource_name
            for resource_name in resource_names
            if await self._add_single_resource(resource_name, metadata, metrics)
        ]
        if len(added_resources) == 0:
            _LOGGER.debug("No resources added to Home Assistant")

    async def _remove_resources(self, resource_names: list[str]) -> None:
        """Remove multiple resources."""
        removed_resources = []
        device_entries = self.get_integration_device_entries()
        # Loop through all device entries
        for device in device_entries:
            removed = [
                resource_name
                for resource_name in resource_names
                if await self._remove_single_resource(device, resource_name)
            ]
            removed_resources.extend(removed)
        if len(removed_resources) == 0:
            _LOGGER.debug("No resources removed from Home Assistant")

    async def _add_single_resource(
        self, resource_name: str, metadata: MetadataData, metrics: list[str]
    ) -> bool:
        """Add a single resource to Home Assistant."""
        device_registry = self.hass.data[dr.DATA_REGISTRY]
        # Find the resource in metadata
        resource = None
        for res in metadata.resources.values():
            if res.name == resource_name:
                resource = res
                break
        if not resource:
            _LOGGER.error("Resource %s not found in metadata", resource_name)
            return False
        # Add resource to coordinator if not present
        if resource_name not in self.coordinator.resources:
            self.coordinator.resources[resource_name] = resource
        # Create entities
        sensors = create_resource_sensors(
            resource, self.host, self.coordinator, metrics
        )
        updates = create_resource_update_entities(
            resource, self.host, self.coordinator, metrics
        )
        if not sensors and not updates:
            _LOGGER.warning("No entities created for resource %s", resource_name)
            return False
        # Register device
        device_info = sensors[0].device_info if sensors else updates[0].device_info
        device_entry = device_registry.async_get_or_create(
            config_entry_id=self.config_entry.entry_id,
            name=device_info.get("name"),
            model=device_info.get("model"),
            identifiers=device_info.get("identifiers"),
            entry_type=device_info.get("entry_type"),
            manufacturer=device_info.get("manufacturer"),
            sw_version=device_info.get("sw_version"),
        )
        # Link entities to device
        for sensor in sensors:
            sensor.device_entry = device_entry
        for update in updates:
            update.device_entry = device_entry
        # Add entities to platforms
        if sensors:
            sensor_platform = self.get_platform(Platform.SENSOR)
            await sensor_platform.async_add_entities(sensors)
        if updates:
            update_platform = self.get_platform(Platform.UPDATE)
            await update_platform.async_add_entities(updates)
        _LOGGER.info("Added device registry entry: %s.%s", DOMAIN, resource_name)
        return True

    async def _remove_single_resource(
        self, device: DeviceEntry, resource_name: str
    ) -> bool:
        """Remove a single resource from Home Assistant."""
        if device.name != resource_name:
            return False
        device_registry = self.hass.data[dr.DATA_REGISTRY]
        # Remove resource from coordinator
        if resource_name in self.coordinator.resources:
            self.coordinator.resources.pop(resource_name)
        # Remove device and all its entities
        device_registry.async_remove_device(device.id)
        _LOGGER.info("Removed device registry entry: %s.%s", DOMAIN, resource_name)
        return True

    async def _add_metrics_to_device(
        self, device_entry: DeviceEntry, metric_keys: list[str]
    ) -> None:
        """Add metrics to a specific device."""
        added_metrics = [
            metric_key
            for metric_key in metric_keys
            if await self._add_single_metric_to_device(device_entry, metric_key)
        ]
        if len(added_metrics) == 0:
            _LOGGER.debug("No metrics added to device '%s'", device_entry.name)

    async def _remove_metrics_from_device(
        self, device: DeviceEntry, metric_keys: list[str]
    ) -> None:
        """Remove metrics from a specific device."""
        removed_metrics = [
            metric_key
            for metric_key in metric_keys
            if await self._remove_single_metric_from_device(device, metric_key)
        ]
        if len(removed_metrics) == 0:
            _LOGGER.debug("No metrics remove from device '%s'", device.name)

    async def _add_single_metric_to_device(
        self, device_entry: DeviceEntry, metric_key: str
    ) -> bool:
        """Add a single metric to a device."""
        sensors = []
        updates = []
        # Create entities for the metric
        for resource in self.coordinator.resources.values():
            if (resource.name == device_entry.name and not resource.is_virtual) or (
                resource.via_resource == device_entry.name and resource.is_virtual
            ):
                sensors.extend(
                    create_resource_sensors(
                        resource, self.host, self.coordinator, [metric_key]
                    )
                )
                updates.extend(
                    create_resource_update_entities(
                        resource, self.host, self.coordinator, [metric_key]
                    )
                )
        if not sensors and not updates:
            return False
        # Add entities to platforms
        if sensors:
            sensor_platform = self.get_platform(Platform.SENSOR)
            await sensor_platform.async_add_entities(sensors)
        if updates:
            update_platform = self.get_platform(Platform.UPDATE)
            await update_platform.async_add_entities(updates)
        return True

    async def _remove_single_metric_from_device(
        self, device: DeviceEntry, metric_key: str
    ) -> bool:
        """Remove a single metric from a device."""
        entity_registry = self.hass.data[er.DATA_REGISTRY]
        removed = False
        # Find and remove entities with the metric key
        relevant_entities = [
            entity_entry
            for entity_entry in entity_registry.entities.data.values()
            if (
                entity_entry.config_entry_id == self.config_entry.entry_id
                and entity_entry.device_id == device.id
                and entity_entry.translation_key == metric_key
            )
        ]
        # Remove entities from the registry
        for entity_entry in relevant_entities:
            entity_registry.async_remove(entity_entry.entity_id)
            removed = True
        # Remove virtual device if no entities left and it's a virtual device
        if removed and device.via_device_id:
            remaining_entities = [
                entity_entry
                for entity_entry in entity_registry.entities.data.values()
                if (
                    entity_entry.config_entry_id == self.config_entry.entry_id
                    and entity_entry.device_id == device.id
                )
            ]
            if len(remaining_entities) == 0:
                device_registry = self.hass.data[dr.DATA_REGISTRY]
                device_registry.async_remove_device(device.id)
        return removed
