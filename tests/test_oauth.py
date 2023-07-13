import base64
import unittest
from SpotifyAPI import SpotifyOAuth
from unittest.mock import patch, MagicMock
import io
from PIL import Image

unittest.TestLoader.sortTestMethodsUsing = None

GET_DICT = {"id": "fake_id", "name": "fake_name", "type": "album"}
POST_DICT = {"expires_in": 3600, "access_token": "access_token"}

def make_mock_response(status_code, return_value):
    mock_response = MagicMock(status_code=status_code, url="https://www.fakeredirect.com/redirect")
    mock_response.json.return_value = return_value
    return mock_response

def mocked_request(*args, **kwargs):
    if "data" in kwargs:
        return make_mock_response(200, POST_DICT)
    return make_mock_response(200, GET_DICT)

class TestOAuth(unittest.TestCase):
    auth = SpotifyOAuth("clid", "clst", "https://fadelafuente.github.io/")

    @patch('SpotifyAPI.oauth.requests')
    @patch('SpotifyAPI.oauth.SpotifyOAuth.get_redirect_url', MagicMock(return_value="https://fadelafuente.github.io/callback?code=fake_code"))
    def test_00_request_user_auth(self, mock_requests):
        mock_requests.get.return_value = make_mock_response(200, None)
        self.auth.request_user_auth(scopes=None)
        self.assertEqual(self.auth.scopes, None)
        self.assertEqual(self.auth.code, "fake_code")

        self.auth.request_user_auth(scopes=["user-top-read"])
        self.assertEqual(self.auth.scopes, ["user-top-read"])
        self.assertEqual(self.auth.code, "fake_code")

    # I seriously do not understand why I can only do it this way instead of the previous way like in 
    # test_client, but what can I do
    @patch('SpotifyAPI.oauth.requests')
    @patch('SpotifyAPI.client.requests.post', MagicMock(side_effect=mocked_request))
    @patch('SpotifyAPI.oauth.SpotifyOAuth.get_redirect_url', MagicMock(return_value="https://fadelafuente.github.io/callback?code=fake_code"))
    def test_01_get_playback(self, mock_oauth_get):
        mock_oauth_get.get.return_value = make_mock_response(200, GET_DICT)
        response = self.auth.get_playback()
        self.assertEqual(response, {})
        self.auth.request_user_auth(scopes=SpotifyOAuth.available_scopes)
        self.assertEqual(self.auth.scopes, SpotifyOAuth.available_scopes)
        response = self.auth.get_playback()
        self.assertEqual(response["id"], "fake_id")

    @patch('SpotifyAPI.oauth.requests.put')
    @patch('SpotifyAPI.client.requests.post', MagicMock(side_effect=mocked_request))
    @patch('SpotifyAPI.oauth.SpotifyOAuth.get_redirect_url', MagicMock(return_value="https://fadelafuente.github.io/callback?code=fake_code"))
    def test_02_transfer_playback(self, mock_oauth_get):
        mock_oauth_get.return_value = make_mock_response(200, None)
        with self.assertRaises(Exception) as context:
            response = self.auth.transfer_playback(["fake_id1", "fake_id2"])
        self.assertTrue("More than one device id was submitted. Please submit only 1 device id." in str(context.exception))
        response = self.auth.transfer_playback(["fake_id"])
        self.assertTrue(response)
        response = self.auth.transfer_playback("fake_id")
        self.assertTrue(response)

    @patch('SpotifyAPI.oauth.requests.put')
    @patch('SpotifyAPI.client.requests.post', MagicMock(side_effect=mocked_request))
    @patch('SpotifyAPI.oauth.SpotifyOAuth.get_redirect_url', MagicMock(return_value="https://fadelafuente.github.io/callback?code=fake_code"))
    def test_03_set_repeat_mode(self, mock_oauth_get):
        mock_oauth_get.return_value = make_mock_response(200, None)
        with self.assertRaises(Exception) as context:
            response = self.auth.set_repeat_mode("fake_state")
        self.assertTrue("Invalid state. Refer to the Spotify API Documentation for valid states: "
                            "https://developer.spotify.com/documentation/web-api/reference/set-repeat-mode-on-users-playback" in str(context.exception))
        response = self.auth.set_repeat_mode("track")
        self.assertTrue(response)
        response = self.auth.set_repeat_mode("context")
        self.assertTrue(response)

    @patch('SpotifyAPI.oauth.requests.post')
    @patch('SpotifyAPI.client.requests.post', MagicMock(side_effect=mocked_request))
    @patch('SpotifyAPI.oauth.SpotifyOAuth.get_redirect_url', MagicMock(return_value="https://fadelafuente.github.io/callback?code=fake_code"))
    def test_04_add_item_to_queue(self, mock_oauth_get):
        mock_oauth_get.return_value = make_mock_response(200, None)
        with self.assertRaises(Exception) as context:
            response = self.auth.add_item_to_queue("spotify:album:abcde1234")
        self.assertTrue("Invalid URI. Please submit either a track or episode URI." in str(context.exception))
        response = self.auth.add_item_to_queue("spotify:track:abcde1234")
        self.assertTrue(response)
        response = self.auth.add_item_to_queue("spotify:episode:abcde1234")
        self.assertTrue(response)
    
    @patch('SpotifyAPI.oauth.requests.get')
    @patch('SpotifyAPI.client.requests.post', MagicMock(side_effect=mocked_request))
    @patch('SpotifyAPI.oauth.SpotifyOAuth.get_redirect_url', MagicMock(return_value="https://fadelafuente.github.io/callback?code=fake_code"))
    def test_05_get_recently_played_tracks(self, mock_oauth_get):
        mock_oauth_get.return_value = make_mock_response(200, GET_DICT)
        with self.assertRaises(Exception) as context:
            response = self.auth.get_recently_played_tracks(after="after", before="before")
        self.assertTrue("If after is specified, before must not be specified, and vice versa." in str(context.exception))
        response = self.auth.get_recently_played_tracks(before="before")
        self.assertEqual(response["id"], "fake_id")
        response = self.auth.get_recently_played_tracks(after="after")
        self.assertEqual(response["id"], "fake_id")

    @patch('SpotifyAPI.oauth.requests.put')
    @patch('SpotifyAPI.client.requests.post', MagicMock(side_effect=mocked_request))
    @patch('SpotifyAPI.oauth.SpotifyOAuth.get_redirect_url', MagicMock(return_value="https://fadelafuente.github.io/callback?code=fake_code"))
    def test_06_add_cover_image(self, mock_oauth_get):
        mock_oauth_get.return_value = make_mock_response(200, None)

        with open('tests/image2.png', "rb") as image:
            image_data = base64.b64encode(image.read())     
        with self.assertRaises(ValueError) as context:
            response = self.auth.add_cover_image("fake_playlist", image_data)
        self.assertTrue("Image is not a JPEG image." in str(context.exception))

        with open('tests/image.jpg', "rb") as image:
            image_data = base64.b64encode(image.read())  
        response = self.auth.add_cover_image("fake_playlist", image_data)
        self.assertTrue(response)

    @patch('SpotifyAPI.oauth.requests.get')
    @patch('SpotifyAPI.client.requests.post', MagicMock(side_effect=mocked_request))
    @patch('SpotifyAPI.oauth.SpotifyOAuth.get_redirect_url', MagicMock(return_value="https://fadelafuente.github.io/callback?code=fake_code"))
    def test_07_get_top_items(self, mock_oauth_get):
        mock_oauth_get.return_value = make_mock_response(200, GET_DICT)
        with self.assertRaises(Exception) as context:
            response = self.auth.get_top_items("fake_type")
        self.assertTrue("Invalid type. Valid values are 'artists' or 'tracks'" in str(context.exception))
        response = self.auth.get_top_items("artists")
        self.assertEqual(response["id"], "fake_id")

    @patch('SpotifyAPI.oauth.requests.delete')
    @patch('SpotifyAPI.client.requests.post', MagicMock(side_effect=mocked_request))
    @patch('SpotifyAPI.oauth.SpotifyOAuth.get_redirect_url', MagicMock(return_value="https://fadelafuente.github.io/callback?code=fake_code"))
    def test_08_unfollow_artists_or_users(self, mock_oauth_get):
        mock_oauth_get.return_value = make_mock_response(200, None)
        with self.assertRaises(Exception) as context:
            response = self.auth.unfollow_artists_or_users("track", ["id1", "id2", "id3"])
        self.assertTrue("Invalid type. Valid values are 'artist' or 'user'" in str(context.exception))
        response = self.auth.unfollow_artists_or_users("artist", ["id1", "id2", "id3"])
        self.assertTrue(response)

    def test_09_validate_scopes(self):
        with self.assertRaises(Exception) as context:
            self.auth.validate_scopes("fake_scope")
        with self.assertRaises(Exception) as context:
            self.auth.validate_scopes(["ugc-image-upload",
                        "user-read-playback-state",
                        "playlist-read-private",
                        "fake_scope"])
