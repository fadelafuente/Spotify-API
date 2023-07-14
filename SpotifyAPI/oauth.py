
__all__ = ["SpotifyOAuth", "SpotifyPKCE"]

import base64
import requests
import json
import io
import math
import random
from hashlib import sha256
from PIL import Image
from urllib.parse import urlencode, urlparse, parse_qs
from client import SpotifyClient

'''
Authentication Code Flow 

Reference: https://developer.spotify.com/documentation/web-api/tutorials/code-flow
'''   
class SpotifyOAuth(SpotifyClient):
    redirect_uri = None
    code = None
    state = None
    scopes = None
    refresh_token = None
    default_limit = 20
    min_limit = 0
    max_limit = 50
    default_offset = 0
    min_offset = 0
    max_offset = 1000
    available_scopes = ["ugc-image-upload",
                        "user-read-playback-state",
                        "user-modify-playback-state",
                        "user-read-currently-playing",
                        "playlist-read-private",
                        "playlist-modify-private",
                        "playlist-modify-public",
                        "user-follow-modify",
                        "user-follow-read",
                        "user-read-playback-position",
                        "user-top-read",
                        "user-read-recently-played",
                        "user-library-modify",
                        "user-library-read",
                        "user-read-email",
                        "user-read-private"]

    def __init__(self, client_id, client_secret, redirect_uri, scopes=None, *args, **kwargs):
        super().__init__(client_id, client_secret, *args, **kwargs)
        self.redirect_uri = redirect_uri
        if scopes != None:
            self.request_user_auth(scopes=scopes)

    def get_code_data(self, scope, state, show_dialog):
        data = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "show_dialog": show_dialog
        }

        if scope != None:
            scope = self.convert_list_to_str(" ", scope)
            data["scope"] = scope
        if state != None:
            data["state"] = state
        
        return data
    
    def validate_scopes(self, scopes):
        if scopes == None:
            return True
        if not isinstance(scopes, list):
            raise Exception("Unsupported scopes type, please provide a list of scopes")
        if not all(s in self.available_scopes for s in scopes):
            raise Exception("One of the scopes provided is invalid, "
                            "please refer to the Spotify API documentation: " 
                            "https://developer.spotify.com/documentation/web-api/concepts/scopes")
        self.scopes = scopes
        return True
    
    def has_required_scopes(self, required_scopes):
        scopes = self.scopes
        if scopes == None:
            return False
        if len(scopes) < len(required_scopes):
            return False
        if all(s in scopes for s in required_scopes):
            return True
        return False
    
    def get_redirect_url(self, url):
        print(f"Follow this url: {url}")
        print("input the redirected url: ")
        redirected_url = input()
        return redirected_url
    
    def request_user_auth(self, scopes:list=None, state:str=None, show_dialog:bool=False):
        if self.validate_scopes(scopes=scopes):
            data = self.get_code_data(scopes, state, show_dialog)
        data = urlencode(data)

        response = requests.get("https://accounts.spotify.com/authorize?" + data)
        if response.status_code not in range(200, 299):
            raise Exception(f"Authorization failed, could not redirect.")
        url = response.url
        redirected_url = self.get_redirect_url(url)

        parsed_query = self.parse_url_query(redirected_url)
        if "error" in parsed_query:
            error = parsed_query["error"]
            raise Exception(f"Authorization failed, {error}")
        if "code" not in parsed_query:
            raise Exception("Authorization failed, the authorization code is missing")
        
        # code is returned as a list, so access the first index to get the code string
        self.code = parsed_query["code"][0]
        if "state" in parsed_query:
            self.state = parsed_query["state"]
        return True
    
    def get_token_data(self):
        return {"grant_type": "authorization_code",
                "code": self.code,
                "redirect_uri": self.redirect_uri}
    
    def get_refresh_data(self):
        return {"grant_type": "refresh_token",
                "refresh_token": self.refresh_token}
    
    def refresh_access_token(self):
        data = self.get_refresh_data()
        self.request_access_token(token_data=data)

    def request_access_token(self, token_data):
        data = super().request_access_token(token_data)
        if isinstance(data, dict) and "refresh_token" in data:
            self.refresh_token = data["refresh_token"]
        return True
    
    def get_response(self, id, resource_type="albums", version="v1", query=None, request_type="GET", required_scopes=[], data=None):
        if not self.has_required_scopes(required_scopes=required_scopes):
            return {}
        endpoint = self.build_endpoint(id, resource_type, version, query)

        headers = self.get_access_headers()
        if request_type == "PUT":
            response = requests.put(endpoint, headers=headers, data=data)
            return True
        elif request_type == "DELETE":
            response = requests.delete(endpoint, headers=headers, data=data)
            return True
        elif request_type == "POST":
            response = requests.post(endpoint, headers=headers, data=data)
            return True
        else:
            response = requests.get(endpoint, headers=headers, data=data)
 
        return response.json()
    
    def check_uris(self, uris):
        if len(uris) > 100:
            raise Exception("Maximum number of URIs exceeded. Please limit to 100 URIs per request.")
        if not all("spotify:track:" in uri or "spotify:episode:" in uri for uri in uris):
            raise Exception("One or more URI is invalid, only submit a track or episode URI. "
                            "Examples: spotify:track:1301WleyT98MSxVHPZCA6M, spotify:episode:512ojhOuo1ktJprKbVcKyQ")
        return
    
    def create_json_body(self, **kwargs):
        data = {}
        for key, value in kwargs.items():
            if value != None:
                data[key] = value
        if data == {}:
             return None
        return json.dumps(data)
    
    def create_list_of_objects(self, uris):
        # create an array of objects/uris
        # example: 
        # { 
        #   "tracks": [
        #       { "uri": "spotify:track:4iV5W9uYEdYUVa79Axb7Rh" },
        #       { "uri": "spotify:track:1301WleyT98MSxVHPZCA6M" }
        #   ] 
        # }
        #
        # Reference: https://developer.spotify.com/documentation/web-api/reference/remove-tracks-playlist
        tracks = []
        episodes = []
        uris_dict = {}
        for uri in uris:
            if "spotify:track:" in uri:
                tracks.append({"uri": uri})
            else:
                episodes.append({"uri": uri})
        if tracks != []:
            uris_dict["tracks"] = tracks
        if episodes != []:
            uris_dict["episodes"] = episodes
        return uris_dict
    
    def parse_url_query(self, url:str):
        parsed_url = urlparse(url)
        if parsed_url.scheme != "https":
            return {}
        parsed_query = parse_qs(parsed_url.query)
        return parsed_query

    '''
    GET /me/albums
    '''   
    def get_saved_albums(self, market:str|None=None, limit:int|None=None, offset:int|None=None):
        required_scopes = ["user-library-read"]
        query_params = self.create_query(market=market, limit=limit, offset=offset)
        return self.get_response(-1, resource_type="me/albums", query=query_params, required_scopes=required_scopes)
    
    def save_albums(self, _ids:list):
        required_scopes = ["user-library-modify"]
        query_params = self.convert_list_to_dict("ids", _ids)
        query_params = urlencode(query_params)
        return self.get_response(-1, resource_type="me/albums", query=query_params, request_type="PUT", required_scopes=required_scopes)

    def remove_saved_albums(self, _ids:list):
        required_scopes = ["user-library-modify"]
        query_params = self.convert_list_to_dict("ids", _ids)
        query_params = urlencode(query_params)
        return self.get_response(-1, resource_type="me/albums", query=query_params, request_type="DELETE", required_scopes=required_scopes)   

    def check_saved_albums(self, _ids:list):
        required_scopes = ["user-library-read"]
        query_params = self.convert_list_to_dict("ids", _ids)
        query_params = urlencode(query_params)
        return self.get_response(-1, resource_type="me/albums/contains", query=query_params, required_scopes=required_scopes)

    '''
    GET /me/audiobooks
    '''
    def get_saved_audiobooks(self, limit:int=default_limit, offset:int=default_offset):
        required_scopes = ["user-library-read"]
        query_params = self.create_query(limit=limit, offset=offset)
        return self.get_response(-1, resource_type="me/audiobooks", query=query_params, required_scopes=required_scopes)
    
    def save_audiobooks(self, _ids:list):
        required_scopes = ["user-library-modify"]
        query_params = self.convert_list_to_dict("ids", _ids)
        query_params = urlencode(query_params)
        return self.get_response(-1, resource_type="me/audiobooks", query=query_params, request_type="PUT", required_scopes=required_scopes)

    def remove_saved_audiobooks(self, _ids:list):
        required_scopes = ["user-library-modify"]
        query_params = self.convert_list_to_dict("ids", _ids)
        query_params = urlencode(query_params)
        return self.get_response(-1, resource_type="me/audiobooks", query=query_params, request_type="DELETE", required_scopes=required_scopes)   

    def check_saved_audiobooks(self, _ids:list):
        required_scopes = ["user-library-read"]
        query_params = self.convert_list_to_dict("ids", _ids)
        query_params = urlencode(query_params)
        return self.get_response(-1, resource_type="me/audiobooks/contains", query=query_params, required_scopes=required_scopes)

    '''
    GET /episodes
    Required Parameters:
        id(s): str|list
    '''

    # Required Scopes: user-read-playback-position
    def get_episode(self, _id:str, market:str|None=None):
        required_scopes = ["user-read-playback-position"]
        query_params = self.create_query(market=market)
        return self.get_response(_id, resource_type="episodes", query=query_params, required_scopes=required_scopes)

    # Required Scopes: user-read-playback-position
    def get_episodes(self, _ids:list, market:str|None=None):
        required_scopes = ["user-read-playback-position"]
        query_params = self.convert_list_to_dict("ids", _ids)
        query_params = self.create_query(query_params, market=market)
        return self.get_response(-1, resource_type="episodes", query=query_params, required_scopes=required_scopes)
    
    '''
    GET /me/episodes
    '''   
    def get_saved_episodes(self, market:str|None=None, limit:int|None=None, offset:int|None=None):
        required_scopes = ["user-library-read", "user-read-playback-position"]
        query_params = self.create_query(market=market, limit=limit, offset=offset)
        return self.get_response(-1, resource_type="me/episodes", query=query_params, required_scopes=required_scopes)
    
    def save_episodes(self, _ids:list):
        required_scopes = ["user-library-modify"]
        query_params = self.convert_list_to_dict("ids", _ids)
        query_params = urlencode(query_params)
        return self.get_response(-1, resource_type="me/episodes", query=query_params, request_type="PUT", required_scopes=required_scopes)
    
    def remove_saved_episodes(self, _ids:list):
        required_scopes = ["user-library-modify"]
        query_params = self.convert_list_to_dict("ids", _ids)
        query_params = urlencode(query_params)
        return self.get_response(-1, resource_type="me/episodes", query=query_params, request_type="DELETE", required_scopes=required_scopes)
    
    def check_saved_episodes(self, _ids:list):
        required_scopes = ["user-library-read"]
        query_params = self.convert_list_to_dict("ids", _ids)
        query_params = urlencode(query_params)
        return self.get_response(-1, resource_type="me/episodes/contains", query=query_params, required_scopes=required_scopes)

    '''
    GET /me/player
    '''
    def get_playback(self, market:str|None=None, additional_types:list=None):
        required_scopes = ["user-read-playback-state"]
        query_params = self.create_query(market=market, additional_types=additional_types)
        return self.get_response(-1, resource_type="me/player", query=query_params, required_scopes=required_scopes)
    
    def transfer_playback(self, device_id:list|str, play:bool=True):
        required_scopes = ["user-modify-playback-state"]
        # only accepts 1 device id, any more results in a 400 error
        if isinstance(device_id, list) and len(device_id) != 1:
             raise Exception("More than one device id was submitted. Please submit only 1 device id.")
        if not isinstance(device_id, list):
            device_id = [device_id]
        data = self.create_json_body(device_ids=device_id, play=play)
        return self.get_response(-1, resource_type="me/player", request_type="PUT", required_scopes=required_scopes, data=data)

    def get_available_devices(self):
        required_scopes = ["user-read-playback-state"]
        return self.get_response(-1, resource_type="me/player/devices", required_scopes=required_scopes)
    
    def get_currently_playing_track(self, market:str|None=None, additional_types:list=None):
        required_scopes = ["user-read-currently-playing"]
        query_params = self.create_query(market=market, additional_types=additional_types)
        return self.get_response(-1, resource_type="me/player/currently-playing", query=query_params, required_scopes=required_scopes)
    
    def start_playback(self, device_id=None):
        required_scopes = ["user-modify-playback-state"]
        query_params = self.create_query(device_id=device_id)
        return self.get_response(-1, resource_type="me/player/play", query=query_params, request_type="PUT", required_scopes=required_scopes)
    
    def stop_playback(self, device_id=None):
        required_scopes = ["user-modify-playback-state"]
        query_params = self.create_query(device_id=device_id)
        return self.get_response(-1, resource_type="me/player/pause", query=query_params, request_type="PUT", required_scopes=required_scopes)
    
    def skip_to_next(self, device_id=None):
        required_scopes = ["user-modify-playback-state"]
        query_params = self.create_query(device_id=device_id)
        return self.get_response(-1, resource_type="me/player/next", query=query_params, request_type="POST", required_scopes=required_scopes)
    
    def skip_to_previous(self, device_id=None):
        required_scopes = ["user-modify-playback-state"]
        query_params = self.create_query(device_id=device_id)
        return self.get_response(-1, resource_type="me/player/previous", query=query_params, request_type="POST", required_scopes=required_scopes)

    def seek_position(self, position_ms:int, device_id=None):
        required_scopes = ["user-modify-playback-state"]
        query_params = self.create_query(position_ms=position_ms, device_id=device_id)
        return self.get_response(-1, resource_type="me/player/seek", query=query_params, request_type="PUT", required_scopes=required_scopes)

    def set_repeat_mode(self, state:str, device_id=None):
        required_scopes = ["user-modify-playback-state"]
        if state not in ["track", "context", "off"]:
            raise Exception("Invalid state. Refer to the Spotify API Documentation for valid states: "
                            "https://developer.spotify.com/documentation/web-api/reference/set-repeat-mode-on-users-playback")
        query_params = self.create_query(state=state, device_id=device_id)
        return self.get_response(-1, resource_type="me/player/repeat", query=query_params, request_type="PUT", required_scopes=required_scopes)

    def set_volume(self, volume_percent:int, device_id=None):
        required_scopes = ["user-modify-playback-state"]
        # simply do nothing if volume percent is outside of range
        if volume_percent not in range(0, 101):
            return False
        query_params = self.create_query(volume_percent=volume_percent, device_id=device_id)
        return self.get_response(-1, resource_type="me/player/volume", query=query_params, request_type="PUT", required_scopes=required_scopes)

    def toggle_shuffle(self, state:bool, device_id=None):
        required_scopes = ["user-modify-playback-state"]
        query_params = self.create_query(state=state, device_id=device_id)
        return self.get_response(-1, resource_type="me/player/shuffle", query=query_params, request_type="PUT", required_scopes=required_scopes)
    
    def get_recently_played_tracks(self, limit:str|None=None, after:int|None=None, before:int|None=None):
        required_scopes = ["user-read-recently-played"]
        # Only one should be specified, not both
        if after != None and before != None:
            raise Exception("If after is specified, before must not be specified, and vice versa.")
        query_params = self.create_query(limit=limit, after=after, before=before)
        return self.get_response(-1, resource_type="me/player/recently-played", query=query_params, required_scopes=required_scopes)
    
    def get_queue(self):
        required_scopes = ["user-read-playback-state"]
        return self.get_response(-1, resource_type="me/player/queue", required_scopes=required_scopes)
    
    def add_item_to_queue(self, uri:str, device_id=None):
        required_scopes = ["user-modify-playback-state"]
        if not("spotify:track:" in uri or "spotify:episode:" in uri):
            raise Exception("Invalid URI. Please submit either a track or episode URI.")
        query_params = self.create_query(uri=uri, device_id=device_id)
        return self.get_response(-1, resource_type="me/player/queue", query=query_params, request_type="POST", required_scopes=required_scopes)

    '''
    /playlists
    '''
    def change_playlist_details(self, _playlist_id:str, name:str|None=None, public:bool|None=None, collaborative:bool|None=None, description:str|None=None):
        required_scopes = ["playlist-modify-public", "playlist-modify-private"]
        if public:
            collaborative = False
        data = self.create_json_body(name=name, public=public, collaborative=collaborative, description=description)
        return self.get_response(_playlist_id, resource_type="playlists", request_type="PUT", required_scopes=required_scopes, data=data)
    
    def get_platlist_items(self, _playlist_id:str, market:str|None=None, fields:str|None=None, limit:str|None=None, offset:str|None=None, additional_types:list|None=None):
        required_scopes = ["playlist-read-private"]
        query_params = self.create_query(market=market, fields=fields, limit=limit, offset=offset, additional_types=additional_types)
        return self.get_response(f"{_playlist_id}/tracks", resource_type="playlists", query=query_params, required_scopes=required_scopes)  
    
    def update_playlist_items(self, _playlist_id:str, uris:list|None=None, range_start:int|None=None, range_length:int|None=None, snapshot_id:str|None=None):
        required_scopes = ["playlist-modify-public", "playlist-modify-private"]
        self.check_uris(uris)
        data = self.create_json_body(uris=uris, range_start=range_start, range_length=range_length, snapshot_id=snapshot_id)
        return self.get_response(f"{_playlist_id}/tracks", resource_type="playlists", request_type="PUT", required_scopes=required_scopes, data=data)
    
    def add_items_to_playlist(self, _playlist_id:str, uris:list|None=None, position:int|None=None):
        required_scopes = ["playlist-modify-public", "playlist-modify-private"]
        self.check_uris(uris)
        data = self.create_json_body(uris=uris, position=position)
        return self.get_response(f"{_playlist_id}/tracks", resource_type="playlists", request_type="POST", required_scopes=required_scopes, data=data)
    
    def remove_items_to_playlist(self, _playlist_id:str, uris:list, snapshot_id:str|None=None):
        required_scopes = ["playlist-modify-public", "playlist-modify-private"]
        self.check_uris(uris)
        uris = self.create_list_of_objects(uris=uris)
        data = self.create_json_body(uris=uris, snapshot_id=snapshot_id)
        return self.get_response(f"{_playlist_id}/tracks", resource_type="playlists", request_type="DELETE", required_scopes=required_scopes, data=data)
    
    def get_current_users_playlists(self, limit:int|None=None, offset:int|None=None):
        required_scopes = ["playlist-read-private"]
        query_params = self.create_query(limit=limit, offset=offset)
        return self.get_response(-1, resource_type="me/playlists", query=query_params, required_scopes=required_scopes)

    def get_users_playlists(self, _user_id:str, limit:int|None=None, offset:int|None=None):
        required_scopes = ["playlist-read-private"]
        query_params = self.create_query(limit=limit, offset=offset)
        return self.get_response(f"{_user_id}/playlists", resource_type="users", query=query_params, required_scopes=required_scopes)
    
    def create_playlist(self, _user_id:str, name:str, public:bool|None=True, collaborative:bool|None=False, description:str|None=None):
        required_scopes = ["playlist-modify-public", "playlist-modify-private"]
        if public:
            collaborative = False
        data = self.create_json_body(name=name, public=public, collaborative=collaborative, description=description)
        return self.get_response(f"{_user_id}/playlists", resource_type="users", request_type="POST", required_scopes=required_scopes, data=data)

    def add_cover_image(self, _playlist_id:str, image_data:str):
        required_scopes = ["ugc-image-upload", "playlist-modify-public", "playlist-modify-private"]

        decoded_string = base64.b64decode(image_data)
        im = Image.open(io.BytesIO(decoded_string))
        im.verify()
        if im.format != "JPEG":
            raise ValueError("Image is not a JPEG image.")
        
        return self.get_response(f"{_playlist_id}/images", resource_type="playlists", request_type="PUT", required_scopes=required_scopes, data=image_data)

    '''
    /me/shows
    '''
    def get_show(self, _show_id:str, market:str|None=None):
        required_scopes = ["user-read-playback-position"]
        query_params = self.create_query(market=market)
        return self.get_response(_show_id, resource_type="shows", query=query_params, required_scopes=required_scopes)
    
    def get_shows(self, _show_ids:list, market:str|None=None):
        required_scopes = ["user-read-playback-position"]
        ids = self.convert_list_to_str(",", _show_ids)
        query_params = self.create_query(ids=ids, market=market)
        return self.get_response(-1, resource_type="shows", query=query_params, required_scopes=required_scopes)

    def get_saved_shows(self, limit:str|None=None, offset:str|None=None):
        required_scopes = ["user-library-read"]
        query_params = self.create_query(limit=limit, offset=offset)
        return self.get_response(-1, resource_type="me/shows", query=query_params, required_scopes=required_scopes)
    
    def save_shows(self, _show_ids:list):
        required_scopes = ["user-library-modify"]
        ids = self.convert_list_to_str(",", _show_ids)
        query_params = self.create_query(ids=ids)
        return self.get_response(-1, resource_type="me/shows", query=query_params, request_type="PUT", required_scopes=required_scopes)
    
    def remove_saved_shows(self, _show_ids:list, market:str|None=None):
        required_scopes = ["user-library-modify"]
        ids = self.convert_list_to_str(",", _show_ids)
        query_params = self.create_query(ids=ids, market=market)
        return self.get_response(-1, resource_type="me/shows", query=query_params, request_type="DELETE", required_scopes=required_scopes)
    
    def check_saved_shows(self, _show_ids:list):
        required_scopes = ["user-read-playback-position"]
        ids = self.convert_list_to_str(",", _show_ids)
        query_params = self.create_query(ids=ids)
        return self.get_response(-1, resource_type="me/shows/contains", query=query_params, required_scopes=required_scopes)
    
    '''
    /tracks
    '''
    def get_saved_tracks(self, market:str|None=None, limit:int|None=None, offset:int|None=None):
        required_scopes = ["user-library-read"]
        query_params = self.create_query(market=market, limit=limit, offset=offset)
        return self.get_response(-1, resource_type="me/tracks", query=query_params, required_scopes=required_scopes)
    
    def save_tracks(self, _track_ids:list):
        required_scopes = ["user-library-modify"]
        ids = self.convert_list_to_str(",", _track_ids)
        query_params = self.create_query(ids=ids)
        return self.get_response(-1, resource_type="me/tracks", query=query_params, request_type="PUT", required_scopes=required_scopes)

    def remove_saved_tracks(self, _track_ids:list):
        required_scopes = ["user-library-modify"]
        ids = self.convert_list_to_str(",", _track_ids)
        query_params = self.create_query(ids=ids)
        return self.get_response(-1, resource_type="me/tracks", query=query_params, request_type="DELETE", required_scopes=required_scopes)
    
    def check_saved_tracks(self, _show_ids:list):
        required_scopes = ["user-library-read"]
        ids = self.convert_list_to_str(",", _show_ids)
        query_params = self.create_query(ids=ids)
        return self.get_response(-1, resource_type="me/tracks/contains", query=query_params, required_scopes=required_scopes)
    
    '''
    GET /me
    '''
    def get_current_users_profile(self):
        required_scopes = ["user-read-private", "user-read-email"]
        return self.get_response(-1, resource_type="me", required_scopes=required_scopes)

    def get_top_items(self, type:str, time_range:str|None=None, limit:int|None=None, offset:int|None=None):
        required_scopes = ["user-top-read"]
        if type not in ["artists", "tracks"]:
            raise Exception("Invalid type. Valid values are 'artists' or 'tracks'")
        if time_range not in ["long_term", "medium_term", "short_term"]:
            time_range = None
        query_params = self.create_query(time_range=time_range, limit=limit, offset=offset)
        return self.get_response(type, resource_type="me/top", query=query_params, required_scopes=required_scopes)

    def follow_playlist(self, _playlist_id:str, public:bool=True):
        required_scopes = ["playlist-modify-public", "playlist-modify-private"]
        data = self.create_json_body(public=public)
        return self.get_response(f"{_playlist_id}/followers", resource_type="playlists", request_type="PUT", required_scopes=required_scopes, data=data)
    
    def unfollow_playlist(self, _playlist_id:str):
        required_scopes = ["playlist-modify-public", "playlist-modify-private"]
        return self.get_response(f"{_playlist_id}/followers", resource_type="playlists", request_type="DELETE", required_scopes=required_scopes)

    '''
    NOTE 6/25/2023: Currently only artist is supported for type, however type is left as a 
         parameter if this were to change in the future.
    '''
    def get_followed_artists(self, type:str|None="artist", after:str|None=None, limit:int|None=None):
        required_scopes = ["user-follow-read"]
        type = "artist"
        query_params = self.create_query(type=type, after=after, limit=limit)
        return self.get_response(-1, resource_type="me/following", query=query_params, required_scopes=required_scopes)
    
    def follow_artists_or_users(self, type:str, _ids:list):
        required_scopes = ["user-follow-modify"]
        if type not in ["artist", "user"]:
            raise Exception("Invalid type. Valid values are 'artist' or 'user'")
        ids = self.convert_list_to_str(",", _ids)
        query_params = self.create_query(type=type, ids=ids)
        return self.get_response(-1, resource_type="me/following", query=query_params, request_type="PUT", required_scopes=required_scopes)
    
    def unfollow_artists_or_users(self, type:str, _ids:list):
        required_scopes = ["user-follow-modify"]
        if type not in ["artist", "user"]:
            raise Exception("Invalid type. Valid values are 'artist' or 'user'")
        ids = self.convert_list_to_str(",", _ids)
        query_params = self.create_query(type=type, ids=ids)
        return self.get_response(-1, resource_type="me/following", query=query_params, request_type="DELETE", required_scopes=required_scopes)
    
    def check_artists_or_users(self, type:str, _ids:list):
        required_scopes = ["user-follow-read"]
        if type not in ["artist", "user"]:
            raise Exception("Invalid type. Valid values are 'artist' or 'user'")
        ids = self.convert_list_to_str(",", _ids)
        query_params = self.create_query(type=type, ids=ids)
        return self.get_response(-1, resource_type="me/following/contains", query=query_params, required_scopes=required_scopes)

class SpotifyPKCE(SpotifyOAuth):
    code_verifier = None
    code_challenge = None

    def generate_code_verifier(self):
        verifier = ""
        length = random.randint(43, 128)
        possible = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~"
        for num in range(0, length):
            verifier += possible[math.floor(random.random() * len(possible))]   
        self.code_verifier = verifier

    def generate_code_challenge(self):
        data = self.code_verifier.encode('utf-8')
        challenge_digest = sha256(data).digest()
        code_challenge = base64.urlsafe_b64encode(challenge_digest).decode('utf-8')
        self.code_challenge = code_challenge.replace('=', '')

    def set_verifier_and_challenge(self):
        self.generate_code_verifier()
        self.generate_code_challenge()
    
    def get_code_data(self, scope, state, show_dialog):
        data = super().get_code_data(scope, state, show_dialog)
        data["code_challenge_method"] = "S256"
        data["code_challenge"] = self.code_challenge
        return data
    
    def get_token_headers(self):
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        return headers
    
    def get_token_data(self):
        return {"grant_type": "authorization_code",
                "code": self.code,
                "redirect_uri": self.redirect_uri,
                "client_id": self.client_id,
                "code_verifier": self.code_verifier}
    
    def get_refresh_data(self):
        data = super().get_refresh_data()
        data["client_id"] = self.client_id
        return data
    
    def request_user_auth(self, scopes: list = None, state: str = None, show_dialog: bool = False):
        self.set_verifier_and_challenge()
        return super().request_user_auth(scopes, state, show_dialog)
    