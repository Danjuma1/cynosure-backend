import django.core.validators
import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('cause_lists', '0002_causelistimage'),
        ('cases', '0002_initial'),
        ('courts', '0001_initial'),
        ('judges', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='BriefRequest',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_deleted', models.BooleanField(db_index=True, default=False)),
                ('deleted_at', models.DateTimeField(blank=True, null=True)),
                ('hearing_date', models.DateField(db_index=True)),
                ('case_number', models.CharField(blank=True, max_length=100)),
                ('parties', models.CharField(blank=True, max_length=500)),
                ('brief_type', models.CharField(choices=[
                    ('mention', 'Mention / Call Over'),
                    ('argue_motion', 'Argue Motion'),
                    ('full_appearance', 'Full Court Appearance'),
                    ('file_process', 'File Court Process'),
                    ('collect_certified_copy', 'Collect Certified Copy'),
                    ('other', 'Other'),
                ], max_length=30)),
                ('instructions', models.TextField()),
                ('offered_fee', models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ('fee_negotiable', models.BooleanField(default=True)),
                ('deadline', models.DateTimeField(blank=True, null=True)),
                ('status', models.CharField(choices=[
                    ('open', 'Open'),
                    ('accepted', 'Accepted'),
                    ('completed', 'Completed'),
                    ('cancelled', 'Cancelled'),
                    ('expired', 'Expired'),
                ], db_index=True, default='open', max_length=20)),
                ('application_count', models.PositiveIntegerField(default=0)),
                ('requester', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='brief_requests_posted',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('cause_list_entry', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='brief_requests',
                    to='cause_lists.causelistentry',
                )),
                ('case', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='brief_requests',
                    to='cases.case',
                )),
                ('court', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='brief_requests',
                    to='courts.court',
                )),
                ('judge', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='brief_requests',
                    to='judges.judge',
                )),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='BriefApplication',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_deleted', models.BooleanField(db_index=True, default=False)),
                ('deleted_at', models.DateTimeField(blank=True, null=True)),
                ('proposed_fee', models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ('message', models.TextField(blank=True)),
                ('status', models.CharField(choices=[
                    ('pending', 'Pending'),
                    ('accepted', 'Accepted'),
                    ('rejected', 'Rejected'),
                    ('withdrawn', 'Withdrawn'),
                ], db_index=True, default='pending', max_length=20)),
                ('brief_request', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='applications',
                    to='brief_connect.briefrequest',
                )),
                ('applicant', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='brief_applications',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='BriefEngagement',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('agreed_fee', models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ('status', models.CharField(choices=[
                    ('confirmed', 'Confirmed'),
                    ('in_progress', 'In Progress'),
                    ('completed', 'Completed'),
                    ('disputed', 'Disputed'),
                    ('cancelled', 'Cancelled'),
                ], db_index=True, default='confirmed', max_length=20)),
                ('outcome_notes', models.TextField(blank=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('brief_request', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='engagement',
                    to='brief_connect.briefrequest',
                )),
                ('holding_lawyer', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='engagements_as_holder',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('requester', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='engagements_as_requester',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='BriefReview',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('rating', models.PositiveSmallIntegerField(validators=[
                    django.core.validators.MinValueValidator(1),
                    django.core.validators.MaxValueValidator(5),
                ])),
                ('comment', models.TextField(blank=True)),
                ('engagement', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='review',
                    to='brief_connect.briefengagement',
                )),
                ('reviewer', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='reviews_given',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('reviewee', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='reviews_received',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='briefrequest',
            index=models.Index(fields=['status', 'hearing_date'], name='brief_req_status_date_idx'),
        ),
        migrations.AddIndex(
            model_name='briefrequest',
            index=models.Index(fields=['court', 'hearing_date'], name='brief_req_court_date_idx'),
        ),
        migrations.AddIndex(
            model_name='briefrequest',
            index=models.Index(fields=['requester', 'status'], name='brief_req_requester_status_idx'),
        ),
        migrations.AddIndex(
            model_name='briefrequest',
            index=models.Index(fields=['hearing_date'], name='brief_req_hearing_date_idx'),
        ),
        migrations.AddIndex(
            model_name='briefapplication',
            index=models.Index(fields=['brief_request', 'status'], name='brief_app_request_status_idx'),
        ),
        migrations.AddIndex(
            model_name='briefapplication',
            index=models.Index(fields=['applicant', 'status'], name='brief_app_applicant_status_idx'),
        ),
        migrations.AlterUniqueTogether(
            name='briefapplication',
            unique_together={('brief_request', 'applicant')},
        ),
        migrations.AddIndex(
            model_name='briefengagement',
            index=models.Index(fields=['holding_lawyer', 'status'], name='brief_eng_holder_status_idx'),
        ),
        migrations.AddIndex(
            model_name='briefengagement',
            index=models.Index(fields=['requester', 'status'], name='brief_eng_requester_status_idx'),
        ),
        migrations.AddIndex(
            model_name='briefreview',
            index=models.Index(fields=['reviewee'], name='brief_rev_reviewee_idx'),
        ),
    ]
