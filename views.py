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

    p = Playlist2Spreadsheet(py_url)

    table_entries = p.write_data_to_file()

    context = {
        "field_list": all_field_names,
        "table_headers": table_entries[0]
        "table_entries": table_entries[1:]
    }
    return render(request, "pl2spread/spreadsheet.html", context)