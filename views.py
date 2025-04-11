from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
import logging, re

from pl2spread.playlist2spreadsheet import Playlist2Spreadsheet

all_field_names = [
        'track_title',
        'artist_name',
        'album_title',
        'release_year',
        'artist_genres',
        'artist_popularity',
        'song_popularity'
    ]

def index(request):

    context = {
        "all_field_names": all_field_names
    }
    return render(request, "pl2spread/index.html", context)

def create_spreadsheet(request):
    params = ""
    for k,v in request.POST.items():
        if k not in ["playlist_url", "csrftoken", "csrfmiddlewaretoken"]:
            params += k + "=" + v + "?"

    response = HttpResponseRedirect(reverse("pl2spread:spreadsheet", kwargs={"py_url": request.POST["playlist_url"], "params": params}))
    return response

def spreadsheet(request, py_url, params):
    fields=[]
    for kv in params.split("?"): # key=value
        fields.append(kv.split("=")[0])
    p = Playlist2Spreadsheet()
    table_entries = p.export(py_url, filename="", fieldlist=fields)
    context = {
        "table_headers": table_entries[0],
        "table_entries": table_entries[1:]
    }
    return render(request, "pl2spread/spreadsheet.html", context)
