from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django import forms
from ..models import Follow, Group, Post
from django.core.cache import cache

User = get_user_model()


class ViewsTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='admin')
        self.client.force_login(self.user)
        self.group = Group.objects.create(
            title='Тестовая группа',
            slug='test_slug',
            description='Описание тестовой группы',
        )
        self.post = Post.objects.create(
            text='Текст тестового поста',
            author=self.user,
            group=self.group,
        )

    def check_post_info(self, post):
        with self.subTest(post=post):
            self.assertEqual(post.text, self.post.text)
            self.assertEqual(post.author, self.post.author)
            self.assertEqual(post.group.id, self.post.group.id)

    def test_index_page_show_correct_context(self):
        """Шаблон index.html сформирован правильно."""
        response = self.client.get(reverse('posts:index'))
        self.check_post_info(response.context['page_obj'][0])

    def test_groups_page_show_correct_context(self):
        """Шаблон group_list.html сформирован правильно."""
        response = self.client.get(
            reverse(
                'posts:group_list',
                kwargs={'slug': self.group.slug})
        )
        self.assertEqual(response.context['group'], self.group)
        self.check_post_info(response.context['page_obj'][0])

    def test_profile_page_show_correct_context(self):
        """Шаблон profile.html сформирован правильно."""
        response = self.client.get(
            reverse(
                'posts:profile',
                kwargs={'username': self.user.username}))
        self.assertEqual(response.context['author'], self.user)
        self.check_post_info(response.context['page_obj'][0])

    def test_detail_page_show_correct_context(self):
        """Шаблон post_detail.html сформирован правильно."""
        response = self.client.get(
            reverse(
                'posts:post_detail',
                kwargs={'post_id': self.post.id}))
        self.check_post_info(response.context['post'])

    def test_forms_show_correct(self):
        """Проверка коректности форм post_create, post_edit."""
        context = {
            reverse('posts:post_create'),
            reverse('posts:post_edit', kwargs={'post_id': self.post.id, }),
        }
        for reverse_page in context:
            with self.subTest(reverse_page=reverse_page):
                response = self.client.get(reverse_page)
                self.assertIsInstance(
                    response.context['form'].fields['text'],
                    forms.fields.CharField)
                self.assertIsInstance(
                    response.context['form'].fields['group'],
                    forms.fields.ChoiceField)

    def test_post_create_correct(self):
        """Проверка создания поста с указанной группой."""
        new_group = Group.objects.create(
            title='Новая тестовая группа',
            slug='new_slug',
            description='Описание новой тестовой группы',
        )
        self.post.group = new_group
        self.post.save()

        urls = [
            reverse('posts:index'),
            reverse('posts:group_list', kwargs={'slug': new_group.slug}),
            reverse('posts:profile', kwargs={'username': self.user.username}),
            reverse('posts:group_list', kwargs={'slug': self.group.slug}),
        ]

        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                if response.context.get('page_obj'):
                    self.assertIn(self.post, response.context['page_obj'])


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create(
            username='admin',
        )
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test_slug',
            description='Описание группы',
        )
        cls.posts = [
            Post.objects.create(
                text=f'Пост #{i}',
                author=cls.user,
                group=cls.group
            ) for i in range(13)
        ]

    def setUp(self):
        self.unauthorized_client = Client()

    def test_paginator_on_pages(self):
        """Проверка пагинации на страницах."""
        url_pages = [
            reverse('posts:index'),
            reverse('posts:group_list', kwargs={'slug': self.group.slug}),
            reverse('posts:profile', kwargs={'username': self.user.username}),
        ]
        for reverse_ in url_pages:
            with self.subTest(reverse_=reverse_):
                response = self.unauthorized_client.get(reverse_)
                page_obj = response.context['page_obj']
                self.assertEqual(len(page_obj), 10)
                self.assertEqual(page_obj.paginator.num_pages, 2)

                response = self.unauthorized_client.get(f'{reverse_}?page=2')
                page_obj = response.context['page_obj']
                self.assertEqual(len(page_obj), 3)


class ViewscommentsTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='admin')

    def test_auth_required_to_comment(self):
        """Только авторизованный пользователь может комментировать посты"""
        post = Post.objects.create(
            text='Текст тестового поста',
            author=self.user,
        )
        response = self.client.post(
            reverse('posts:add_comment', kwargs={'post_id': post.id}),
            {'text': 'Test comment'}
        )
        next_url = reverse("posts:add_comment", kwargs={"post_id": post.id})
        login_url = reverse("login") + "?next=" + next_url
        self.assertRedirects(
            response,
            login_url
        )
        self.client.force_login(self.user)
        response = self.client.post(
            reverse('posts:add_comment', kwargs={'post_id': post.id}),
            {'text': 'Test comment'}
        )
        self.assertRedirects(
            response,
            reverse('posts:post_detail', kwargs={'post_id': post.id})
        )
        self.assertEqual(
            len(Post.objects.get(id=post.id).comments.all()), 1
        )

    def test_comment_appears_after_creation(self):
        """После успешной отправки комментарий появляется на странице поста"""
        self.client.force_login(self.user)
        post = Post.objects.create(
            text='Текст тестового поста',
            author=self.user,
        )
        comment_text = 'Текст тестового комментария'
        self.client.post(
            reverse('posts:add_comment', kwargs={'post_id': post.id}),
            {'text': comment_text}
        )
        response = self.client.get(
            reverse('posts:post_detail', kwargs={'post_id': post.id})
        )
        self.assertContains(response, comment_text)


class ViewsCacheTests(TestCase):
    def setUp(self):
        self.authorized_client = Client()
        self.user = User.objects.create_user(username='admin')
        self.authorized_client.force_login(self.user)
        self.group = Group.objects.create(
            title='Тестовая группа',
            slug='test_slug',
            description='Описание тестовой группы',
        )
        self.post = Post.objects.create(
            text='Текст тестового поста',
            author=self.user,
            group=self.group,
        )
        cache.clear()

    def test_cache_index(self):
        """Проверка работы кеша на главной странице"""
        response1 = self.authorized_client.get(reverse('posts:index'))
        content1 = response1.content
        self.assertIn('Текст тестового поста'.encode(), content1)
        response2 = self.authorized_client.get(reverse('posts:index'))
        content2 = response2.content
        self.assertIn('Текст тестового поста'.encode(), content2)
        self.assertEqual(content1, content2)
        Post.objects.create(
            text='Пост для проверки кеша',
            author=self.user)
        cache.clear()
        response3 = self.authorized_client.get(reverse('posts:index'))
        content3 = response3.content
        self.assertIn('Пост для проверки кеша'.encode(), content3)
        self.assertNotEqual(content2, content3)
        self.assertEqual(response3.status_code, 200)


class FollowTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user1 = User.objects.create_user(username='user1')
        self.user2 = User.objects.create_user(username='user2')
        self.client.force_login(self.user1)

    def test_follow_user(self):
        """Проверка, что пользователь может подписаться на других."""
        count_before = Follow.objects.count()
        response = self.client.get(
            reverse(
                'posts:profile_follow',
                kwargs={'username': self.user2.username}
            )
        )
        count_after = Follow.objects.count()
        self.assertEqual(count_after, count_before + 1)
        self.assertRedirects(
            response,
            reverse('posts:profile', kwargs={'username': self.user2.username})
        )
        self.assertTrue(
            Follow.objects.filter(user=self.user1, author=self.user2).exists()
        )

    def test_unfollow_user(self):
        """Проверка, что пользователь может отписаться от других."""
        Follow.objects.create(user=self.user1, author=self.user2)
        response = self.client.get(
            reverse(
                'posts:profile_unfollow',
                kwargs={'username': self.user2.username}
            )
        )
        self.assertRedirects(
            response,
            reverse('posts:profile', kwargs={'username': self.user2.username})
        )
        self.assertFalse(
            Follow.objects.filter(
                user=self.user1, author=self.user2
            ).exists()
        )
        self.assertEqual(
            Follow.objects.count(),
            0,
            'Количество подписок в базе данных не уменьшилось после отписки.'
        )

    def test_new_post_in_follower_feed(self):
        """Запись пользователя появляется в ленте тех, кто на него подписан."""
        self.client.get(
            reverse(
                'posts:profile_follow',
                kwargs={'username': self.user2.username}
            )
        )
        Post.objects.create(author=self.user2, text='test post')
        response = self.client.get(reverse('posts:follow_index'))
        self.assertContains(response, 'test post')

    def test_new_post_not_in_non_follower_feed(self):
        """Запись пользователя не появляется в ленте тех, кто не подписан."""
        Post.objects.create(author=self.user2, text='test post')
        response = self.client.get(reverse('posts:follow_index'))
        self.assertNotContains(response, 'test post')
