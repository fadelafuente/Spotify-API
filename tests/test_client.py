import os
from dotenv import load_dotenv
from SpotifyAPI import SpotifyClient

load_dotenv()

# For testing purposes, will remove later 
client_id = os.environ.get("client_id")
client_secret = os.environ.get("client_secret")

client = SpotifyClient(client_id=client_id, client_secret=client_secret)