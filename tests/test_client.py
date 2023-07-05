import unittest
from SpotifyAPI import SpotifyClient
from unittest.mock import patch, MagicMock

def make_mock_get_response(status_code, return_value):
    mock_response = MagicMock(status_code=status_code)
    mock_response.json.return_value = return_value
    return mock_response

def make_mock_post_response(status_code, return_value):
    mock_post_response = MagicMock(status_code=status_code)
    mock_post_response.json.return_value = return_value
    return mock_post_response

class TestClient(unittest.TestCase):
    GET_DICT = {"id": "fake_id", "name": "fake_name", "type": "album"}
    POST_DICT = {"expires_in": 3600, "access_token": "access_token"}
    client = SpotifyClient("clid", "clst")

    @patch('SpotifyAPI.client.requests')
    def test_get_response(self, mock_requests):
        mock_requests.get.return_value = make_mock_get_response(200, self.GET_DICT)
        mock_requests.post.return_value = make_mock_post_response(200, self.POST_DICT)
        response = self.client.get_response(id="fake_id")
        self.assertEqual(response["id"], "fake_id")
        self.assertEqual(self.client.access_token, "access_token")
        self.assertNotEqual(self.client.access_token_expires, None)


    @patch('SpotifyAPI.client.requests')
    def test_search_pass(self, mock_requests):
        return_dict = {"track": self.GET_DICT}
        mock_requests.get.return_value = make_mock_get_response(200, return_dict)
        mock_requests.post.return_value = make_mock_post_response(200, self.POST_DICT)
        response = self.client.search({"track": "Doxy", "artist": "Miles Davis"})
        self.assertEqual(len(response), 1)

    @patch('SpotifyAPI.client.requests')
    def test_get_album(self, mock_requests):
        mock_requests.get.return_value = make_mock_get_response(200, self.GET_DICT)
        mock_requests.post.return_value = make_mock_post_response(200, self.POST_DICT)
        response = self.client.get_album("fake_id")
        self.assertEqual(response["id"], "fake_id")

    @patch('SpotifyAPI.client.requests')
    def test_get_tracks_audio_features(self, mock_requests):
        return_dict = self.GET_DICT
        mock_requests.get.return_value = make_mock_get_response(200, return_dict)
        mock_requests.post.return_value = make_mock_post_response(200, self.POST_DICT)

        response = self.client.get_tracks_audio_features("fake_id1")
        self.assertEqual(response["id"], "fake_id")

        return_dict["id"] = ["fake_id1", "fake_id2"]
        response = self.client.get_tracks_audio_features("fake_id1")
        self.assertEqual(response["id"], ["fake_id1", "fake_id2"])
        
        with self.assertRaises(Exception) as context:
            self.client.get_tracks_audio_features("fake_id1,fake_id2")
        self.assertTrue("Pass as a list when using more than one track id." in str(context.exception))

    @patch('SpotifyAPI.client.requests')
    @patch('SpotifyAPI.client.SpotifyClient.get_genre_seeds')
    def test_get_recommendations(self, mock_requests, mock_genre_seeds):
        mock_requests.get.return_value = make_mock_get_response(200, self.GET_DICT)
        mock_requests.post.return_value = make_mock_post_response(200, self.POST_DICT)
        mock_genre_seeds.return_value = ["acoustic", "afrobeat", "alt-rock", "alternative", "ambient"]

        with self.assertRaises(Exception) as context:
            self.client.get_recommendations()
        
        message = "Please pass in any combination of seed_artists, seed_genres, and seed_tracks."
        self.assertTrue(message in str(context.exception))

        with self.assertRaises(Exception) as context:
            self.client.get_recommendations(seed_genres=[1, 2, 3, 4, 5, 6])
        message = "Up to 5 seed values may be provided in any combination of seed_artists, seed_tracks and seed_genres."
        self.assertTrue(message in str(context.exception))

        with self.assertRaises(Exception) as context:
            self.client.get_recommendations(seed_genres=["fake_genre", "acoustic", "afrobeat"])
        message = "One or more genres are not available, check available genre seeds with the get_genre_seeds() method."
        self.assertTrue(message in str(context.exception))

    def test_check_recommendations_kwargs(self):
        response = self.client.check_recommendations_kwargs(key="value", min_radius=5, min_danceability=0.8)
        self.assertEqual(response, {"min_danceability": 0.8})

    def test_check_additional_types(self):
        response = self.client.check_additional_types(["track", "album"])
        self.assertEqual(response, None)

        response = self.client.check_additional_types(["track", "episode"])
        self.assertEqual(response, "track,episode")

    def test_create_query(self):
        response = self.client.create_query(additional_types=None, market=None)
        self.assertEqual(response, None)

        response = self.client.create_query(additional_types=["track", "album"], limit=55, offset=-55, market=None)
        self.assertTrue(isinstance(response, str))
        self.assertTrue("market" not in response)
        self.assertTrue("track%2Calbum" not in response)
        self.assertTrue(str(self.client.max_limit) in response)
        self.assertTrue(str(55) not in response)
        self.assertTrue("offset=" + str(self.client.min_offset) in response)