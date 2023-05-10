import base64
import datetime
import os
import requests
from dotenv import load_dotenv
from urllib.parse import urlencode

load_dotenv()

# For testing purposes, will remove later 
client_id = os.environ.get("client_id")
client_secret = os.environ.get("client_secret")
redirect_uri = os.environ.get("redirect_uri")
token_url = os.environ.get("token_url")

class SpotifyAPI(object):
    access_token = None
    access_token_expires = None
    access_expired = True
    client_id = None
    client_secret = None
    token_url = None
    base_url = "https://api.spotify.com"

    def __init__(self, client_id, client_secret, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client_id = client_id
        self.client_secret = client_secret
        self.token_url = token_url

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

    def perform_auth(self):
        token_data = self.get_token_data()
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
        return True
    
    def get_access_token(self):     
        access_token = self.access_token
        expires = self.access_token_expires
        now = datetime.datetime.now()

        if access_token == None or expires < now:
            self.perform_auth()
            return self.get_access_token()
        
        return access_token
    
    def get_access_headers(self):
        access_token = self.get_access_token()
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        return headers
    
    def get_response(self, id, resource_type="albums", version="v1"):
        endpoint = f"{self.base_url}/{version}/{resource_type}/{id}"
        headers = self.get_access_headers()
        response = requests.get(endpoint, headers=headers)

        if response.status_code not in range(200, 299):
            return {}   
        return response.json()

    def search(self, query, search_type='artist'):
        endpoint = f"{self.base_url}/v1/search"
        headers = self.get_access_headers()

        data = urlencode({"q": query, "type": search_type.lower()})

        lookup_url = f"{endpoint}?{data}"
        response = requests.get(lookup_url, headers=headers)
        data = response.json()

        if response.status_code not in range(200, 299):
            return {}
                
        return data
    
    def get_albums(self, _id=None):
        return self.get_response(_id, resource_type="albums")
    
    def get_artists(self, _id=None):
        return self.get_response(_id, resource_type="artists")

client = SpotifyAPI(client_id=client_id, client_secret=client_secret)

#s = client.search("Time", search_type="track")

s = client.get_albums("7fe4Mem3wWgY6zkTFuKUI9")

print(s)