import datetime
import requests
from django.core.mail import send_mail
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, HttpResponseNotFound
from django.template import loader
from django.utils import translation
from django.utils.translation import gettext

from marathon.models import Marathon, Contestant, Nomination, Image


def set_language(request):
    user_language = request.GET.get('language', 'en')
    print('user_language=', user_language)
    translation.activate(user_language)
    response =  redirect(request.META.get('HTTP_REFERER', '/'))
    response.set_cookie(settings.LANGUAGE_COOKIE_NAME, user_language)
    return response


def redirect_to_main(request):
    return redirect('index') 

def index_view(request):
    context = {
        'images': Image.objects.filter(is_starred=True).order_by('?')[:5],
        'marathons': Marathon.objects.all(),
        'contestants': Contestant.objects.all(),
    }
    return render(request, 'marathon/index.html', context=context)

def marathons_view(request):
    marathons = Marathon.objects.all()
    context = {
        'marathons': marathons,
    }
    return render(request, 'marathon/marathons.html', context=context)


def marathon_view(request, marathon_name):
    marathon = get_object_or_404(Marathon, name=marathon_name)
    context = {
        'marathon': marathon,
        'events': marathon.event_set.all().order_by('-date'),
        'nomination_categories': Nomination.objects.all().values_list('category', flat=True).distinct(),
        'images': Image.objects.filter(marathon=marathon, contestant=None),

    }
    return render(request, 'marathon/marathon.html', context=context)


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
        'bla': settings.CSRF_TRUSTED_ORIGINS,
        'host': settings.EMAIL_HOST_USER,
        'rec': settings.EMAIL_RECIPIENT,
    }
    template = loader.get_template('marathon/contacts.html')
    return HttpResponse(template.render(context, request))



