import os
from django.conf import settings
from rest_framework import serializers
from .models import Message


class MessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source='sender.full_name', read_only=True)

    class Meta:
        model = Message
        fields = [
            'id', 'engagement', 'sender', 'sender_name', 'message_type',
            'body', 'attachment', 'duration_seconds', 'is_read', 'read_at', 'created_at',
        ]
        read_only_fields = ['id', 'engagement', 'sender', 'is_read', 'read_at', 'created_at']

    def validate_attachment(self, value):
        if not value:
            return value
        ext = os.path.splitext(value.name)[1].lower()
        allowed = settings.CYNOSURE_SETTINGS['ALLOWED_UPLOAD_EXTENSIONS']
        if ext not in allowed:
            raise serializers.ValidationError(f"Unsupported file type: {ext}")
        max_size = settings.CYNOSURE_SETTINGS['CHAT_ATTACHMENT_MAX_SIZE']
        if value.size > max_size:
            raise serializers.ValidationError(f"File too large. Max size is {max_size // (1024 * 1024)}MB.")
        return value

    def validate(self, attrs):
        message_type = attrs.get('message_type', 'text')
        if message_type == 'text' and not attrs.get('body', '').strip():
            raise serializers.ValidationError('Text messages require a body.')
        if message_type != 'text' and not attrs.get('attachment'):
            raise serializers.ValidationError('An attachment is required for this message type.')
        return attrs
