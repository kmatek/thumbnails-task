import tempfile
import shutil
import os
from PIL import Image as pill_image
from django.urls import reverse
from django.core.files.uploadedfile import InMemoryUploadedFile
from rest_framework.test import APITestCase
from rest_framework import status
from core.tests.test_models import sample_user, sample_plan, sample_thumbnail
from core.models import ThumbnailImage, Image, ExpiredLinkImage

IMAGE_UPLOAD_URL = reverse('thumbnail:upload-image')


def expired_link_create_url(uuid):
    return reverse('thumbnail:create-link', args=[uuid])


def expired_link_retrieve_url(uuid):
    return reverse('thumbnail:retrieve-link', args=[uuid])


class ImageViewsTests(APITestCase):
    def setUp(self):
        self.plan = sample_plan(name='Plan', expired_link=False)
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
            self.assertEqual(ThumbnailImage.objects.all().count(), 1)

    def test_image_upload_not_allowed_methods(self):
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

    def test_expired_link_create_permissions(self):
        with tempfile.NamedTemporaryFile(suffix='.png') as image_file:
            image = pill_image.new('RGB', (1, 1))
            image.save(image_file, 'png')
            image = InMemoryUploadedFile(
                image_file, 'image', 'image.png',
                'png', image_file.tell(), None)
            image_model = Image.objects.create(user=self.user, image=image)

        payload = {'duration': 300}
        self.user.plan = self.plan
        self.client.force_authenticate(self.user)
        res = self.client.post(
            expired_link_create_url(image_model.uuid), payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

        self.plan.expired_link = True
        self.user.plan = self.plan
        res = self.client.post(
            expired_link_create_url(image_model.uuid), payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertIn('link', res.data)

    def test_expired_link_create_not_allowed_methods(self):
        self.client.force_authenticate(self.user)
        self.plan.expired_link = True
        self.user.plan = self.plan
        payload = {'duration': 300}

        with tempfile.NamedTemporaryFile(suffix='.png') as image_file:
            image = pill_image.new('RGB', (1, 1))
            image.save(image_file, 'png')
            image = InMemoryUploadedFile(
                image_file, 'image', 'image.png',
                'png', image_file.tell(), None)
            image_model = Image.objects.create(user=self.user, image=image)

        res = self.client.get(
            expired_link_create_url(image_model.uuid), payload)
        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        res = self.client.put(
            expired_link_create_url(image_model.uuid), payload)
        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        res = self.client.patch(
            expired_link_create_url(image_model.uuid), payload)
        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        res = self.client.delete(
            expired_link_create_url(image_model.uuid), payload)
        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_authenticated_user_is_not_the_owner_of_image(self):
        self.client.force_authenticate(self.user)
        user2 = sample_user(
            email='test2@email.com', name='test2', password='testpassword')
        user2.plan = self.plan
        payload = {'duration': 300}

        with tempfile.NamedTemporaryFile(suffix='.png') as image_file:
            image = pill_image.new('RGB', (1, 1))
            image.save(image_file, 'png')
            image = InMemoryUploadedFile(
                image_file, 'image', 'image.png',
                'png', image_file.tell(), None)
            image_model = Image.objects.create(user=user2, image=image)

        res = self.client.post(
            expired_link_create_url(image_model.uuid), payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_expired_link_with_invalid_payload(self):
        self.client.force_authenticate(self.user)
        self.plan.expired_link = True
        self.user.plan = self.plan
        payload = {'duration': 299}

        with tempfile.NamedTemporaryFile(suffix='.png') as image_file:
            image = pill_image.new('RGB', (1, 1))
            image.save(image_file, 'png')
            image = InMemoryUploadedFile(
                image_file, 'image', 'image.png',
                'png', image_file.tell(), None)
            image_model = Image.objects.create(user=self.user, image=image)

        res = self.client.post(
            expired_link_create_url(image_model.uuid), payload)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

        payload = {'duration': 30001}
        res = self.client.post(
            expired_link_create_url(image_model.uuid), payload)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_expired_link_retrieve_not_allowed_methods(self):
        link = ExpiredLinkImage.objects.create(duration=300)

        res = self.client.post(expired_link_retrieve_url(link.uuid))
        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        res = self.client.patch(expired_link_retrieve_url(link.uuid))
        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        res = self.client.put(expired_link_retrieve_url(link.uuid))
        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        res = self.client.delete(expired_link_retrieve_url(link.uuid))
        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_expired_link_retrieve_expired(self):
        link = ExpiredLinkImage.objects.create(duration=300)
        link.duration = -1
        link.save()

        res = self.client.get(expired_link_retrieve_url(link.uuid))
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_expired_link_retrieve(self):
        self.client.force_authenticate(self.user)
        self.plan.expired_link = True
        self.user.plan = self.plan
        payload = {'duration': 300}

        with tempfile.NamedTemporaryFile(suffix='.png') as image_file:
            image = pill_image.new('RGB', (1, 1))
            image.save(image_file, 'png')
            image = InMemoryUploadedFile(
                image_file, 'image', 'image.png',
                'png', image_file.tell(), None)
            image_model = Image.objects.create(user=self.user, image=image)

            res = self.client.post(
                expired_link_create_url(image_model.uuid), payload)
            self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        link = ExpiredLinkImage.objects.all().first()
        res = self.client.get(expired_link_retrieve_url(link.uuid))

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('binary_image', res.data)
        self.assertTrue(link.binary_image)
        self.assertEqual(link.duration, payload['duration'])
