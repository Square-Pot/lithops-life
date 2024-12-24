import datetime
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
    state = models.CharField(max_length=50, choices=STATUS_CHOICES, default='pending')
    title_image = models.OneToOneField('Image', related_name='marathon_title_image', on_delete=models.SET_NULL, null=True, blank=True)
    participants_number = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f'{self.name} ({self.seeding_date})'
    

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
        if self.field_number:
            parts.append(f", {self.field_number}")
        return format_html(" ".join(parts))

    @property
    def full_name(self):
        parts = [self.genus[0]]
        if self.species:
            parts.append(self.species)
        if self.subspecies:
            parts.append(f"ssp. {self.subspecies}")
        if self.variety:
            parts.append(f"var. {self.variety}")
        if self.cultivar:
            parts.append(f"cv. '{self.cultivar}'")
        if self.field_number:
            parts.append(f", '{self.field_number}'")
        return " ".join(parts)


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


class Nomination(models.Model):
    title = models.CharField(max_length=255)
    category = models.CharField(max_length=100)
    winner_name = models.CharField(max_length=255, blank=True)
    winner_username = models.CharField(max_length=255, blank=True)
    marathon = models.ForeignKey(Marathon, on_delete=models.CASCADE)
    poll_image = models.OneToOneField('Image', related_name='nomination_poll_image', on_delete=models.SET_NULL, null=True, blank=True)
    poll_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return self.title


class Image(models.Model):
    url = models.URLField()
    author = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    contestant = models.ForeignKey(Contestant, related_name='images', on_delete=models.SET_NULL, null=True, blank=True)
    marathon = models.ForeignKey(Marathon, related_name='images', on_delete=models.SET_NULL, null=True, blank=True)
    nomination = models.ForeignKey(Nomination, related_name='images', on_delete=models.SET_NULL, null=True, blank=True)
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


