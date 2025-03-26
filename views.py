from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse

from pl2spread.playlist2spreadsheet import Playlist2Spreadsheet

def index(request):

    all_field_names = [
        'track_title',
        'artist_name',
        'album_title',
        'release_year',
        'artist_genres',
        'artist_popularity',
        'song_popularity'
    ]

    context = {
        "all_field_names": all_field_names
    }

    return render(request, "pl2spread/index.html", context)


def create_spreadsheet(request):

    playlist_url = request.POST["playlist_url"]

    response =  HttpResponseRedirect(reverse("pl2spread:spreadsheet", kwargs={"py_url": playlist_url}))

    for field, value in request.POST.items():
            response.set_cookie(field, value)

    return response


def spreadsheet(request, py_url):

    fields = []
    for field, value in request.COOKIES.items():
        if field != "playlist_url" or "csrftoken" or "csrfmiddlewaretoken":
            fields.append(value)

    p = Playlist2Spreadsheet(py_url)

    table_entries = p.write_data_to_file(fieldlist=fields)

    context = {
        "table_headers": table_entries[0],
        "table_entries": table_entries[1:]
    }
    return render(request, "pl2spread/spreadsheet.html", context)

