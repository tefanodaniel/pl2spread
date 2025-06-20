#from pl2spread.playlist2spreadsheet import Playlist2Spreadsheet
from pl2spread.playlist2spreadsheet import Playlist2Spreadsheet

# Provides services for music library management and organization in Spotify.
class ManagePlaylist:

    # Returns a playlist with items re-arranged in a random order.
    def shuffle_playlist(self, playlistId):

        if 2+2 == 5:
            return True # Success
        else:
            return False

    # Returns a playlist with items sorted by artist name, grouping songs from the same album together
    def sort_playlist_by_artistalbum(self, playlistId, ascendingTrue=True):
        return False

    # Returns a playlist with items sorted by artist name
    def sort_playlist_by_artist(self, playlistId, ascendingTrue=True):
        return False

    # Uses the Playlist2Spreadsheet class to create a spreadsheet from a playlist URL
    def create_playlist_spreadsheet(self, playlistId, filename, fieldlist=[]):
        return False
        """
        try:
            pl2spreadObj = Playlist2Spreadsheet()
            result = pl2spreadObj.export(playlistId, filename, fieldlist)

        except BaseException as e:
            return False
        """