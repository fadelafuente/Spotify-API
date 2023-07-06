import unittest
from SpotifyAPI import SpotifyOAuth
from unittest.mock import patch, MagicMock

def make_mock_response(status_code, return_value):
    mock_response = MagicMock(status_code=status_code, url="https://www.fakeredirect.com/redirect")
    mock_response.json.return_value = return_value
    return mock_response

class TestOAuth(unittest.TestCase):
    GET_DICT = {"id": "fake_id", "name": "fake_name", "type": "album"}
    POST_DICT = {"expires_in": 3600, "access_token": "access_token"}

    @patch('SpotifyAPI.oauth.requests')
    @patch('SpotifyAPI.oauth.SpotifyOAuth.get_redirect_url', MagicMock(return_value="https://fadelafuente.github.io/callback?code=fake_code"))
    def test_request_user_auth(self, mock_requests):
        auth = SpotifyOAuth("clid", "clst", "https://fadelafuente.github.io/")
        mock_requests.get.return_value = make_mock_response(200, None)
        auth.request_user_auth()
        self.assertEqual(auth.scopes, None)
        self.assertEqual(auth.code, "fake_code")

        auth.request_user_auth(scopes=["user-top-read"])
        self.assertEqual(auth.scopes, ["user-top-read"])
        self.assertEqual(auth.code, "fake_code")

    # I seriously do not understand why I can only do it this way instead of the previous way like in 
    # test_client, but what can I do
    @patch('SpotifyAPI.oauth.requests.get')
    @patch('SpotifyAPI.client.requests.post')
    @patch('SpotifyAPI.client.requests.get')
    @patch('SpotifyAPI.oauth.SpotifyOAuth.get_redirect_url', MagicMock(return_value="https://fadelafuente.github.io/callback?code=fake_code"))
    def test_get_playback(self, mock_oauth_get, mock_client_post, mock_client_get):
        auth = SpotifyOAuth("clid", "clst", "https://fadelafuente.github.io/")
        mock_oauth_get.return_value = make_mock_response(200, self.GET_DICT)
        mock_client_post.return_value = make_mock_response(200, self.POST_DICT)
        mock_client_get.return_value = make_mock_response(200, self.GET_DICT)
        response = auth.get_playback()
        self.assertEqual(response, {})
        auth.request_user_auth(scopes=["user-read-playback-state"])
        self.assertEqual(auth.scopes, ["user-read-playback-state"])
        response = auth.get_playback()
        self.assertEqual(response["id"], "fake_id")