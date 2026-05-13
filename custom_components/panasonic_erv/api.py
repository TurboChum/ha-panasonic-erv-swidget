"""PANasonic ERV API client."""

class PanasonicERVApi:
    """Simple wrapper for Panasonic ERV HTTP calls."""

    def __init__(self, session, device_url):
        self._session = session
        self._device_url = device_url

    async def async_get_state(self):
        return await self._session.get_json(f"{self._device_url}/api/v1/state")

    async def async_set_mode(self, mode):
        payload = {"host": {"components": {"0": {"mode": mode}}}}
        await self._session.async_post_json(f"{self._device_url}/api/v1/command", payload)

    async def async_set_power(self, power_on):
        state = "on" if power_on else "off"
        payload = {"host": {"components": {"0": {"toggle": {"state": state}}}}}
        await self._session.async_post_json(f"{self._device_url}/api/v1/command", payload)
