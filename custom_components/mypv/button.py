"""Buttons of myPV integration."""

import logging

from homeassistant.components.button import ButtonDeviceClass, ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import COMM_HUB, DOMAIN

_LOGGER = logging.getLogger(__name__)

PID_POWER_ON_VALUE = 3000
PID_POWER_OFF_VALUE = 0


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities):
    """Add all myPV button entities."""
    comm = hass.data[DOMAIN][entry.entry_id][COMM_HUB]

    for device in comm.devices:
        async_add_entities(device.buttons)


class MpvBoostButton(CoordinatorEntity, ButtonEntity):
    """Representation of myPV button."""

    def __init__(self, device, key, info) -> None:
        """Initialize the button."""
        super().__init__(device.comm)
        self.device = device
        self.comm = device.comm
        self._key = key
        self._name = info[0]
        self._type = info[2]

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def unique_id(self):
        """Return unique id based on device serial and variable."""
        return f"{self.device.serial_number}_{self._name}"

    @property
    def device_info(self):
        """Return information about the device."""
        return {
            "identifiers": {(DOMAIN, self.device.serial_number)},
            "name": self.device.name,
            "manufacturer": "myPV",
            "model": self.device.model,
        }

    @property
    def icon(self):
        """Return icon."""
        return "mdi:heat-wave"

    async def async_press(self) -> None:
        """Instruct the button to activate."""
        await self.comm.activate_boost(self.device, 1)  # 1 to activate boost


class MpvBoostOffButton(MpvBoostButton):
    """Representation of myPV button to shut off boost."""

    async def async_press(self) -> None:
        """Instruct the button to deactivate."""
        await self.comm.activate_boost(self.device, 0)  # 0 to deactivate boost
