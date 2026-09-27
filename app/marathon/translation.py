from modeltranslation.translator import register, TranslationOptions
from .models import Marathon, Event, Nomination


@register(Marathon)
class MarathonTranslationOptions(TranslationOptions):
    fields = ('description', )
    
@register(Event)
class EventTranslationOptions(TranslationOptions):
    fields = ('title', )
    

@register(Nomination)
class NominationTranslationOptions(TranslationOptions):
    fields = ('title', 'category')
