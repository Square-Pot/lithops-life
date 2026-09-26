import datetime
import hashlib
from pathlib import Path
from urllib.parse import urlparse

import requests
from django.core.mail import send_mail
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.http import FileResponse, HttpResponse, HttpResponseNotFound, Http404
from django.template import loader
from django.utils import translation
from django.utils.translation import gettext

from django.db.models import Q, Prefetch

from marathon import watermark
from marathon.models import Marathon, Contestant, Image, Nominee, Participant


def set_language(request):
    user_language = request.GET.get('language', 'en')
    if user_language not in dict(settings.LANGUAGES):
        user_language = settings.LANGUAGE_CODE
    translation.activate(user_language)
    response =  redirect(request.META.get('HTTP_REFERER', '/'))
    response.set_cookie(settings.LANGUAGE_COOKIE_NAME, user_language)
    return response


def redirect_to_main(request):
    return redirect('index') 

def index_view(request):
    context = {
        'images': Image.objects.filter(is_starred=True).order_by('?')[:5],
        'marathons': Marathon.objects.all().order_by('-id'),
        'contestants': Contestant.objects.all(),
    }
    return render(request, 'marathon/index.html', context=context)

def marathons_view(request):
    marathons = Marathon.objects.all()
    context = {
        'marathons': marathons,
    }
    return render(request, 'marathon/marathons.html', context=context)


# финальные фото: привязаны к участнику или номинации, либо к марафону без вида (старые etc/NN.jpg)
FINAL_PHOTOS = Q(participant__isnull=False) | Q(nomination__isnull=False) | Q(marathon__isnull=False, contestant__isnull=True)


def marathon_view(request, marathon_name):
    marathon = get_object_or_404(Marathon, name=marathon_name)
    context = {
        'marathon': marathon,
        'events': marathon.event_set.all().order_by('-date'),
        'nomination_categories': marathon.nomination_set.values_list('category', flat=True).distinct(),
        'nominations': marathon.nomination_set.prefetch_related(
            Prefetch('nominees', queryset=Nominee.objects.select_related('participant').order_by('-is_winner', '-votes'))
        ),
        'images': Image.objects.filter(marathon=marathon, contestant=None),
        'final_photos_count': Image.objects.filter(FINAL_PHOTOS, marathon=marathon).count(),

    }
    return render(request, 'marathon/marathon.html', context=context)


def gallery_view(request):
    images = (
        Image.objects.filter(FINAL_PHOTOS)
        .select_related('marathon', 'contestant', 'participant', 'nomination')
        .order_by('-marathon__seeding_date', '-is_winner', '-is_starred', 'id')
    )
    marathon_name = request.GET.get('marathon')
    if marathon_name:
        images = images.filter(marathon__name=marathon_name)
    if request.GET.get('winners'):
        images = images.filter(is_winner=True)
    context = {
        'images': images,
        'selected_marathon': marathon_name,
        'winners_only': bool(request.GET.get('winners')),
        'gallery_marathons': Marathon.objects.filter(images__in=Image.objects.filter(FINAL_PHOTOS)).distinct().order_by('-seeding_date'),
    }
    return render(request, 'marathon/gallery.html', context=context)


WATERMARK_HOSTS = ('storage.yandexcloud.net',)


def photo_download(request, image_id):
    """Финальное фото с водяным знаком марафона — для промо, отдаём всем."""
    img = get_object_or_404(Image.objects.filter(FINAL_PHOTOS).select_related('marathon'), pk=image_id)
    if urlparse(img.url).hostname not in WATERMARK_HOSTS:
        raise Http404
    marathon_name = img.marathon.name if img.marathon else ''
    key = hashlib.sha1(f'{img.url}|{marathon_name}|{watermark.VERSION}'.encode()).hexdigest()[:16]
    cache_dir = Path(settings.WATERMARK_CACHE_DIR)
    cached = cache_dir / f'{img.pk}-{key}.jpg'
    if not cached.exists():
        try:
            response = requests.get(img.url, timeout=20)
            response.raise_for_status()
        except requests.RequestException:
            return HttpResponse(status=502)
        cache_dir.mkdir(parents=True, exist_ok=True)
        tmp = cached.with_suffix('.tmp')
        tmp.write_bytes(watermark.apply(response.content, marathon_name))
        tmp.replace(cached)
    filename = f'lithops.life_marathon{marathon_name}_{img.pk}.jpg'
    return FileResponse(open(cached, 'rb'), as_attachment=True, filename=filename, content_type='image/jpeg')


def participant_view(request, slug):
    participant = get_object_or_404(Participant, slug=slug)
    nominees = (
        participant.nominations
        .select_related('nomination', 'nomination__marathon')
        .order_by('-nomination__marathon__seeding_date', '-is_winner', 'nomination__id')
    )
    by_marathon = {}
    for nominee in nominees:
        by_marathon.setdefault(nominee.nomination.marathon, []).append(nominee)
    context = {
        'participant': participant,
        'by_marathon': by_marathon.items(),
        'wins': sum(n.is_winner for n in nominees),
        'finals': len(by_marathon),
        'images': participant.images.select_related('marathon', 'contestant', 'nomination').order_by('-marathon__seeding_date', 'id'),
    }
    return render(request, 'marathon/participant.html', context=context)


def contestant_view(request, contestant_short_name):
    contestant = get_object_or_404(Contestant, short_name=contestant_short_name)
    rest_contestants = (
        Contestant.objects
        .filter(marathon=contestant.marathon)
        .exclude(id=contestant.id)
    )
    context = { 
        'contestant': contestant,
        'rest_contestants': rest_contestants,
    }
    template = loader.get_template('marathon/contestant.html')
    return HttpResponse(template.render(context, request))


def about(request):
    context = {}
    template = loader.get_template('marathon/about.html')
    return HttpResponse(template.render(context, request))


def partners(request):
    context = {}
    template = loader.get_template('marathon/partners.html')
    return HttpResponse(template.render(context, request))

def knowledge(request):
    context = {}
    template = loader.get_template('marathon/knowledge.html')
    return HttpResponse(template.render(context, request))

def publications(request):
    context = {}
    template = loader.get_template('marathon/publications.html')
    return HttpResponse(template.render(context, request))

def rules(request):
    context = {}
    template = loader.get_template('marathon/rules.html')
    return HttpResponse(template.render(context, request))

def contacts(request):
    result = None
    subject = request.GET.get('subject', 'None')
    if not subject:
        subject = 'etc'
    if subject not in ['membership', 'partnership']:
        subject = 'etc'

    if request.method == 'POST':
        recaptcha_response = request.POST.get('g-recaptcha-response')
        data = {
            'secret': settings.RECAPTCHA_SECRET_KEY,
            'response': recaptcha_response
        }
        response = requests.post('https://www.google.com/recaptcha/api/siteverify', data=data)
        result = response.json()
        if result['success']:
    
            email = request.POST.get('email', '')
            subject = request.POST.get('subject', '')
            message = request.POST.get('message', '')

            if email and subject and message:
                send_mail(subject, message + '\n' + email, settings.EMAIL_HOST_USER, settings.EMAIL_RECIPIENT)
                result = 'success'
            else: 
                result = 'error'
        else: 
            result = 'error'
    
    context = {
        'subject': subject,
        'result': result,
    }
    template = loader.get_template('marathon/contacts.html')
    return HttpResponse(template.render(context, request))



