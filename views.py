from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.urls import reverse
from django.db import models
from django.conf import settings
import logging, re

from pl2spread.playlist2spreadsheet import Playlist2Spreadsheet

# 0th FIELD ALWAYS TRACK_TITLE
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
        "all_field_names": all_field_names[1:]
    }
    return render(request, "pl2spread/index.html", context)

def create_spreadsheet(request):

    field_value = request.POST["playlist_url"]
    r = re.compile(r"^.*[:\/]playlist[:\/]([a-zA-Z0-9]+).*$")
    m = r.match(field_value)
    py_url = ""
    if m:
        py_url = m.group(1)
    else:
        #raise Http404("Not a valid URL to a Spotify playlist.")
        return HttpResponse("Not a valid URL to a Spotify playlist. (%s)" % field_value)

    params = "" + f"track_title={all_field_names[0]}?"
    for k,v in request.POST.items():
        if k not in ["playlist_url", "csrftoken", "csrfmiddlewaretoken"]:
            params += k + "=" + v + "?"

    response = HttpResponseRedirect(reverse("pl2spread:spreadsheet", kwargs={"py_url": py_url, "params": params}))
    return response

def spreadsheet(request, py_url, params):
    fields=[]
    for kv in params.split("?"): # key=value
        fields.append(kv.split("=")[0])

    filepath = f"pl2spread/tmp/data-{py_url}.csv"
    p = Playlist2Spreadsheet()
    playlist = p.export(py_url, filename=f"{settings.STATIC_ROOT}/{filepath}", fieldlist=fields)
    context = {
        "playlist_info": playlist["metadata"],
        "table_headers": playlist["data"][0]["fields"],
        "table_entries": playlist["data"][1:],
        "filepath": filepath
    }
    return render(request, "pl2spread/spreadsheet.html", context)

def download(request):
    return
    #return FileResponse(openfile, "as_attachment"=True, filename=)
