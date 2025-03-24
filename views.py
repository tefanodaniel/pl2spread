from django.shortcuts import render
from django.http import HttpResponse
from pl2spread.playlist2spreadsheet import Playlist2Spreadsheet

def index(request):

    all_field_names = {
        'track_title',
        'artist_name',
        'album_title',
        'release_year',
        'artist_genres',
        'artist_popularity',
        'song_popularity'
    }

    context = {
        "all_field_names": all_field_names
    }

    return render(request, "pl2spread/index.html", context)

def spreadsheet(request, py_url):

    all_field_names = {
        'track_title',
        'artist_name',
        'album_title',
        'release_year',
        'artist_genres',
        'artist_popularity',
        'song_popularity'
    }

    p = Playlist2Spreadsheet()

    table_entries = p.scrape_playlist(py_url)

    context = {
        "field_list": all_field_names,
        "table_entries": table_entries
    }
    return render(request, "pl2spread/spreadsheet.html", context)