from rest_framework import serializers
from .models import PolicyDocument


class PolicyDocumentSerializer(serializers.ModelSerializer):
    checkpoint_display = serializers.CharField(source='get_checkpoint_display', read_only=True)

    class Meta:
        model = PolicyDocument
        fields = ['id', 'checkpoint', 'checkpoint_display', 'version', 'title', 'body', 'created_at']
