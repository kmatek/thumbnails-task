from unittest.mock import patch
import os
import shutil
import tempfile
from PIL import Image
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.utils import timezone
from core import models


def sample_user(**params):
    """Creating a user model for testing."""
    return get_user_model().objects.create_user(**params)


def sample_superuser(**params):
    """Creating a superuser model for testing."""
    return get_user_model().objects.create_superuser(**params)


def sample_plan(**params):
    """Creating a plan model for testing."""
    return models.Plan.objects.create(**params)


def sample_thumbnail(**params):
    """Creating a thumbnail model for testing."""
    return models.Thumbnail.objects.create(**params)


def sample_image(**params):
    """Creating a image model for testing."""
    return models.Image.objects.create(**params)


def sample_thumbnail_image(**params):
    """Create a thumbnail image model for testing."""
    return models.ThumbnailImage.objects.create(**params)


def sample_expired_link_image(**params):
    """Create a expired link image model for testing."""
    return models.ExpiredLinkImage.objects.create(**params)


@override_settings(
    SUSPEND_SIGNALS=True
)
class ModelsTests(TestCase):
    def tearDown(self):
        """Clear media folder."""
        path = '/vol/web/media/uploads/test@email.com'
        if os.path.exists(path):
            shutil.rmtree(path)

    def test_create_user_with_correct_email(self):
        params = {
            'email': 'test@email.com',
            'name': 'test',
            'password': 'testpassword',
        }
        user = sample_user(**params)

        for key in params.keys():
            if key == 'password':
                self.assertTrue(user.check_password(params[key]))
                continue
            self.assertEqual(getattr(user, key), params[key])

    def test_create_user_with_invalid_email(self):
        with self.assertRaises(ValueError):
            params = {
                'email': None,
                'name': 'test',
                'password': 'testpassword'
            }
            sample_user(**params)

    def test_create_user_with_invalid_name(self):
        with self.assertRaises(ValueError):
            params = {
                'email': 'test@email.com',
                'name': None,
                'password': 'testpassword'
            }
            sample_user(**params)

    def test_normalize_email(self):
        params = {
            'email': 'test@EMAIL.COM',
            'name': 'test',
            'password': 'testpassword'
        }
        user = sample_user(**params)
        self.assertEqual(user.email, params['email'].lower())

    def test_normalize_name(self):
        params = {
            'email': 'test@email.com',
            'name': 'TEST',
            'password': 'testpassword'
        }
        user = sample_user(**params)
        self.assertEqual(user.name, params['name'].lower())

    def test_create_superuser(self):
        params = {
            'email': 'admin@email.com',
            'name': 'admin',
            'password': 'adminpassword'
        }
        super_user = sample_superuser(**params)
        self.assertTrue(super_user.is_staff)
        self.assertTrue(super_user.is_superuser)

    def test_thumbnail_model(self):
        params = {'value': 100}
        thumbnail = sample_thumbnail(**params)
        self.assertEqual(thumbnail.value, params['value'])

    def test_plan_model(self):
        params = {
            'name': 'test_plan',
            'original_image': True,
            'expired_link': True
        }
        plan = sample_plan(**params)
        thumbs = [sample_thumbnail(**{'value': f'10{i}'}) for i in range(3)]
        plan.thumbnails.set(thumbs)

        for key in params.keys():
            self.assertEqual(getattr(plan, key), params[key])

        for thumbnail in thumbs:
            self.assertIn(thumbnail, plan.thumbnails.all())

    @patch('core.models.uuid.uuid4')
    def test_image_file_path(self, patched_uuid):
        uuid = 'test-uuid'
        patched_uuid.return_value = uuid
        file_path = models.image_file_path(None, 'example.png')
        self.assertEqual(file_path, f'uploads/{uuid}.png')

    @patch('core.models.uuid.uuid4')
    def test_image_model(self, patched_uuid):
        params = {
            'email': 'test@email.com',
            'name': 'test',
            'password': 'testpassword'
        }
        user = sample_user(**params)

        with tempfile.NamedTemporaryFile(suffix='.png') as image_file:
            image = Image.new('RGB', (1, 1))
            image.save(image_file, 'png')
            image = InMemoryUploadedFile(
                image_file, 'image', 'image.png',
                'png', image_file.tell(), None)
            image_model = sample_image(user=user, image=image)

            uuid = 'test-uuid'
            patched_uuid.return_value = uuid
            file_path = models.image_file_path(image_model, image.name)
            self.assertEqual(file_path, f'uploads/{uuid}.png')
            self.assertTrue(image_model.image)

    def test_image_model_upload_with_invalid_ext(self):
        params = {
            'email': 'test@email.com',
            'name': 'test',
            'password': 'testpassword'
        }
        user = sample_user(**params)
        with self.assertRaises(ValidationError):
            with tempfile.NamedTemporaryFile(suffix='.gif') as image_file:
                image = Image.new('RGB', (1, 1))
                image.save(image_file, 'gif')
                image = InMemoryUploadedFile(
                    image_file, 'image', 'image.gif',
                    'gif', image_file.tell(), None)
                image_model = sample_image(user=user, image=image)
                image_model.full_clean()  # validate fields without saving

    @patch('core.models.uuid.uuid4')
    def test_thumbnail_image_model(self, patched_uuid):
        with tempfile.NamedTemporaryFile(suffix='.png') as thumbnail_file:
            thumbnail = Image.new('RGB', (1, 1))
            thumbnail.save(thumbnail_file, 'png')
            thumbnail = InMemoryUploadedFile(
                thumbnail_file, 'thumb', 'thumb.png',
                'png', thumbnail_file.tell(), None)
            thumbnail_model = sample_thumbnail_image(
                thumbnailed_image=thumbnail,
                thumbnail_value=sample_thumbnail(**{'value': '1'}))

            uuid = 'test-uuid'
            patched_uuid.return_value = uuid
            file_path = models.image_file_path(thumbnail_model, thumbnail.name)
            self.assertEqual(file_path, f'uploads/{uuid}.png')
            self.assertTrue(thumbnail_model.thumbnailed_image)

    def test_thumbnail_image_model_upload_with_invalid_ext(self):
        with self.assertRaises(ValidationError):
            with tempfile.NamedTemporaryFile(suffix='.gif') as thumbnail_file:
                thumbnail = Image.new('RGB', (1, 1))
                thumbnail.save(thumbnail_file, 'gif')
                thumbnail = InMemoryUploadedFile(
                    thumbnail_file, 'thumbnail', 'thumbnail.gif',
                    'gif', thumbnail_file.tell(), None)
                thumbnail_model = sample_thumbnail_image(
                    thumbnailed_image=thumbnail,
                    thumbnail_value=sample_thumbnail(**{'value': '1'}))
                thumbnail_model.full_clean()  # validate fields without saving

    @patch('core.models.uuid.uuid4')
    def test_expired_link_image_model(self, patched_uuid):
        with tempfile.NamedTemporaryFile(suffix='.png') as bimage_file:
            bimage = Image.new('RGB', (1, 1))
            bimage.save(bimage_file, 'png')
            bimage = InMemoryUploadedFile(
                bimage_file, 'bimage', 'bimage.png',
                'png', bimage_file.tell(), None)
            bimage_model = sample_expired_link_image(
                duration=300, binary_image=bimage)

            uuid = 'test-uuid'
            patched_uuid.return_value = uuid
            file_path = models.image_file_path(bimage_model, bimage.name)
            self.assertEqual(file_path, f'uploads/{uuid}.png')
            self.assertTrue(bimage_model.binary_image)
            self.assertEqual(
                bimage_model.date_created.hour, timezone.now().hour)
            self.assertEqual(
                bimage_model.date_created.minute, timezone.now().minute)

    def test_expired_link_image_model_upload_with_invalid_ext(self):
        with self.assertRaises(ValidationError):
            with tempfile.NamedTemporaryFile(suffix='.gif') as bimage_file:
                bimage = Image.new('RGB', (1, 1))
                bimage.save(bimage_file, 'gif')
                bimage = InMemoryUploadedFile(
                    bimage_file, 'bimage', 'bimage.gif',
                    'gif', bimage_file.tell(), None)
                bimage_model = sample_expired_link_image(
                    duration=300, binary_image=bimage)
                bimage_model.full_clean()  # validate fields without saving
