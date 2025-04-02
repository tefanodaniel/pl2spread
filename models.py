from django.db import models

# Create your models here.
class Playlists(models.Model):
    playlist_id = models.CharField(max_length=200, primary_key=True,
                                        db_column="playlist_id")

    def __str__(self):
        return " ".join("playlist_id:", playlist_id)

class Tracks(models.Model):
    # DEFAULT_AUTO_FIELD
    track_id = models.BigAutoField(primary_key=True, db_column="track_id")
    track_title = models.CharField(max_length=200)
    artist_name = models.CharField(max_length=200)
    album_title = models.CharField(max_length=200)
    release_year = models.DateTimeField()
    artist_genres = models.CharField(max_length=200)
    artist_popularity = models.CharField(max_length=100)
    song_popularity = models.CharField(max_length=100)

    def __str__(self):
        return " ".join("{ track_title:", self.track_title, "artist_name:", self.artist_name, "album_title:",
                        self.album_title, "release_year:", self.release_year, "artist_genres:", self.artist_genres,
                        "artist_popularity:", self.artist_popularity, "song_popularity:", self.song_popularity,
                        "track_id:", str(self.track_id), "}")

class TracksPlaylist(models.Model):
    pk = models.CompositePrimaryKey("playlist_id", "track_id")
    playlist_id = models.ForeignKey(Playlists, on_delete=models.CASCADE, db_column="playlist_id")
    track_id = models.ForeignKey(Tracks, on_delete=models.CASCADE, db_column="track_id")

    def __str__(self):
        return " ".join("playlist_id:", playlist_id, "track_id:", track_id)