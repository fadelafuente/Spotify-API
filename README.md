# Spotify-API
This library was created for learning purposes, and makes using the Spotify API easier to use in Python.

## Quick Start
### Client Credentials
```
client = SpotifyClient(client_id="<your-client-id>", 
  client_secret="<your-client-secret>")
  
albums = client.get_new_releases()
```

### Authorization Code Flow
NOTE: using code flow also has access to any data that can be obtained using the client credentials.

If the scopes are not passed in, then only the methods provided by client credentials can be used. The methods requiring user authorization will return an empty dictionary.
```
auth = SpotifyOAuth(client_id="<your-client-id>", 
  client_secret="<your-client-secret>",
  redirect_uri="<your-redirect-uri>",
  scopes=["user-library-read", "user-read-playback-position"])

episodes = auth.get_saved_episodes()
```

You can also add this line if scopes was not passed previously, or if you want to change the authorization scopes.
```
auth.request_user_auth(scopes=["user-library-read"])
```
