from django.urls import path

from . import views

app_name = "pl2spread"
urlpatterns = [
    path("", views.index, name="index"),
    path("spreadsheet", views.create_spreadsheet, name="create_spreadsheet"),
    path("spreadsheet/<str:py_url>/<str:params>/", views.spreadsheet, name="spreadsheet")
]