from unittest import TestCase
from httpretty import HTTPretty
from cloudcafe.identity.v2_0.extensions_api.client import ExtensionAPI_Client

IDENTITY_ENDPOINT_URL = "http://localhost:35357"


class ExtensionsClientTest(TestCase):
    def setUp(self):
        self.url = IDENTITY_ENDPOINT_URL
        self.serialized_format = "json"
        self.deserialized_format = "json"
        self.auth_token = "AUTH_TOKEN"
        self.keystone_admin = "OS-KSADM"

        self.extensions_api_client = ExtensionAPI_Client(
            url=self.url,
            auth_token=self.auth_token,
            serialized_format=self.serialized_format,
            deserialized_format=self.deserialized_format,
            keystone_admin="OS-KSADM"
        )
        HTTPretty.enable()

    def test_list_extensions(self):
        url = "{0}/v2.0/extensions".format(self.url)
        HTTPretty.register_uri(HTTPretty.GET, url,
                               body=self._build_expected_body_response())

        actual_response = self.extensions_api_client.list_extensions()

        assert HTTPretty.last_request.headers['Content-Type'] == \
            'application/{0}'.format(self.serialized_format)
        assert HTTPretty.last_request.headers['Accept'] == \
            'application/{0}'.format(self.serialized_format)
        assert HTTPretty.last_request.headers['X-Auth-Token'] == \
            self.auth_token

        assert 200 == actual_response.status_code
        assert url == actual_response.url

    def test_list_roles(self):
        url = "{0}/v2.0/{1}/roles".format(self.url, self.keystone_admin)
        HTTPretty.register_uri(HTTPretty.GET, url,
                               body=self._build_expected_roles_response())

        actual_response = self.extensions_api_client.list_roles()

        assert HTTPretty.last_request.headers['Content-Type'] == \
            'application/{0}'.format(self.serialized_format)
        assert HTTPretty.last_request.headers['Accept'] == \
            'application/{0}'.format(self.serialized_format)
        assert HTTPretty.last_request.headers['X-Auth-Token'] == \
            self.auth_token

        assert 200 == actual_response.status_code
        assert url == actual_response.url

    def _build_expected_body_response(self):
        return {"extensions": [{"values": []}]}

    def _build_expected_roles_response(self):
        return {"roles": []}
