from .models import Marathon

def marathon_list(request):
    # отдельное имя, чтобы страницы со своим списком marathons не подменяли меню
    return {
        'menu_marathons': Marathon.objects.order_by('seeding_date'),
    }
