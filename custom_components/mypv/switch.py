"""Switches of myPV integration."""

import asyncio
import logging
from typing import Any

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import COMM_HUB, DOMAIN

_LOGGER = logging.getLogger(__name__)

PID_POWER_ON_VALUE = 3000
PID_POWER_OFF_VALUE = 0


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities):
    """Add all myPV switch entities."""
    comm = hass.data[DOMAIN][entry.entry_id][COMM_HUB]

    for device in comm.devices:
        async_add_entities(device.switches)


class MpvSetupSwitch(CoordinatorEntity, SwitchEntity):
    """Representation of myPV switch."""

    _attr_device_class = SwitchDeviceClass.SWITCH

    def __init__(self, device, key, info) -> None:
        """Initialize the switch."""
        super().__init__(device.comm)
        self.device = device
        self.comm = device.comm
        self._key = key
        self._name = info[0]
        self._type = info[2]

    @property
    def name(self):
        """Return the name of the switch."""
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
    def is_on(self) -> bool:
        """Return status of output."""
        return self.device.setup[self._key] == 1

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._attr_is_on = self.device.setup[self._key] == 1
        self.async_write_ha_state()

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Instruct the switch to turn on."""
        await self.comm.switch(self.device, self._key, True)
        await self.device.update()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Instruct the switch to turn off."""
        await self.comm.switch(self.device, self._key, False)
        await self.device.update()


class MpvBoostSwitch(CoordinatorEntity, SwitchEntity):
    """Representation of myPV switch."""

    _attr_device_class = SwitchDeviceClass.SWITCH

    def __init__(self, device, key, info) -> None:
        """Initialize the switch."""
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
    def is_on(self) -> bool:
        """Return status of output."""
        return self.device.data[self._key] == 1

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._attr_is_on = self.device.data[self._key] == 1
        self.async_write_ha_state()

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Instruct the switch to turn on."""
        await self.comm.switch_boost(self.device, True)
        await self.device.update()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Instruct the switch to turn off."""
        await self.comm.switch_boost(self.device, False)
        await self.device.update()


class MpvHttpSwitch(CoordinatorEntity, SwitchEntity):
    """Representation of myPV switch."""

    _attr_device_class = SwitchDeviceClass.SWITCH

    def __init__(self, device, key) -> None:
        """Initialize the switch."""
        super().__init__(device.comm)
        self.device = device
        self.comm = device.comm
        self._key = key
        self._name = "Enable HTTP"

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
    def is_on(self) -> bool:
        """Return status of output."""
        return self.device.setup[self._key] == 1

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._attr_is_on = self.device.setup[self._key] == 1
        self.async_write_ha_state()

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Instruct the switch to turn on."""
        await self.comm.set_control_mode(self.device, 1)
        await self.device.update()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Instruct the switch to turn off."""
