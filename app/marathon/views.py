import datetime
from django.shortcuts import render
from django.http import HttpResponse, HttpResponseNotFound
from django.template import loader

def index_view(request):
    return render(request, 'marathon/2023.html')


def table_view(request, species_id):
    species_ids = {
        'annarosa': 'Lithops hookeri var. dabneri cv. Annarosa',
        'c188': 'Lithops werneri, C188',
        'c262': 'Lithops gracildelineata, C262'
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