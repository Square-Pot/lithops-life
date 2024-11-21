from django.urls import path
from . import views

urlpatterns = [
    path("", views.index_view, name="marathons"),
    path("contest/<str:contestant_short_name>", views.contestant_view, name="contestant"),
    path("<str:marathon_name>", views.marathon_view, name="marathon"),   
]