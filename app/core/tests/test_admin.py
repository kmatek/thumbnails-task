from django.test import TestCase, Client, override_settings
from django.contrib.auth import get_user_model
from django.urls import reverse
from core.models import Plan, Thumbnail


@override_settings(
    SUSPEND_SIGNALS=True
)
class AdminSiteTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.admin_user = get_user_model().objects.create_superuser(
            email='admin@test.com', name='admin', password='testadminpassword') # noqa
        self.client.force_login(self.admin_user)
        self.user = get_user_model().objects.create_user(
            email='test@test.com', password='testpassword', name='testusername') # noqa
        self.thumbnail = Thumbnail.objects.create(value=100)
        self.plan = Plan.objects.create(name='Plan')
        self.plan.thumbnails.add(self.thumbnail)

    def test_users_listed(self):
        url = reverse('admin:core_user_changelist')
        res = self.client.get(url)

        self.assertEqual(res.status_code, 200)
        self.assertContains(res, self.user.email)

    def test_change_user_page(self):
        url = reverse('admin:core_user_change', args=[self.user.id])
        res = self.client.get(url)

        self.assertEqual(res.status_code, 200)

    def test_create_user_page(self):
        url = reverse('admin:core_user_add')
        res = self.client.get(url)

        self.assertEqual(res.status_code, 200)

    def test_delete_user_page(self):
        url = reverse('admin:core_user_delete', args=[self.user.id])
        res = self.client.get(url)

        self.assertEqual(res.status_code, 200)

    def test_thumbnail_listed(self):
        url = reverse('admin:core_thumbnail_changelist')
        res = self.client.get(url)

        self.assertEqual(res.status_code, 200)
        self.assertContains(res, str(self.thumbnail.value))

    def test_change_thumbnail_page(self):
        url = reverse('admin:core_thumbnail_change', args=[self.thumbnail.id])
        res = self.client.get(url)

        self.assertEqual(res.status_code, 200)

    def test_create_thumbnail_page(self):
        url = reverse('admin:core_thumbnail_add')
        res = self.client.get(url)

        self.assertEqual(res.status_code, 200)

    def test_delete_thumbnail_page(self):
        url = reverse('admin:core_thumbnail_delete', args=[self.thumbnail.id])
        res = self.client.get(url)

        self.assertEqual(res.status_code, 200)

    def test_plan_listed(self):
        url = reverse('admin:core_plan_changelist')
        res = self.client.get(url)

        self.assertEqual(res.status_code, 200)
        self.assertContains(res, self.plan.name)

    def test_change_plan_page(self):
        url = reverse('admin:core_plan_change', args=[self.plan.id])
        res = self.client.get(url)

        self.assertEqual(res.status_code, 200)

    def test_create_plan_page(self):
        url = reverse('admin:core_plan_add')
        res = self.client.get(url)

        self.assertEqual(res.status_code, 200)

    def test_delete_plan_page(self):
        url = reverse('admin:core_plan_delete', args=[self.plan.id])
        res = self.client.get(url)

        self.assertEqual(res.status_code, 200)
