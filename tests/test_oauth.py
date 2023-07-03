from SpotifyAPI import SpotifyOAuth
import os
from dotenv import load_dotenv

client_id = "PLACEHOLDER_TEST_ID"
client_secret = "PLACEHOLDER_TEST_SECRET"
redirect_uri = "PLACEHOLDER_TEST_URI"
scopes = ["scope1", "scope2", "scope3"]

load_dotenv()

# For testing purposes, will remove later 
client_id = os.environ.get("client_id")
client_secret = os.environ.get("client_secret")
redirect_uri = os.environ.get("redirect_uri")

required_scopes = ["user-top-read"]