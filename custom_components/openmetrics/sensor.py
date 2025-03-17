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
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from custom_components.openmetrics.metrics.data import ResourceInfoData

from .const import (
    DOMAIN,
    METRIC_CONTAINER_STATUS,
    METRIC_CONTAINER_UPTIME,
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
    PROPERTY_DEVICE_VERSION,
    PROPERTY_DISK_SIZE,
    PROPERTY_LAST_START_TIME,
    PROPERTY_MEMORY_SIZE,
    RESOURCE_TYPE_CONTAINER,
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
}
VIRTUAL_SENSORS = {
    METRIC_CONTAINER_STATUS: SensorEntityDescription(
        key=METRIC_CONTAINER_STATUS,
        icon="mdi:docker",
        translation_key=METRIC_CONTAINER_STATUS,
    ),
    METRIC_CONTAINER_UPTIME: SensorEntityDescription(
        key=METRIC_CONTAINER_UPTIME,
        icon="mdi:clock-outline",
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        suggested_unit_of_measurement=UnitOfTime.DAYS,
        suggested_display_precision=0,
        translation_key=METRIC_CONTAINER_UPTIME,
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
    # Get coordinator
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    host = hass.data[DOMAIN][entry.entry_id]["host"]
    metric_keys = entry.data["metrics"]
    # Create sensors
    for resource in coordinator.resources.values():
        # Create sensors for each resource
        sensors = create_resource_sensors(resource, host, coordinator, metric_keys)
        # Add sensors to hass
        async_add_entities(sensors)


def create_resource_sensors(
    resource: ResourceInfoData,
    host: str,
    coordinator,
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
            sensor = OpenMetricsSensor(coordinator, description, device_info)
            sensors.append(sensor)
    return sensors


def create_device_info(
    unique_id: str,
    resource: ResourceInfoData,
    via_device: tuple[str, str] | None = None,
) -> DeviceInfo:
    """Create a device info object for a resource."""
    # Create device info object
    device_info = DeviceInfo(
        name=resource.name,
        identifiers={(DOMAIN, unique_id)},
    )
    # Set model if provided
    if resource.model:
        device_info["model"] = resource.model
        device_info["sw_version"] = resource.software
    else:
        device_info["model"] = resource.software
        device_info["sw_version"] = resource.version
    # Set serial number if provided
    if resource.serial_number:
        device_info["serial_number"] = resource.serial_number
    # Set entry type if container
    if resource.type == RESOURCE_TYPE_CONTAINER:
        device_info["entry_type"] = DeviceEntryType.SERVICE
    # Set via_device if provided
    if via_device:
        device_info["via_device"] = via_device
    # Return the device info object
    return device_info


class OpenMetricsSensor(CoordinatorEntity, SensorEntity):
    """Representation of an OpenMetrics sensor."""

    _attr_has_entity_name = True
    entity_description: SensorEntityDescription
    device_info: DeviceInfo

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        description: SensorEntityDescription,
        device_info: DeviceInfo,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self.device_info = device_info
        identifier = next(iter(device_info.get("identifiers", {})))
        self._attr_unique_id = f"{identifier[1]}_{description.key}"

    @property
    def translation_key(self) -> str | None:
        """Return the translation key to translate the entity's name and states."""
        return self.entity_description.translation_key

    @property
    def unique_id(self) -> str | None:
        """Return the unique ID."""
        return self._attr_unique_id

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
        return self.coordinator.data.get(resource, {}).get(self.entity_description.key)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return the state attributes."""
        # Set the last start time attribute
        if isinstance(self.coordinator, get_coordinator_class()):
            if self.entity_description.key == METRIC_DEVICE_NAME:
                properties = {}
                if self.device_info.get("model"):
                    properties[PROPERTY_DEVICE_MODEL] = self.device_info.get("model")
                if self.device_info.get("serial_number"):
                    properties[PROPERTY_DEVICE_SERIAL] = self.device_info.get(
                        "serial_number"
                    )
                if self.device_info.get("sw_version"):
                    properties[PROPERTY_DEVICE_SOFTWARE] = self.device_info.get(
                        "sw_version"
                    )
                if self.device_info.get("version"):
                    properties[PROPERTY_DEVICE_VERSION] = self.device_info.get(
                        "version"
                    )
                return properties
            if (
                self.entity_description.key
                in (METRIC_UPTIME_SECONDS, METRIC_CONTAINER_UPTIME)
                and self.coordinator.last_start_time is not None
            ):
                return {PROPERTY_LAST_START_TIME: self.coordinator.last_start_time}
            if (
                self.entity_description.key == METRIC_CPU_USAGE_PCT
                and self.coordinator.cpu_cores is not None
            ):
                return {PROPERTY_CPU_CORES: self.coordinator.cpu_cores}
            if (
                self.entity_description.key
                in (METRIC_MEMORY_USAGE_BYTES, METRIC_MEMORY_USAGE_PCT)
            ) and self.coordinator.memory_size is not None:
                return {PROPERTY_MEMORY_SIZE: self.coordinator.memory_size}
            if (
                self.entity_description.key
                in (METRIC_DISK_USAGE_BYTES, METRIC_DISK_USAGE_PCT)
            ) and self.coordinator.disk_size is not None:
                return {PROPERTY_DISK_SIZE: self.coordinator.disk_size}
            return None
