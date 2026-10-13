from django.urls import path
from . import views

urlpatterns = [
    path("contest/<str:contestant_short_name>", views.contestant_view, name="contestant"),
    path("<str:marathon_name>", views.marathon_view, name="marathon"),
    path("<str:marathon_name>/nomination/<int:pk>", views.nomination_view, name="nomination"),
]