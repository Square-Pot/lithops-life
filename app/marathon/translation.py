from modeltranslation.translator import register, TranslationOptions
from .models import Marathon, Event


@register(Marathon)
class MarathonTranslationOptions(TranslationOptions):
    fields = ('description', )
    
@register(Event)
class EventTranslationOptions(TranslationOptions):
    fields = ('title', )
    
