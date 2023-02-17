import tempfile
from PIL import Image as pill_image
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from .test_models import (
    sample_user,
    sample_plan,
    sample_thumbnail
)
from core.models import Image

IMAGE_UPLOAD_URL = reverse('thumbnail:upload-image')


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True
)
class SignalsTests(APITestCase):
    def setUp(self):
        self.plan = sample_plan(name='test')
        self.plan.thumbnails.add(sample_thumbnail(value=100).id)
        self.user = sample_user(
            email='test@test.com', name='test',
            password='testpassword', plan=self.plan)

    def test_user_change_plan_signal(self):
        # Create image
        self.client.force_authenticate(user=self.user)
        with tempfile.NamedTemporaryFile(suffix='.png') as image_file:
            img = pill_image.new('RGB', (200, 200))
            img.save(image_file, 'png')
            image_file.seek(0)
            res = self.client.post(
                IMAGE_UPLOAD_URL, {'image': image_file}, format='multipart')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Image.objects.first().thumbnails.count(), 1)

        # After change plan
        plan2 = sample_plan(name='test2')
        thumbnails = [sample_thumbnail(value=f'10{i}') for i in range(1, 10)]
        plan2.thumbnails.set(thumbnails)
        self.user.plan = plan2
        self.user.save()
        self.assertEqual(Image.objects.first().thumbnails.count(), 10)
