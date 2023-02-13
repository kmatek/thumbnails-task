from rest_framework import serializers
from core.models import Image


class ImageUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Image
        exclude = ('user', 'id')
