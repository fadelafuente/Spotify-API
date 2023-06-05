# Spotify-API
This library was created for learning purposes, and makes using the Spotify API easier to use in Python

## Quick Start
### Client Credentials
```
client = SpotifyClient(client_id="<your-client-id>", 
  client_secret="<your-client-secret>")
  
albums = client.get_new_releases()
```

### Authorization Code Flow
NOTE: using code flow also has access to any data that can be obtained using the client credentials.
```
auth = SpotifyOAuth(client_id="<your-client-id>", 
  client_secret="<your-client-secret>",
  redirect_uri="<your-redirect-uri>")

episodes = auth.get_saved_episodes()
```
