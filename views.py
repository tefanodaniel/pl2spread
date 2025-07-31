from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.urls import reverse
from django.conf import settings

import spotipy
from spotipy.oauth2 import SpotifyOAuth
from spotipy import SpotifyOauthError as SpotifyOauthError
from spotipy import SpotifyException as SpotifyException
from spotipy.cache_handler import DjangoSessionCacheHandler

import logging
from datetime import datetime
import random
import string
import re

import requests

from pl2spread.playlist2spreadsheet import Playlist2Spreadsheet, read_secrets_file
import pl2spread.manageplaylist as ManagePlaylist

#logger = logging.getLogger("pl2spread.views")
django = logging.getLogger("django")

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

def generate_random_string(length):
    characters = string.ascii_letters + string.digits  # Letters and digits
    return ''.join(random.choices(characters, k=length))

def spotify_oauth2(request): # utility function - not a view

    scopes = "playlist-read-private playlist-read-collaborative playlist-modify-private playlist-modify-public"

    oauth = SpotifyOAuth(client_id=ManagePlaylist.client_id,
                                client_secret=ManagePlaylist.client_secret,
                                redirect_uri=ManagePlaylist.REDIRECT_URI,
                                scope=scopes,
                                cache_handler=DjangoSessionCacheHandler(request))
    return oauth

def spotify_login(request):
    auth_url = spotify_oauth2(request).get_authorize_url()
    return HttpResponseRedirect(auth_url)

def spotify_callback(request):
    try:
        code = request.GET["code"]
        auth_manager = spotify_oauth2(request).get_access_token(code)
        django.debug(str(request.session))
        return HttpResponseRedirect(reverse("pl2spread:index")) # POST successful login attempt to INDEX - pl2spread

    except KeyError as KE:
        django.debug(KE)
        return Http404("Authentication failed.")

def index(request):
    context = {
        "all_field_names": all_field_names[1:],
    }

    return render(request, "pl2spread/index.html", context)

# Handles tools requests and redirects to main tools page.
def complete_action(request):

    # Validate request parameters
    if len(request.POST) == 0:
        return Http404("No data submitted to the server. Try submitting the form again!")
    try:
        django.debug(str(request.session))

        auth_manager = spotify_oauth2(request)

        django.debug(str(request.session))

        posted_url = request.POST["playlist_url"]
        r = re.compile(r"^.*[:\/]playlist[:\/]([a-zA-Z0-9]+).*$")
        m = r.match(posted_url)
        py_url = ""
        if m:
            py_url = m.group(1)
        else:
            return HttpResponse("Not a valid URL to a Spotify playlist. (%s)" % posted_url)

        # Complete tool action based on request type.
        action = request.POST["action"]

        # (TODO: Should be a switch statement here)
        if action == "shuffle":
            result = ManagePlaylist.shuffle_playlist(auth_manager, py_url)
            if result:
                return HttpResponse("Successfully shuffled playlist.")
            else:
                return HttpResponse("Unable to shuffle playlist for some reason.")

        elif action == "order-artistalbum":
            result = ManagePlaylist.sort_playlist_by_artistalbum(auth_manager, py_url)
            if result:
                return HttpResponse("Successfully sorted playlist by artist name and album.")

        elif action == "order-artist":
            result = ManagePlaylist.sort_playlist_by_artist(auth_manager, py_url)
            if result:
                return HttpResponse("Successfully sorted playlist by artist name.")

        elif action == "create-csv":
            return create_spreadsheet(auth_manager, request)

        else:
            return HttpResponse("No tool action selected before form submission.")

    except Exception as err:
        django.debug(err)
        #return HttpResponse("Our apologies for the inconvenience, an error has occurred with the application.")
        raise err

    context = {}
    return render(request, "pl2spread/action_redirect.html", context)

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
        return HttpResponse("Our apologies for the inconvenience, an error has occurred with the application.")

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
        return HttpResponse("Our apologies for the inconvenience, an error has occurred with the application.")

    else:
        context = {
            "playlist_info": playlist["metadata"],
            "table_headers": playlist["data"][0]["fields"][:-1], # getting an empty item for an additional entry in the table headers list... hacky fix
            "table_entries": playlist["data"][1:],
            "filepath": filepath
        }
        return render(request, "pl2spread/spreadsheet.html", context)
