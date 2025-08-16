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

def spotify_oauth2(request): # utility function - not a view
    scopes = "playlist-read-private playlist-read-collaborative playlist-modify-private playlist-modify-public"

    oauth = SpotifyOAuth(client_id=ManagePlaylist.client_id,
                                client_secret=ManagePlaylist.client_secret,
                                redirect_uri=ManagePlaylist.redirect_uri,
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
        return HttpResponseRedirect(reverse("pl2spread:index")) # POST successful login attempt to INDEX - pl2spread

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
    # Validate request parameters
    if len(request.POST) == 0:
        return Http404("No data submitted to the server. Try submitting the form again!")
    try:
        auth_manager = spotify_oauth2(request) # verify what this does when it fails... ie the application is not authorized already

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
        if action in ["shuffle", "order-artistalbum", "order-artist"]:
            try:
                token_info = request.session['token_info']
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

        elif action == "create-csv":

            if False: #WIP
                return HttpResponseRedirect(reverse("pl2spread:callback_action", kwargs={"action": action, "result": int(0)}))
            else:
                params = "" + f"track_title={all_field_names[0]}?" # bc should always be returned with sheet
                for k,v in request.POST.items():
                    if k not in ["playlist_url", "csrftoken", "csrfmiddlewaretoken"]:
                        params += k + "=" + v + "?"

                return HttpResponseRedirect(reverse("pl2spread:spreadsheet", kwargs={"py_url": py_url, "params": params}))

        else:
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
        return HttpResponse(f"Our apologies for the inconvenience, an error has occurred with the application.\n\n{err}")

    else:
        context = {
            "playlist_info": playlist_obj["metadata"],
            "table_headers": playlist_obj["data"][0]["fields"][:-1], # getting an empty item for an additional entry in the table headers list... hacky fix
            "table_entries": playlist_obj["data"][1:],
            "filepath": temp_filepath
        }
        return render(request, "pl2spread/spreadsheet.html", context)
