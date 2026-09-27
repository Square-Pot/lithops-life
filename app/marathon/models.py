import datetime
import re
from django.db import models
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _


class Marathon(models.Model):
    STATUS_CHOICES = [
        ('pending', _('Ожидание')),
        ('in_progress', _('В процессе')),
        ('final', _('Финал')),
        ('completed', _('Завершен')),
    ]
    
    name = models.CharField(max_length=255)
    description = models.TextField()
    seeding_date = models.DateField()
    title_image = models.OneToOneField('Image', related_name='marathon_title_image', on_delete=models.SET_NULL, null=True, blank=True)
    participants_number = models.PositiveIntegerField(default=0)
    details = models.TextField(blank=True, help_text='Формат сезона, если он отличается от обычного (например, «год качества»)')
    format_note = models.CharField(max_length=255, blank=True, help_text='Коротко для карточки вместо числа конкурсных видов')
    sowing_table_url = models.URLField(blank=True, help_text='Таблица посевов')
    data_table_url = models.URLField(blank=True, help_text='Таблица данных конкурсного посева (всхожесть, грунт, свет)')

    def __str__(self):
        return f'{self.name} ({self.seeding_date})'
    

    COMPLETED_AFTER_FINALE = datetime.timedelta(days=45)  # если в календаре нет события «Финал: итоги…»

    def state_on(self, day):
        """Статус по календарю: посев → в процессе; год с посева или первое событие «Финал…» → финал;
        «Финал: итоги…» (или 45 дней после последнего финального события) → завершён."""
        if day < self.seeding_date:
            return 'pending'
        finale = [e for e in self.event_set.all() if (e.title_ru or e.title or '').startswith('Финал')]
        results = [e.date for e in finale if 'итоги' in (e.title_ru or e.title or '')]
        if results:
            if day >= min(results):
                return 'completed'
        elif finale and day >= max(e.date for e in finale) + self.COMPLETED_AFTER_FINALE:
            return 'completed'
        one_year = self.seeding_date.replace(year=self.seeding_date.year + 1)
        if day >= one_year or any(day >= e.date for e in finale):
            return 'final'
        return 'in_progress'

    @property
    def state(self):
        return self.state_on(datetime.date.today())

    def get_state_display(self):
        return dict(self.STATUS_CHOICES)[self.state]

    def get_state_color(self):
        COLORS = {
            'pending': 'warning',
            'in_progress': 'success',
            'final': 'danger',
            'completed': 'secondary',
        }
        return COLORS.get(self.state, 'primary')
    
    @property
    def age_days(self):
        return (datetime.date.today() - self.seeding_date).days        
    
    @property
    def current_event(self):
        return self.event_set.filter(
            date__lt=datetime.date.today()
        ).order_by('date').last()



class Contestant(models.Model):
    genus = models.CharField(max_length=100)
    species = models.CharField(max_length=100, blank=True)
    subspecies = models.CharField(max_length=100, blank=True)
    variety = models.CharField(max_length=100, blank=True)
    cultivar = models.CharField(max_length=100, blank=True)
    field_number = models.CharField(max_length=100, blank=True)
    short_name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    marathon = models.ForeignKey(Marathon, on_delete=models.CASCADE)
    category = models.CharField(max_length=100, blank=True)
    title_image = models.OneToOneField('Image', related_name='contestant_title_image', on_delete=models.SET_NULL, null=True, blank=True)
    dzi = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return f'{self.marathon.name} {self.short_name}'
    
    @property
    def full_botanic_name(self):
        parts = [f"<em>{self.genus[0]}.</em>"]
        if self.species:
            parts.append(f"<em>{self.species}</em>")
        if self.subspecies:
            parts.append(f"<small>ssp.</small>&nbsp;<em>{self.subspecies}</em>")
        if self.variety:
            parts.append(f"<small>var.</small>&nbsp;<em>{self.variety}</em>")
        if self.cultivar:
            parts.append(f"<small>cv.</small>&nbsp;'{self.cultivar}'")
        name = " ".join(parts)
        if self.field_number:
            name += f", {self.field_number}"
        return format_html(name)

    @property
    def full_name(self):
        parts = [f"{self.genus[0]}."]
        if self.species:
            parts.append(self.species)
        if self.subspecies:
            parts.append(f"ssp. {self.subspecies}")
        if self.variety:
            parts.append(f"var. {self.variety}")
        if self.cultivar:
            parts.append(f"cv. '{self.cultivar}'")
        name = " ".join(parts)
        if self.field_number:
            name += f", {self.field_number}"
        return name


class Event(models.Model):
    date = models.DateField()
    marathon = models.ForeignKey(Marathon, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    published = models.BooleanField(default=False)

    def __str__(self):
        return f'[{ self.marathon.name }] {self.date.strftime("%d.%m.%Y")} - {self.title}'
    
    @property
    def color(self):
        if self.date > datetime.date.today():
            return 'black-50'
        else:
            return 'dark'


def nomination_key(title):
    """Ключ для сопоставления названий номинаций без учёта пробелов и пунктуации
    («…pseudotruncatellavar.» == «…pseudotruncatella var.», хвостовая «;» и т. п.)."""
    return re.sub(r'[\W_]+', '', title or '').lower()


class NominationQuerySet(models.QuerySet):
    def by_title(self, title):
        key = nomination_key(title)
        return [n for n in self if nomination_key(n.title_ru or n.title) == key]


class Nomination(models.Model):
    title = models.CharField(max_length=255)
    category = models.CharField(max_length=100)
    winner_name = models.CharField(max_length=255, blank=True)
    winner_username = models.CharField(max_length=255, blank=True)
    marathon = models.ForeignKey(Marathon, on_delete=models.CASCADE)
    poll_image = models.OneToOneField('Image', related_name='nomination_poll_image', on_delete=models.SET_NULL, null=True, blank=True)
    poll_date = models.DateField(null=True, blank=True)
    poll_url = models.URLField(blank=True)
    total_voters = models.PositiveIntegerField(null=True, blank=True)

    objects = NominationQuerySet.as_manager()

    def __str__(self):
        return self.title


class Image(models.Model):
    url = models.URLField()
    author = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    contestant = models.ForeignKey(Contestant, related_name='images', on_delete=models.SET_NULL, null=True, blank=True)
    marathon = models.ForeignKey(Marathon, related_name='images', on_delete=models.SET_NULL, null=True, blank=True)
    nomination = models.ForeignKey(Nomination, related_name='images', on_delete=models.SET_NULL, null=True, blank=True)
    participant = models.ForeignKey('Participant', related_name='images', on_delete=models.SET_NULL, null=True, blank=True)
    is_winner = models.BooleanField(default=False)
    is_starred = models.BooleanField(default=False)

    def __str__(self):
        data = []
        if self.marathon: 
            data.append(f"Marathon {self.marathon.name}")
        if self.contestant:
            data.append(f"{self.contestant.short_name}")
        data.append(self.url.split('/')[-1])
        return " - ".join(data)




class Participant(models.Model):
    """Человек — участник марафона (в отличие от Contestant, который вид растения)."""
    display_name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=100, unique=True)
    tg_id = models.BigIntegerField(null=True, blank=True, unique=True)
    tg_username = models.CharField(max_length=100, blank=True)
    note = models.TextField(blank=True)

    def __str__(self):
        return f'{self.display_name} ({self.tg_username or self.slug})'

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('participant', args=[self.slug])


class Nominee(models.Model):
    nomination = models.ForeignKey(Nomination, related_name='nominees', on_delete=models.CASCADE)
    participant = models.ForeignKey(Participant, related_name='nominations', on_delete=models.CASCADE)
    plant = models.CharField(max_length=255, blank=True, help_text='Примечание к растению, если у участника их несколько')
    is_winner = models.BooleanField(default=False)
    votes = models.PositiveIntegerField(null=True, blank=True)
    photo_msgs = models.TextField(blank=True, help_text='Ссылки на посты с фото в Telegram, по одной на строку')

    def __str__(self):
        return f'{self.nomination} — {self.participant.display_name}'
