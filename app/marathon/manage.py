"""Кабинет номинаций: номинанты, их фото и публикация номинации — без Django admin, удобно с телефона.
Доступ — пользователь Django с правом marathon.manage_nominations (выдаётся в админке)."""
import functools

from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.text import slugify
from django.utils import translation
from django.views.decorators.http import require_POST

from marathon import storage
from marathon.models import Image, Marathon, Nomination, Nominee, Participant
from marathon.permissions import can_manage_nominations

CATEGORIES = ['Конкурсные', 'Внеконкурсные']
MAX_UPLOAD = 20 * 1024 * 1024  # браузер присылает уже уменьшенное фото; это предохранитель


def manager_required(view):
    @functools.wraps(view)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path(), reverse('manage_login'))
        if not can_manage_nominations(request.user):
            raise PermissionDenied
        # кабинет только на русском: названия номинаций и подписи — в русских полях
        with translation.override('ru'):
            return view(request, *args, **kwargs)
    return wrapper


TRANSLIT = dict(zip('абвгдеёжзийклмнопрстуфхцчшщъыьэюя',
                    'a b v g d e e zh z i y k l m n o p r s t u f kh ts ch sh shch _ y _ e yu ya'.split()))


def unique_slug(name):
    base = slugify(''.join(TRANSLIT.get(c, c) for c in name.lower()).replace('_', '')) or 'participant'
    slug, n = base[:90], 2
    while Participant.objects.filter(slug=slug).exists():
        slug, n = f'{base[:90]}-{n}', n + 1
    return slug


def _default_marathon():
    marathons = list(Marathon.objects.order_by('-seeding_date'))
    for m in marathons:
        if m.state == 'final':
            return m
    return next((m for m in marathons if m.nomination_set.exists()), marathons[0] if marathons else None)


@manager_required
def index(request):
    name = request.GET.get('marathon') or request.POST.get('marathon')
    marathon = get_object_or_404(Marathon, name=name) if name else _default_marathon()
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        if not title:
            messages.error(request, 'Нужно название номинации.')
        else:
            nomination = Nomination.objects.create(
                marathon=marathon, title=title,
                category=request.POST.get('category') or CATEGORIES[0],
                nominee_label='number' if request.POST.get('nominee_label') == 'number' else 'name',
            )
            messages.success(request, f'Номинация «{nomination.title}» создана, пока не опубликована.')
            return redirect('manage_nomination', nomination.pk)
        return redirect(f"{reverse('manage_index')}?marathon={marathon.name}")
    nominations = (marathon.nomination_set.order_by('category', 'id') if marathon else Nomination.objects.none())
    rows = [(n, n.nominees.count(), n.images.count()) for n in nominations]
    return render(request, 'marathon/manage/index.html', {
        'marathon': marathon,
        'marathons': Marathon.objects.order_by('-seeding_date'),
        'rows': rows,
        'categories': CATEGORIES,
        'label_choices': Nomination.LABEL_CHOICES,
    })


def _delete_images(request, images):
    """Удаляет объекты в бакете, затем записи. Если бакет не ответил — запись остаётся, чтобы не терять файл."""
    for img in images:
        try:
            storage.delete_photo(img.url)
        except storage.StorageError as e:
            messages.error(request, f'Фото не удалено: {e}')
            return False
        img.delete()
    return True


@manager_required
def nomination(request, pk):
    nomination = get_object_or_404(Nomination.objects.select_related('marathon'), pk=pk)
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'settings':
            nomination.is_published = bool(request.POST.get('is_published'))
            nomination.nominee_label = 'number' if request.POST.get('nominee_label') == 'number' else 'name'
            nomination.save(update_fields=['is_published', 'nominee_label'])
            messages.success(request, 'Опубликовано.' if nomination.is_published else 'Сохранено, номинация скрыта.')
        elif action == 'add_nominee':
            _add_nominee(request, nomination)
        elif action == 'delete_nominee':
            nominee = get_object_or_404(Nominee, pk=request.POST.get('nominee'), nomination=nomination)
            images = Image.objects.filter(nomination=nomination, participant=nominee.participant)
            if _delete_images(request, images):
                nominee.delete()
                messages.success(request, f'Номинант {nominee.participant.display_name} удалён.')
        elif action == 'delete_photo':
            img = get_object_or_404(Image, pk=request.POST.get('photo'), nomination=nomination)
            if _delete_images(request, [img]):
                messages.success(request, 'Фото удалено.')
        return redirect('manage_nomination', nomination.pk)

    nominees = list(nomination.nominees.select_related('participant').order_by('id'))
    photos = {}
    for img in nomination.images.order_by('id'):
        photos.setdefault(img.participant_id, []).append(img)
    taken = {n.participant_id for n in nominees}
    return render(request, 'marathon/manage/nomination.html', {
        'nomination': nomination,
        'nominees': [(n, photos.get(n.participant_id, [])) for n in nominees],
        'participants': Participant.objects.exclude(id__in=taken).order_by('display_name'),
        'label_choices': Nomination.LABEL_CHOICES,
    })


def _add_nominee(request, nomination):
    new_name = request.POST.get('new_name', '').strip()
    if new_name:
        username = request.POST.get('new_username', '').strip().lstrip('@')
        participant = Participant.objects.filter(tg_username__iexact=username).first() if username else None
        if participant is None:
            participant = Participant.objects.create(display_name=new_name, tg_username=username, slug=unique_slug(new_name))
    elif request.POST.get('participant'):
        participant = get_object_or_404(Participant, pk=request.POST.get('participant'))
    else:
        messages.error(request, 'Выберите участника или впишите нового.')
        return
    # фото привязаны к паре номинация + участник, поэтому один участник — один номинант
    _, created = Nominee.objects.get_or_create(nomination=nomination, participant=participant)
    if created:
        messages.success(request, f'Добавлен номинант {participant.display_name}.')
    else:
        messages.info(request, f'{participant.display_name} уже в номинации.')


@require_POST
@manager_required
def upload_photo(request, pk):
    nominee = get_object_or_404(Nominee.objects.select_related('nomination__marathon', 'participant'), pk=pk)
    upload = request.FILES.get('photo')
    if upload is None:
        return JsonResponse({'error': 'нет файла'}, status=400)
    if upload.size > MAX_UPLOAD:
        return JsonResponse({'error': 'файл больше 20 МБ'}, status=400)
    try:
        data = storage.normalize_photo(upload.read())
    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)
    try:
        url = storage.upload_nominee_photo(nominee.nomination, data)
    except storage.StorageError as e:
        return JsonResponse({'error': str(e)}, status=502)
    img = Image.objects.create(url=url, marathon=nominee.nomination.marathon,
                               nomination=nominee.nomination, participant=nominee.participant)
    return JsonResponse({'id': img.pk, 'url': img.url, 'thumb': reverse('photo_thumb', args=[img.pk])})
