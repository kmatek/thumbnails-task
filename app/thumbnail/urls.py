from django.urls import path
from .views import (
     ImageUploadAPIView,
     ExpiredLinkImageCreateAPIView,
     ExpiredLinkImageRetrieveAPIView,
     ImageListAPIView
)

app_name = 'thumbnail'

urlpatterns = [
    path('', ImageListAPIView.as_view(), name='list-image'),
    path('upload/', ImageUploadAPIView.as_view(), name='upload-image'),
    path('create-link/<uuid:image_pk>/',
         ExpiredLinkImageCreateAPIView.as_view(), name='create-link'),
    path('retreive-link/<uuid:bimage_pk>/',
         ExpiredLinkImageRetrieveAPIView.as_view(), name='retrieve-link'),
]
