"""
import models

class Pl2SpreadDb:

    def __init__(self):
        pass

    def save(self, playlist_id, model):

      # save a new playlist to the Db
      if not Playlists.objects.filter(playlist_id=playlist_id).exists():
          p = Playlist(playlist_id=playlist_id)
          p.save()

      for track in model:
          pass
      #
      # if track not in Tracks database
      #
      # then insert into Tracks, also insert into TracksPlaylist
      #
      # if track found in Tracks database
      #
      # then insert (track_id, playlist_id) into TracksPlaylist
      #
"""