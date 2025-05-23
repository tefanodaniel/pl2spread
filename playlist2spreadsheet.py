import requests, csv
from pprint import pprint
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import logging

logger = logging.getLogger() # make errors go here

def read_secrets_file(filename):

  client_id = ""
  client_secret = ""

  with open(filename, 'r') as file:
      # Read the file line by line
      lines = file.readlines()
      for line in lines:
        line = line.strip()
        if line.find("client_id") != -1:
          client_id = line[line.find("client_id")+len("client_id")+1:]
        if line.find("client_secret") != -1:
          client_secret = line[line.find("client_secret")+len("client_secret")+1:]

  return (client_id, client_secret)

class Playlist2Spreadsheet:

  MAX_BUFFER_SIZE = 50

  cached = {"artists": dict() } # { "artists": {"id": {name: string, genres: string[], popularity: int }}}

  def __init__(self, client_id, client_secret):
    self.sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=client_id,
                                                           client_secret=client_secret))
    self.client_id = client_id
    self.client_secret = client_secret
    self.access_token = ""

  """
  Main class function. Gets list of Tracks in Spotify playlist with the playlist id provided.
  """
  def tracks_list(self, playlist_id):
      items = []
      offset = 0
      while True: # Request list of Tracks on playlist from Spotify API
          try:
              playlist_items = self.sp.playlist_items(playlist_id,
                                          offset=offset,
                                          fields='items.track(name,artists(name,id),album(name,release_date),popularity),total',
                                          additional_types=['track'])

          except spotipy.SpotifyOauthError as err: # possible
              raise spotipy.SpotifyOauthError(err.message, err.error, err.error_description)

          except spotipy.SpotifyException as err:
              raise spotipy.SpotifyException(err.http_status, err.code, err.msg, err.reason)

          else:
              if len(playlist_items['items']) == 0:
                  break

              self.get_additional_track_metadata(items, playlist_items["items"])

              offset = offset + len(playlist_items['items']) # print(offset, "/", playlist_items['total'])

      return items

  """
  Gets additional metadata from API and caches it for later use.

  Additional info:
      artist genres
      artist popularity

  """
  def get_additional_track_metadata(self, model, tracks):

      ids = []
      for t in tracks:
          for a in t["track"]["artists"]:
            a["genre"] = []
            a["popularity"] = []
            if a["id"] in self.cached["artists"]:
              a["genres"] = self.cached["artists"][a["id"]]["genres"]
              a["popularity"] = self.cached["artists"][a["id"]]["popularity"]
            else:
              if a["id"] not in ids:
                ids.append(a["id"])
          model.append(t["track"])

      if len(ids) > 0:
        artist_infos = self.get_artists_info(ids)
        self.cached["artists"].update(artist_infos)
        num_artists_cached = len(artist_infos)
        if num_artists_cached > 0:
          print(f"Cached {num_artists_cached} artists this round.")

      for t in tracks: # Do update again for tracks not in cache originally
        for a in t["track"]["artists"]:
            if a["id"] in self.cached["artists"]:
              a["genres"] = (self.cached["artists"][a["id"]]["genres"])
              a["popularity"] = (self.cached["artists"][a["id"]]["popularity"])
            else:
              # shouldn't get here because the cache was updated and we have the artists information now
              print("ERROR -- Cache malfunction! Unable to find artist information post-reload.")
              a["genres"] = []
              a["popularity"] = []


  def artists_info_from_api(self, artists):

      artists_string = ""
      if len(artists) > 1:
        artists_string = ",".join(artists)
      else:
        artists_string = artists[0]

      # authenticate
      r = requests.post(url="https://accounts.spotify.com/api/token",
                        headers={"Content-Type": "application/x-www-form-urlencoded"},
                        data={"grant_type": "client_credentials",
                              "client_id": self.client_id,
                              "client_secret": self.client_secret})
      if r.status_code != 200:
        print(f"Error seeking credentials from Spotify server. {r.status_code}")
        return []
      self.access_token = r.json()["access_token"]
      r = requests.get(f"https://api.spotify.com/v1/artists",
                      headers={"Authorization": f"Bearer {self.access_token}" },
                      params={"ids": artists_string})
      if r.status_code != 200:
        print("Error retrieving information from Spotify API")
        r.raise_for_status()
        return []
      return r.json()

  def get_artists_info(self, ids):

      info ={"artists": []}
      result = {} # {"id": {"name": string, "genres": string[], "popularity": int}}
      #ids = list(set(ids))

      MAX_NUM_IDS = 20 # v1 API can handle up to 20 ids at a time

      def chunked_list(lst, chunk_size):
        for i in range(0, len(lst), chunk_size):
            yield lst[i:i + chunk_size]

      if len(ids) == 0:
        pass

      elif len(ids) <= MAX_NUM_IDS:
        info = self.artists_info_from_api(ids)

      else:
        for chunk in chunked_list(ids, MAX_NUM_IDS):
          info["artists"].extend(self.artists_info_from_api(chunk)["artists"])

      # TODO: Why aren't we just returning info object? Why do we need to create a result object?
      if len(info["artists"]) > 0:
        for i in info["artists"]:
            result[i["id"]] = {"name": i["name"], "genres": i["genres"], "popularity": i["popularity"]}
      return result

  def export(self, playlist_id: str, filename="", fieldlist=[]):

      playlist = {"data": [], "metadata": {}}

      if (len(fieldlist) == 0):
        fieldlist = ["track_title",'artist_name','album_title','release_year','artist_genres','artist_popularity',"song_popularity"]
      playlist["data"].append({"fields": fieldlist}) # First entry in data object is dict of fieldnames

      items = self.tracks_list(playlist_id)

      for track in items:
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

      del items

      try:
          response = self.sp.playlist(playlist_id, fields="tracks.total,name,owner.display_name")
      except spotipy.SpotifyException as err:
          # do something
          pass
      else:
          playlist["metadata"]["total_tracks"] = response["tracks"]["total"]
          playlist["metadata"]["name"] = response["name"]
          playlist["metadata"]["owner_display_name"] = response["owner"]["display_name"]

      if filename != "":
        with open(filename, 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldlist)
            writer.writeheader()
            for row in playlist["data"][1:]:
              writer.writerow(row)

      return playlist

if __name__ == "__main__":
    short_tp = 'spotify:playlist:7wtTPHDLubKGXneN0E45iH'

    playlist2spreadsheet = Playlist2Spreadsheet()
    p1 = playlist2spreadsheet.export(short_tp)
    pprint(p1)