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
    METRIC_CPU_TEMP,
    METRIC_CPU_USAGE_PCT,
    METRIC_DISK_USAGE_BYTES,
    METRIC_DISK_USAGE_PCT,
    METRIC_MEMORY_USAGE_BYTES,
    METRIC_MEMORY_USAGE_PCT,
    METRIC_NETWORK_RECEIVE_BYTES,
    METRIC_NETWORK_TRANSMIT_BYTES,
    METRIC_UPTIME_SECONDS,
    PROPERTY_CPU_CORES,
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
    resources: list[ResourceInfoData] = hass.data[DOMAIN][entry.entry_id]["resources"]
    coordinators = hass.data[DOMAIN][entry.entry_id]["coordinators"]
    for resource in resources:
        coordinator = coordinators[resource.name]
        sensors = create_resource_sensors(hass, entry, resource, coordinator)
        # Add sensors to hass
        async_add_entities(sensors)


def create_resource_sensors(
    hass: HomeAssistant, entry: ConfigEntry, resource, coordinator
) -> list[Any]:
    """Create sensor entities for the given resource."""
    sensors = []
    host = hass.data[DOMAIN][entry.entry_id]["host"]
    for key, description in SENSORS.items():
        # Check if metric is selected/enabled
        if key in entry.data["metrics"]:
            sensor = create_sensor(resource, coordinator, description, host)
            sensors.append(sensor)
    return sensors


def create_sensor(resource: ResourceInfoData, coordinator, description, host):
    """Create a sensor for an OpenMetrics resource."""
    unique_id = f"{host}_{resource.name}"
    entry_type = None
    if resource.type == RESOURCE_TYPE_CONTAINER:
        entry_type = DeviceEntryType.SERVICE
    # Device info object
    device_info = DeviceInfo(
        name=resource.name,
        model=resource.software,
        # manufacturer=resource.get("vendor"),
        sw_version=resource.version,
        identifiers={(DOMAIN, unique_id)},
        entry_type=entry_type,
    )
    return OpenMetricsSensor(coordinator, description, device_info)


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
        if self.coordinator.data is None:
            return None
        value = self.coordinator.data.get(self.entity_description.key)
        if value is None:
            return None
        return value

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return the state attributes."""
        # Set the last start time attribute
        if isinstance(self.coordinator, get_coordinator_class()):
            if (
                self.entity_description.key == METRIC_UPTIME_SECONDS
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
