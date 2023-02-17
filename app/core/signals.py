import functools
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.conf import settings
from .models import Image
from thumbnail.tasks import create_thumbnails


def suspendingreceiver(signal, **decorator_kwargs):
    def our_wrapper(func):
        @receiver(signal, **decorator_kwargs)
        @functools.wraps(func)
        def fake_receiver(sender, **kwargs):
            if settings.SUSPEND_SIGNALS:
                return
            return func(sender, **kwargs)
        return fake_receiver
    return our_wrapper


@suspendingreceiver(post_save, sender=get_user_model())
def update_thumbnails(sender, instance, created, **kwargs):
    """
    Update user's thumbnail when change plan
    and there will be new thumbnail values.
    """
    # Get current plan id if user has plan
    try:
        current_plan = instance.plan
        # Get cached user's plan id
        cache_key = f'{instance.email}-plan'
        cached_plan = cache.get(cache_key)
    except AttributeError:
        return
    # Set if cached plan id not exists
    if not cached_plan:
        cache.set(cache_key, current_plan)
        return
    else:
        # Update thumbnails
        if current_plan.id != cached_plan.id:
            # Cache new plan
            cache.set(cache_key, current_plan)
            # Get current thumbnails and cached thumbnails
            current_thumbnails = current_plan.thumbnails.all()
            cached_thumbnails = cached_plan.thumbnails.all()
            # Compare them
            current_set = set(current_thumbnails)
            cached_set = set(cached_thumbnails)
            difference = current_set - cached_set
            difference_values = [thumb.value for thumb in difference]
            # If there is difference between
            if difference:
                # Get user images
                images = Image.objects.filter(user=instance)\
                    .prefetch_related('thumbnails')\
                    .prefetch_related('thumbnails__thumbnail_value')
                # Create new thumbnails
                # I cant figure out how to make it faster
                # so i ended up with O(n^2)
                for image in images:
                    # Check if thumbnail image with
                    # value from difference exists
                    for thumb_image in image.thumbnails.all():
                        thumb_value = thumb_image.thumbnail_value.value
                        if thumb_value in difference_values:
                            difference_values.remove(thumb_value)
                    # Create thumbnails for every value
                    if difference_values:
                        create_thumbnails(
                            image.id, thumbnail_values=difference_values)
