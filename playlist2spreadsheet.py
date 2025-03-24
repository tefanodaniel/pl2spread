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

import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import requests
import csv

class Playlist2Spreadsheet:

  MAX_BUFFER_SIZE = 50

  def __init__(self, playlist_id, client_id="5469d6f0530444b094b670becf1ea407", client_secret="5b86a619674f4473a522c8bbcdb9c557"):

    self.client_id = client_id
    self.client_secret = client_secret

    self.cached = {"artists": dict() } # { "artists": {"id": {name: string, genres: string[], popularity: int }}}

    self.access_token = ""
    self.sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=self.client_id,
                                                           client_secret=self.client_secret))
    self.model = self.load_model(playlist_id)

  def api_get_artists(self, artists):

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

  """
  def get_average_artist_genres(artist_id):

      r = requests.get(f"https://api.spotify.com/v1/artists/{artist_id}/related-artists",
                      headers={"Authorization": f"Bearer {access_token}" })

      if r.status_code != 200:
        print(f"Error retrieving information from Spotify API for artist {artist_id}")
        return []

      response = r.json()

      average_genres = []
      g_occ = {} # {"genre": int}
      for a in response["artists"]:
        for g in a["genres"]:
          if g in g_occ:
            g_occ[g] += 1
          else:
            g_occ[g] = 1

      average_genres = [g for g in g_occ if g_occ[g] > 1]

      return average_genres
  """

  def get_artists_info(self, ids):


      response ={"artists": []}
      result = {} # {"id": {"name": string, "genres": string[], "popularity": int}}
      #ids = list(set(ids))

      MAX_NUM_IDS = 20 # v1 API can handle up to 20 ids at a time

      def chunked_list(lst, chunk_size):
        for i in range(0, len(lst), chunk_size):
            yield lst[i:i + chunk_size]

      if len(ids) == 0:
        pass

      elif len(ids) <= MAX_NUM_IDS:

        response = self.api_get_artists(ids)

      else:
        for chunk in chunked_list(ids, MAX_NUM_IDS):
          response["artists"].extend(self.api_get_artists(chunk)["artists"])

      # for a in response["artists"]:
      #   if a["genres"] == []:
      #     a["genres"] = get_average_artist_genres(a["id"])

      if len(response["artists"]) > 0:
        for a in response["artists"]:
            result[a["id"]] = {"name": a["name"], "genres": a["genres"], "popularity": a["popularity"]}
      return result


  def update(self, model, tracks):
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

        model.append(t["track"])


  def write_data_to_file(self, filename=""):

      output = []
      output.append({"track_title": str(),'artist_name': str(),'album_title': str(),'release_year': str(), 'artist_genres': str(), 'artist_popularity': str(), "song_popularity": str()})
      for track in self.model:
            title = track["name"]
            artists = ";".join([a["name"] for a in track["artists"]])
            release_year = track["album"]["release_date"]
            album_title = track["album"]["name"]

            a_genres = set()
            for a in track["artists"]:
              for g in a["genres"]:
                a_genres.add(g)

            artist_genres = ";".join(a_genres)
            artist_popularity = ";".join([str(a["popularity"]) for a in track["artists"]])
            song_popularity = track["popularity"]

            track_row = {"track_title": title, 'artist_name': artists, 'album_title': album_title,
                        'release_year': release_year, 'artist_genres': artist_genres, 'artist_popularity': artist_popularity,
                        "song_popularity": song_popularity}
            output.append(track_row)

      if filename != "":
        with open(filename, 'w', newline='') as csvfile:
            fieldnames = ["track_title",'artist_name','album_title','release_year', 'artist_genres', 'artist_popularity', "song_popularity"]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for row in output:
              writer.writerow(row)

      return output

  def load_model(self, playlist_id):

      offset = 0
      model = []

      while True:

          # Get base information about a set of tracks
          response = self.sp.playlist_items(playlist_id,
                                      offset=offset,
                                      fields='items.track(name,artists(name,id),album(name,release_date),popularity),total',
                                      additional_types=['track'])

          if len(response['items']) == 0:
              break

          # Insert new set of tracks into model bucket
          self.update(model, response["items"])

          offset = offset + len(response['items'])
          print(offset, "/", response['total'])
      return model