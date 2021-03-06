"""Support for a Genius Hub system."""
from datetime import timedelta
import logging

import aiohttp
import voluptuous as vol

from geniushubclient import GeniusHubClient

from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_TOKEN, CONF_USERNAME
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.discovery import async_load_platform
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_track_time_interval

_LOGGER = logging.getLogger(__name__)

DOMAIN = "geniushub"

SCAN_INTERVAL = timedelta(seconds=60)

_V1_API_SCHEMA = vol.Schema({vol.Required(CONF_TOKEN): cv.string})
_V3_API_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): cv.string,
        vol.Required(CONF_USERNAME): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
    }
)
CONFIG_SCHEMA = vol.Schema(
    {DOMAIN: vol.Any(_V3_API_SCHEMA, _V1_API_SCHEMA)}, extra=vol.ALLOW_EXTRA
)


async def async_setup(hass, hass_config):
    """Create a Genius Hub system."""
    kwargs = dict(hass_config[DOMAIN])
    if CONF_HOST in kwargs:
        args = (kwargs.pop(CONF_HOST),)
    else:
        args = (kwargs.pop(CONF_TOKEN),)

    hass.data[DOMAIN] = {}
    broker = GeniusBroker(hass, args, kwargs)

    try:
        await broker._client.hub.update()  # pylint: disable=protected-access
    except aiohttp.ClientResponseError as err:
        _LOGGER.error("Setup failed, check your configuration, %s", err)
        return False
    broker.make_debug_log_entries()

    async_track_time_interval(hass, broker.async_update, SCAN_INTERVAL)

    for platform in ["climate", "water_heater"]:
        hass.async_create_task(
            async_load_platform(hass, platform, DOMAIN, {}, hass_config)
        )

    if broker._client.api_version == 3:  # pylint: disable=protected-access
        for platform in ["sensor", "binary_sensor"]:
            hass.async_create_task(
                async_load_platform(hass, platform, DOMAIN, {}, hass_config)
            )

    return True


class GeniusBroker:
    """Container for geniushub client and data."""

    def __init__(self, hass, args, kwargs):
        """Initialize the geniushub client."""
        self._hass = hass
        self._client = hass.data[DOMAIN]["client"] = GeniusHubClient(
            *args, **kwargs, session=async_get_clientsession(hass)
        )

    async def async_update(self, now, **kwargs):
        """Update the geniushub client's data."""
        try:
            await self._client.hub.update()
        except aiohttp.ClientResponseError as err:
            _LOGGER.warning("Update failed, %s", err)
            return
        self.make_debug_log_entries()

        async_dispatcher_send(self._hass, DOMAIN)

    def make_debug_log_entries(self):
        """Make any useful debug log entries."""
        # pylint: disable=protected-access
        _LOGGER.debug(
            "Raw JSON: \n\nhub._raw_zones = %s \n\nhub._raw_devices = %s",
            self._client.hub._raw_zones,
            self._client.hub._raw_devices,
        )
