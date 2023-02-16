from io import BytesIO
import uuid
from celery import shared_task
from PIL import Image as pill_image
from django.core.files.uploadedfile import InMemoryUploadedFile
from core.models import Image, ThumbnailImage, Thumbnail, ExpiredLinkImage


def create_thumb(image: Image, thumbnail: Thumbnail) -> int:
    """Create a thumbnail."""
    with pill_image.open(image.image) as im:
        io_img = BytesIO()
        # Make thumbnail
        size = thumbnail.value, thumbnail.value
        im.thumbnail(size)
        im.save(io_img, 'png')
        thumb_image = InMemoryUploadedFile(
            io_img, 'image', 'image.png',
            'png', io_img.tell(), None)
        # Create model
        model = ThumbnailImage.objects.create(
            thumbnail_value=thumbnail,
            thumbnailed_image=thumb_image
        )
        # Return model's id
        return model.id


@shared_task
def create_thumbnails(image_id: int) -> None:
    """Create thumbnails for all values."""
    # Get image
    image = Image.objects.get(id=image_id)
    # Get thumbnails
    thumbnails = Thumbnail.objects.all()
    thumbnail_ids = []
    # Create thumbnails for every thumbnail
    for thumbnail in thumbnails:
        model_id = create_thumb(image, thumbnail)
        # Append model's id
        thumbnail_ids.append(model_id)
    # Add new thumbnails to the image
    image.thumbnails.add(*thumbnail_ids)
    image.save()


@shared_task
def create_binary_image(image_id: int, duration: int) -> uuid.uuid4:
    """Create an binary image with given duration"""
    # Get image
    image = Image.objects.get(id=image_id)
    # Create a binary image
    with pill_image.open(image.image) as im:
        io_img = BytesIO()
        im = im.convert('1')
        im.save(io_img, 'png',)
        b_image = InMemoryUploadedFile(
            io_img, 'image', 'image.png',
            'png', io_img.tell(), None)
        # Create a model
        model = ExpiredLinkImage.objects.create(
            duration=duration, binary_image=b_image)
        return model.uuid
