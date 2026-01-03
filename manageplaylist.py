import spotipy
from spotipy.oauth2 import SpotifyOAuth
import random
import requests
import csv
import logging

logger = logging.getLogger("django")

PLAYLIST_MAX_SONG_COUNT=10000
MAX_BUFFER_SIZE = 50
cached = {"artists": dict() } # { "artists": {"id": {name: string, genres: string[], popularity: int }}}

# Provides services for music library management and organization in Spotify.

"""
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
"""

def fetch_artist_metadata(auth_manager, artist_ids):
    artists_string = ""
    if len(artist_ids) > 1:
        artists_string = ",".join(artist_ids)
    else:
        artists_string = artist_ids[0]

    token = auth_manager.get_access_token(as_dict=False)
    # print(token)
    r = requests.get(f"https://api.spotify.com/v1/artists",
                  headers={"Authorization": f"Bearer {token}" },
                  params={"ids": artists_string})

    if r.status_code != 200:
        # print("Error retrieving information from Spotify API") TODOTODOTODO: Should be a log statement but not configured :/
        r.raise_for_status()
        return []
    return r.json()

def chunked_list(lst, chunk_size):
        for i in range(0, len(lst), chunk_size):
            yield lst[i:i + chunk_size]

def get_artist_metadata(auth_manager, artist_ids):
    MAX_NUM_IDS = 20 # v1 API can handle up to 20 ids at a time
    info ={"artists": []}
    result = {} # {"id": {"name": string, "genres": string[], "popularity": int}}
    #ids = list(set(ids))
    for chunk in chunked_list(artist_ids, MAX_NUM_IDS):
        info["artists"].extend(fetch_artist_metadata(auth_manager, chunk)["artists"])

    # TODO: Why aren't we just returning info object? Why do we need to create a result object?
    if len(info["artists"]) > 0:
        for i in info["artists"]:
            result[i["id"]] = {"name": i["name"], "genres": i["genres"], "popularity": i["popularity"]}
    return result

def add_track_metadata(auth_manager, model, tracks):

    # Identifies what artists metadata is available in cache
    ids_not_in_cache = []
    for t in tracks:
        for a in t["track"]["artists"]:
            a["genres"] = []
            a["popularity"] = []
            if a["id"] in cached["artists"]:
                a["genres"] = cached["artists"][a["id"]]["genres"]
                a["popularity"] = cached["artists"][a["id"]]["popularity"]
            else:
                if a["id"] not in ids_not_in_cache:
                    ids_not_in_cache.append(a["id"])
        model.append(t["track"])

    if len(ids_not_in_cache) == 0:
        pass
    else:
        # Do cache update with ids not found in cache
        artist_infos = get_artist_metadata(auth_manager, ids_not_in_cache)
        cached["artists"].update(artist_infos)

        num_artists_cached = len(artist_infos) # Log number of artists that were added to cache this round
        if num_artists_cached > 0:
            print(f"Cached {num_artists_cached} artists this round.")

    # Add new metadata retrieved to tracks
    for t in tracks:
        for a in t["track"]["artists"]:
            if a["id"] in cached["artists"]:
                a["genres"] = cached["artists"][a["id"]]["genres"] if cached["artists"][a["id"]]["genres"] else "n/a"
                a["popularity"] = cached["artists"][a["id"]]["popularity"] if cached["artists"][a["id"]]["popularity"] else "n/a"
            else:
                # shouldn't get here because the cache was updated and we have the artists information now
                print("ERROR -- Cache malfunction! Unable to find artist information post-reload.")
                a["genres"] = []
                a["popularity"] = []

def make_playlist_model(auth_manager, playlist_id):
    model = []
    offset = 0
    while True: # Request list of Tracks on playlist from Spotify API
        try:
            spotify = spotipy.Spotify(auth_manager=auth_manager)
            playlist_items = spotify.playlist_items(playlist_id,
                                      offset=offset,
                                      fields='items.track(name,artists(name,id),album(name,release_date),popularity),total',
                                      additional_types=['track'])

            if len(playlist_items['items']) == 0:
                break

            add_track_metadata(auth_manager, model, playlist_items["items"])

            offset = offset + len(playlist_items['items']) # print(offset, "/", playlist_items['total'])

        except spotipy.SpotifyOauthError as err: # possible
            raise spotipy.SpotifyOauthError(err.message, err.error, err.error_description)

        except spotipy.SpotifyException as err:
            raise spotipy.SpotifyException(err.http_status, err.code, err.msg, err.reason)

    return model

def export_and_get_datatable(auth_manager, playlist_id, filename="", fieldlist=[]):

    playlist = {"data": [], "metadata": {}}
    if (len(fieldlist) == 0):
        fieldlist = ["track_title", 'artist_name','album_title','release_year','artist_genres','artist_popularity',"song_popularity"]
        #fieldlist.append(["added_at", "added_by"])
    playlist["data"].append({"fields": fieldlist}) # First entry in data object is dict of fieldnames

    for track in make_playlist_model(auth_manager, playlist_id):
        tr = {}
        if "track_title" in fieldlist:
            tr["track_title"] = track["name"]
        if "artist_name" in fieldlist:
            tr["artist_name"] = ";".join([a["name"] for a in track["artists"]])
        if "album_title" in fieldlist:
            tr["album_title"] = track["album"]["name"]
        if "release_year" in fieldlist:
            tr["release_year"] = track["album"]["release_date"]
        if "artist_genres" in fieldlist:
            a_genres = set()
            for a in track["artists"]:
                for g in a["genres"]:
                    a_genres.add(g)
            tr["artist_genres"] = ";".join(a_genres)
        if "artist_popularity" in fieldlist:
            tr["artist_popularity"] = ";".join([str(a["popularity"]) for a in track["artists"]])
        if "song_popularity" in fieldlist:
            tr["song_popularity"] = track["popularity"]

        playlist["data"].append(tr)
    try:
        spotify = spotipy.Spotify(auth_manager=auth_manager)
        res = spotify.playlist(playlist_id, fields="tracks.total,name,owner.display_name")

    except spotipy.SpotifyException as err:
        # do something
        pass
    else:
        playlist["metadata"]["total_tracks"] = res["tracks"]["total"]
        playlist["metadata"]["name"] = res["name"]
        playlist["metadata"]["owner_display_name"] = res["owner"]["display_name"]

    logger.debug("---- Entering log for Manageplaylist.py -----")
    logger.debug("---- Entering log for Manageplaylist.py -----")
    logger.debug("\n")
    logger.debug("Code line: 199")
    logger.debug(f"Showing playlist data to be written to file: {filename}")
    logger.debug(playlist["metadata"])
    logger.debug(playlist["data"][0:5])
    logger.debug("---- Exiting log ----")
    logger.debug("---- Exiting log ----")
    logger.debug("---- Exiting log ----")
    logger.debug("---- Exiting log ----")

    if filename != "":
        with open(filename, 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldlist)
            writer.writeheader()
            for row in playlist["data"][1:]:
                writer.writerow(row)
    return playlist

# Returns a playlist with items re-arranged in a random order.
def shuffle_playlist(auth_manager, playlistId):

    try:
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