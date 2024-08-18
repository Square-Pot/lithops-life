from django.urls import path
from . import views

urlpatterns = [
    path("", views.index_view, name="marathons"),
    path("about", views.about, name="marathon about"),
    path("partners", views.partners, name="marathon partners"),
    path("contacts", views.contacts, name="marathon contacts"),
    path("2023", views.first_view, name="marathon 2023"),
    path("2024", views.second_view, name="marathon 2024"),
    path("2023/<str:species_id>", views.table_view, name="species table"),
]