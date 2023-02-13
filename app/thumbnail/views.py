from rest_framework import generics, permissions
from .serializers import ImageUploadSerializer
from .permissions import DoesUserHaveTier


class ImageUploadAPIView(generics.CreateAPIView):
    """Upload an image view."""
    serializer_class = ImageUploadSerializer
    permission_classes = (permissions.IsAuthenticated, DoesUserHaveTier)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
