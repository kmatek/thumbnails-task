import tempfile
import shutil
import os
from PIL import Image as pill_image
from django.urls import reverse
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.test import override_settings
from rest_framework.test import APITestCase
from rest_framework import status
from core.tests.test_models import sample_user, sample_plan, sample_thumbnail
from core.models import ThumbnailImage, Image, ExpiredLinkImage
from ..serializers import ImageListSerializer

IMAGE_UPLOAD_URL = reverse('thumbnail:upload-image')
IMAGE_LIST_URL = reverse('thumbnail:list-image')


def expired_link_create_url(uuid):
    return reverse('thumbnail:create-link', args=[uuid])


def expired_link_retrieve_url(uuid):
    return reverse('thumbnail:retrieve-link', args=[uuid])


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True
)
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

    def test_image_list_not_allowed_methods(self):
        self.client.force_authenticate(self.user)
        self.user.plan = self.plan

        res = self.client.post(IMAGE_LIST_URL)
        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        res = self.client.put(IMAGE_LIST_URL)
        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        res = self.client.patch(IMAGE_LIST_URL)
        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        res = self.client.delete(IMAGE_LIST_URL)
        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_image_list_permissions(self):
        res = self.client.get(IMAGE_LIST_URL)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(self.user)
        res = self.client.get(IMAGE_LIST_URL)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

        self.user.plan = self.plan
        res = self.client.get(IMAGE_LIST_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_image_list(self):
        self.client.force_authenticate(self.user)
        self.user.plan = self.plan
        self.user.save()
        with tempfile.NamedTemporaryFile(suffix='.png') as image_file:
            img = pill_image.new('RGB', (200, 200))
            img.save(image_file, 'png')
            image_file.seek(0)
            res = self.client.post(
                IMAGE_UPLOAD_URL, {'image': image_file}, format='multipart')

        image = Image.objects.all().first()
        res = self.client.get(IMAGE_LIST_URL)
        serializer = ImageListSerializer(image)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        # Make this becouse i cant figure out
        # how pass same context as in response to the serializer
        image_url = res.data[0].get('thumbnails')[0]['thumbnailed_image']
        self.assertEqual(
            image_url[17:],
            serializer.data.get('thumbnails')[0]['thumbnailed_image']
        )
        self.assertIn('thumbnails', res.data[0])
        self.assertNotIn('expired_link', res.data[0])
        self.assertNotIn('image', res.data[0])

    def test_image_list_full_option(self):
        self.client.force_authenticate(self.user)
        self.plan.thumbnails.add(sample_thumbnail(**{'value': 400}))
        self.plan.original_image = True
        self.plan.expired_link = True
        self.plan.save()
        self.user.plan = self.plan
        self.user.save()
        with tempfile.NamedTemporaryFile(suffix='.png') as image_file:
            img = pill_image.new('RGB', (200, 200))
            img.save(image_file, 'png')
            image_file.seek(0)
            res = self.client.post(
                IMAGE_UPLOAD_URL, {'image': image_file}, format='multipart')

        image = Image.objects.all().first()
        res = self.client.get(IMAGE_LIST_URL)
        serializer = ImageListSerializer(image)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        # Make this becouse i cant figure out
        # how pass same context as in response to the serializer
        test_list = []
        for thumb in res.data[0].get('thumbnails'):
            temp_dict = {
                'thumbnailed_image': thumb.get('thumbnailed_image')[17:],
                'value': thumb.get('value')
            }
            test_list.append(temp_dict)

        for thumb in serializer.data.get('thumbnails'):
            self.assertIn(thumb, test_list)

        self.assertEqual(image.thumbnails.all().count(), 2)
        self.assertIn('thumbnails', res.data[0])
        self.assertIn('expired_link', res.data[0])
        self.assertIn('image', res.data[0])
