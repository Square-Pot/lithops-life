from django.urls import path
from . import views

urlpatterns = [
    path("", views.index_view, name="marathons"),
    path("2023", views.first_view, name="marathon 2023"),
    path("2023/<str:species_id>", views.table_view, name="species table"),
]