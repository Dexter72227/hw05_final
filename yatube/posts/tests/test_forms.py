import shutil
import tempfile
from http import HTTPStatus

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..models import Group, Post

User = get_user_model()
TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.post_author = User.objects.create_user(
            username='author')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test_slug',
            description='Описание тестовой группы',
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.guest_user = Client()
        self.authorized_user = Client()
        self.authorized_user.force_login(self.post_author)
        self.auth_user_comm = Client()

    def test_for_authorized_user_and_image(self):
        """Валидная форма создает запись c картинкой."""
        posts_count = Post.objects.count()
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        form_data = {
            'text': 'Тестовый текст',
            'group': self.group.id,
            'image': uploaded,
        }
        response = self.authorized_user.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertRedirects(
            response,
            reverse(
                'posts:profile',
                kwargs={'username': self.post_author.username})
        )
        self.assertEqual(Post.objects.count(), posts_count + 1)
        post = Post.objects.latest('id')
        self.assertEqual(post.text, form_data['text'])
        self.assertEqual(post.author, self.post_author)
        self.assertEqual(post.group_id, form_data['group'])
        response = self.guest_user.get(reverse('posts:index'))
        self.assertContains(response, '<img', count=1)
        response = self.guest_user.get(reverse('posts:profile', kwargs={
            'username': self.post_author.username
        }))
        self.assertContains(response, '<img', count=1)
        response = self.guest_user.get(reverse('posts:post_detail', kwargs={
            'post_id': post.id
        }))
        self.assertContains(response, '<img', count=1)
        response = self.guest_user.get(reverse('posts:group_list', kwargs={
            'slug': self.group.slug
        }))
        self.assertContains(response, '<img', count=1)

    def test_edit_post_valid_form(self):
        """Проверка при отправке валидной формы со страницы редактирования."""
        post = Post.objects.create(
            text='Текст поста для редактирования',
            author=self.post_author,
            group=self.group,
        )
        form_data = {
            'text': 'Отредактированный текст поста',
            'group': self.group.id,
        }
        response = self.authorized_user.post(
            reverse(
                'posts:post_edit',
                args=[post.id]),
            data=form_data,
            follow=True
        )
        self.assertRedirects(
            response,
            reverse('posts:post_detail', kwargs={'post_id': post.id})
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        post.refresh_from_db()
        self.assertEqual(post.text, form_data['text'])
        self.assertEqual(post.author, self.post_author)
        self.assertEqual(post.group_id, form_data['group'])

    def test_nonauthorized_user_create_post(self):
        """Проверка создания записи не авторизированным пользователем."""
        posts_count = Post.objects.count()
        form_data = {
            'text': 'Текст поста',
            'group': self.group.id,
        }
        response = self.guest_user.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        redirect = reverse('login') + '?next=' + reverse('posts:post_create')
        self.assertRedirects(response, redirect)
        self.assertEqual(Post.objects.count(), posts_count)
