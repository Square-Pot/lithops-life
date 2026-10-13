"""Фото номинантов в Yandex Object Storage (бакет тот же, что у остальных Image).
Ключи — только из окружения (.env): AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY; S3_BUCKET, S3_ENDPOINT_URL — необязательно."""
import io
import os
import uuid

from PIL import Image as PILImage, ImageOps

ENDPOINT_URL = os.environ.get('S3_ENDPOINT_URL', 'https://storage.yandexcloud.net')
BUCKET = os.environ.get('S3_BUCKET', 'lithops.life')
MAX_SIDE = 2560  # по длинной стороне: крупный просмотр на ПК, а файл ~1 МБ
CACHE_CONTROL = 'public, max-age=31536000, immutable'  # ключ со случайным uuid, файл не меняется


class StorageError(Exception):
    pass


def _client():
    if not (os.environ.get('AWS_ACCESS_KEY_ID') and os.environ.get('AWS_SECRET_ACCESS_KEY')):
        raise StorageError('нет ключей Object Storage (AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY в .env)')
    import boto3
    return boto3.client('s3', endpoint_url=ENDPOINT_URL, region_name='ru-central1')


def public_url(key):
    return f"{ENDPOINT_URL.rstrip('/')}/{BUCKET}/{key}"


def normalize_photo(data):
    """JPEG без EXIF (там бывают координаты), с учётом поворота, не больше MAX_SIDE. ValueError — не картинка."""
    try:
        photo = PILImage.open(io.BytesIO(data))
        photo = ImageOps.exif_transpose(photo).convert('RGB')
    except Exception as e:
        raise ValueError('файл не похож на фото') from e
    photo.thumbnail((MAX_SIDE, MAX_SIDE), PILImage.LANCZOS)
    out = io.BytesIO()
    photo.save(out, 'JPEG', quality=85, optimize=True)
    return out.getvalue()


def upload_nominee_photo(nomination, data):
    """Кладёт нормализованное фото в бакет, возвращает публичный URL."""
    key = f'finals/{nomination.marathon.name}/nominations/{nomination.pk}/{uuid.uuid4().hex}.jpg'
    try:
        _client().put_object(Bucket=BUCKET, Key=key, Body=data, ContentType='image/jpeg', CacheControl=CACHE_CONTROL)
    except StorageError:
        raise
    except Exception as e:
        raise StorageError(f'Object Storage не принял файл: {e}') from e
    return public_url(key)


def delete_photo(url):
    """Удаляет объект, если он лежит в нашем бакете; чужие URL не трогает."""
    prefix = public_url('')
    if not url.startswith(prefix):
        return
    try:
        _client().delete_object(Bucket=BUCKET, Key=url[len(prefix):])
    except StorageError:
        raise
    except Exception as e:
        raise StorageError(f'Object Storage не удалил файл: {e}') from e
