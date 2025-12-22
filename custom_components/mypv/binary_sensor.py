"""Binary sensors of myPV integration."""

import logging
from typing import TYPE_CHECKING, Any, override

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import COMM_HUB, DOMAIN

if TYPE_CHECKING:
    from .communicate import MypvCommunicator
    from .mypv_device import MpyDevice

    CoordinatorEntity = CoordinatorEntity[MypvCommunicator]

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add all myPV binary sensor entities."""
    comm = hass.data[DOMAIN][entry.entry_id][COMM_HUB]

    for device in comm.devices:
        async_add_entities(device.binary_sensors)


class MpvBinSensor(CoordinatorEntity, BinarySensorEntity):
    """Representation of a MyPV binary sensor."""

    def __init__(
        self,
        device: "MpyDevice",
        key: str,
        info: list[Any],
    ) -> None:
        """Initialize the sensor."""
        super().__init__(device.comm)
        self._device = device
        self.entity_description = BinarySensorEntityDescription(
            key=key,
            has_entity_name=True,
            name=info[0],
            device_class=None,
        )
        self._attr_unique_id = (
            f"{self._device.serial_number}_{self.entity_description.name}"
        )
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._device.serial_number)},
            name=self._device.name,
            manufacturer="myPV",
            model=self._device.model,
        )

    @override
    def _handle_coordinator_update(self) -> None:
        key = self.entity_description.key
        try:
            value = self._device.data[key]  # type: ignore  # noqa: PGH003
        except (KeyError, TypeError):
            _LOGGER.warning(
                "Update for %s failed, key %s not found", self.entity_id, key
            )
        else:
            self._attr_is_on = self.map_bool_value(value)
            super()._handle_coordinator_update()

    def map_bool_value(self, value: Any) -> bool:
        """Help to map the value to a boolean."""
        match value:
            case "1" | 1 | True:
                return True
            case "0" | 0 | False:
                return False
            case _:
                _LOGGER.warning("Unexpected value for binary sensor: %r", value)
                return False


class MpvBin1Sensor(MpvBinSensor):
    """Representation of a MyPV binary sensor for AC-Thor 9s."""

    def map_bool_value(self, value: Any) -> bool:
        """Help to map the value to a boolean."""
        if isinstance(value, int):
            str_number = str(value).zfill(4)
        elif isinstance(value, str):
            str_number = str(int(value)).zfill(4)  # Ensure it's zero-padded
        else:
            _LOGGER.warning("Unexpected type for binary sensor value: %r", value)
            return False
        return str_number[0] == "1"


class MpvBin2Sensor(MpvBinSensor):
    """Representation of a MyPV binary sensor for AC-Thor 9s."""

    def map_bool_value(self, value: Any) -> bool:
        """Help to map the value to a boolean."""
        if isinstance(value, int):
            str_number = str(value).zfill(4)
        elif isinstance(value, str):
            str_number = str(int(value)).zfill(4)  # Ensure it's zero-padded
        else:
            _LOGGER.warning("Unexpected type for binary sensor value: %r", value)
            return False
        return str_number[1] == "1"


class MpvBin3Sensor(MpvBinSensor):
    """Representation of a MyPV binary sensor for AC-Thor 9s."""

    def map_bool_value(self, value: Any) -> bool:
        """Help to map the value to a boolean."""
        if isinstance(value, int):
            str_number = str(value).zfill(4)
        elif isinstance(value, str):
            str_number = str(int(value)).zfill(4)  # Ensure it's zero-padded
        else:
            _LOGGER.warning("Unexpected type for binary sensor value: %r", value)
            return False
        return str_number[2] == "1"
