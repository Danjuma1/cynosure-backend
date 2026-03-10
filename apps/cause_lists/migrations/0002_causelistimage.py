"""
Migration: add CauseListImage model.
"""
from django.conf import settings
import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cause_lists', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='CauseListImage',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_deleted', models.BooleanField(default=False)),
                ('deleted_at', models.DateTimeField(blank=True, null=True)),
                ('image', models.ImageField(upload_to='cause_lists/images/')),
                ('thumbnail', models.ImageField(blank=True, upload_to='cause_lists/thumbnails/')),
                ('page_number', models.PositiveSmallIntegerField(default=1, help_text='Page order (1-based)')),
                ('caption', models.CharField(blank=True, max_length=255)),
                ('file_size', models.PositiveIntegerField(default=0, help_text='Compressed size in bytes')),
                ('width', models.PositiveSmallIntegerField(default=0)),
                ('height', models.PositiveSmallIntegerField(default=0)),
                ('cause_list', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='images',
                    to='cause_lists.causelist',
                )),
                ('uploaded_by', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='uploaded_cause_list_images',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'ordering': ['cause_list', 'page_number'],
            },
        ),
        migrations.AddIndex(
            model_name='causelistimage',
            index=models.Index(fields=['cause_list', 'page_number'], name='cause_lists_cl_img_cl_page_idx'),
        ),
    ]
