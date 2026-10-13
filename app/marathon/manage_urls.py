from django.contrib.auth import views as auth_views
from django.urls import path

from . import manage

urlpatterns = [
    path("", manage.index, name="manage_index"),
    path("login", auth_views.LoginView.as_view(template_name="marathon/manage/login.html"), name="manage_login"),
    path("logout", auth_views.LogoutView.as_view(next_page="manage_login"), name="manage_logout"),
    path("nomination/<int:pk>", manage.nomination, name="manage_nomination"),
    path("nominee/<int:pk>/photos", manage.upload_photo, name="manage_upload_photo"),
]
