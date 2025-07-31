from django.urls import path

from . import views

app_name = "pl2spread"
urlpatterns = [
    path("", views.index, name="index"),
    path("authorize", views.spotify_login, name="authorize"),
    path("authorize/callback", views.spotify_callback, name="authorize-callback"),
    path("complete_action", views.complete_action, name="complete_action"),
    path("spreadsheet", views.create_spreadsheet, name="create_spreadsheet"),
    path("spreadsheet/<str:py_url>/<str:params>/", views.spreadsheet, name="spreadsheet")
]