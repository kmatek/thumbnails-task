from django.test import TestCase
from django.core.cache import cache


class RedisTestCase(TestCase):
    def test_redis_connection(self):
        key = 'test_key'
        value = 'test_value'
        cache.set(key, value)

        result = cache.get(key)
        self.assertEqual(result, value)
