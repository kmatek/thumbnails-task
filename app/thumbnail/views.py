from rest_framework import generics, permissions, status
from rest_framework.response import Response
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.cache import cache
from .serializers import (
    ImageUploadSerializer,
    ExpiredLinkImageSerializer,
    ImageListSerializer
)
from .permissions import DoesUserHaveTier, CanCreateLink
from core.models import ExpiredLinkImage, Image


class ImageUploadAPIView(generics.CreateAPIView):
    """Upload an image view."""
    serializer_class = ImageUploadSerializer
    permission_classes = (permissions.IsAuthenticated, DoesUserHaveTier)

    def perform_create(self, serializer):
        """Upload an image with authenticated user."""
        cache_key = f'queryset_{self.request.user.id}'
        # Get cached queryset
        queryset = cache.get(cache_key)
        # Clear cache if exists
        if queryset:
            cache.delete(cache_key)
        # Pass authenticated user to the serializer
        serializer.save(user=self.request.user)


class ImageListAPIView(generics.ListAPIView):
    """List user images."""
    serializer_class = ImageListSerializer
    permission_classes = (permissions.IsAuthenticated, DoesUserHaveTier)

    def get_queryset(self):
        """Get authenticated user's images and cache them for 15 minutes."""
        cache_key = f'queryset_{self.request.user.id}'
        # Get cached queryset
        queryset = cache.get(cache_key)
        # Set cache if not exists
        if not queryset:
            queryset = Image.objects.filter(user=self.request.user)\
                .select_related('user__plan')\
                .prefetch_related('user__plan__thumbnails')\
                .prefetch_related('thumbnails')\
                .prefetch_related('thumbnails__thumbnail_value')\
                .order_by('-id')
            cache.set(cache_key, queryset, 60*15)
        return queryset


class ExpiredLinkImageCreateAPIView(generics.CreateAPIView):
    """Create en expired link with a binary image."""
    serializer_class = ExpiredLinkImageSerializer
    permission_classes = (permissions.IsAuthenticated, CanCreateLink)

    def get_serializer_context(self):
        """Add image_uuid to the context."""
        return {
            'request': self.request,
            'format': self.format_kwarg,
            'view': self,
            'image_uuid': self.kwargs.get('image_pk')
        }


class ExpiredLinkImageRetrieveAPIView(generics.RetrieveAPIView):
    """Retrieve en expired link with a binary image."""
    serializer_class = ExpiredLinkImageSerializer

    def get_object(self):
        """Return binary image by uuid."""
        return ExpiredLinkImage.objects.get(uuid=self.kwargs.get('bimage_pk'))

    def retrieve(self, *args, **kwargs):
        """Check that link is still available."""
        # Get binary image
        instance = self.get_object()
        # Get passed seconds since created
        passed_seconds = timezone.now() - instance.date_created
        # Check that link is still available
        if passed_seconds.seconds > instance.duration:
            return Response(
                {'detail': _('Link has expired.')},
                status=status.HTTP_400_BAD_REQUEST)
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
