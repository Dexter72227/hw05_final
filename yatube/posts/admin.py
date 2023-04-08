from django.contrib import admin

from .models import Group, Post, Comment, Follow


class PostAdmin(admin.ModelAdmin):
    list_display = ('pk', 'text', 'pub_date', 'author', 'group')
    search_fields = ('text',)
    list_filter = ('pub_date',)
    list_editable = ('group',)
    empty_value_display = '-пусто-'


class Groupadmin(admin.ModelAdmin):
    list_display = ('pk', 'title', 'slug', 'description')
    list_editable = ('slug',)
    empty_value_display = '-пусто-'


class CommentAdmin(admin.ModelAdmin):
    list_display = ('pk', 'post', 'author', 'text', 'created')
    search_fields = ('text',)
    list_filter = ('created',)
    empty_value_display = '-пусто-'


class FollowAdmin(admin.ModelAdmin):
    list_display = ('user', 'author')
    empty_value_display = '-пусто-'


admin.site.register(Post, PostAdmin)
admin.site.register(Group, Groupadmin)
admin.site.register(Comment, CommentAdmin)
admin.site.register(Follow, FollowAdmin)
