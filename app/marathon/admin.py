from django.contrib import admin

from marathon.models import Marathon, Contestant, Event, Nomination, Image, Participant, Nominee

admin.site.register(Marathon)
admin.site.register(Contestant)
admin.site.register(Event)
admin.site.register(Image)


class NomineeInline(admin.TabularInline):
    model = Nominee
    extra = 0
    autocomplete_fields = ('participant', 'nomination')


@admin.register(Nomination)
class NominationAdmin(admin.ModelAdmin):
    list_display = ('title', 'marathon', 'category', 'poll_date')
    list_filter = ('marathon', 'category')
    search_fields = ('title',)
    inlines = (NomineeInline,)


@admin.register(Participant)
class ParticipantAdmin(admin.ModelAdmin):
    list_display = ('display_name', 'tg_username', 'tg_id', 'slug')
    search_fields = ('display_name', 'tg_username', 'slug')
    prepopulated_fields = {'slug': ('display_name',)}
    inlines = (NomineeInline,)
