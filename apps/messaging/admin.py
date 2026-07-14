from django.contrib import admin
from .models import Message


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'engagement', 'sender', 'message_type', 'is_read', 'created_at']
    list_filter = ['message_type', 'is_read']
    search_fields = ['sender__email', 'body']
    raw_id_fields = ['engagement', 'sender']
    readonly_fields = ['created_at']
