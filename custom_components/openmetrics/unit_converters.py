"""Unit conversion utilities."""

import re
from math import ceil, floor

from homeassistant.const import UnitOfDataRate, UnitOfInformation
from homeassistant.util.unit_conversion import BaseUnitConverter


class DataSizeConverter(BaseUnitConverter):
    """Utility to convert data size values."""

    UNIT_CLASS = "data_size"
    NORMALIZED_UNIT = UnitOfInformation.BYTES
    # Units in terms of bytes
    _UNIT_CONVERSION: dict[str | None, float] = {
        UnitOfInformation.BYTES: 1,
        UnitOfInformation.KILOBYTES: 1 / 1e3,
        UnitOfInformation.MEGABYTES: 1 / 1e6,
        UnitOfInformation.GIGABYTES: 1 / 1e9,
        UnitOfInformation.TERABYTES: 1 / 1e12,
        UnitOfInformation.PETABYTES: 1 / 1e15,
        UnitOfInformation.EXABYTES: 1 / 1e18,
        UnitOfInformation.ZETTABYTES: 1 / 1e21,
        UnitOfInformation.YOTTABYTES: 1 / 1e24,
        UnitOfInformation.KIBIBYTES: 1 / 2**10,
        UnitOfInformation.MEBIBYTES: 1 / 2**20,
        UnitOfInformation.GIBIBYTES: 1 / 2**30,
        UnitOfInformation.TEBIBYTES: 1 / 2**40,
        UnitOfInformation.PEBIBYTES: 1 / 2**50,
        UnitOfInformation.EXBIBYTES: 1 / 2**60,
        UnitOfInformation.ZEBIBYTES: 1 / 2**70,
        UnitOfInformation.YOBIBYTES: 1 / 2**80,
    }

    @classmethod
    def is_valid_unit(cls, unit: str) -> bool:
        """Check if the given unit is supported.

        Args:
            unit: The unit to check

        Returns:
            bool: True if the unit is supported, False otherwise

        """
        return unit in cls._UNIT_CONVERSION


class DataRateConverter(BaseUnitConverter):
    """Utility to convert data rate values."""

    UNIT_CLASS = "data_rate"
    NORMALIZED_UNIT = UnitOfDataRate.BITS_PER_SECOND
    # Units in terms of bits per second
    _UNIT_CONVERSION: dict[str | None, float] = {
        UnitOfDataRate.BITS_PER_SECOND: 1,
        UnitOfDataRate.KILOBITS_PER_SECOND: 1 / 1e3,
        UnitOfDataRate.MEGABITS_PER_SECOND: 1 / 1e6,
        UnitOfDataRate.GIGABITS_PER_SECOND: 1 / 1e9,
        UnitOfDataRate.BYTES_PER_SECOND: 1 / 8,
        UnitOfDataRate.KILOBYTES_PER_SECOND: 1 / (8 * 1e3),
        UnitOfDataRate.MEGABYTES_PER_SECOND: 1 / (8 * 1e6),
        UnitOfDataRate.GIGABYTES_PER_SECOND: 1 / (8 * 1e9),
        UnitOfDataRate.KIBIBYTES_PER_SECOND: 1 / (8 * 2**10),
        UnitOfDataRate.MEBIBYTES_PER_SECOND: 1 / (8 * 2**20),
        UnitOfDataRate.GIBIBYTES_PER_SECOND: 1 / (8 * 2**30),
        "Mbps": 1 / 1e6,
    }

    @classmethod
    def is_valid_unit(cls, unit: str) -> bool:
        """Check if the given unit is supported.

        Args:
            unit: The unit to check

        Returns:
            bool: True if the unit is supported, False otherwise

        """
        return unit in cls._UNIT_CONVERSION


def get_appropriate_unit(data_size_bytes):
    """Determine the most appropriate unit for a given byte size."""
    # Map length to decimal units
    decimal_units = [
        UnitOfInformation.BYTES,
        UnitOfInformation.KILOBYTES,
        UnitOfInformation.MEGABYTES,
        UnitOfInformation.GIGABYTES,
        UnitOfInformation.TERABYTES,
        UnitOfInformation.PETABYTES,
        UnitOfInformation.EXABYTES,
        UnitOfInformation.ZETTABYTES,
        UnitOfInformation.YOTTABYTES,
    ]
    # Determine appropriate unit based on number length
    length = ceil(len(str(floor(data_size_bytes))) / 3)
    index = min(length, len(decimal_units)) - 1  # Cap at the largest available unit
    # Return the appropriate unit
    return decimal_units[index]


def convert_data_size(
    data_size: str | float,
    target_unit: str,
    source_unit: str = UnitOfInformation.BYTES,
) -> float:
    """Convert a data size string to a specified target unit.

    Args:
        data_size (str | float): The data size as string (e.g., '100MB', '1GB', '512KB') or as float (e.g., 1000000000.0)
        target_unit (str): The target unit to convert to (e.g., UnitOfInformation.GIBIBYTES)
        source_unit (str, optional): The source unit to convert from (default is UnitOfInformation.BYTES)

    Returns:
        float: The converted data size value in target unit.

    Raises:
        ValueError: If the input string format is invalid or unit is not supported.
        TypeError: If the input data_size is not a string or float.

    """
    # Extract numeric value and unit from string
    if isinstance(data_size, str):
        match = re.match(r"^([\d.]+)\s*([A-Za-z]+)?$", data_size.strip())
        if not match:
            raise ValueError(f"Invalid data size format: {data_size}")
        value = float(match.group(1))
        source_unit = match.group(2)
    elif isinstance(data_size, float | int):
        value = data_size
    else:
        raise TypeError(f"Expected str or float, got {type(data_size).__name__}")
    # Validate if source unit is supported using public method
    if not DataSizeConverter.is_valid_unit(source_unit):
        raise ValueError(f"Unsupported unit: {source_unit}")

    # Map from decimal to binary units
    binary_equivalent: dict[str | None, str] = {
        UnitOfInformation.KILOBYTES: UnitOfInformation.KIBIBYTES,
        UnitOfInformation.MEGABYTES: UnitOfInformation.MEBIBYTES,
        UnitOfInformation.GIGABYTES: UnitOfInformation.GIBIBYTES,
        UnitOfInformation.TERABYTES: UnitOfInformation.TEBIBYTES,
        UnitOfInformation.PETABYTES: UnitOfInformation.PEBIBYTES,
        UnitOfInformation.EXABYTES: UnitOfInformation.EXBIBYTES,
        UnitOfInformation.ZETTABYTES: UnitOfInformation.ZEBIBYTES,
        UnitOfInformation.YOTTABYTES: UnitOfInformation.YOBIBYTES,
    }
    # Use binary units for values that are multiples of 64
    if value % 64 == 0 and value % 10 != 0 and target_unit in binary_equivalent:
        target_unit = binary_equivalent[target_unit]

    # Convert source unit to target unit and return the result
    return DataSizeConverter.convert(value, source_unit, target_unit)


def convert_data_rate(
    data_rate: str | float,
    target_unit: str,
    source_unit: str = UnitOfDataRate.BYTES_PER_SECOND,
) -> float:
    """Convert a data rate string to a specified target unit.

    Args:
        data_rate (str | float): The data rate as string (e.g., '100Mbps', '1Gbps', '512Kbps') or as float (e.g., 1000000000.0)
        target_unit (str): The target unit to convert to (e.g., UnitOfDataRate.MEGABITS_PER_SECOND)
        source_unit (str, optional): The source unit to convert from (default is UnitOfDataRate.BYTES_PER_SECOND)

    Returns:
        float: The converted data rate value in target unit.

    Raises:
        ValueError: If the input string format is invalid or unit is not supported.
        TypeError: If the input data_rate is not a string or float.

    Examples:
        >>> _convert_data_rate("100Mbps", UnitOfDataRate.GIGABITS_PER_SECOND)
        0.1
        >>> _convert_data_rate("1Gbps", UnitOfDataRate.MEGABYTES_PER_SECOND)
        125.0

    """
    # Extract numeric value and unit from string
    if isinstance(data_rate, str):
        match = re.match(r"^([\d.]+)\s*([A-Za-z]+)?$", str(data_rate).strip())
        if not match:
            raise ValueError(f"Invalid data rate format: {data_rate}")
        value = float(match.group(1))
        source_unit = match.group(2)
    elif isinstance(data_rate, float | int):
        value = data_rate
    else:
        raise TypeError(f"Expected str or float, got {type(data_rate).__name__}")
    # Validate if source unit is supported using public method
    if not DataRateConverter.is_valid_unit(source_unit):
        raise ValueError(f"Unsupported unit: {source_unit}")
    # Convert source unit to target unit and return the result
    return DataRateConverter.convert(value, source_unit, target_unit)
