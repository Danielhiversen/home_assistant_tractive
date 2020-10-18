"""Support for Tractive location sharing."""
import asyncio
import json
import logging
from datetime import datetime, timedelta

import aiohttp
import async_timeout
import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.components.device_tracker import PLATFORM_SCHEMA
from homeassistant.const import (
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
    CONF_PASSWORD,
)
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.typing import ConfigType

_LOGGER = logging.getLogger(__name__)

API_URL = "https://graph.tractive.com/3"

CONF_MAX_GPS_ACCURACY = "max_gps_accuracy"


PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_USERNAME): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
        vol.Optional(CONF_MAX_GPS_ACCURACY, default=100000): vol.Coerce(float),
    }
)


async def async_setup_scanner(hass, config: ConfigType, async_see, discovery_info=None):
    """Set up the Google Maps Location sharing scanner."""
    scanner = TractiveScanner(hass, config, async_see)
    return await scanner.async_init()


class TractiveScanner:
    """Representation of a Tractive scanner."""

    def __init__(self, hass, config: ConfigType, async_see) -> None:
        """Initialize the scanner."""
        self.async_see = async_see
        self.hass = hass
        self._session = async_get_clientsession(hass)
        self._username = config[CONF_USERNAME]
        self._password = config[CONF_PASSWORD]
        self.max_gps_accuracy = config[CONF_MAX_GPS_ACCURACY]
        self.scan_interval = config.get(CONF_SCAN_INTERVAL) or timedelta(seconds=120)

        self._user_credentials = None
        self._tracker_ids = []
        self._timeout = 10

    async def async_init(self):
        """Further initialize connection to Tractive."""

        if not await self.get_user_credentials():
            return False

        await self._async_update()
        async_track_time_interval(self.hass, self._async_update, self.scan_interval)
        return True

    async def get_user_credentials(self):
        """Get user credentials."""
        headers = {
            "x-tractive-client": "5728aa1fc9077f7c32000186",
            "content-type": "application/json;charset=UTF-8",
            "accept": "application/json, text/plain, */*",
        }

        try:
            with async_timeout.timeout(self._timeout):
                resp = await self._session.post(
                    f"{API_URL}/auth/token",
                    data=json.dumps(
                        {
                            "platform_email": self._username,
                            "platform_token": self._password,
                            "grant_type": "tractive",
                        }
                    ),
                    headers=headers,
                )
            if resp.status != 200:
                _LOGGER.error(
                    "Error getting token from Tractive, resp code: %s %s",
                    resp.status,
                    resp.reason,
                )
                return False
            result = await resp.json()
            self._user_credentials = result
        except aiohttp.ClientError as err:
            _LOGGER.error("Error connecting to Tractives: %s ", err, exc_info=True)
            raise
        except asyncio.TimeoutError:
            return False

        headers = {
            "x-tractive-client": "5728aa1fc9077f7c32000186",
            "content-type": "application/json;charset=UTF-8",
            "accept": "application/json, text/plain, */*",
            "x-tractive-user": self._user_credentials["user_id"],
            "authorization": f"Bearer {self._user_credentials['access_token']}",
        }

        try:
            with async_timeout.timeout(self._timeout):
                resp = await self._session.get(
                    f"{API_URL}/user/{self._user_credentials['user_id']}/trackers",
                    headers=headers,
                )
            if resp.status != 200:
                _LOGGER.error("Error connecting to Tractive, resp code: %s", resp)
                return False
            result = await resp.json()
            for tracker in result:
                self._tracker_ids.append(tracker["_id"])

        except aiohttp.ClientError as err:
            _LOGGER.error("Error connecting to Tractives: %s ", err, exc_info=True)
            raise
        except asyncio.TimeoutError:
            return False
        return True

    async def _fetch_tracker_data(self, tracker_id):
        headers = {
            "x-tractive-client": "5728aa1fc9077f7c32000186",
            "content-type": "application/json;charset=UTF-8",
            "accept": "application/json, text/plain, */*",
            "x-tractive-user": self._user_credentials["user_id"],
            "authorization": f"Bearer {self._user_credentials['access_token']}",
        }
        hw_report = []
        try:
            with async_timeout.timeout(self._timeout):
                resp = await self._session.get(
                    f"{API_URL}/device_hw_report/{tracker_id}/", headers=headers
                )
            if resp.status != 200:
                _LOGGER.error(
                    "Error connecting to Tractive, resp code: %s %s",
                    resp.status,
                    resp.reason,
                )
            else:
                hw_report = await resp.json()
        except aiohttp.ClientError as err:
            _LOGGER.error("Error connecting to Tractives: %s ", err, exc_info=True)
            raise
        except asyncio.TimeoutError:
            pass

        now = datetime.timestamp(datetime.now())
        time_from = now - 3600 * 6

        try:
            with async_timeout.timeout(self._timeout):
                resp = await self._session.get(
                    f"{API_URL}/tracker/{tracker_id}//positions?"
                    f"time_from={time_from}&"
                    f"time_to={now}&"
                    f"format=json_segments",
                    headers=headers,
                )
            if resp.status != 200:
                _LOGGER.error(
                    "Error connecting to Tractive, resp code: %s %s",
                    resp.status,
                    resp.reason,
                )
                return [], None
            result = await resp.json()
        except aiohttp.ClientError as err:
            _LOGGER.error("Error connecting to Tractives: %s ", err, exc_info=True)
            raise
        except asyncio.TimeoutError:
            return []
        return hw_report, result

    async def _async_update(self, now=None):
        for tracker_id in self._tracker_ids:
            _LOGGER.debug("Updating %s", tracker_id)
            hw_report, result = await self._fetch_tracker_data(tracker_id)
            if not result:
                await self.get_user_credentials()
                hw_report, result = await self._fetch_tracker_data(tracker_id)
                if not result:
                    _LOGGER.error("No data")
                    return

            points = result[0]
            if not points:
                _LOGGER.error("No points")
                continue
            _LOGGER.debug("points %s", points)
            point = points[-1]
            if point["pos_uncertainty"] > self.max_gps_accuracy:
                _LOGGER.warning("High uncertainty, %s", point["pos_uncertainty"])
                continue

            latitude, longitude = point.pop("latlong")
            battery = hw_report.get("battery_level")
            hw_report.pop("_id")
            hw_report.pop("_type")
            hw_report.pop("report_id")
            hw_report.pop("time")
            point.update(hw_report)
            point['time'] = datetime.fromtimestamp(point['time'])
            _LOGGER.debug("point data %s (%s, %s)", point, latitude, longitude)
            await self.async_see(
                dev_id=tracker_id,
                source_type=point.pop("sensor_used"),
                gps=(latitude, longitude),
                icon="mdi:cat",
                battery=battery,
                attributes=point,
            )
