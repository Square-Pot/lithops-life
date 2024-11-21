from django.contrib import admin

from marathon.models import Marathon, Contestant, Event, Nomination, Image

admin.site.register(Marathon)
admin.site.register(Contestant)
admin.site.register(Event)
admin.site.register(Nomination)
admin.site.register(Image)