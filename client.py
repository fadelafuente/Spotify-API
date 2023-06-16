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

class SpotifyClient(object):
    access_token = None
    access_token_expires = None
    access_expired = True
    client_id = None
    client_secret = None
    token_url = "https://accounts.spotify.com/api/token"
    base_url = "https://api.spotify.com"
    default_limit = 20
    min_limit = 0
    max_limit = 50
    default_offset = 0
    min_offset = 0
    max_offset = 1000

    def __init__(self, client_id, client_secret, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client_id = client_id
        self.client_secret = client_secret

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
    def convert_list_to_str(self, separator, list_items, max_length=50):
        if len(list_items) > max_length:
            raise Exception("Maximum number of ids exceeded")
        return separator.join([f"{item}" for item in list_items])

    def convert_list_to_dict(self, key, list_items, max_length=50):
        item_string = self.convert_list_to_str(separator=",", list_items=list_items, max_length=max_length)
        return {key: item_string}
    
    def set_limit(self, limit:int):
        if limit != self.default_limit:
            if limit < self.min_limit:
                limit = self.min_limit
            if limit > self.max_limit:
                limit = self.max_limit
        return limit
    
    def set_offset(self, offset:int):
        if offset != self.default_offset:
            if offset < self.min_offset:
                offset = self.min_offset
            if offset > self.max_offset:
                offset = self.max_offset
        return offset
    
    def create_query(self, params={}, **kwargs):
        for key, value in kwargs.items():
            if key == "additional_types":
                value = self.check_additional_types(additional_types=value)
            if value != None:
                if key == "offset":
                    value = self.set_offset(value)
                elif key == "limit":
                    value = self.set_limit(value)
                params[key] = value
        if params == {}:
             return None
        return urlencode(params)
    
    def parse_url_query(self, url:str):
        parsed_url = urlparse(url)
        if parsed_url.scheme != "https":
            return {}
        parsed_query = parse_qs(parsed_url.query)
        return parsed_query
    
    def build_endpoint(self, id, resource_type, version, query):
        endpoint = f"{self.base_url}/{version}/{resource_type}"
        if id != -1:
            endpoint += f"/{id}"
        if query != None:
            endpoint += f"?{query}"
        return endpoint
          
    def get_response(self, id, resource_type="albums", version="v1", query=None):
        endpoint = self.build_endpoint(id, resource_type, version, query)
        headers = self.get_access_headers()
        response = requests.get(endpoint, headers=headers)

        print(endpoint)

        # if response.status_code not in range(200, 299):
        #     return response.json()   
        return response.json()
    
    def check_additional_types(self, additional_types):
        if additional_types != None:
            # Valid types are track and episode, check if additional_types is not equal or a subset
            # NOTE: The spotify API documentation shows that this might be deprecated in the future
            # Reference: https://developer.spotify.com/documentation/web-api/reference/get-information-about-the-users-current-playback
            if all(a_type in ["track", "episode"] for a_type in additional_types):
                return self.convert_list_to_str(separator=",", list_items=additional_types)
        return None

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
    def search(self, query:str|dict, search_type:str="album", market:str|None=None, limit:int|None=None, offset:int|None=None, include_external:str|None=None):
        # if query is a dictionary, change it to a string where each key-value pair is separated by spaces   
        if isinstance(query, dict):
            query = " ".join([f"{k}:{v}" for k, v in query.items()])

        if include_external != "audio":
            include_external = None
        query_params = self.create_query(q=query, type=search_type.lower(), include_external=include_external, market=market, limit=limit, offset=offset)
        return self.get_search_response(query_params)

    def get_search_response(self, query):
        return self.get_response(-1, resource_type="search", query=query)

    '''
    GET /albums
    Required Parameter(s):
        id(s) (str|list)
    '''
    def get_album(self, _id:str, market:str|None=None):
        query_params = self.create_query(market=market)
        return self.get_response(_id, resource_type="albums", query=query_params)
    
    def get_albums(self, _ids:list, market:str|None=None):
        query_params = self.convert_list_to_dict("ids", _ids, length=20)
        query_params = self.create_query(query_params, market=market)   
        return self.get_response(-1, resource_type="albums", query=query_params)
    
    def get_album_tracks(self, _id:str, market:str|None=None, limit:int|None=None, offset:int|None=None):
        query_params = self.create_query(market=market, limit=limit, offset=offset)
        return self.get_response(f"{_id}/tracks", resource_type="albums", query=query_params)
    
    # uses country string instead of market string
    def get_new_releases(self, country:str=None, limit:int|None=None, offset:int|None=None):
        query_params = self.create_query(country=country, limit=limit, offset=offset)
        return self.get_response(-1, resource_type="browse/new-releases", query=query_params)

    '''
    GET /Artists
    Required Parameters:
        id(s) (str|list)
    '''
    def get_artist(self, _id:int):
        return self.get_response(_id, resource_type="artists")
    
    def get_artists(self, _ids:list):
        query_params = self.convert_list_to_dict("ids", _ids)
        query_params = urlencode(query_params)

        return self.get_response(-1, resource_type="artists", query=query_params)
    
    def get_artist_albums(self, _id:str, include_groups:list|None=None, market:str|None=None, limit:int|None=None, offset:int|None=None):
        query_params = self.create_query(include_groups=include_groups, market=market, limit=limit, offset=offset)
        return self.get_response(f"{_id}/albums", resource_type="artists", query=query_params)

    # The documentation does not say the market string is required, and the example provided actually excludes it.
    # However, excluding the market string here returns a 400 error, so default is set to 'US'
    #
    # Reference: https://developer.spotify.com/documentation/web-api/reference/get-an-artists-top-tracks
    def get_artist_top_tracks(self, _id:int, market:str="US"):
        query_params = self.create_query(market=market)
        return self.get_response(f"{_id}/top-tracks", resource_type="artists", query=query_params)
    
    def get_artist_related_artists(self, _id:int):
        return self.get_response(f"{_id}/related-artists", resource_type="artists")

    '''
    GET /audiobooks
    Required Parameters:
        id(s) (str|list)
    '''
    def get_audiobook(self, _id:str, market:str|None=None):
        query_params = self.create_query(market=market)
        return self.get_response(_id, resource_type="audiobooks", query=query_params)
    
    def get_audiobooks(self, _ids:list, market:str|None=None):
        query_params = self.convert_list_to_dict("ids", _ids)
        query_params = self.create_query(query_params, market=market)
        return self.get_response(-1, resource_type="audiobooks", query=query_params)
    
    def get_audiobook_chapters(self, _id:str, market:str|None=None, limit:int|None=None, offset:int|None=None):
        query_params = self.create_query(market=market, limit=limit, offset=offset)
        return self.get_response(f"{_id}/chapters", resource_type="audiobooks", query=query_params)
    
    '''
    GET /browse/categories

    locale parameter (not required): similar to the market code, but consists of a 
        language code before the country code.
        example used in documentation: es_MX, meaning "Spanish (Mexico)"

    Reference: https://developer.spotify.com/documentation/web-api/reference/get-categories
    '''
    def get_browse_categories(self, country:str|None=None, locale:str|None=None, limit:int=default_limit, offset:int=default_offset):
        query_params = self.create_query(country=country, locale=locale, limit=limit, offset=offset)
        return self.get_response(-1, resource_type="browse/categories", query=query_params)
    
    def get_browse_category(self, category:str, country:str|None=None, locale:str|None=None):
        query_params = self.create_query(country=country, locale=locale)
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
        query_params = self.create_query(market=market)
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
    GET /playlists
    '''
    def get_playlist(self, _playlist_id:str, market:str|None=None, fields:str|None=None, additional_types:list|None=None):
        query_params = self.create_query(market=market, fields=fields, additional_types=additional_types)
        return self.get_response(_playlist_id, resource_type="playlists", query=query_params)
    
    def get_featured_playlists(self, country:str|None=None, locale:str|None=None, timestamp:str|None=None, limit:str|None=None, offset:str|None=None):
        query_params = self.create_query(country=country, locale=locale, timestamp=timestamp, limit=limit, offset=offset)
        return self.get_response(-1, resource_type="browse/featured-playlists", query=query_params)
    
    def get_categorys_playlists(self, _category_id:str, country:str|None=None, limit:str|None=None, offset:str|None=None):
        query_params = self.create_query(country=country, limit=limit, offset=offset)
        return self.get_response(f"{_category_id}/playlists", resource_type="browse/categories", query=query_params)
    
    def get_playlist_cover(self, _playlist_id:str):
        return self.get_response(f"{_playlist_id}/images", resource_type="playlists")
    