"""Class for interacting with OpenMetrics."""

import logging
from http import HTTPStatus

import aiohttp
from homeassistant.exceptions import HomeAssistantError

from .lib import parser, prom_parser
from .lib.metrics_core import Metric
from .metrics.data import MetadataData
from .metrics.processor import MetricsProcessor, ProcessingError

_LOGGER = logging.getLogger(__name__)


class RequestError(HomeAssistantError):
    """Error to indicate a client request error."""


class InvalidAuthError(HomeAssistantError):
    """Error to indicate there is invalid auth."""


class CannotConnectError(HomeAssistantError):
    """Error to indicate we cannot connect."""


class ClientError(HomeAssistantError):
    """Base class for client errors."""


class OpenMetricsClient:
    """Class for interacting with OpenMetrics."""

    def __init__(
        self, url: str, verify_ssl: bool, username=None, password=None
    ) -> None:
        """Initialize the OpenMetrics client."""
        self.url = url
        self.verify_ssl = verify_ssl
        self.username = username
        self.password = password
        self.processor = MetricsProcessor()

    async def _make_request(
        self,
        session: aiohttp.ClientSession,
        method: str,
        url: str,
        headers: dict | None = None,
        data: dict | None = None,
    ) -> aiohttp.ClientResponse:
        """Make an HTTP request."""
        return await session.request(
            method, url, headers=headers, data=data, verify_ssl=self.verify_ssl
        )

    async def _async_request_data(self) -> tuple[str, str | None]:
        """Request data from metrics provider."""
        async with aiohttp.ClientSession() as session:
            headers = {"Accept": "application/openmetrics-text;charset=utf-8"}
            if self.username and self.password:
                auth = aiohttp.BasicAuth(self.username, self.password)
                headers["Authorization"] = auth.encode()

            try:
                response = await self._make_request(session, "GET", self.url, headers)
            except aiohttp.ClientConnectionError as e:
                raise CannotConnectError(str(e)) from e
            except aiohttp.ClientError as e:
                raise RequestError(str(e)) from e

            if response.status == HTTPStatus.OK.value:
                return (await response.text(), response.headers.get("Content-Type"))
            if response.status == HTTPStatus.UNAUTHORIZED.value:
                raise InvalidAuthError(f"Invalid auth for {self.url}")

            raise RequestError(
                f"Request failed with status code '{response.status}' and reason '{response.reason}'"
            )

    def _parse_data(self, response_text: str, content_type: str | None) -> list[Metric]:
        """Parse metrics provider data."""
        try:
            if content_type and "text/plain" in content_type:
                families = prom_parser.text_string_to_metric_families(response_text)
            elif content_type and "application/openmetrics-text" in content_type:
                families = parser.text_string_to_metric_families(response_text)
            else:
                raise ProcessingError(f"Content type '{content_type}' not supported")
        except Exception as e:
            raise ProcessingError(str(e)) from e

        _LOGGER.debug("Metrics successfully parsed")
        return list(families)

    async def get_metadata(self) -> MetadataData:
        """Get metadata from a metrics provider."""
        response_text, content_type = await self._async_request_data()
        families = self._parse_data(response_text, content_type)
        return self.processor.extract_metadata(families)

    async def get_metrics(self, resources: list[str]) -> dict:
        """Get metrics from a metrics provider."""
        response_text, content_type = await self._async_request_data()
        families = self._parse_data(response_text, content_type)
        return self.processor.extract_metrics(families, resources)
