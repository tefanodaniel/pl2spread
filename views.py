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

def read_secrets_file(filename):
    with open(filename, "r") as file:
        line = file.readline()
        first = line.strip().split("=")[1]
        line = file.readline()
        second = line.strip().split("=")[1]
    return (first, second)

def spotify_oauth2(request): # utility function - not a view
    scopes = "playlist-read-private playlist-read-collaborative playlist-modify-private playlist-modify-public"
    redirect_uri = "http://127.0.0.1:8000/pl2spread/authorize/callback"
    client_id, client_secret = read_secrets_file("pl2spread/secrets")

    oauth = SpotifyOAuth(client_id=client_id,
                                client_secret=client_secret,
                                redirect_uri=redirect_uri,
                                scope=scopes,
                                cache_handler=DjangoSessionCacheHandler(request))
    return oauth

def spotify_login(request):
    auth_url = spotify_oauth2(request).get_authorize_url()
    return HttpResponseRedirect(auth_url)

def spotify_callback(request):
    try:
        code = request.GET["code"]
        request.session["token"] = spotify_oauth2(request).get_access_token(code)

        return HttpResponseRedirect(reverse("pl2spread:index"))

    except KeyError as KE:
        django.debug(KE)
        return Http404("Authentication failed.")

def index(request):
    context = {
        "all_field_names": all_field_names[1:],
        "action": "",
        "result": 0
    }
    return render(request, "pl2spread/index.html", context)

def callback_action(request, action, result):
    context = {
        "all_field_names": all_field_names[1:],
        "action": action,
        "result": "success" if result else "failed"
    }
    return render(request, "pl2spread/index.html", context)

# Handles tools requests and redirects to main tools page.
def complete_action(request):
    
    if len(request.POST) == 0: # Validate request parameters
        return Http404("No data submitted to the server. Try submitting the form again!")
    try:
        action = request.POST["action"]
        posted_url = request.POST["playlist_url"]
        r = re.compile(r"^.*[:\/]playlist[:\/]([a-zA-Z0-9]+).*$")
        m = r.match(posted_url)
        py_url = ""
        if m:
            py_url = m.group(1)
        else:
            # This should be an actual page with a link back to the home page.
            return HttpResponse("Not a valid URL or URI to a Spotify playlist. (%s)" % posted_url)

        if action in ["shuffle", "order-artistalbum", "order-artist", "create-csv"]: # Complete tool action based on request type.
            try:
                token_info = request.session['token_info']
                auth_manager = spotify_oauth2(request)

            except KeyError:
                django.debug("Token not found in the session")
                return HttpResponseRedirect(reverse("pl2spread:authorize"))

            if action == "shuffle":
                action_success = ManagePlaylist.shuffle_playlist(auth_manager, py_url)
                return HttpResponseRedirect(reverse("pl2spread:callback_action", kwargs={"action": action, "result": int(action_success)}))

            if action == "order-artistalbum":
                action_success = ManagePlaylist.sort_playlist_by_artistalbum(auth_manager, py_url)
                return HttpResponseRedirect(reverse("pl2spread:callback_action", kwargs={"action": action, "result": int(action_success)}))

            if action == "order-artist":
                action_success = ManagePlaylist.sort_playlist_by_artist(auth_manager, py_url)
                return HttpResponseRedirect(reverse("pl2spread:callback_action", kwargs={"action": action, "result": int(action_success)}))

            if action == "create-csv":
                params = "" + f"track_title={all_field_names[0]}?" # bc should always be returned with sheet
                for k,v in request.POST.items():
                    if k not in ["playlist_url", "csrftoken", "csrfmiddlewaretoken", "action"]:
                       params += k + "=" + v + "?"
                return HttpResponseRedirect(reverse("pl2spread:spreadsheet", kwargs={"py_url": py_url, "params": params}))

        else:
            django.debug(err)
            return HttpResponse("No tool action selected before form submission.")

    except Exception as err:
        django.debug(err)
        return HttpResponse("Our apologies for the inconvenience, an error has occurred with the application.")
        #raise err

def spreadsheet(request, py_url, params):
    try:
        fields=[]
        for kv in params.split("?"): # key=value
            fields.append(kv.split("=")[0])

        temp_filepath = f"{settings.STATIC_ROOT}/pl2spread/tmp/data-{py_url}.csv"
        auth_manager = spotify_oauth2(request)
        playlist_obj = ManagePlaylist.export_and_get_datatable(auth_manager, py_url, filename=temp_filepath, fieldlist=fields)

    except Exception as err:
        django.debug(err) # if no params or filepath corrupted
        return HttpResponse(f"Our apologies for the inconvenience, an error has occurred with the application.\n\n{err}")

    context = {
        "playlist_info": playlist_obj["metadata"],
        "table_headers": playlist_obj["data"][0]["fields"][:-1], # getting an empty item for an additional entry in the table headers list... hacky fix
        "table_entries": playlist_obj["data"][1:],
        "filepath": temp_filepath
    }
    return render(request, "pl2spread/spreadsheet.html", context)
