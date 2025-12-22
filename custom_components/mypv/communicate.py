"""Provides the myPV DataUpdateCoordinator."""

import asyncio
from datetime import timedelta
import json
import logging
import socket
import time

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import CONF_DEFAULT_INTERVAL, CONF_HOSTS, DOMAIN, UPDATE_INTERVAL
from .mypv_device import MpyDevice

_LOGGER = logging.getLogger(__name__)


def get_own_ip(def_ip):
    """Return string of own ip."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect((def_ip, 80))
    own_ip = s.getsockname()[0]
    s.close()
    return own_ip


async def detect_mypv(ip_str: str) -> list[str]:
    """Detect myPV devices by udp broadcast, return list of ips."""

    timeout_time = 30
    time_out = time.time() + timeout_time
    mypv_detect_port = 16124
    detected_ips = []
    ip_parts = ip_str.split(".")
    udp_ip = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}.255"
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.settimeout(timeout_time)

    sock.sendto(b"<broadcast>", (udp_ip, mypv_detect_port))

    while time.time() < time_out:
        try:
            data, addr = sock.recvfrom(1024)
            detected_ips.append(addr)
            await asyncio.sleep(0.02)
        except TimeoutError:
            pass

    return detected_ips


class MypvCommunicator(DataUpdateCoordinator):
    """Class to perform all myPV communications."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize data updater."""
        self.config_entry = entry
        self.hosts = entry.data[CONF_HOSTS]
        self._info = None
        self._setup = None
        self._next_update = 0
        # For systems before v1.0.0
        if UPDATE_INTERVAL not in entry.data:
            data = dict(entry.data)
            data[UPDATE_INTERVAL] = CONF_DEFAULT_INTERVAL
            hass.config_entries.async_update_entry(entry, data=data)
        update_interval = timedelta(seconds=entry.data[UPDATE_INTERVAL])
        self.logger = _LOGGER
        self.devices = []
        self.hass = hass
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            config_entry=entry,
            update_interval=update_interval,
        )

    async def initialize(self):
        """Do the async stuff."""

        # detected_ips = await detect_mypv(self.hosts[0])
        for ip_str in self.hosts:
            try:
                info_data = await self.check_ip(ip_str)
                if info_data:
                    self.devices.append(MpyDevice(self, ip_str, info_data))
                    await self.devices[-1].initialize()

            except Exception as err_msg:  # noqa: BLE001
                self.logger.info(f"Error searching for ELWA devices: {err_msg}")  # noqa: G004

    async def _async_update_data(self) -> None:
        """Update status of all ELWA devices."""

        for mpv_dev in self.devices:
            await mpv_dev.update()

    async def do_get_request(self, url: str) -> str:
        """Perform asyncio get request."""
        timeout = aiohttp.ClientTimeout(total=5)
        async with (
            aiohttp.ClientSession(timeout=timeout) as session,
            session.get(url) as resp,
        ):
            return await resp.text()

    async def check_ip(self, ip):
        """Update inverter info."""
        try:
            url = f"http://{ip}/mypv_dev.jsn"
            response_text = await self.do_get_request(url)
            return json.loads(response_text)
        except Exception:  # noqa: BLE001
            return False

    async def info_update(self, device):
        """Update inverter info."""
        try:
            url = f"http://{device.ip}/mypv_dev.jsn"
            response_text = await self.do_get_request(url)
            return json.loads(response_text)
        except Exception:  # noqa: BLE001
            return False

    async def data_update(self, device):
        """Update inverter data info."""
        try:
            url = f"http://{device.ip}/data.jsn"
            response_text = await self.do_get_request(url)
            return json.loads(response_text)
        except Exception as err_msg:  # noqa: BLE001
            self.logger.info(f"Error during data update: {err_msg}")  # noqa: G004
            return False

    async def setup_update(self, device):
        """Update inverter setup info."""
        try:
            url = f"http://{device.ip}/setup.jsn"
            response_text = await self.do_get_request(url)
            return json.loads(response_text)
        except Exception as err_msg:  # noqa: BLE001
            self.logger.info(f"Error during setup update: {err_msg}")  # noqa: G004
            return False

    async def state_update(self, device):
        """Update control state."""
        if device.control_enabled:
            try:
                url = f"http://{device.ip}/control.html?"
                response_text = await self.do_get_request(url)
                self.get_state_dict(response_text, device)
            except Exception as err_msg:  # noqa: BLE001
                self.logger.warning(f"Error during control update: {err_msg}")  # noqa: G004
                device.control_enabled = False
                return False
            else:
                return True
        return False

    async def set_number(self, device, key, act_val: int):
        """Set heating temperature."""
        try:
            url = f"http://{device.ip}/setup.jsn?{key}={act_val}"
            response_text = await self.do_get_request(url)
            self.get_state_dict(response_text, device)
            return True  # noqa: TRY300
        except Exception as err_msg:  # noqa: BLE001
            self.logger.warning(f"Error during set power command: {err_msg}")  # noqa: G004
            return False

    async def set_power(self, device, act_pow: int):
        """Set heater power."""
        try:
            url = f"http://{device.ip}/control.html?power={act_pow}"
            response_text = await self.do_get_request(url)
            self.get_state_dict(response_text, device)
            return True  # noqa: TRY300
        except Exception as err_msg:  # noqa: BLE001
            self.logger.warning(f"Error during set power command: {err_msg}")  # noqa: G004
            return False

    async def set_control_mode(self, device, act_mode: int):
        """Set power control mode, e.g. html."""
        try:
            url = f"http://{device.ip}/setup.jsn?ctrl={act_mode}"
            response_text = await self.do_get_request(url)  # noqa: F841
            # self.get_state_dict(response_text, device)
            return True  # noqa: TRY300
        except Exception as err_msg:  # noqa: BLE001
            self.logger.warning(f"Error during set control mode command: {err_msg}")  # noqa: G004
            return False

    async def set_pid_power(self, device, act_pow: int):
        """Set heater power with local pid control."""
        try:
            url = f"http://{device.ip}/control.html?pid_power={act_pow}"
            response_text = await self.do_get_request(url)
            self.get_state_dict(response_text, device)
        except Exception as err_msg:  # noqa: BLE001
            self.logger.warning(f"Error during set pid power command: {err_msg}")  # noqa: G004
            return False
        else:
            return True

    async def switch(self, device, key, state: bool):
        """Set heater power with local pid control."""
        try:
            url = f"http://{device.ip}/setup.jsn?{key}={int(state)}"
            response_text = await self.do_get_request(url)
            self.get_state_dict(response_text, device)
        except Exception as err_msg:  # noqa: BLE001
            self.logger.warning(f"Error during boost command: {err_msg}")  # noqa: G004
            return False
        else:
            return True

    async def activate_boost(self, device, mode: int = 1):
        """Set heater power with local pid control."""
        try:
            url = f"http://{device.ip}/data.jsn?bststrt={mode}"
            await self.do_get_request(url)
        except Exception as err_msg:  # noqa: BLE001
            self.logger.warning(f"Error during boost command: {err_msg}")  # noqa: G004
            return False
        else:
            return True

    def get_state_dict(self, text: str, device) -> None:
        """Convert lines to state dict."""

        text = text.replace("\r\n", "<br>").replace("\n", "<br>")
        resp_lines = text.split("<br>")
        for line in resp_lines:
            if len(line) > 4 and not line.startswith("<"):
                parts = line.split("=")
                if len(parts) >= 2:
                    device.state_dict[parts[0]] = parts[1].split()[0].replace(",", "")
