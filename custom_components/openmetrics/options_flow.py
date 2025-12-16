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
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    selector,
)

from .client import CannotConnectError, InvalidAuthError, OpenMetricsClient
from .const import CONF_METRICS, CONF_RESOURCES, DOMAIN
from .coordinator import OpenMetricsDataUpdateCoordinator
from .entity_manager import OpenMetricsEntityManager
from .metrics.data import MetadataData
from .metrics.processor import MetricsError, ResourcesError

_LOGGER = logging.getLogger(__name__)


class OpenMetricsOptionsFlowHandler(OptionsFlow):
    """Options flow handler for the OpenMetrics integration."""

    metadata: MetadataData

    def __init__(self) -> None:
        """Initialize options flow."""
        # OpenMetrics client will be inizialized when config_entry is available
        self._client: OpenMetricsClient | None = None
        # Entity manager will be initialized when hass is available
        self._entity_manager: OpenMetricsEntityManager | None = None

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
        """Get available resources from the metadata."""
        return [
            resource.name
            for resource in self.metadata.resources.values()
            if resource.name and not resource.is_virtual
        ]

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        errors: dict[str, str] = {}
        configured_resources = self.config_entry.data[CONF_RESOURCES]
        configured_metrics = list(dict.fromkeys(self.config_entry.data[CONF_METRICS]))
        configured_scan_interval = self.config_entry.data[CONF_SCAN_INTERVAL]
        # Process user input if available
        if user_input is not None:
            try:
                # Validate input
                config_input = self._validate_input(user_input)
                # Get metadata for entity operations
                self.metadata = await self.client.get_metadata()
                # Update resources and metrics using entity manager
                await self.entity_manager.update_resources(
                    config_input[CONF_RESOURCES], self.metadata
                )
                await self.entity_manager.update_metrics(config_input[CONF_METRICS])
                # Update scan interval
                self._update_scan_interval(config_input[CONF_SCAN_INTERVAL])
                # Set entry data
                data = self.config_entry.data.copy()
                data[CONF_RESOURCES] = config_input[CONF_RESOURCES]
                data[CONF_METRICS] = list(dict.fromkeys(config_input[CONF_METRICS]))
                data[CONF_SCAN_INTERVAL] = config_input[CONF_SCAN_INTERVAL]
                # Update entry
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
                # Update configured values for form display in case of errors
                configured_resources = user_input[CONF_RESOURCES]
                configured_metrics = user_input[CONF_METRICS]
                configured_scan_interval = user_input[CONF_SCAN_INTERVAL]
        # Get available options for the form
        available_resources = []
        available_metrics = []
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
        # Define data schema
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
        # Show form
        return self.async_show_form(
            step_id="init",
            data_schema=data_schema,
            errors=errors,
        )

    def _validate_input(self, data: dict[str, Any]) -> dict[str, Any]:
        """Process user input and validate it."""
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
        """Update the scan interval if it has changed."""
        current_scan_interval = int(self.config_entry.data[CONF_SCAN_INTERVAL])
        if new_scan_interval != current_scan_interval:
            # Get coordinator
            coordinator: OpenMetricsDataUpdateCoordinator = self.hass.data[DOMAIN][
                self.config_entry.entry_id
            ]["coordinator"]
            # Update the update interval
            coordinator.update_interval = timedelta(seconds=new_scan_interval)
            _LOGGER.info("Updated scan interval to %s seconds", new_scan_interval)

    def _create_client(self, data: dict[str, Any]) -> OpenMetricsClient:
        """Create a new OpenMetricsClient instance."""
        url = data[CONF_URL]
        username = data.get(CONF_USERNAME)
        password = data.get(CONF_PASSWORD)
        verify_ssl = data[CONF_VERIFY_SSL]
        return OpenMetricsClient(url, verify_ssl, username, password)
