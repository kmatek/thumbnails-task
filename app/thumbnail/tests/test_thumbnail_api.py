import tempfile
import shutil
import os
from PIL import Image as pill_image
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from core.tests.test_models import sample_user, sample_plan, sample_thumbnail

IMAGE_UPLOAD_URL = reverse('thumbnail:upload-image')


class ImageViewsTests(APITestCase):
    def setUp(self):
        self.plan = sample_plan(name='Plan')
        self.plan.thumbnails.add(sample_thumbnail(**{'value': 100}))
        self.user = sample_user(
            email='test@email.com', name='test', password='testpassword')

    def tearDown(self):
        """Clear media folder."""
        path = '/vol/web/media/uploads/test@email.com'
        if os.path.exists(path):
            shutil.rmtree(path)

    def test_image_upload_permissions(self):
        with tempfile.NamedTemporaryFile(suffix='.png') as image_file:
            img = pill_image.new('RGB', (200, 200))
            img.save(image_file, 'png')
            image_file.seek(0)
            res = self.client.post(
                IMAGE_UPLOAD_URL, {'image': image_file}, format='multipart')

            self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(user=self.user)
        with tempfile.NamedTemporaryFile(suffix='.png') as image_file:
            img = pill_image.new('RGB', (200, 200))
            img.save(image_file, 'png')
            image_file.seek(0)
            res = self.client.post(
                IMAGE_UPLOAD_URL, {'image': image_file}, format='multipart')

            self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

        self.user.plan = self.plan
        with tempfile.NamedTemporaryFile(suffix='.png') as image_file:
            img = pill_image.new('RGB', (200, 200))
            img.save(image_file, 'png')
            image_file.seek(0)
            res = self.client.post(
                IMAGE_UPLOAD_URL, {'image': image_file}, format='multipart')

            self.assertEqual(res.status_code, status.HTTP_201_CREATED)
            self.assertEqual(self.user.image_set.count(), 1)

    def test_image_upload_allowed_method(self):
        self.client.force_authenticate(user=self.user)
        self.user.plan = self.plan

        res = self.client.get(IMAGE_UPLOAD_URL)
        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        res = self.client.patch(IMAGE_UPLOAD_URL)
        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        res = self.client.put(IMAGE_UPLOAD_URL)
        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        res = self.client.delete(IMAGE_UPLOAD_URL)
        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_image_upload_with_wrong_ext(self):
        self.client.force_authenticate(user=self.user)
        self.user.plan = self.plan

        with tempfile.NamedTemporaryFile(suffix='.gif') as image_file:
            img = pill_image.new('RGB', (200, 200))
            img.save(image_file, 'gif')
            image_file.seek(0)
            res = self.client.post(
                IMAGE_UPLOAD_URL, {'image': image_file}, format='multipart')

            self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(self.user.image_set.count(), 0)
