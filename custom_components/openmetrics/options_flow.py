"""Options flow for openmetrics integration."""

import logging
from datetime import timedelta
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlowResult, OptionsFlow
from homeassistant.const import (
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_URL,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
)
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
    selector,
)

from .client import CannotConnectError, InvalidAuthError, OpenMetricsClient
from .const import (
    CONF_CUSTOM_METRIC_DEVICE_CLASS,
    CONF_CUSTOM_METRIC_GROUP_BY,
    CONF_CUSTOM_METRIC_ICON,
    CONF_CUSTOM_METRIC_ID,
    CONF_CUSTOM_METRIC_NAME,
    CONF_CUSTOM_METRIC_PRECISION,
    CONF_CUSTOM_METRIC_QUERY,
    CONF_CUSTOM_METRIC_RESOURCE,
    CONF_CUSTOM_METRIC_STATE_CLASS,
    CONF_CUSTOM_METRIC_UNIT,
    CONF_CUSTOM_METRICS,
    CONF_METRICS,
    CONF_RESOURCES,
    DOMAIN,
)
from .coordinator import OpenMetricsDataUpdateCoordinator
from .custom_metrics import generate_custom_metric_id, parse_metric_query
from .entity_manager import OpenMetricsEntityManager
from .metrics.data import MetadataData
from .metrics.processor import MetricsError, ResourcesError

_LOGGER = logging.getLogger(__name__)

_ADD_NEW = "__add_new__"
_DONE = "__done__"

_STATE_CLASS_OPTIONS = [
    {"value": "", "label": "None"},
    {"value": "measurement", "label": "Measurement"},
    {"value": "total", "label": "Total"},
    {"value": "total_increasing", "label": "Total (increasing)"},
]

_DEVICE_CLASS_OPTIONS = [
    {"value": "", "label": "None"},
    {"value": "apparent_power", "label": "Apparent power"},
    {"value": "aqi", "label": "Air quality index"},
    {"value": "atmospheric_pressure", "label": "Atmospheric pressure"},
    {"value": "battery", "label": "Battery"},
    {"value": "carbon_dioxide", "label": "Carbon dioxide"},
    {"value": "carbon_monoxide", "label": "Carbon monoxide"},
    {"value": "current", "label": "Current"},
    {"value": "data_rate", "label": "Data rate"},
    {"value": "data_size", "label": "Data size"},
    {"value": "date", "label": "Date"},
    {"value": "distance", "label": "Distance"},
    {"value": "duration", "label": "Duration"},
    {"value": "energy", "label": "Energy"},
    {"value": "frequency", "label": "Frequency"},
    {"value": "gas", "label": "Gas"},
    {"value": "humidity", "label": "Humidity"},
    {"value": "illuminance", "label": "Illuminance"},
    {"value": "irradiance", "label": "Irradiance"},
    {"value": "moisture", "label": "Moisture"},
    {"value": "monetary", "label": "Monetary"},
    {"value": "nitrogen_dioxide", "label": "Nitrogen dioxide"},
    {"value": "nitrogen_monoxide", "label": "Nitrogen monoxide"},
    {"value": "nitrous_oxide", "label": "Nitrous oxide"},
    {"value": "ozone", "label": "Ozone"},
    {"value": "ph", "label": "pH"},
    {"value": "pm1", "label": "PM1"},
    {"value": "pm10", "label": "PM10"},
    {"value": "pm25", "label": "PM2.5"},
    {"value": "power", "label": "Power"},
    {"value": "power_factor", "label": "Power factor"},
    {"value": "precipitation", "label": "Precipitation"},
    {"value": "precipitation_intensity", "label": "Precipitation intensity"},
    {"value": "pressure", "label": "Pressure"},
    {"value": "reactive_power", "label": "Reactive power"},
    {"value": "signal_strength", "label": "Signal strength"},
    {"value": "sound_pressure", "label": "Sound pressure"},
    {"value": "speed", "label": "Speed"},
    {"value": "sulphur_dioxide", "label": "Sulphur dioxide"},
    {"value": "temperature", "label": "Temperature"},
    {"value": "timestamp", "label": "Timestamp"},
    {"value": "volatile_organic_compounds", "label": "Volatile organic compounds"},
    {"value": "voltage", "label": "Voltage"},
    {"value": "volume", "label": "Volume"},
    {"value": "volume_flow_rate", "label": "Volume flow rate"},
    {"value": "water", "label": "Water"},
    {"value": "weight", "label": "Weight"},
    {"value": "wind_speed", "label": "Wind speed"},
]


class OpenMetricsOptionsFlowHandler(OptionsFlow):
    """Options flow handler for the OpenMetrics integration."""

    metadata: MetadataData

    def __init__(self) -> None:
        """Initialize options flow."""
        self._client: OpenMetricsClient | None = None
        self._entity_manager: OpenMetricsEntityManager | None = None
        self._editing_metric_id: str | None = None

    # ---------------------------------------------------------------------------
    # Properties
    # ---------------------------------------------------------------------------

    @property
    def client(self) -> OpenMetricsClient:
        """Get or create the OpenMetrics client instance."""
        if self._client is None:
            self._client = self._create_client(dict(self.config_entry.data))
        if self._client is None:
            raise HomeAssistantError(
                "OpenMetrics client is not set for this config entry"
            )
        return self._client

    @property
    def entity_manager(self) -> OpenMetricsEntityManager:
        """Get or create the entity manager instance."""
        if self._entity_manager is None:
            self._entity_manager = self.hass.data[DOMAIN][self.config_entry.entry_id][
                "entity_manager"
            ]
        if self._entity_manager is None:
            raise HomeAssistantError("Entity manager is not set for this config entry")
        return self._entity_manager

    def _get_available_resources(self) -> list[str]:
        """Get non-virtual resource names from the metadata."""
        return [
            resource.name
            for resource in self.metadata.resources.values()
            if resource.name and not resource.is_virtual
        ]

    def _get_configured_resources(self) -> list[str]:
        """Return the resources currently selected in the config entry."""
        return self.config_entry.data.get(CONF_RESOURCES, [])

    # ---------------------------------------------------------------------------
    # Main menu
    # ---------------------------------------------------------------------------

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show the main options menu."""
        return self.async_show_menu(
            step_id="init",
            menu_options=["configure", "custom_metrics"],
        )

    # ---------------------------------------------------------------------------
    # Configure step (resources / metrics / scan interval)
    # ---------------------------------------------------------------------------

    async def async_step_configure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage resources, metrics, and scan interval."""
        errors: dict[str, str] = {}
        configured_resources = self.config_entry.data[CONF_RESOURCES]
        configured_metrics = list(dict.fromkeys(self.config_entry.data[CONF_METRICS]))
        configured_scan_interval = self.config_entry.data[CONF_SCAN_INTERVAL]

        if user_input is not None:
            try:
                config_input = self._validate_configure_input(user_input)
                self.metadata = await self.client.get_metadata()
                await self.entity_manager.update_resources(
                    config_input[CONF_RESOURCES], self.metadata
                )
                await self.entity_manager.update_metrics(config_input[CONF_METRICS])
                self._update_scan_interval(config_input[CONF_SCAN_INTERVAL])
                data = self.config_entry.data.copy()
                data[CONF_RESOURCES] = config_input[CONF_RESOURCES]
                data[CONF_METRICS] = list(dict.fromkeys(config_input[CONF_METRICS]))
                data[CONF_SCAN_INTERVAL] = config_input[CONF_SCAN_INTERVAL]
                self.hass.config_entries.async_update_entry(
                    self.config_entry, data=data, options=self.config_entry.options
                )
                return self.async_create_entry(title=None, data={})
            except ResourcesError as e:
                _LOGGER.error("Resources error: %s", str(e))
                errors["base"] = "no_resources"
            except MetricsError as e:
                _LOGGER.error("Metrics error: %s", str(e))
                errors["base"] = "no_metrics"
            except ValueError as e:
                _LOGGER.error("Invalid input: %s", str(e))
                errors["base"] = "invalid_input"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            finally:
                configured_resources = user_input[CONF_RESOURCES]
                configured_metrics = user_input[CONF_METRICS]
                configured_scan_interval = user_input[CONF_SCAN_INTERVAL]

        available_resources: list[str] = []
        available_metrics: list[str] = []
        try:
            self.metadata = await self.client.get_metadata()
            available_resources = self._get_available_resources()
            available_metrics = self.metadata.available_metrics
        except CannotConnectError as e:
            _LOGGER.error("Failed to connect: %s", str(e))
            errors["base"] = "cannot_connect"
        except InvalidAuthError as e:
            _LOGGER.error("Authentication failed: %s", str(e))
            errors["base"] = "invalid_auth"
        except Exception as e:  # noqa: BLE001
            _LOGGER.error("Unexpected error getting metadata: %s", str(e))
            errors["base"] = "unknown"

        data_schema = vol.Schema(
            {
                vol.Required(
                    CONF_RESOURCES,
                    description={"suggested_value": configured_resources},
                ): SelectSelector(
                    SelectSelectorConfig(
                        options=available_resources,
                        translation_key=CONF_RESOURCES,
                        multiple=True,
                        mode=SelectSelectorMode.LIST,
                    )
                ),
                vol.Required(
                    CONF_METRICS,
                    description={"suggested_value": configured_metrics},
                ): SelectSelector(
                    SelectSelectorConfig(
                        options=available_metrics,
                        translation_key=CONF_METRICS,
                        multiple=True,
                        mode=SelectSelectorMode.LIST,
                    )
                ),
                vol.Required(
                    CONF_SCAN_INTERVAL,
                    description={"suggested_value": configured_scan_interval},
                ): selector(
                    {
                        "number": {
                            "mode": "box",
                            "min": 1,
                            "max": 60,
                            "step": 1,
                        }
                    }
                ),
            },
            extra=vol.ALLOW_EXTRA,
        )
        return self.async_show_form(
            step_id="configure",
            data_schema=data_schema,
            errors=errors,
        )

    def _validate_configure_input(self, data: dict[str, Any]) -> dict[str, Any]:
        """Validate configure step input."""
        resources = data.get(CONF_RESOURCES, [])
        metrics = data.get(CONF_METRICS, [])
        scan_interval = data.get(CONF_SCAN_INTERVAL)
        if len(resources) == 0:
            raise ResourcesError("No resources selected")
        if len(metrics) == 0:
            raise MetricsError("No metrics selected")
        if scan_interval is None or not isinstance(scan_interval, (float, int)):
            raise ValueError("Invalid or missing scan interval")
        if scan_interval < 1 or scan_interval > 60:
            raise ValueError("Scan interval must be between 1 and 60 seconds")
        return {
            CONF_RESOURCES: resources,
            CONF_METRICS: metrics,
            CONF_SCAN_INTERVAL: scan_interval,
        }

    def _update_scan_interval(self, new_scan_interval: int) -> None:
        """Update the coordinator scan interval if it changed."""
        current_scan_interval = int(self.config_entry.data[CONF_SCAN_INTERVAL])
        if new_scan_interval != current_scan_interval:
            coordinator: OpenMetricsDataUpdateCoordinator = self.hass.data[DOMAIN][
                self.config_entry.entry_id
            ]["coordinator"]
            coordinator.update_interval = timedelta(seconds=new_scan_interval)
            _LOGGER.info("Updated scan interval to %s seconds", new_scan_interval)

    def _create_client(self, data: dict[str, Any]) -> OpenMetricsClient:
        """Create a new OpenMetricsClient instance."""
        return OpenMetricsClient(
            data[CONF_URL],
            data[CONF_VERIFY_SSL],
            data.get(CONF_USERNAME),
            data.get(CONF_PASSWORD),
        )

    # ---------------------------------------------------------------------------
    # Custom metrics management
    # ---------------------------------------------------------------------------

    def _current_custom_metrics(self) -> list[dict]:
        return list(self.config_entry.data.get(CONF_CUSTOM_METRICS, []))

    async def async_step_custom_metrics(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show a list of existing custom metric mappings with add / done options."""
        if user_input is not None:
            action = user_input.get("action", _DONE)
            if action == _ADD_NEW:
                self._editing_metric_id = None
                return await self.async_step_custom_metric_edit()
            if action == _DONE:
                return self.async_create_entry(title=None, data={})
            # Editing an existing metric
            self._editing_metric_id = action
            return await self.async_step_custom_metric_edit()

        custom_metrics = self._current_custom_metrics()
        options = [{"value": _ADD_NEW, "label": "Add new mapping"}]
        for cm in custom_metrics:
            options.append(
                {"value": cm[CONF_CUSTOM_METRIC_ID], "label": cm[CONF_CUSTOM_METRIC_NAME]}
            )
        options.append({"value": _DONE, "label": "Done"})

        return self.async_show_form(
            step_id="custom_metrics",
            data_schema=vol.Schema(
                {
                    vol.Required("action", default=_ADD_NEW): SelectSelector(
                        SelectSelectorConfig(
                            options=options,
                            mode=SelectSelectorMode.LIST,
                        )
                    )
                }
            ),
        )

    async def async_step_custom_metric_edit(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Add or edit a custom metric mapping."""
        errors: dict[str, str] = {}
        existing: dict = {}
        if self._editing_metric_id:
            for cm in self._current_custom_metrics():
                if cm[CONF_CUSTOM_METRIC_ID] == self._editing_metric_id:
                    existing = cm
                    break

        configured_resources = self._get_configured_resources()

        if user_input is not None:
            # Handle delete
            if user_input.get("delete"):
                if self._editing_metric_id:
                    new_list = [
                        cm
                        for cm in self._current_custom_metrics()
                        if cm[CONF_CUSTOM_METRIC_ID] != self._editing_metric_id
                    ]
                    await self._save_custom_metrics(new_list)
                return await self.async_step_custom_metrics()

            try:
                validated = self._validate_custom_metric_input(user_input, configured_resources)
            except ValueError as e:
                errors["base"] = str(e)
            else:
                new_list = self._current_custom_metrics()
                if self._editing_metric_id:
                    # Replace existing entry in-place
                    validated[CONF_CUSTOM_METRIC_ID] = self._editing_metric_id
                    new_list = [
                        validated if cm[CONF_CUSTOM_METRIC_ID] == self._editing_metric_id else cm
                        for cm in new_list
                    ]
                else:
                    validated[CONF_CUSTOM_METRIC_ID] = generate_custom_metric_id()
                    new_list.append(validated)
                await self._save_custom_metrics(new_list)
                return await self.async_step_custom_metrics()

        resource_options = [{"value": r, "label": r} for r in configured_resources]

        schema_dict: dict = {
            vol.Required(
                CONF_CUSTOM_METRIC_RESOURCE,
                description={"suggested_value": existing.get(CONF_CUSTOM_METRIC_RESOURCE, "")},
            ): SelectSelector(
                SelectSelectorConfig(
                    options=resource_options,
                    mode=SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Required(
                CONF_CUSTOM_METRIC_QUERY,
                description={"suggested_value": existing.get(CONF_CUSTOM_METRIC_QUERY, "")},
            ): TextSelector(TextSelectorConfig(type=TextSelectorType.TEXT)),
            vol.Optional(
                CONF_CUSTOM_METRIC_GROUP_BY,
                description={
                    "suggested_value": ", ".join(
                        existing.get(CONF_CUSTOM_METRIC_GROUP_BY) or []
                    )
                },
            ): TextSelector(TextSelectorConfig(type=TextSelectorType.TEXT)),
            vol.Required(
                CONF_CUSTOM_METRIC_NAME,
                description={"suggested_value": existing.get(CONF_CUSTOM_METRIC_NAME, "")},
            ): TextSelector(TextSelectorConfig(type=TextSelectorType.TEXT)),
            vol.Optional(
                CONF_CUSTOM_METRIC_UNIT,
                description={"suggested_value": existing.get(CONF_CUSTOM_METRIC_UNIT, "")},
            ): TextSelector(TextSelectorConfig(type=TextSelectorType.TEXT)),
            vol.Optional(
                CONF_CUSTOM_METRIC_ICON,
                description={"suggested_value": existing.get(CONF_CUSTOM_METRIC_ICON, "")},
            ): TextSelector(TextSelectorConfig(type=TextSelectorType.TEXT)),
            vol.Optional(
                CONF_CUSTOM_METRIC_DEVICE_CLASS,
                description={"suggested_value": existing.get(CONF_CUSTOM_METRIC_DEVICE_CLASS, "")},
            ): SelectSelector(
                SelectSelectorConfig(
                    options=_DEVICE_CLASS_OPTIONS,
                    mode=SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Optional(
                CONF_CUSTOM_METRIC_STATE_CLASS,
                description={"suggested_value": existing.get(CONF_CUSTOM_METRIC_STATE_CLASS, "")},
            ): SelectSelector(
                SelectSelectorConfig(
                    options=_STATE_CLASS_OPTIONS,
                    mode=SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Optional(
                CONF_CUSTOM_METRIC_PRECISION,
                description={"suggested_value": existing.get(CONF_CUSTOM_METRIC_PRECISION)},
            ): NumberSelector(
                NumberSelectorConfig(min=0, max=10, step=1, mode=NumberSelectorMode.BOX)
            ),
        }
        if self._editing_metric_id:
            schema_dict[vol.Optional("delete", default=False)] = selector(
                {"boolean": {}}
            )

        return self.async_show_form(
            step_id="custom_metric_edit",
            data_schema=vol.Schema(schema_dict, extra=vol.ALLOW_EXTRA),
            errors=errors,
            description_placeholders={
                "editing": "true" if self._editing_metric_id else "false"
            },
        )

    def _validate_custom_metric_input(
        self, data: dict[str, Any], configured_resources: list[str]
    ) -> dict:
        """Validate and normalise custom metric form input."""
        resource = data.get(CONF_CUSTOM_METRIC_RESOURCE, "").strip()
        query = data.get(CONF_CUSTOM_METRIC_QUERY, "").strip()
        name = data.get(CONF_CUSTOM_METRIC_NAME, "").strip()

        if not resource:
            raise ValueError("resource_required")
        if resource not in configured_resources:
            raise ValueError("resource_invalid")
        if not query:
            raise ValueError("query_required")
        try:
            parse_metric_query(query)
        except ValueError:
            raise ValueError("query_invalid")
        if not name:
            raise ValueError("name_required")

        result: dict[str, Any] = {
            CONF_CUSTOM_METRIC_RESOURCE: resource,
            CONF_CUSTOM_METRIC_QUERY: query,
            CONF_CUSTOM_METRIC_NAME: name,
        }
        group_by_raw = data.get(CONF_CUSTOM_METRIC_GROUP_BY, "")
        if isinstance(group_by_raw, list):
            group_by = [s.strip() for s in group_by_raw if str(s).strip()]
        else:
            group_by = [s.strip() for s in str(group_by_raw).split(",") if s.strip()]
        if group_by:
            result[CONF_CUSTOM_METRIC_GROUP_BY] = group_by
        if unit := data.get(CONF_CUSTOM_METRIC_UNIT, "").strip():
            result[CONF_CUSTOM_METRIC_UNIT] = unit
        if icon := data.get(CONF_CUSTOM_METRIC_ICON, "").strip():
            result[CONF_CUSTOM_METRIC_ICON] = icon
        if device_class := data.get(CONF_CUSTOM_METRIC_DEVICE_CLASS, "").strip():
            result[CONF_CUSTOM_METRIC_DEVICE_CLASS] = device_class
        if state_class := data.get(CONF_CUSTOM_METRIC_STATE_CLASS, "").strip():
            result[CONF_CUSTOM_METRIC_STATE_CLASS] = state_class
        if (precision := data.get(CONF_CUSTOM_METRIC_PRECISION)) is not None:
            result[CONF_CUSTOM_METRIC_PRECISION] = int(precision)
        return result

    async def _save_custom_metrics(self, new_list: list[dict]) -> None:
        """Persist updated custom metrics list and reconcile HA entities."""
        await self.entity_manager.update_custom_metrics(new_list)
        data = self.config_entry.data.copy()
        data[CONF_CUSTOM_METRICS] = new_list
        self.hass.config_entries.async_update_entry(
            self.config_entry, data=data, options=self.config_entry.options
        )
