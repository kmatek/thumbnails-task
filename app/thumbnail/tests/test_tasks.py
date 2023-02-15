import tempfile
import uuid
from PIL import Image as pill_image
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import InMemoryUploadedFile
from ..tasks import create_thumbnail, create_binary_image
from core.models import ThumbnailImage, Image, Thumbnail, ExpiredLinkImage


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True
)
class CeleryTasksTest(TestCase):
    def test_create_thumbnail_task(self):
        params = {
            'email': 'test@email.com',
            'name': 'test',
            'password': 'testpassword'
        }
        user = get_user_model().objects.create(**params)
        thumb = Thumbnail.objects.create(value=200)

        with tempfile.NamedTemporaryFile(suffix='.png') as image_file:
            image = pill_image.new('RGB', (1, 1))
            image.save(image_file, 'png')
            image = InMemoryUploadedFile(
                image_file, 'image', 'image.png',
                'png', image_file.tell(), None)
            image_model = Image.objects.create(user=user, image=image)
            self.assertTrue(image_model.image)

        result = create_thumbnail.delay(
            image_id=image_model.id, value=thumb.value)
        self.assertTrue(result.successful())
        self.assertEqual(type(result.get()), int)
        self.assertEqual(result.get(), ThumbnailImage.objects.all().first().id)

    def test_create_binary_image(self):
        params = {
            'email': 'test@email.com',
            'name': 'test',
            'password': 'testpassword'
        }
        user = get_user_model().objects.create(**params)

        with tempfile.NamedTemporaryFile(suffix='.png') as image_file:
            image = pill_image.new('RGB', (1, 1))
            image.save(image_file, 'png')
            image = InMemoryUploadedFile(
                image_file, 'image', 'image.png',
                'png', image_file.tell(), None)
            image_model = Image.objects.create(user=user, image=image)
            self.assertTrue(image_model.image)

        result = create_binary_image.delay(
            image_id=image_model.id, duration=400)
        self.assertTrue(result.successful())
        self.assertEqual(type(result.get()), uuid.UUID)
        self.assertEqual(
            result.get(), ExpiredLinkImage.objects.all().first().uuid)
