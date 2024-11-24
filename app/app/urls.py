"""app URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static
from django.conf import settings
from marathon import views as marathon_views


urlpatterns = [
    path('admin/', admin.site.urls),
    # path('', marathon_views.redirect_to_marathon, name='redirect_to_marathon'),
    path('', marathon_views.index_view, name="index"),
    path("marathons", marathon_views.marathons_view, name="marathons"),
    path("marathon/", marathon_views.redirect_to_main, name="redirect_to_main"),
    path("marathon/", include("marathon.urls")),
    path("about", marathon_views.about, name="marathon about"),
    path("partners", marathon_views.partners, name="marathon partners"),
    path("contacts", marathon_views.contacts, name="marathon contacts"),
    path("knowledge", marathon_views.knowledge, name="marathon knowledge"),
    path("rules", marathon_views.rules, name="marathon rules"),
] 

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
