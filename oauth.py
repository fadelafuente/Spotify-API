import base64
import datetime
import time
import os
import requests
import json
from dotenv import load_dotenv
from urllib.parse import urlencode
from urllib.parse import urlparse, parse_qs
from client import SpotifyClient

load_dotenv()

# For testing purposes, will remove later 
client_id = os.environ.get("client_id")
client_secret = os.environ.get("client_secret")
redirect_uri = os.environ.get("redirect_uri")

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
                        "app-remote-control",
                        "streaming",
                        "playlist-read-private",
                        "playlist-read-collaborative",
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
                        "user-read-private",
                        "user-soa-link",
                        "user-soa-unlink",
                        "user-manage-entitlements",
                        "user-manage-partner",
                        "user-create-partner"]

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
    
    def request_user_auth(self, scopes:list=None, state:str=None, show_dialog:bool=False):
        access_token = self.access_token
        if self.validate_scopes(scopes=scopes):
            data = self.get_code_data(scopes, state, show_dialog)
        data = urlencode(data)

        if access_token == None:
            response = requests.get("https://accounts.spotify.com/authorize?" + data)
        if response.status_code not in range(200, 299):
            raise Exception(f"Authorization failed, could not redirect.")
        url = response.url

        print(f"Follow this url: {url}")
        print("input the redirected url: ")
        redirected_url = input()

        parsed_query = self.parse_url_query(redirected_url)
        if "error" in parsed_query:
            error = parsed_query["error"]
            raise Exception(f"Authorization failed, {error}")

        if "code" not in parsed_query:
            return False
        self.code = parsed_query["code"]
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
            return
        elif request_type == "DELETE":
            response = requests.delete(endpoint, headers=headers, data=data)
            return
        elif request_type == "POST":
            response = requests.post(endpoint, headers=headers, data=data)
            return
        else:
            response = requests.get(endpoint, headers=headers, data=data)
 
        return response.json()
    
    '''
    GET /me/albums
    '''   
    def get_saved_albums(self, market:str="", limit:int=default_limit, offset:int=default_offset):
        required_scopes = ["user-library-read"]
        query_params = self.create_query({}, market=market, limit=limit, offset=offset)
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
        query_params = self.create_query({}, limit=limit, offset=offset)
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
    def get_episode(self, _id:str, market:str=""):
        required_scopes = ["user-read-playback-position"]
        query_params = self.create_query({}, market=market)
        return self.get_response(_id, resource_type="episodes", query=query_params, required_scopes=required_scopes)

    # Required Scopes: user-read-playback-position
    def get_episodes(self, _ids:list, market:str=""):
        required_scopes = ["user-read-playback-position"]
        query_params = self.convert_list_to_dict("ids", _ids)
        query_params = self.create_query(query_params, market=market)
        return self.get_response(-1, resource_type="episodes", query=query_params, required_scopes=required_scopes)
    
    '''
    GET /me/episodes
    '''   
    def get_saved_episodes(self, market:str="", limit:int=default_limit, offset:int=default_offset):
        required_scopes = ["user-library-read", "user-read-playback-position"]
        query_params = self.create_query({}, market=market, limit=limit, offset=offset)
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
    def get_playback(self, market:str="", additional_types:list=None):
        required_scopes = ["user-read-playback-state"]
        query_params = {}
        if additional_types != None:
            # Valid types are track and episode, check if additional_types is not equal or a subset
            # NOTE: The spotify API documentation shows that this might be deprecated in the future
            # Reference: https://developer.spotify.com/documentation/web-api/reference/get-information-about-the-users-current-playback
            if all(a_type in ["track", "episode"] for a_type in additional_types):
                query_params["additional_types"] = additional_types
        query_params = self.create_query(query_params, market=market)
        return self.get_response(-1, resource_type="me/player", query=query_params, required_scopes=required_scopes)
    
    def transfer_playback(self, device_id, play=True):
        required_scopes = ["user-modify-playback-state"]
        # only accepts 1 device id, any more results in a 400 error
        if isinstance(device_id, list) and len(device_id) != 1:
             return {}
        if not isinstance(device_id, list):
            device_id = [device_id]
        data = {"device_ids": device_id, "play": play}
        data = json.dumps(data)
        return self.get_response(-1, resource_type="me/player", request_type="PUT", required_scopes=required_scopes, data=data)

    def get_available_devices(self):
        required_scopes = ["user-read-playback-state"]
        return self.get_response(-1, resource_type="me/player/devices", required_scopes=required_scopes)
    
    def get_currently_playing_track(self, market:str="", additional_types:list=None):
        required_scopes = ["user-read-currently-playing"]
        query_params = {}
        if additional_types != None:
            # Valid types are track and episode, check if additional_types is not equal or a subset
            # NOTE: The spotify API documentation shows that this might be deprecated in the future
            # Reference: https://developer.spotify.com/documentation/web-api/reference/get-information-about-the-users-current-playback
            if all(a_type in ["track", "episode"] for a_type in additional_types):
                query_params["additional_types"] = additional_types
        query_params = self.create_query(query_params, market=market)
        return self.get_response(-1, resource_type="me/player/currently-playing", query=query_params, required_scopes=required_scopes)
    
    def start_playback(self, device_id=None):
        required_scopes = ["user-modify-playback-state"]
        query_params = None
        if device_id != None:
            query_params = {"device_id": device_id}
        return self.get_response(-1, resource_type="me/player/play", query=query_params, request_type="PUT", required_scopes=required_scopes)
    
    def pause_playback(self, device_id=None):
        required_scopes = ["user-modify-playback-state"]
        query_params = None
        if device_id != None:
            query_params = {"device_id": device_id}
        return self.get_response(-1, resource_type="me/player/pause", query=query_params, request_type="PUT", required_scopes=required_scopes)
    
    def skip_to_next(self, device_id=None):
        required_scopes = ["user-modify-playback-state"]
        query_params = None
        if device_id != None:
            query_params = {"device_id": device_id}
        return self.get_response(-1, resource_type="me/player/next", query=query_params, request_type="POST", required_scopes=required_scopes)
    
    def skip_to_previous(self, device_id=None):
        required_scopes = ["user-modify-playback-state"]
        query_params = None
        if device_id != None:
            query_params = {"device_id": device_id}
        return self.get_response(-1, resource_type="me/player/previous", query=query_params, request_type="POST", required_scopes=required_scopes)

    def seek_position(self, position_ms:int, device_id=None):
        required_scopes = ["user-modify-playback-state"]
        query_params = {"position_ms": position_ms}
        if device_id != None:
            query_params = {"device_id": device_id}
        return self.get_response(-1, resource_type="me/player/seek", query=query_params, request_type="PUT", required_scopes=required_scopes)

    def set_repeat_mode(self, state:str, device_id=None):
        required_scopes = ["user-modify-playback-state"]
        if state not in ["track", "context", "off"]:
            return
        query_params = {"state": state}
        if device_id != None:
            query_params = {"device_id": device_id}
        return self.get_response(-1, resource_type="me/player/repeat", query=query_params, request_type="PUT", required_scopes=required_scopes)
