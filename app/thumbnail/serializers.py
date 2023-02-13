from io import BytesIO
from PIL import Image as pill_image
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers, status
from rest_framework.reverse import reverse
from core.models import (
    Image, ThumbnailImage, Plan, Thumbnail, ExpiredLinkImage)


def create_thumbnail(image: Image, value: Thumbnail) -> None:
    """Create a thumbnail according to given image and size."""
    with pill_image.open(image.image) as im:
        io_img = BytesIO()
        # Make thumbnail
        size = value.value, value.value
        im.thumbnail(size)
        im.save(io_img, 'png')
        thumb_image = InMemoryUploadedFile(
            io_img, 'image', 'image.png',
            'png', io_img.tell(), None)
        # Creating a model
        ThumbnailImage.objects.create(
            original_image=image, thumbnail_value=value,
            thumbnailed_image=thumb_image)


class ImageUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Image
        exclude = ('user', 'uuid', 'id')
        extra_kwargs = {'image': {'write_only': True}}

    def create(self, validated_data):
        """Creating an image and thumbnails according to their values from the plan.""" # noqa
        image = Image.objects.create(**validated_data)
        plan = Plan.objects.prefetch_related('thumbnails') \
            .get(id=self.context.get('request').user.plan_id)
        # Create thumbnails
        for value in plan.thumbnails.all():
            create_thumbnail(image, value)
        return object()  # Return none


class ExpiredLinkImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpiredLinkImage
        exclude = ('date_created', 'uuid')
        extra_kwargs = {
            'binary_image': {'read_only': True},
            'duration': {'write_only': True}
        }

    def to_representation(self, instance):
        """Change representation for creating expired link model."""
        ret = super().to_representation(instance)
        request = self.context.get("request")
        if request.method == 'POST':
            ret.pop('binary_image')
            url = reverse(
                "thumbnail:retrieve-link",
                args=[instance.uuid], request=request)
            ret['link'] = url
        return ret

    def validate(self, data):
        """Check that user is image owner."""
        user = self.context.get("request").user
        image = Image.objects.get(uuid=self.context.get('image_uuid'))
        if user != image.user:
            msg = _('You are not the owner of the image.')
            return serializers.ValidationError(
                {'detail': msg}, status_code=status.HTTP_403_FORBIDDEN)
        data['image'] = image
        return data

    def create(self, validated_data):
        image = validated_data['image']
        with pill_image.open(image.image) as im:
            io_img = BytesIO()
            # Make binary image
            im = im.convert('1')
            im.save(io_img, 'png',)
            b_image = InMemoryUploadedFile(
                io_img, 'image', 'image.png',
                'png', io_img.tell(), None)
            # Creating a model
            return ExpiredLinkImage.objects.create(
                duration=validated_data['duration'], binary_image=b_image)
