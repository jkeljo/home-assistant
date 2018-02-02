"""Http views to control the config manager."""
import asyncio

import voluptuous as vol

from homeassistant import config_manager
from homeassistant.components.http import (
    HomeAssistantView, RequestDataValidator)


# Will upload to PyPi when closer to merging.
REQUIREMENTS = ['https://github.com/balloob/voluptuous-json/archive/master.zip'
                '#voluptuous_json==0.1']


@asyncio.coroutine
def async_setup(hass):
    """Enable the Home Assistant views."""
    hass.http.register_view(ConfigManagerView)
    return True


class ConfigManagerView(HomeAssistantView):
    """View to interact with the config manager."""

    url = '/api/config/config_manager/flow/{domain}'
    name = 'api:config:config_manager:flow'

    @asyncio.coroutine
    @RequestDataValidator(vol.Schema({
        vol.Optional('flow_id'): str,
        vol.Optional('step_id'): str,
        vol.Optional('user_input'): dict,
    }), allow_empty=True)
    def post(self, request, domain, data):
        """Handle a POST request."""
        import voluptuous_json

        hass = request.app['hass']

        if data.get('step_id') in ['discovery']:
            return self.json_message('Invalid step specified', 400)

        try:
            result = yield from hass.config_manager.async_configure(
                domain, **data)
        except config_manager.UnknownHandler:
            return self.json_message('Invalid handler specified', 404)
        except config_manager.UnknownStep:
            return self.json_message('Invalid step specified', 400)

        if result['type'] == config_manager.RESULT_TYPE_FORM:
            schema = result['data_schema']
            if schema is None:
                result['data_schema'] = []
            else:
                result['data_schema'] = voluptuous_json.convert(schema)

        return self.json(result)
