from django.urls import path
from .views import ImageUploadAPIView

app_name = 'thumbnail'

urlpatterns = [
    path('upload/', ImageUploadAPIView.as_view(), name='upload-image'),
]
