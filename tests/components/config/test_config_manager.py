"""Test config manager API."""

import asyncio
from unittest.mock import patch

import pytest

from homeassistant.config_manager import ConfigFlowHandler
from homeassistant.setup import async_setup_component
from homeassistant.components.config import config_manager


@pytest.fixture
def client(hass, test_client):
    """Fixture that can interact with the config manager API."""
    hass.loop.run_until_complete(async_setup_component(hass, 'http', {}))
    hass.loop.run_until_complete(config_manager.async_setup(hass))
    yield hass.loop.run_until_complete(test_client(hass.http.app))


@asyncio.coroutine
def test_initialize_flow(hass, client):
    """Test we can initialize a flow."""
    class TestFlow(ConfigFlowHandler):
        @asyncio.coroutine
        def async_step_init(self, user_input=None):
            return self.async_show_form(
                title='test-title',
                step_id='init')

    with patch('homeassistant.config_manager.HANDLERS.get',
               return_value=TestFlow):
        resp = yield from client.post('/api/config/config_manager/flow/test')

    assert resp.status == 200
    data = yield from resp.json()

    assert data['title'] == 'test-title'
    assert data['step_id'] == 'init'


@asyncio.coroutine
def test_abort(hass, client):
    """Test a flow that aborts."""
    class TestFlow(ConfigFlowHandler):
        @asyncio.coroutine
        def async_step_init(self, user_input=None):
            return self.async_abort(reason='bla')

    with patch('homeassistant.config_manager.HANDLERS.get',
               return_value=TestFlow):
        resp = yield from client.post('/api/config/config_manager/flow/test')

    assert resp.status == 200
    data = yield from resp.json()
    data.pop('flow_id')
    assert data == {
        'reason': 'bla',
        'type': 'abort'
    }


@asyncio.coroutine
def test_create_account(hass, client):
    """Test a flow that creates an account."""
    class TestFlow(ConfigFlowHandler):
        @asyncio.coroutine
        def async_step_init(self, user_input=None):
            return self.async_create_entry(
                title='Test Entry',
                data={'secret': 'account_token'}
            )

    with patch('homeassistant.config_manager.HANDLERS.get',
               return_value=TestFlow):
        resp = yield from client.post('/api/config/config_manager/flow/test')

    assert resp.status == 200
    data = yield from resp.json()
    data.pop('flow_id')
    assert data == {
        'title': 'Test Entry',
        'type': 'create_entry'
    }


@asyncio.coroutine
def test_discovery_not_allowed(hass, client):
    """Test a flow that creates an account."""
    class TestFlow(ConfigFlowHandler):
        @asyncio.coroutine
        def async_step_init(self, user_input=None):
            return self.async_create_entry(
                title='Test Entry',
                data={'secret': 'account_token'}
            )

    with patch('homeassistant.config_manager.HANDLERS.get',
               return_value=TestFlow):
        resp = yield from client.post(
            '/api/config/config_manager/flow/test', json={
                'step_id': 'discovery'
            })

    assert resp.status == 400


@asyncio.coroutine
def test_two_step_flow(hass, client):
    """Test we can finish a two step flow."""
    class TestFlow(ConfigFlowHandler):
        @asyncio.coroutine
        def async_step_init(self, user_input=None):
            return self.async_show_form(
                title='test-title',
                step_id='account')

        @asyncio.coroutine
        def async_step_account(self, user_input=None):
            return self.async_create_entry(
                title=user_input['user_title'],
                data={'secret': 'account_token'}
            )

    with patch('homeassistant.config_manager.HANDLERS.get',
               return_value=TestFlow):
        resp = yield from client.post('/api/config/config_manager/flow/test')
        assert resp.status == 200
        data = yield from resp.json()
        assert data['type'] == 'form'

    with patch('homeassistant.config_manager.HANDLERS.get',
               return_value=TestFlow):
        resp = yield from client.post(
            '/api/config/config_manager/flow/test', json={
                'flow_id': data['flow_id'],
                'step_id': data['step_id'],
                'user_input': {
                    'user_title': 'user-title'
                }
            })
        assert resp.status == 200
        data = yield from resp.json()
        assert data['type'] == 'create_entry'
        assert data['title'] == 'user-title'
