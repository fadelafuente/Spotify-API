import base64
import datetime
import os
import requests
from dotenv import load_dotenv
from urllib.parse import urlencode
from urllib.parse import urlparse, parse_qs

load_dotenv()

# For testing purposes, will remove later 
client_id = os.environ.get("client_id")
client_secret = os.environ.get("client_secret")
redirect_uri = os.environ.get("redirect_uri")

class SpotifyClient(object):
    access_token = None
    access_token_expires = None
    access_expired = True
    client_id = None
    client_secret = None
    redirect_uri = None
    token_url = "https://accounts.spotify.com/api/token"
    base_url = "https://api.spotify.com"
    default_limit = 20
    min_limit = 0
    max_limit = 50
    default_offset = 0
    min_offset = 0
    max_offset = 1000

    def __init__(self, client_id, client_secret, redirect_uri, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri

    '''
    Client Credentials

    Reference: https://developer.spotify.com/documentation/web-api/tutorials/client-credentials-flow
    '''
    def get_client_credentials(self):
        '''
        returns base64 encoded string
        '''
        client_id = self.client_id
        client_secret = self.client_secret
        if(client_id == None or client_secret == None):
            raise Exception("You must set client_id and client_secret")

        client_creds = f"{client_id}:{client_secret}"
        client_creds_b64 = base64.b64encode(client_creds.encode())
        return client_creds_b64.decode()

    def get_token_headers(self): 
        client_creds = self.get_client_credentials() # <base64 encoded client_id:client_secret>
        return {
            "Authorization": f"Basic {client_creds}"
        }
    
    def get_token_data(self):
        return {
            "grant_type": "client_credentials"
        }

    def request_access_token(self, token_data):
        token_url = self.token_url
        token_headers = self.get_token_headers()

        response = requests.post(token_url, data=token_data, headers=token_headers)
        data = response.json()

        if response.status_code not in range(200, 299):
            raise Exception(f"Could not authenticate client. Error: {data}")

        now = datetime.datetime.now()
        access_token = data["access_token"]
        self.access_token = access_token
        expires_in = data["expires_in"]
        expires = now + datetime.timedelta(seconds=expires_in)
        self.access_token_expires = expires
        self.access_expired = expires < now

        # return data so oauth code flow can set refresh_token
        if "refresh_token" in data:
            return data
        return True
    
    def get_access_headers(self):
        access_token = self.get_access_token()
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        return headers
    
    def refresh_access_token(self):
        self.access_token = None
    
    def get_access_token(self):     
        access_token = self.access_token
        expires = self.access_token_expires
        now = datetime.datetime.now()

        # if the access token was not given/expired,
        # get/refresh the access token
        if access_token == None:
            token_data = self.get_token_data()
            self.request_access_token(token_data=token_data)
            return self.get_access_token()
        elif expires < now:
            self.refresh_access_token()
            return self.get_access_token()
        
        return access_token
    
    '''
    Helper functions
    '''
    def convert_list_to_str(self, separator, list_items):
        return separator.join([f"{item}" for item in list_items])

    def convert_list_to_dict(self, key, list_items):
        item_string = ",".join([f"{item}" for item in list_items])
        return {key: item_string}
    
    def set_limit(self, limit:int, dict):
        if limit != self.default_limit:
            if limit < self.min_limit:
                limit = self.min_limit
            if limit > self.max_limit:
                limit = self.max_limit
            dict["limit"] = limit
        return dict
    
    def set_offset(self, offset:int, dict):
        if offset != self.default_offset:
            if offset < self.min_offset:
                offset = self.min_offset
            if offset > self.max_offset:
                offset = self.max_offset
            dict["offset"] = offset
        return dict
    
    def set_market(self, market:str, dict):
        if market != "":
            dict["market"] = market
        return dict
    
    def create_query(self, dict, market="", limit=default_limit, offset=default_offset):
        dict = self.set_market(market, dict)
        dict = self.set_limit(limit, dict)
        dict = self.set_offset(offset, dict)
        if dict == {}:
             return None
        return urlencode(dict)
    
    def parse_url_query(self, url:str):
        parsed_url = urlparse(url)
        if parsed_url.scheme != "https":
            return {}
        parsed_query = parse_qs(parsed_url.query)
        return parsed_query
          
    def get_response(self, id, resource_type="albums", version="v1", query=None):
        endpoint = f"{self.base_url}/{version}/{resource_type}"
        if id != -1:
            endpoint += f"/{id}"
        if query != None:
            endpoint += f"?{query}"

        print(endpoint)

        headers = self.get_access_headers()
        response = requests.get(endpoint, headers=headers)

        # if response.status_code not in range(200, 299):
        #     return response.json()   
        return response.json()

    '''
    GET /search
    Required Parameters:
        q: string or dictionary
            A string will refer to a single track, album, artist, etc.
            A dictionary should stay within the available filters

            available filters: album, artist, track, year,
            upc, tag:hipster, tag:new, isrc, genre

            NOTE: tag:hipster, tag:new, and upc are only
            available while searching albums  
        type: string or array of strings
            allowed values: album, artist, playlist, track,
            show, episode, audiobook

    Returns: Dictionary

    Reference Link: https://developer.spotify.com/documentation/web-api/reference/search
    '''
    def search(self, query:str|dict, search_type:str="albums", market:str="", limit:int=default_limit, offset:int=default_offset, include_external:str=""):
        # if query is a dictionary, change it to a string where each key-value pair is separated by spaces   
        if isinstance(query, dict):
            query = " ".join([f"{k}:{v}" for k, v in query.items()])

        query_dict = {"q": query, "type": search_type.lower()}
        if include_external == "audio":
            query_dict["include_external"] = include_external
        query_params = self.create_query(query_dict, market, limit, offset)
        return self.get_search_response(query_params)

    def get_search_response(self, query):
        return self.get_response(-1, resource_type="search", query=query)

    '''
    GET /albums
    Required Parameter(s):
        id(s) (str|list)
    '''
    def get_album(self, _id:str, market:str=""):
        query_params = self.create_query({}, market=market)
        return self.get_response(_id, resource_type="albums", query=query_params)
    
    def get_albums(self, _ids:list, market:str=""):
        if len(_ids) > 20:
            raise Exception("Maximum number of ids exceeded")
        query_params = self.convert_list_to_dict("ids", _ids)
        query_params = self.create_query(query_params, market=market)
    
        return self.get_response(-1, resource_type="albums", query=query_params)
    
    def get_album_tracks(self, _id:str, market:str="", limit:int=default_limit, offset:int=default_offset):
        query_params = self.create_query({}, market=market, limit=limit, offset=offset)
        return self.get_response(f"{_id}/tracks", resource_type="albums", query=query_params)

    '''
    GET /Artists
    Required Parameters:
        id(s) (str|list)
    '''
    def get_artist(self, _id:int):
        return self.get_response(_id, resource_type="artists")
    
    def get_artists(self, _ids:list):
        if len(_ids) > 50:
            raise Exception("Maximum number of ids exceeded")
        query_params = self.convert_list_to_dict("ids", _ids)
        query_params = urlencode(query_params)

        return self.get_response(-1, resource_type="artists", query=query_params)
    
    def get_artist_albums(self, _id:str, include_groups:list|None=None, market:str="", limit:int=default_limit, offset:int=default_offset):
        query_params = {}
        if include_groups != None:
            query_params = self.convert_list_to_dict("include_groups", include_groups)
        query_params = self.create_query(query_params, market=market, limit=limit, offset=offset)

        return self.get_response(f"{_id}/albums", resource_type="artists", query=query_params)

    # The documentation does not say the market string is required, and the example provided actually excludes it.
    # However, excluding the market string here returns a 400 error, so default is set to 'US'
    #
    # Reference: https://developer.spotify.com/documentation/web-api/reference/get-an-artists-top-tracks
    def get_artist_top_tracks(self, _id:int, market:str="US"):
        query_params = self.create_query({}, market=market)
        return self.get_response(f"{_id}/top-tracks", resource_type="artists", query=query_params)
    
    def get_artist_related_artists(self, _id:int):
        return self.get_response(f"{_id}/related-artists", resource_type="artists")

    '''
    GET /audiobooks
    Required Parameters:
        id(s) (str|list)
    '''
    def get_audiobook(self, _id:str, market:str=""):
        query_params = self.create_query({}, market=market)
        return self.get_response(_id, resource_type="audiobooks", query=query_params)
    
    def get_audiobooks(self, _ids:list, market:str=""):
        if len(_ids) > 50:
            raise Exception("Maximum number of ids exceeded")
        query_params = self.convert_list_to_dict("ids", _ids)
        query_params = self.create_query(query_params, market=market)
        return self.get_response(-1, resource_type="audiobooks", query=query_params)
    
    def get_audiobook_chapters(self, _id:str, market:str="", limit:int=default_limit, offset:int=default_offset):
        query_params = self.create_query({}, market=market, limit=limit, offset=offset)
        return self.get_response(f"{_id}/chapters", resource_type="audiobooks", query=query_params)
    
    '''
    GET /browse/categories

    locale parameter (not required): similar to the market code, but consists of a 
        language code before the country code.
        example used in documentation: es_MX, meaning "Spanish (Mexico)"

    Reference: https://developer.spotify.com/documentation/web-api/reference/get-categories
    '''
    def get_browse_categories(self, country:str|None=None, locale:str|None=None, limit:int=default_limit, offset:int=default_offset):
        query_params = {}
        if country != None:
            query_params["country"] = country
        if locale != None:
            query_params["locale"] = locale
        query_params = self.create_query(query_params, limit=limit, offset=offset)
        return self.get_response(-1, resource_type="browse/categories", query=query_params)
    
    def get_browse_category(self, category:str, country:str|None=None, locale:str|None=None):
        query_params = {}
        if country != None:
            query_params["country"] = country
        if locale != None:
            query_params["locale"] = locale
        query_params = self.create_query(query_params)
        return self.get_response(-1, resource_type=f"browse/categories/{category}", query=query_params)
    
    '''
    GET /chapters
    Required Parameters:
        id(s): str|list

    NOTE: The documentation does not say the market code is required, but exluding it 
        returns a 500 error. Because of this, the market code is set to 'US' by default.
        This applies to the next two methods.
    REASON: Chapters are only available for the US, UK, Ireland, New Zealand and Australia 
    markets.

    Reference: https://developer.spotify.com/documentation/web-api/reference/get-a-chapter
    '''
    def get_chapter(self, _id:str, market:str="US"):
        query_params = self.create_query({}, market=market)
        return self.get_response(_id, resource_type="chapters", query=query_params)
    
    def get_chapters(self, _ids:list, market:str="US"):
        query_params = self.convert_list_to_dict("ids", _ids)
        query_params = self.create_query(query_params, market=market)
        return self.get_response(-1, resource_type="chapters", query=query_params)
    
    '''
    GET /episodes
    Required Parameters:
        id(s): str|list
    '''
    
    '''
    GET /recommendations/available-genre-seeds
    '''
    def get_genre_seeds(self):
        return self.get_response(-1, resource_type="recommendations/available-genre-seeds")
    
    '''
    GET /markets
    '''
    def get_available_markets(self):
        return self.get_response(-1, resource_type="markets")

'''
Authentication Code Flow

Reference: https://developer.spotify.com/documentation/web-api/tutorials/code-flow
'''   
class SpotifyOAuth(SpotifyClient):
    code = None
    state = None
    scope = None
    refresh_token = None
    default_limit = 20
    min_limit = 0
    max_limit = 50
    default_offset = 0
    min_offset = 0
    max_offset = 1000

    def __init__(self, client_id, client_secret, redirect_uri, *args, **kwargs):
        super().__init__(client_id, client_secret, redirect_uri, *args, **kwargs)

    # get-scope? maybe method that returns scope for each call? or just offer all?
    # I can do this: have user provide scope, if the methods have the scope, it can continue
    # if it does not, return None 
    def get_code_data(self, scope, state, show_dialog):
        data = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "show_dialog": show_dialog
        }

        if scope != None:
            if isinstance(scope, list):
                scope = self.convert_list_to_str(" ", scope)
            else:
                data["scope"] = scope
        if state != None:
            data["state"] = state
        
        return data
    
    def request_user_auth(self, scope:str|list=None, state:str=None, show_dialog:bool=False):
        access_token = self.access_token
        data = self.get_code_data(scope, state, show_dialog)
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
    
    # Required scope(s): user-library-read
    def get_my_saved_albums(self, market:str="", limit:int=default_limit, offset:int=default_offset):
        query_params = self.create_query({}, market=market, limit=limit, offset=offset)
        return self.get_response(-1, resource_type="me/albums", query=query_params)

    '''
    GET /episodes
    Required Parameters:
        id(s): str|list
    '''
    def get_episode(self, _id:str, market:str=""):
        query_params = self.create_query({}, market=market)
        return self.get_response(_id, resource_type="episodes", query=query_params)

