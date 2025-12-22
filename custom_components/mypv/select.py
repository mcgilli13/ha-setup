"""Platform for select integration."""

from __future__ import annotations

from enum import Enum

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add input_select for passed config_entry in HA."""
    hbtn_rt: HbtnRouter = hass.data[DOMAIN][entry.entry_id].router
    hbtn_cord: DataUpdateCoordinator = hbtn_rt.coord
    smhub = hass.data[DOMAIN][entry.entry_id]

    new_devices = []
    for hbt_module in hbtn_rt.modules:
        if hbt_module.mod_type[:16] == "Smart Controller":
            # Mode setting is per group, entities linked to smart controllers only
            new_devices.append(
                HbtnSelectDaytimeModePush(
                    hbt_module, hbtn_rt, hbtn_cord, len(new_devices)
                )
            )
            new_devices.append(
                HbtnSelectAlarmModePush(
                    hbt_module, hbtn_rt, hbtn_cord, len(new_devices)
                )
            )
            new_devices.append(
                HbtnSelectGroupModePush(
                    hbt_module, hbtn_rt, hbtn_cord, len(new_devices)
                )
            )
    new_devices.append(HbtnSelectDaytimeMode(0, hbtn_rt, hbtn_cord, len(new_devices)))
    new_devices.append(HbtnSelectAlarmMode(0, hbtn_rt, hbtn_cord, len(new_devices)))
    new_devices.append(HbtnSelectGroupMode(0, hbtn_rt, hbtn_cord, len(new_devices)))
    for log_level in smhub.loglvl:
        new_devices.append(
            HbtnSelectLoggingLevel(smhub, log_level, hbtn_cord, len(new_devices))
        )

    # Fetch initial data so we have data when entities subscribe
    #
    # If the refresh fails, async_config_entry_first_refresh will
    # raise ConfigEntryNotReady and setup will try again later
    #
    # If you do not want to retry setup on failure, use
    # coordinator.async_refresh() instead
    if new_devices:
        await hbtn_cord.async_config_entry_first_refresh()
        async_add_entities(new_devices)


class GroupMode(Enum):
    """Habitron group mode states."""

    absent = 16
    present = 32
    sleeping = 48
    update = 63
    config = 64
    user1 = 80
    user2 = 96
    vacation = 112


class HbtnMode(CoordinatorEntity, SelectEntity):
    """Representation of a input select for Habitron modes."""

    _attr_has_entity_name = True
    _attr_should_poll = True  # for poll updates

    def __init__(
        self,
        module: int | HbtnModule,
        hbtnr: HbtnRouter,
        coord: DataUpdateCoordinator,
        idx: int,
    ) -> None:
        """Initialize a Habitron mode, pass coordinator to CoordinatorEntity."""
        super().__init__(coord, context=idx)
        self.idx = idx
        if isinstance(module, int):
            self._module = hbtnr
        else:
            self._module = module
        self._mode = hbtnr.mode0 if isinstance(module, int) else int(module.mode.value)
        self._current_option = ""
        self.hbtnr = hbtnr
        self._attr_translation_key = "habitron_mode"
        self._value = 0
        self._enum = DaytimeMode
        self._mask: int = 0
        group_enum = Enum(
            value="group_enum",
            names=[
                ("HTTP", 1),
                ("Modbus TCP", 2),
                ("Fronius auto", 3),
                ("Fronius manual", 4),
                ("SMA Home Manager", 5),
                ("Steca auto", 6),
                ("Varta auto", 7),
                ("Varta manual", 8),
                ("my-PV Meter auto", 9),
                ("my-PV Meter manual", 10),
                ("my-PV Meter direct", 11),
                ("RCT Power manual", 14),
                ("Adjustable Modbus TCP", 15),
            ],
        )

    @property
    def available(self) -> bool:
        """Set true to let HA know that this entity is online."""
        return True

    # To link this entity to its device, this property must return an
    # identifiers value matching that used in the module
    @property
    def device_info(self) -> DeviceInfo:
        """Return information to link this entity with the correct device."""
        if isinstance(self._module, HbtnRouter):
            return {"identifiers": {(DOMAIN, self.hbtnr.uid)}}
        return {"identifiers": {(DOMAIN, self._module.uid)}}

    @property
    def name(self) -> str | None:
        """Return the display name of this selector."""
        return self._attr_name

    @property
    def options(self) -> list[str]:
        """Return all mode names of enumeration type."""
        return [mode.name for mode in self._enum]

    @property
    def current_option(self) -> str:
        """Return the current mode name."""
        return self._current_option

    @property
    def state(self) -> str | None:
        """Return the entity state."""
        current_option = self._current_option
        if current_option is None or current_option not in self.options:
            return None
        return current_option

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator, get current module mode."""
        if isinstance(self._module, HbtnRouter):
            self._mode = self.hbtnr.mode0
        else:
            self._mode = int(self._module.mode.value)
        if self._mode == 0:
            # should not be the case
            return
        self._value = self._mode & self._mask
        if self._value not in [c.value for c in self._enum]:
            self.hbtnr.logger.warning(f"Could not find {self._value} in mode enum")  # noqa: G004
            return
        self._current_option = self._enum(self._value).name
        self.async_write_ha_state()

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        mode_val = self._enum[option].value
        if isinstance(self._module, HbtnRouter):
            self._mode = (self.hbtnr.mode0 & (0xFF - self._mask)) + mode_val
            await self.hbtnr.comm.async_set_group_mode(self.hbtnr.id, 0, self._mode)
        else:
            self._mode = (int(self._module.mode.value) & (0xFF - self._mask)) + mode_val
            await self._module.comm.async_set_group_mode(
                self._module.mod_addr, self._module.group, self._mode
            )
