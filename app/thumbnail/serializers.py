from django.utils.translation import gettext_lazy as _
from rest_framework import serializers, status
from rest_framework.reverse import reverse
from core.models import (Image, ThumbnailImage, ExpiredLinkImage)
from .tasks import create_thumbnails, create_binary_image


class ImageUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Image
        exclude = ('user', 'uuid', 'id', 'thumbnails')
        extra_kwargs = {'image': {'write_only': True}}

    def create(self, validated_data):
        """Creating an image and thumbnails."""
        # Create image
        image = Image.objects.create(**validated_data)
        # Create thumbnails
        create_thumbnails.delay(image.id)
        # Return None
        return object()


class ThumbnailImageSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = ThumbnailImage
        fields = ('thumbnailed_image',)

    def to_representation(self, instance):
        """Change thumbnail_value to value."""
        ret = super().to_representation(instance)
        # Replace
        ret['value'] = instance.thumbnail_value.value
        return ret


class ImageListSerializer(serializers.ModelSerializer):
    thumbnails = serializers.SerializerMethodField(read_only=True)
    expired_link = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Image
        exclude = ('uuid', 'user', 'id')

    def get_expired_link(self, obj):
        """Create binary_image link."""
        # Get request
        request = self.context.get('request')
        # Create link to expired link
        return reverse(
                "thumbnail:create-link",
                args=[obj.uuid], request=request)

    def get_thumbnails(self, obj):
        """Shows fields and thumbnails depending on user's plan."""
        # Get allowed thumbnail values
        allowed_thumbs_values = [
            thumb.value
            for thumb in obj.user.plan.thumbnails.all()
        ]
        # Filter thumbnails with allowed ones
        query = filter(
            lambda x: x.thumbnail_value.value in allowed_thumbs_values,
            obj.thumbnails.all()
        )
        return ThumbnailImageSerializer(
            query, many=True, context=self.context).data

    def to_representation(self, instance):
        """Change reprenstation vie according to the plan."""
        ret = super().to_representation(instance)
        # Drop expired link field
        if not instance.user.plan.expired_link:
            ret.pop('expired_link')
        # Drop original image field
        if not instance.user.plan.original_image:
            ret.pop('image')
        return ret


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
        # Get user
        request = self.context.get("request")
        # Drop binary image field when user created link
        if request.method == 'POST':
            ret.pop('binary_image')
            # Create link
            url = reverse(
                "thumbnail:retrieve-link",
                args=[instance.uuid], request=request)
            ret['link'] = url
        return ret

    def validate(self, data):
        """Check that user is image owner."""
        # Get user
        user = self.context.get("request").user
        # Get image
        image = Image.objects.get(uuid=self.context.get('image_uuid'))
        # Check that user is owner of an image
        if user != image.user:
            msg = _('You are not the owner of the image.')
            return serializers.ValidationError(
                {'detail': msg}, status_code=status.HTTP_403_FORBIDDEN)
        # Add image to validated data
        data['image'] = image
        return data

    def create(self, validated_data):
        """Create binary image model."""
        # Get image
        image = validated_data['image']
        # Get duration
        duration = validated_data['duration']
        # Create binary image
        result = create_binary_image.delay(image.id, duration)
        # Return binary image
        return ExpiredLinkImage.objects.get(uuid=result.get())
