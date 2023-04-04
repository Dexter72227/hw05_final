from http import HTTPStatus
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from ..models import Group, Post
from ..forms import PostForm

User = get_user_model()


class Form_Tests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.post_author = User.objects.create_user(
            username='post_author',
        )
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test_slug',
            description='Описание тестовой группы',
        )

        cls.uploaded_image = SimpleUploadedFile(
            name='test_image.jpg',
            content=open('posts/tests/test_image.jpg', 'rb').read(),
            content_type='image/jpeg'
        )

    def test_post_with_image_context(self):
        """Проверка наличия изображения в словаре контекста на нужных страницах."""
        post = Post.objects.create(
            text='Текст поста с картинкой',
            author=self.post_author,
            group=self.group,
            image=self.uploaded_image
        )

        urls = [
            reverse('posts:index'),
            reverse('posts:profile', kwargs={'username': self.post_author.username}),
            reverse('posts:group_list', kwargs={'slug': self.group.slug}),
            reverse('posts:post_detail', kwargs={'post_id': post.id}),
        ]

        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertContains(response, '<img')
    def setUp(self):
        self.authorized_user = Client()
        self.authorized_user.force_login(self.post_author)

    def test_create_post_valid_form(self):
        """Проверка при отправке валидной формы со страницы создания поста + картинка."""
        posts_count = Post.objects.count()
        form_data = {
            'text': 'Текст поста',
            'group': self.group.id,
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
        
        form_data_with_image = {
            'text': 'Текст поста с картинкой',
            'group': self.group.id,
        }
        files_data = {'image': self.uploaded_image}
        response_with_image = self.authorized_user.post(
            reverse('posts:post_create'),
            data=form_data_with_image,
            files=files_data,
            follow=True
        )
        self.assertRedirects(
            response_with_image,
            reverse(
                'posts:profile',
                kwargs={'username': self.post_author.username})
        )
        self.assertEqual(Post.objects.count(), posts_count + 2)
    

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
