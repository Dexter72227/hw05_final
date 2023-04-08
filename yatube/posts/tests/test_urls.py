from http import HTTPStatus
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from ..models import Group, Post, Comment


User = get_user_model()


class UrlsTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test_slug',
            description='Описание тестовой группы',
        )

        cls.author = User.objects.create_user(
            username='author')
        cls.user = User.objects.create_user(
            username='user')
        cls.post = Post.objects.create(
            text='Текст тестового поста',
            author=cls.author,
            group=cls.group,
        )
        cls.comment = Comment.objects.create(
            post=cls.post,
            author=cls.author,
            text='Тестовый комментарий',
        )

    def setUp(self):
        self.unauthorized_user = Client()
        self.post_author = Client()
        self.post_author.force_login(self.author)
        self.authorized_user = Client()
        self.authorized_user.force_login(self.user)

    def test_urls(self):
        """Проверка, что URL-адрес использует правильный шаблон."""
        templates_url_names = {
            '/': 'posts/index.html',
            f'/group/{self.group.slug}/': 'posts/group_list.html',
            f'/profile/{self.author.username}/': 'posts/profile.html',
            f'/posts/{self.post.id}/': 'posts/post_detail.html',
            f'/posts/{self.post.id}/edit/': 'posts/create_post.html',
            '/create/': 'posts/create_post.html',
            '/follow/': 'posts/follow.html',
        }
        for adress, template in templates_url_names.items():
            with self.subTest(adress=adress):
                response = self.post_author.get(adress)
                self.assertTemplateUsed(response, template)

    def test_unauthorized_user(self):
        """Проверка HTTPStatus для неавторизованного пользователя."""
        field_urls_code = {
            '/': HTTPStatus.OK,
            f'/group/{self.group.slug}/': HTTPStatus.OK,
            '/group/bad_slug/': HTTPStatus.NOT_FOUND,
            f'/profile/{self.author.username}/': HTTPStatus.OK,
            f'/posts/{self.post.id}/': HTTPStatus.OK,
            f'/posts/{self.post.id}/edit/': HTTPStatus.FOUND,
            '/create/': HTTPStatus.FOUND,
            '/unexisting_page/': HTTPStatus.NOT_FOUND,
            '/follow/': HTTPStatus.FOUND,
        }
        for url, response_code in field_urls_code.items():
            with self.subTest(url=url):
                status_code = self.unauthorized_user.get(url).status_code
                self.assertEqual(status_code, response_code)

    def test_authorized_user(self):
        """Проверка HTTPStatus для авторизованного пользователя."""
        field_urls_code = {
            '/': HTTPStatus.OK,
            f'/group/{self.group.slug}/': HTTPStatus.OK,
            '/group/bad_slug/': HTTPStatus.NOT_FOUND,
            f'/profile/{self.author.username}/': HTTPStatus.OK,
            f'/posts/{self.post.id}/': HTTPStatus.OK,
            f'/posts/{self.post.id}/edit/': HTTPStatus.FOUND,
            '/create/': HTTPStatus.OK,
            '/unexisting_page/': HTTPStatus.NOT_FOUND,
            '/follow/': HTTPStatus.OK,
        }
        for url, response_code in field_urls_code.items():
            with self.subTest(url=url):
                status_code = self.authorized_user.get(url).status_code
                self.assertEqual(status_code, response_code)

    def test_author_urls(self):
        """Проверка HTTPStatus для автора."""
        field_urls_code = {
            '/': HTTPStatus.OK,
            f'/group/{self.group.slug}/': HTTPStatus.OK,
            '/group/bad_slug/': HTTPStatus.NOT_FOUND,
            f'/profile/{self.author.username}/': HTTPStatus.OK,
            f'/posts/{self.post.id}/': HTTPStatus.OK,
            f'/posts/{self.post.id}/edit/': HTTPStatus.OK,
            '/create/': HTTPStatus.OK,
            '/unexisting_page/': HTTPStatus.NOT_FOUND,
            '/follow/': HTTPStatus.OK,
        }
        for url, response_code in field_urls_code.items():
            with self.subTest(url=url):
                status_code = self.post_author.get(url).status_code
                self.assertEqual(status_code, response_code)


class Custom404(TestCase):
    def setUp(self):
        self.client = Client()

    def test_custom_404_template(self):
        """Проверка custom 404."""
        response = self.client.get('/non-existent-url/')
        self.assertEqual(response.status_code, 404)
        self.assertTemplateUsed(response, 'core/404.html')
