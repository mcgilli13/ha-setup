"""Config flow for ELWA myPV integration."""
# import logging

import json
from json import JSONDecodeError
from typing import Any

import requests
from requests.exceptions import ConnectTimeout, HTTPError
import voluptuous as vol

from homeassistant import config_entries, exceptions
from homeassistant.core import HomeAssistant, callback

from .const import (
    CONF_DEFAULT_INTERVAL,
    CONF_HOSTS,
    CONF_MAX_INTERVAL,
    CONF_MIN_INTERVAL,
    DEV_IP,
    DOMAIN,
    UPDATE_INTERVAL,
)


@callback
def mypv_entries(hass: HomeAssistant):
    """Return the hosts for the domain."""
    try:
        return hass.config_entries.async_entries(DOMAIN)[0].data[CONF_HOSTS]
    except:  # noqa: E722
        return []


class MpvConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """ELWA myPV config flow."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    @staticmethod  # type: ignore  # noqa: PGH003
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return MpvOptionsFlow(config_entry)

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._errors = {}
        self._info = {}

    def _all_hosts_in_configuration_exist(self, ip_list) -> bool:
        """Return True if all hosts found already exist in configuration."""
        return all(ip in mypv_entries(self.hass) for ip in ip_list)

    def _check_host(self, dev_ip: str) -> tuple[bool, list[str]]:
        """Check if connect to myPV device with given ip address works."""

        host_list: list[str] = []
        try:
            response = requests.get(f"http://{dev_ip}/mypv_dev.jsn", timeout=0.5)
            json.loads(response.text)
            host_list.append(dev_ip)
        except (ConnectTimeout, HTTPError, TypeError, JSONDecodeError):
            pass
        return len(host_list) > 0, host_list

    # def _check_hosts(self, min_ip: str, max_ip: str) -> tuple[bool, str]:
    #     """Check if connect to at least one myPV device in given ip range works."""

    #     # host_list = await detect_mypv(min_ip)
    #     host_list = []
    #     base_ip = min_ip.split(".")
    #     lower_ip = int(min_ip.split(".")[-1])
    #     upper_ip = int(max_ip.split(".")[-1])
    #     for ip in range(lower_ip, upper_ip + 1):
    #         ip_str = f"{base_ip[0]}.{base_ip[1]}.{base_ip[2]}.{ip}"
    #         try:
    #             response = requests.get(f"http://{ip_str}/mypv_dev.jsn", timeout=0.5)
    #             json.loads(response.text)
    #             host_list.append(ip_str)
    #         except (ConnectTimeout, HTTPError, TypeError, JSONDecodeError):
    #             pass
    #     return len(host_list) > 0, host_list

    async def async_step_user(self, user_input=None) -> config_entries.ConfigFlowResult:
        """Handle the initial step."""

        if user_input is None:
            default_dev_ip = "192.168.178.100"
            default_interval = CONF_DEFAULT_INTERVAL
        else:
            default_dev_ip = user_input[DEV_IP]
            default_interval = user_input[UPDATE_INTERVAL]

        if user_input is not None:
            # min_ip = user_input[MIN_IP]
            # max_ip = user_input[MAX_IP]
            dev_ip = user_input[DEV_IP]
            update_interval = user_input[UPDATE_INTERVAL]

            if not (isinstance(update_interval, int)):
                self._errors[UPDATE_INTERVAL] = "invalid_interval"

            if update_interval < CONF_MIN_INTERVAL:
                self._errors[UPDATE_INTERVAL] = "interval_too_short"

            if update_interval > CONF_MAX_INTERVAL:
                self._errors[UPDATE_INTERVAL] = "interval_too_long"

            can_connect, ips_found = await self.hass.async_add_executor_job(
                self._check_host,
                dev_ip,  # min_ip, max_ip
            )
            if can_connect and not self._errors:
                if self._all_hosts_in_configuration_exist(ips_found):
                    self._errors[DEV_IP] = "host_exists"
                else:
                    await self.async_set_unique_id(f"mypv_{dev_ip}")
                    return self.async_create_entry(
                        title="myPV",
                        data={
                            # MIN_IP: min_ip,
                            # MAX_IP: max_ip,
                            DEV_IP: dev_ip,
                            UPDATE_INTERVAL: update_interval,
                            CONF_HOSTS: ips_found,
                        },
                    )
            elif not can_connect:
                self._errors[DEV_IP] = "could_not_connect"

        setup_schema = vol.Schema(
            {
                vol.Required(DEV_IP, default=default_dev_ip): str,
                vol.Required(
                    "update_interval",
                    default=default_interval,
                ): int,
                # vol.Required(MIN_IP, default=user_input[MIN_IP]): str,
                # vol.Required(MAX_IP, default=user_input[MAX_IP]): str,
            }
        )

        return self.async_show_form(
            step_id="user", data_schema=setup_schema, errors=self._errors
        )


class MpvOptionsFlow(config_entries.OptionsFlow, MpvConfigFlow):
    """Allow to change options of integration while running."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self._errors = {}
        self._info = {}

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Manage the options."""
        self._errors = {}
        if user_input is None:
            default_dev_ip = self.config_entry.data[DEV_IP]
            default_interval = self.config_entry.data[UPDATE_INTERVAL]
        else:
            default_dev_ip = user_input[DEV_IP]
            default_interval = user_input[UPDATE_INTERVAL]
        opt_schema = vol.Schema(
            {
                vol.Required(DEV_IP, default=default_dev_ip): str,
                vol.Required(
                    "update_interval",
                    default=default_interval,
                ): int,
                # vol.Required(MIN_IP, default=user_input[MIN_IP]): str,
                # vol.Required(MAX_IP, default=user_input[MAX_IP]): str,
            }
        )
        if user_input is not None:
            # min_ip = user_input[MIN_IP]
            # max_ip = user_input[MAX_IP]
            dev_ip = user_input[DEV_IP]
            update_interval = user_input[UPDATE_INTERVAL]

            if not (isinstance(update_interval, int)):
                self._errors[UPDATE_INTERVAL] = "invalid_interval"

            if update_interval < CONF_MIN_INTERVAL:
                self._errors[UPDATE_INTERVAL] = "interval_too_short"

            if update_interval > CONF_MAX_INTERVAL:
                self._errors[UPDATE_INTERVAL] = "interval_too_long"

            can_connect, ips_found = await self.hass.async_add_executor_job(
                self._check_host,
                dev_ip,  # min_ip, max_ip
            )
            conf_data = {
                # MIN_IP: min_ip,
                # MAX_IP: max_ip,
                DEV_IP: dev_ip,
                UPDATE_INTERVAL: update_interval,
                CONF_HOSTS: ips_found,
            }
            if can_connect and not self._errors:
                return self.async_update_reload_and_abort(
                    self.config_entry,
                    data=conf_data,
                    title="myPV",
                    reason="options_updated",
                    reload_even_if_entry_is_unchanged=False,
                )
            if not can_connect:
                self._errors[DEV_IP] = "could_not_connect"

        return self.async_show_form(
            step_id="init", data_schema=opt_schema, errors=self._errors
        )
