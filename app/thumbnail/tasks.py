from io import BytesIO
import uuid
from celery import shared_task
from PIL import Image as pill_image
from django.core.files.uploadedfile import InMemoryUploadedFile
from core.models import Image, ThumbnailImage, Thumbnail, ExpiredLinkImage


@shared_task
def create_thumbnail(image_id: int, value: int) -> int:
    """Create a thumbnail according to given image and size."""
    image = Image.objects.get(id=image_id)
    thumbnail = Thumbnail.objects.get(value=value)
    with pill_image.open(image.image) as im:
        io_img = BytesIO()
        # Make thumbnail
        size = value, value
        im.thumbnail(size)
        im.save(io_img, 'png')
        thumb_image = InMemoryUploadedFile(
            io_img, 'image', 'image.png',
            'png', io_img.tell(), None)
        # Creating a model
        model = ThumbnailImage.objects.create(
            thumbnail_value=thumbnail, thumbnailed_image=thumb_image)
        return model.id


@shared_task
def create_binary_image(image_id: int, duration: int) -> uuid.uuid4:
    image = Image.objects.get(id=image_id)
    with pill_image.open(image.image) as im:
        io_img = BytesIO()
        # Make binary image
        im = im.convert('1')
        im.save(io_img, 'png',)
        b_image = InMemoryUploadedFile(
            io_img, 'image', 'image.png',
            'png', io_img.tell(), None)
        # Creating a model
        model = ExpiredLinkImage.objects.create(
            duration=duration, binary_image=b_image)
        return model.uuid
