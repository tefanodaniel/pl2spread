from django.urls import path

from . import views

app_name = "pl2spread"
urlpatterns = [
    path("", views.index, name="index"),
    path("authorize", views.spotify_login, name="authorize"),
    path("authorize/callback", views.spotify_callback, name="authorize-callback"),
    path("complete_action", views.complete_action, name="complete_action"),
    path("callback_action/<str:action>/<int:result>", views.callback_action, name="callback_action"),
    path("spreadsheet/<str:py_url>/<str:params>/", views.spreadsheet, name="spreadsheet")
]