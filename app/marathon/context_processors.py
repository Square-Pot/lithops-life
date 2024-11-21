from .models import Marathon

def marathon_list(request):
    marathons = Marathon.objects.all()
    return {
        'marathons': marathons
    }
