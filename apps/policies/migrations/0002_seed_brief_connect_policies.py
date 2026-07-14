from django.db import migrations

PLACEHOLDER_POLICIES = [
    (
        'posting',
        'Brief Connect — Posting Terms',
        "By posting a brief request you confirm the instructions you provide are accurate and that you "
        "are authorised to engage another lawyer for this matter. Your identity will remain anonymous to "
        "other lawyers until you accept an application. Cynosure is a connection platform only and is not "
        "a party to any arrangement between lawyers. [Placeholder text — replace with reviewed legal copy.]"
    ),
    (
        'applying',
        'Brief Connect — Application Terms',
        "By applying to a brief request you confirm you are able and willing to perform the described task "
        "for the proposed fee. Your identity will remain anonymous to the requester and other applicants "
        "until your application is accepted. [Placeholder text — replace with reviewed legal copy.]"
    ),
    (
        'escrow',
        'Brief Connect — Escrow & Payment Terms',
        "Funds you transfer into escrow are held by Cynosure via its payment processor until the engagement "
        "is confirmed complete. A platform commission is added to your payment on top of the agreed fee. "
        "Refunds and releases are subject to the completion-confirmation and dispute-resolution process. "
        "[Placeholder text — replace with reviewed legal copy.]"
    ),
    (
        'completion',
        'Brief Connect — Completion & Dispute Terms',
        "Confirming completion releases the held funds to the holding lawyer and cannot be reversed. "
        "Rejecting completion opens a dispute that Cynosure will review using submitted evidence from both "
        "parties, and Cynosure's resulting decision on release, refund, or split is final. "
        "[Placeholder text — replace with reviewed legal copy.]"
    ),
]


def seed_policies(apps, schema_editor):
    PolicyDocument = apps.get_model('policies', 'PolicyDocument')
    for checkpoint, title, body in PLACEHOLDER_POLICIES:
        PolicyDocument.objects.get_or_create(
            checkpoint=checkpoint, version=1,
            defaults={'title': title, 'body': body, 'is_active': True},
        )


def unseed_policies(apps, schema_editor):
    PolicyDocument = apps.get_model('policies', 'PolicyDocument')
    checkpoints = [c for c, _, _ in PLACEHOLDER_POLICIES]
    PolicyDocument.objects.filter(checkpoint__in=checkpoints, version=1).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('policies', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed_policies, unseed_policies),
    ]
