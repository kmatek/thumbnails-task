import os
import uuid
from django.db import models
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin)
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.utils import timezone


def image_ext_validator(value):
    """Validating thath if image extension is different than PNG or JPEG."""
    extensions = ('png', 'jpg', 'jpeg')
    if not any([True if value.name.endswith(i) else False for i in extensions]): # noqa
        raise ValidationError(_('JPEG and PNG extension are only allowed.'))


def image_file_path(instance, filename):
    """Creating a path that prevent duplication of image name."""
    ext = os.path.splitext(filename)[1]
    filename = f'{uuid.uuid4()}{ext}'

    return os.path.join('uploads', filename)


class UserManager(BaseUserManager):
    """Modify creating a new user/admin user."""
    def create_user(self, email, name, password=None, **extra_fields):
        if not email:
            raise ValueError('User must have an email address')
        if not name:
            raise ValueError('User must have a name')

        user = self.model(
            email=self.normalize_email(email),
            name=name.lower(),
            **extra_fields)
        user.set_password(password)
        user.save(using=self._db)

        return user

    def create_superuser(self, email, name, password):
        super_user = self.create_user(email, name, password)
        super_user.is_staff = True
        super_user.is_superuser = True
        super_user.save(using=self._db)

        return super_user


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(max_length=255, unique=True, blank=False)
    name = models.CharField(max_length=30, unique=True, blank=False)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    plan = models.ForeignKey(
        'Plan', on_delete=models.CASCADE, null=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'


class Thumbnail(models.Model):
    value = models.SmallIntegerField(unique=True)

    def __str__(self):
        return str(self.value)


class Plan(models.Model):
    name = models.CharField(max_length=255, unique=True)
    thumbnails = models.ManyToManyField(
        Thumbnail, related_query_name='thumbnail')
    original_image = models.BooleanField(default=False)
    expired_link = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class Image(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    image = models.ImageField(
        upload_to=image_file_path, validators=[image_ext_validator])
    thumbnails = models.ManyToManyField('ThumbnailImage')


class ThumbnailImage(models.Model):
    thumbnail_value = models.ForeignKey(
        Thumbnail, on_delete=models.PROTECT, null=True)
    thumbnailed_image = models.ImageField(
        upload_to=image_file_path, validators=[image_ext_validator])


class ExpiredLinkImage(models.Model):
    uuid = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False)
    binary_image = models.ImageField(
        upload_to=image_file_path, validators=[image_ext_validator])
    duration = models.SmallIntegerField(
        validators=[MaxValueValidator(30000), MinValueValidator(300)])
    date_created = models.DateTimeField(default=timezone.now)
