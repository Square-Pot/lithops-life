import datetime
from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpResponseNotFound
from django.template import loader



def redirect_to_marathon(request):
    return redirect('marathons') 

def index_view(request):
    today = datetime.date.today()
    second_marathon_days_left = (datetime.date(2024, 10, 1) - today).days
    if second_marathon_days_left <= 0:
        second_marathon_days_left = ''
    context = {'days_left': second_marathon_days_left}
    return render(request, 'marathon/index.html', context=context)

def first_view(request):
    return render(request, 'marathon/2023.html')


def table_view(request, species_id):
    species_ids = {
        'annarosa': 'L. hookeri var. dabneri cv. Annarosa',
        'c188': 'L. werneri, C188',
        'c262': 'L. gracilidelineata, C262'
    }
    
    if species_id not in species_ids:
        return HttpResponseNotFound()
    
    rest_species_ids = list(species_ids.keys())
    rest_species_ids.remove(species_id)
    
    context = { 
        'species_id': species_id,
        'species_full_name': species_ids[species_id],
        'rest_species': rest_species_ids
    }
    template = loader.get_template('marathon/species.html')
    return HttpResponse(template.render(context, request))