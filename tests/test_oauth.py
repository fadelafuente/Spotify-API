import unittest
from SpotifyAPI import SpotifyOAuth
from unittest.mock import patch, MagicMock

required_scopes = ["user-top-read"]

def make_mock_get_response(status_code, return_value):
    mock_response = MagicMock(status_code=status_code, url="https://www.fakeredirect.com/redirect")
    mock_response.json.return_value = return_value
    return mock_response

def make_mock_post_response(status_code, return_value):
    mock_post_response = MagicMock(status_code=status_code)
    mock_post_response.json.return_value = return_value
    return mock_post_response

class TestOAuth(unittest.TestCase):
    GET_DICT = {"id": "fake_id", "name": "fake_name", "type": "album"}
    POST_DICT = {"expires_in": 3600, "access_token": "access_token"}
    auth = SpotifyOAuth("clid", "clst", "https://fadelafuente.github.io/")

    @patch('SpotifyAPI.oauth.requests')
    @patch('SpotifyAPI.oauth.SpotifyOAuth.get_redirect_url', MagicMock(return_value="https://fadelafuente.github.io/callback?code=fake_code"))
    def test_request_user_auth(self, mock_requests):
        mock_requests.get.return_value = make_mock_get_response(200, None)
        self.auth.request_user_auth()
        self.assertEqual(self.auth.scopes, None)
        self.assertEqual(self.auth.code, "fake_code")

        self.auth.request_user_auth(scopes=required_scopes)
        self.assertEqual(self.auth.scopes, required_scopes)
        self.assertEqual(self.auth.code, "fake_code")