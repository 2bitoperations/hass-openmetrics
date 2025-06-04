"""Definition for OpenMetrics sensors."""

from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.components.sensor.const import SensorDeviceClass, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfDataRate,
    UnitOfInformation,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
)

from .const import (
    DOMAIN,
    METRIC_CPU_TEMP,
    METRIC_CPU_USAGE_PCT,
    METRIC_DEVICE_NAME,
    METRIC_DISK_USAGE_BYTES,
    METRIC_DISK_USAGE_PCT,
    METRIC_MEMORY_USAGE_BYTES,
    METRIC_MEMORY_USAGE_PCT,
    METRIC_NETWORK_RECEIVE_BYTES,
    METRIC_NETWORK_TRANSMIT_BYTES,
    METRIC_UPTIME_SECONDS,
    PROPERTY_CPU_CORES,
    PROPERTY_DEVICE_MODEL,
    PROPERTY_DEVICE_SERIAL,
    PROPERTY_DEVICE_SOFTWARE,
    PROPERTY_DISK_SIZE,
    PROPERTY_LAST_START_TIME,
    PROPERTY_MEMORY_SIZE,
    PROPERTY_NETWORK_SPEED,
)
from .entity import OpenMetricsBaseEntity, async_setup_entities, create_device_info
from .metrics.data import ResourceInfoData
from .providers.node_exporter import (
    METRIC_VIRTUAL_RESOURCE_STATUS,
    METRIC_VIRTUAL_RESOURCE_UPTIME,
    METRIC_VIRTUAL_RESOURCES,
)

SENSORS = {
    METRIC_MEMORY_USAGE_BYTES: SensorEntityDescription(
        key=METRIC_MEMORY_USAGE_BYTES,
        icon="mdi:memory",
        device_class=SensorDeviceClass.DATA_SIZE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        suggested_unit_of_measurement=UnitOfInformation.MEGABYTES,
        suggested_display_precision=2,
        translation_key=METRIC_MEMORY_USAGE_BYTES,
    ),
    METRIC_MEMORY_USAGE_PCT: SensorEntityDescription(
        key=METRIC_MEMORY_USAGE_PCT,
        icon="mdi:memory",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        suggested_display_precision=2,
        translation_key=METRIC_MEMORY_USAGE_PCT,
    ),
    METRIC_CPU_USAGE_PCT: SensorEntityDescription(
        key=METRIC_CPU_USAGE_PCT,
        icon="mdi:cpu-64-bit",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        suggested_display_precision=2,
        translation_key=METRIC_CPU_USAGE_PCT,
    ),
    METRIC_CPU_TEMP: SensorEntityDescription(
        key=METRIC_CPU_TEMP,
        icon="mdi:thermometer",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=2,
        translation_key=METRIC_CPU_TEMP,
    ),
    METRIC_DISK_USAGE_BYTES: SensorEntityDescription(
        key=METRIC_DISK_USAGE_BYTES,
        icon="mdi:harddisk",
        device_class=SensorDeviceClass.DATA_SIZE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        suggested_unit_of_measurement=UnitOfInformation.MEGABYTES,
        suggested_display_precision=2,
        translation_key=METRIC_DISK_USAGE_BYTES,
    ),
    METRIC_DISK_USAGE_PCT: SensorEntityDescription(
        key=METRIC_DISK_USAGE_PCT,
        icon="mdi:harddisk",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        suggested_display_precision=2,
        translation_key=METRIC_DISK_USAGE_PCT,
    ),
    METRIC_NETWORK_RECEIVE_BYTES: SensorEntityDescription(
        key=METRIC_NETWORK_RECEIVE_BYTES,
        icon="mdi:download-network",
        device_class=SensorDeviceClass.DATA_RATE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfDataRate.BYTES_PER_SECOND,
        suggested_unit_of_measurement=UnitOfDataRate.KILOBYTES_PER_SECOND,
        suggested_display_precision=2,
        translation_key=METRIC_NETWORK_RECEIVE_BYTES,
    ),
    METRIC_NETWORK_TRANSMIT_BYTES: SensorEntityDescription(
        key=METRIC_NETWORK_TRANSMIT_BYTES,
        icon="mdi:upload-network",
        device_class=SensorDeviceClass.DATA_RATE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfDataRate.BYTES_PER_SECOND,
        suggested_unit_of_measurement=UnitOfDataRate.KILOBYTES_PER_SECOND,
        suggested_display_precision=2,
        translation_key=METRIC_NETWORK_TRANSMIT_BYTES,
    ),
    METRIC_UPTIME_SECONDS: SensorEntityDescription(
        key=METRIC_UPTIME_SECONDS,
        icon="mdi:clock-outline",
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        suggested_unit_of_measurement=UnitOfTime.DAYS,
        suggested_display_precision=0,
        translation_key=METRIC_UPTIME_SECONDS,
    ),
    METRIC_DEVICE_NAME: SensorEntityDescription(
        key=METRIC_DEVICE_NAME,
        icon="mdi:information",
        translation_key=METRIC_DEVICE_NAME,
        entity_registry_visible_default=False,
    ),
    METRIC_VIRTUAL_RESOURCES: SensorEntityDescription(
        key=METRIC_VIRTUAL_RESOURCES,
        icon="mdi:docker",
        translation_key=METRIC_VIRTUAL_RESOURCES,
    ),
}
VIRTUAL_SENSORS = {
    METRIC_VIRTUAL_RESOURCE_STATUS: SensorEntityDescription(
        key=METRIC_VIRTUAL_RESOURCE_STATUS,
        icon="mdi:docker",
        translation_key=METRIC_VIRTUAL_RESOURCE_STATUS,
    ),
    METRIC_VIRTUAL_RESOURCE_UPTIME: SensorEntityDescription(
        key=METRIC_VIRTUAL_RESOURCE_UPTIME,
        icon="mdi:clock-outline",
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        suggested_unit_of_measurement=UnitOfTime.DAYS,
        suggested_display_precision=0,
        translation_key=METRIC_VIRTUAL_RESOURCE_UPTIME,
    ),
}


def get_coordinator_class():
    """Return the coordinator class."""
    from custom_components.openmetrics.coordinator import (
        OpenMetricsDataUpdateCoordinator,
    )

    return OpenMetricsDataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up OpenMetrics sensors based on a config entry."""
    await async_setup_entities(hass, entry, async_add_entities, create_resource_sensors)


def create_resource_sensors(
    resource: ResourceInfoData,
    host: str,
    coordinator: DataUpdateCoordinator,
    metric_keys: list[str],
) -> list[Any]:
    """Create sensor entities for the given resource."""
    sensors = []
    unique_id = f"{host}_{resource.name}"
    if resource.is_virtual:
        via_device = (DOMAIN, f"{host}_{resource.via_resource}")
        device_info = create_device_info(unique_id, resource, via_device)
        sensor_descriptions = VIRTUAL_SENSORS
    else:
        device_info = create_device_info(unique_id, resource)
        sensor_descriptions = SENSORS
    # Create sensors
    for key, description in sensor_descriptions.items():
        # Check if metric is selected/enabled
        if key in metric_keys:
            # Create network interface sensors
            if (
                key in (METRIC_NETWORK_RECEIVE_BYTES, METRIC_NETWORK_TRANSMIT_BYTES)
                and resource.network_interfaces
            ):
                for interface in resource.network_interfaces:
                    # Recreate description with interface as translation placeholder
                    desc = add_translation_placeholders_to_description(
                        description, {"interface": interface}
                    )
                    # Create sensor with modified description and identity
                    sensor = OpenMetricsSensor(
                        coordinator, desc, device_info, interface
                    )
                    sensors.append(sensor)
            # Create other sensors
            else:
                sensor = OpenMetricsSensor(coordinator, description, device_info)
                sensors.append(sensor)
    return sensors


def add_translation_placeholders_to_description(
    description: SensorEntityDescription, placeholder: dict[str, str]
) -> SensorEntityDescription:
    """Add translation placeholders to the sensor description."""
    translation_placeholders = {}
    if description.translation_placeholders:
        translation_placeholders.update(description.translation_placeholders)
    translation_placeholders.update(placeholder)
    return SensorEntityDescription(
        key=description.key,
        icon=description.icon,
        device_class=description.device_class,
        state_class=description.state_class,
        native_unit_of_measurement=description.native_unit_of_measurement,
        suggested_unit_of_measurement=description.suggested_unit_of_measurement,
        suggested_display_precision=description.suggested_display_precision,
        translation_key=description.translation_key,
        translation_placeholders=translation_placeholders,
    )


class OpenMetricsSensor(OpenMetricsBaseEntity, SensorEntity):
    """Representation of an OpenMetrics sensor."""

    _attr_has_entity_name = True
    entity_description: SensorEntityDescription
    device_info: DeviceInfo

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        description: SensorEntityDescription,
        device_info: DeviceInfo,
        identity: str | None = None,
    ) -> None:
        """Initialize the sensor."""
        self.entity_description = description
        self.identity = identity
        super().__init__(coordinator, device_info)

        if self._attr_unique_id and identity:
            # Add identity to the unique ID if provided
            self._attr_unique_id += f"_{identity}"

        if self._attr_unique_id:
            # Replace invalid characters in the unique ID with underscores
            self.entity_id = f"sensor.{self._attr_unique_id.replace('.', '_').replace(':', '_').replace('/', '_')}"

    @property
    def native_value(self) -> StateType:
        """Return the state of the sensor."""
        if not self.coordinator.data:
            return None
        resource = self.device_info.get("name")
        if not resource:
            return None
        if METRIC_DEVICE_NAME in self.entity_description.key:
            return resource
        if self.identity:
            return self.coordinator.data.get(resource, {}).get(
                self.entity_description.key + "_" + self.identity
            )
        return self.coordinator.data.get(resource, {}).get(self.entity_description.key)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return the state attributes."""
        # Set resource related attributes
        if isinstance(self.coordinator, get_coordinator_class()):
            # Set device info attributes
            if self.entity_description.key == METRIC_DEVICE_NAME:
                properties = {}
                # Model
                properties[PROPERTY_DEVICE_MODEL] = (
                    self.device_info.get("model") or "n/a"
                )
                # Software
                if self.device_info.get("entry_type") == DeviceEntryType.SERVICE:
                    software = self.device_info.get("name")
                    if software and self.device_info.get("sw_version"):
                        software += f" {self.device_info.get('sw_version')}"
                else:
                    software = self.device_info.get("sw_version")
                properties[PROPERTY_DEVICE_SOFTWARE] = software or "n/a"
                # Serial number
                properties[PROPERTY_DEVICE_SERIAL] = (
                    self.device_info.get("serial_number") or "n/a"
                )
                # Return the properties
                return properties

            # Get the resource data
            resource = self.device_info.get("name")
            if resource and self.coordinator.data:
                resource_data = self.coordinator.data.get(resource, {})
                if not resource_data:
                    return None
            else:
                return None

            # Set the last start time attribute
            if self.entity_description.key in (
                METRIC_UPTIME_SECONDS,
                METRIC_VIRTUAL_RESOURCE_UPTIME,
            ):
                return {
                    PROPERTY_LAST_START_TIME: resource_data.get(
                        PROPERTY_LAST_START_TIME
                    )
                }
            # Set the CPU cores attribute
            if self.entity_description.key == METRIC_CPU_USAGE_PCT:
                return {PROPERTY_CPU_CORES: resource_data.get(PROPERTY_CPU_CORES)}
            # Set the memory size attribute
            if self.entity_description.key in (
                METRIC_MEMORY_USAGE_BYTES,
                METRIC_MEMORY_USAGE_PCT,
            ):
                return {PROPERTY_MEMORY_SIZE: resource_data.get(PROPERTY_MEMORY_SIZE)}
            # Set the disk size attribute
            if self.entity_description.key in (
                METRIC_DISK_USAGE_BYTES,
                METRIC_DISK_USAGE_PCT,
            ):
                return {PROPERTY_DISK_SIZE: resource_data.get(PROPERTY_DISK_SIZE)}
            # Set the network attribute
            if self.entity_description.key in (
                METRIC_NETWORK_RECEIVE_BYTES,
                METRIC_NETWORK_TRANSMIT_BYTES,
            ):
                network_speed = resource_data.get(PROPERTY_NETWORK_SPEED)
                if network_speed:
                    # Return the network speed for the specific interface
                    if self.identity and self.identity in network_speed:
                        # "network_speed" is the translation key
                        return {"network_speed": network_speed[self.identity]}
            return None
