from django.utils.translation import gettext_lazy as _
from rest_framework import serializers, status
from rest_framework.reverse import reverse
from core.models import (Image, Plan, ThumbnailImage, ExpiredLinkImage)
from .tasks import create_thumbnail, create_binary_image


class ImageUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Image
        exclude = ('user', 'uuid', 'id', 'thumbnails')
        extra_kwargs = {'image': {'write_only': True}}

    def create(self, validated_data):
        """Creating an image and thumbnails according to their values from the plan.""" # noqa
        image = Image.objects.create(**validated_data)
        plan = Plan.objects.prefetch_related('thumbnails') \
            .get(id=self.context.get('request').user.plan_id)
        # Create thumbnails
        thumbs = []
        for value in plan.thumbnails.all():
            thumbs.append(create_thumbnail.delay(image.id, value.value).get())
        image.thumbnails.add(*thumbs)
        return object()  # Return none


class ThumbnailImageSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = ThumbnailImage
        fields = ('thumbnailed_image',)

    def to_representation(self, instance):
        """Change thumbnail_value to value."""
        ret = super().to_representation(instance)
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
        request = self.context.get('request')
        return reverse(
                "thumbnail:create-link",
                args=[obj.uuid], request=request)

    def get_thumbnails(self, obj):
        """Shows fields and thumbnails depending on user's plan."""
        thumbnails = list(obj.thumbnails.all())
        thumb_values = [thumb.thumbnail_value.value for thumb in thumbnails]
        allowed_thumb_values = [
            thumb.value
            for thumb in obj.user.plan.thumbnails.all()
        ]
        # Create new thumbails if user upgrade plan.
        if not allowed_thumb_values == thumb_values:
            thumbs = []
            for value in allowed_thumb_values:
                if value not in thumb_values:
                    thumbs.append(create_thumbnail.delay(obj.id, value).get())
            obj.thumbnails.add(*thumbs)
        # Filter query according to allowed thumbnail values
        query = filter(
            lambda x: x.thumbnail_value.value in allowed_thumb_values,
            thumbnails
        )
        return ThumbnailImageSerializer(
            query, many=True, context=self.context).data

    def to_representation(self, instance):
        """Change reprenstation vie according to the plan."""
        ret = super().to_representation(instance)
        if not instance.user.plan.expired_link:
            ret.pop('expired_link')
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
        duration = validated_data['duration']
        result = create_binary_image.delay(image.id, duration)
        return ExpiredLinkImage.objects.get(uuid=result.get())
