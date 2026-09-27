from django.contrib import admin
from django.utils.html import format_html

from marathon.models import Marathon, Contestant, Event, Nomination, Image, Participant, Nominee

admin.site.register(Marathon)
admin.site.register(Contestant)
admin.site.register(Event)


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


class BoundFilter(admin.SimpleListFilter):
    title = 'привязка к участнику'
    parameter_name = 'bound'

    def lookups(self, request, model_admin):
        return (('no', 'без участника (кроме обложек)'), ('yes', 'с участником'))

    def queryset(self, request, queryset):
        if self.value() == 'no':
            # title_img/ — обложки видов и марафонов, их не привязываем
            return queryset.filter(participant__isnull=True).exclude(url__contains='/title_img/')
        if self.value() == 'yes':
            return queryset.filter(participant__isnull=False)


@admin.register(Image)
class ImageAdmin(admin.ModelAdmin):
    list_display = ('thumb', 'file', 'marathon', 'contestant', 'participant', 'nomination', 'is_winner', 'is_starred')
    list_editable = ('marathon', 'contestant', 'participant', 'nomination', 'is_winner', 'is_starred')
    list_filter = (BoundFilter, 'marathon', 'is_starred', 'is_winner')
    search_fields = ('url', 'author', 'description', 'participant__display_name', 'participant__tg_username')
    list_select_related = ('marathon', 'contestant', 'participant', 'nomination')
    autocomplete_fields = ('participant',)
    list_per_page = 30

    @admin.display(description='')
    def thumb(self, obj):
        return format_html('<a href="{0}" target="_blank"><img src="{0}" style="height:120px;max-width:180px;object-fit:cover"></a>', obj.url)

    @admin.display(description='файл', ordering='url')
    def file(self, obj):
        return obj.url.split('/lithops.life/')[-1]
