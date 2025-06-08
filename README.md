# OpenMetrics Home Assistant Integration

[![GitHub Release](https://img.shields.io/github/release/txxa/hass-openmetrics.svg?style=for-the-badge)](https://github.com/txxa/hass-openmetrics/releases)
[![GitHub Activity](https://img.shields.io/github/commit-activity/y/txxa/hass-openmetrics.svg?style=for-the-badge)](https://github.com/txxa/hass-openmetrics/commits/main)
[![License](https://img.shields.io/github/license/txxa/hass-openmetrics.svg?style=for-the-badge)](https://github.com/txxa/hass-openmetrics/blob/main/LICENSE)
[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge)](https://hacs.xyz/docs/faq/custom_repositories)

_Integration to integrate with OpenMetrics and Prometheus exposition format providers._

The [OpenMetrics specification](https://github.com/OpenObservability/OpenMetrics/blob/main/specification/OpenMetrics.md) defines a standard for exposing metrics in a text-based format. This integration supports both the OpenMetrics format and the Prometheus exposition format, which is a widely adopted format for exposing metrics. The library used to process the data is coming from the [Python client repository](https://github.com/prometheus/client_python/blob/master/prometheus_client/) of Prometheus.

Example applications that provide metrics data in supported formats:
- [Prometheus](https://prometheus.io/)
- [Thanos](https://thanos.io/)
- [Cortex](https://cortexmetrics.io/)
- [Node Exporter](https://github.com/prometheus/node_exporter)
- [cAdvisor](https://github.com/google/cadvisor)
- [Blackbox Exporter](https://github.com/prometheus/blackbox_exporter)

This integration allows you to monitor various metrics from OpenMetrics and Prometheus exposition format providers within Home Assistant.

## Table of contents

- [Features](#features)
- [Installation](#installation)
- [Configuration](#configuration)
- [Compatibility](#compatibility)
- [Development and Maintenance](#development-and-maintenance)
- [Contributions](#contributions)

## Features

- Monitor CPU, memory, disk, network, and uptime metrics of hosts and containers.
- Support for multiple metrics providers.
- Multi-container support for container metrics providers.
- Basic authentication support.
- SSL/TLS support.
- Dynamic sources management for multi-container metrics providers.
- Dynamic metrics management.
- Configurable scan interval for sensor data updates.

## Installation

1. Add this repository as a custom repository to HACS: [![Add Repository](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=txxa&repository=hass-openmetrics&category=integration)
2. Use HACS to install the integration.
3. Restart Home Assistant.
4. Set up the integration using the UI: [![Add Integration](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=openmetrics)

## Configuration

Configuration is done through the Home Assistant UI.

### Initial Setup

To add the integration, go to Settings ➤ Devices & Services ➤ Integrations, click ➕ Add Integration, and search for "OpenMetrics".

The initial setup requests the following information:

- **Provider URL**: The URL of the metrics provider.
- **Username**: The username for the metrics provider web interface.
- **Password**: The password for the metrics provider web interface.
- **Verify SSL certificate**: Whether to verify the SSL certificate of the metrics provider.

### Options

Find configuration options under Settings ➤ Devices & Services ➤ Integrations ➤ OpenMetrics ➤ Configure.

The following options can be configured after the initial setup:

- **Resources to monitor**: The resources to monitor.
- **Metrics to collect**: The metrics to collect.
- **Scan interval [s]**: The interval at which to gather the metrics.

## Compatibility

This integration has been tested with specific versions of metrics providers. To ensure proper functionality, please use the version of this integration that corresponds to your installed metrics providers.

Refer to the compatibility matrix below:

| Integration | Node Exporter | cAdvisor   |
| :---------- | :------------ | :--------- |
| v0.1.x      | 1.8.2        | 0.49.1    |
| v0.2.0      | 1.8.2        | 0.49.1    |
| v0.3.x      | 1.8.2<br>1.9.1        | 0.49.1<br>0.52.1    |

**Important notes:**

- The integration may work with versions of metrics providers not listed here, but these combinations have not been explicitly tested.
- It is recommended to use the most recent integration version compatible with your metrics provider version.
- If you encounter any issues with untested version combinations, please report them in the [Issues](../../issues) section of this repository.

For the best experience, try to keep both the integration and metrics providers updated to their latest compatible versions.

## Development and maintenance

I basically created this integration for my personal purpose. As it fulfils all my current needs I won't develop it further for now.\
However, as long as I am using this integration in my Home Assistant setup I will maintain it actively.

## Contributions

If you want to contribute to this integration, please read the [Contribution guidelines](CONTRIBUTING.md)

### Providing translations for other languages

If you would like to use the integration in another language, you can help out by providing the necessary translations in [custom_components/openmetrics/translations/](./custom_components/openmetrics/translations/) and open a pull request with the changes.
