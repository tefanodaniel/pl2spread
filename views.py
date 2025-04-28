from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.urls import reverse
from django.conf import settings
from spotipy import SpotifyOauthError as SpotifyOauthError
from spotipy import SpotifyException as SpotifyException
import re

from pl2spread.playlist2spreadsheet import Playlist2Spreadsheet, read_secrets_file

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

    if len(request.POST) == 0:
        return Http404("No data submitted to the server. Try submitting the form again!")

    try:
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

        return HttpResponseRedirect(reverse("pl2spread:spreadsheet", kwargs={"py_url": py_url, "params": params}))

    except Exception as err:
        return HttpResponse("Apologies for the inconvenience, an error has occurred with the application.")

def spreadsheet(request, py_url, params):

    filepath = f"pl2spread/tmp/data-{py_url}.csv"
    client_id, client_secret = read_secrets_file("/home/tefanodaniel/mysite/pl2spread/secrets.txt")

    try:
        fields=[]
        for kv in params.split("?"): # key=value
            fields.append(kv.split("=")[0])

        p = Playlist2Spreadsheet(client_id, client_secret)
        playlist = p.export(py_url, filename=f"{settings.STATIC_ROOT}/{filepath}", fieldlist=fields)

    except SpotifyOauthError as err:
        # return error view
        return HttpResponse("We experienced a back-end systems error when accessing the Spotify application.")

    except SpotifyException as err:
        return HttpResponse("We experienced a back-end systems error when accessing the Spotify application.")

    except Exception as err:
        return HttpResponse("Apologies for the inconvenience, an error has occurred with the application.")

    else:
        context = {
            "playlist_info": playlist["metadata"],
            "table_headers": playlist["data"][0]["fields"][:-1], # getting an empty item for an additional entry in the table headers list... hacky fix
            "table_entries": playlist["data"][1:],
            "filepath": filepath
        }
        return render(request, "pl2spread/spreadsheet.html", context)
