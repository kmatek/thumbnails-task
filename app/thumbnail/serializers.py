import tempfile
from PIL import Image as pill_image
from django.core.files.uploadedfile import InMemoryUploadedFile
from rest_framework import serializers
from core.models import Image, ThumbnailImage, Plan, Thumbnail


def create_thumbnail(image: Image, value: Thumbnail) -> None:
    """Create a thumbnail according to given image and size."""
    with tempfile.NamedTemporaryFile(suffix='.png') as image_file:
        with pill_image.open(image.image) as im:
            # Make thumbnail
            size = value.value, value.value
            im.thumbnail(size)
            im.save(image_file, 'png')
            thumb_image = InMemoryUploadedFile(
                image_file, 'image', 'image.png',
                'png', image_file.tell(), None)
            # Creating a model
            ThumbnailImage.objects.create(
                original_image=image, thumbnail_value=value,
                thumbnailed_image=thumb_image)


class ImageUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Image
        exclude = ('user', 'id')
        extra_kwargs = {'image': {'write_only': True}}

    def create(self, validated_data):
        """Creating an image and thumbnails according to their values from the plan.""" # noqa
        image = Image.objects.create(**validated_data)
        plan = Plan.objects.prefetch_related('thumbnails') \
            .get(id=self.context.get('request').user.plan_id)
        # Create thumbnails
        for value in plan.thumbnails.all():
            thumbnail_image = create_thumbnail(image, value)
        return object() # Return none
