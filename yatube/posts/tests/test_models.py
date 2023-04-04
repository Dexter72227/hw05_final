from django.contrib.auth import get_user_model
from django.test import TestCase
from ..models import Group, Post

User = get_user_model()


class PostModelTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test_slug',
            description='Описание тестовой группы',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Текст тестового поста',
        )

    def test_models_group_str(self):
        """Проверка, что у модели group корректно работает __str__."""
        self.assertEqual(self.group.title, str(self.group))

    def test_models_post_str(self):
        """Проверка, что у модели post корректно работает __str__."""
        self.assertEqual(self.post.text[:15], str(self.post))
