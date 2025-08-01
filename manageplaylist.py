import spotipy
from spotipy.oauth2 import SpotifyOAuth
import random
# from pl2spread.playlist2spreadsheet import Playlist2Spreadsheet, read_secrets_file

client_id="5469d6f0530444b094b670becf1ea407"
client_secret="5b86a619674f4473a522c8bbcdb9c557"
PLAYLIST_MAX_SONG_COUNT=10000
redirect_uri = "https://tefanodaniel.pythonanywhere.com/pl2spread/authorize/callback"

# Provides services for music library management and organization in Spotify.
def dump_playlist_contents(auth_manager, playlistId, indexStart=1, indexEnd=PLAYLIST_MAX_SONG_COUNT):

    try:
        spotify = spotipy.Spotify(auth_manager=auth_manager)

        res = spotify.playlist_items(playlistId, fields="next,items(added_at,added_by.id,track(name,href,artists(name,href),show(name,href)")

        playlistTracks = res["items"]
        try:
            while res["next"]:
                res = spotify.next(res)
                playlistTracks.extend(res["items"])

        except KeyError:
            raise Exception("Next page of results not found.")

        info = spotify.playlist(playlistId, fields="tracks.total,name,owner.display_name")

        print("Total tracks: " + str(info["tracks"]["total"]) + " Playlist: " + info["name"] + "Owned by: " + info["owner"]["display_name"])
        if indexEnd == PLAYLIST_MAX_SONG_COUNT:
            indexEnd = len(playlistTracks)
        for index in range(indexStart, indexEnd+1):
            song = playlistTracks[index-1]
            artists = ", ".join([a["name"] for a in song["track"]["artists"]])
            print(str(index) + ".\t" + song["track"]["name"] + "\t" + artists + "\t" + song["added_at"] + "\t" + song["added_by"]["id"])

    except spotipy.SpotifyOauthError as err: # possible
        raise Exception("Whoops. Error authenticating with Spotify") #spotipy.SpotifyOauthError(err.message, err.error, err.error_description)

    except spotipy.SpotifyException as err:
       raise Exception("Whoops. The Spotify client experienced an error.") #spotipy.SpotifyException(err.http_status, err.code, err.msg, err.reason)

    return True

# Returns a playlist with items re-arranged in a random order.

def chunked_list(lst, chunk_size):
        for i in range(0, len(lst), chunk_size):
            yield lst[i:i + chunk_size]

def shuffle_playlist(auth_manager, playlistId):

    try:
        #client_id, client_secret = read_secrets_file("secrets.txt")
        spotify = spotipy.Spotify(auth_manager=auth_manager)

        res = spotify.playlist_items(playlistId, fields="next,items(track(id))")

        playlistTracks = res["items"]
        try:
            while res["next"]:
                res = spotify.next(res)
                playlistTracks.extend(res["items"])
        except KeyError:
            raise Exception("Next page of results not found.")

        if len(playlistTracks) < 1 or len(playlistTracks[0]) < 1:
            return False # unable to retrieve data from Spotify API

        trackIds = []
        for song in playlistTracks:
            trackIds.append(song["track"]["id"])

        random.shuffle(trackIds)

        track_limit = 100
        for chunk in chunked_list(trackIds, track_limit):
            spotify.playlist_remove_all_occurrences_of_items(playlistId, chunk)
            spotify.playlist_add_items(playlistId, chunk)

    except spotipy.SpotifyOauthError as err: # possible
        raise Exception("Whoops. Error authenticating with Spotify") #spotipy.SpotifyOauthError(err.message, err.error, err.error_description)

    except spotipy.SpotifyException as err:
       raise Exception("Whoops. The Spotify client experienced an error.") #spotipy.SpotifyException(err.http_status, err.code, err.msg, err.reason)

    return True


# Returns a playlist with items sorted by artist name, grouping songs from the same album together
def sort_playlist_by_artistalbum(auth_manager, playlistId, ascendingTrue=True):

    try:
        spotify = spotipy.Spotify(auth_manager=auth_manager)

        res = spotify.playlist_items(playlistId, fields="next,items(track(id,artists(name),album(name)))")

        playlistTracks = res["items"]
        try:
            while res["next"]:
                res = spotify.next(res)
                playlistTracks.extend(res["items"])
        except KeyError:
            raise Exception("Next page of results not found.")

        if len(playlistTracks) < 1 or len(playlistTracks[0]) < 1:
            return False # unable to retrieve data from Spotify API

        array = []
        for song in playlistTracks:
            artist = song["track"]["artists"][0]["name"]
            album = song["track"]["album"]["name"]
            trackId = song["track"]["id"]
            array.append((artist, album, trackId))

        sorted_array = sorted(array, key=lambda t: t[0]+t[1], reverse=not ascendingTrue)

        trackIds = []
        for t in sorted_array:
            trackIds.append(t[2])

        track_limit = 100
        for chunk in chunked_list(trackIds, track_limit):
            spotify.playlist_remove_all_occurrences_of_items(playlistId, chunk)
            spotify.playlist_add_items(playlistId, chunk)

    except spotipy.SpotifyOauthError as err: # possible
        raise Exception("Whoops. Error authenticating with Spotify") #spotipy.SpotifyOauthError(err.message, err.error, err.error_description)

    except spotipy.SpotifyException as err:
       raise Exception("Whoops. The Spotify client experienced an error.") #spotipy.SpotifyException(err.http_status, err.code, err.msg, err.reason)

    return True

# Returns a playlist with items sorted by artist name
def sort_playlist_by_artist(auth_manager, playlistId, ascendingTrue=True):

    try:
        spotify = spotipy.Spotify(auth_manager=auth_manager)

        res = spotify.playlist_items(playlistId, fields="next,items(track(id,artists(name)))")

        playlistTracks = res["items"]
        try:
            while res["next"]:
                res = spotify.next(res)
                playlistTracks.extend(res["items"])
        except KeyError:
            raise Exception("Next page of results not found.")

        if len(playlistTracks) < 1 or len(playlistTracks[0]) < 1:
            return False # unable to retrieve data from Spotify API

        array = []
        for song in playlistTracks:
            artist = song["track"]["artists"][0]["name"]
            trackId = song["track"]["id"]
            array.append((artist, trackId))

        sorted_array = sorted(array, key=lambda t: t[0], reverse=not ascendingTrue)

        trackIds = []
        for t in sorted_array:
            trackIds.append(t[2])

        track_limit = 100
        for chunk in chunked_list(trackIds, track_limit):
            spotify.playlist_remove_all_occurrences_of_items(playlistId, chunk)
            spotify.playlist_add_items(playlistId, chunk)

    except spotipy.SpotifyOauthError as err: # possible
        raise Exception("Whoops. Error authenticating with Spotify") #spotipy.SpotifyOauthError(err.message, err.error, err.error_description)

    except spotipy.SpotifyException as err:
       raise Exception("Whoops. The Spotify client experienced an error.") #spotipy.SpotifyException(err.http_status, err.code, err.msg, err.reason)


    return True

def undo(playlistId):

    return False

# Uses the Playlist2Spreadsheet class to create a spreadsheet from a playlist URL
def create_playlist_spreadsheet(auth_manager, playlistId, filename, fieldlist=[]):
    return False
    """
    try:
        pl2spreadObj = Playlist2Spreadsheet()
        result = pl2spreadObj.export(playlistId, filename, fieldlist)

    except BaseException as e:
        return False
    """


