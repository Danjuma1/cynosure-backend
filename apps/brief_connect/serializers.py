"""
Serializers for Brief Connect endpoints.
"""
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Avg
from rest_framework import serializers
from apps.courts.models import Court
from .anonymization import is_connected
from .models import BriefRequest, BriefApplication, BriefEngagement, BriefReview, ProofOfCompletion, FeeOffer


class RequesterIdentityMixin:
    """Shared requester name/bar-number anonymization for BriefRequest serializers."""

    def get_requester_name(self, obj):
        request = self.context.get('request')
        viewer = request.user if request else None
        if is_connected(viewer, obj.requester, obj):
            return obj.requester.full_name
        return f"Lawyer #{obj.anon_code}"

    def get_requester_bar_number(self, obj):
        request = self.context.get('request')
        viewer = request.user if request else None
        if is_connected(viewer, obj.requester, obj):
            return obj.requester.bar_number
        return None


class BriefRequestListSerializer(RequesterIdentityMixin, serializers.ModelSerializer):
    """Compact serializer for feed listings."""
    requester_name = serializers.SerializerMethodField()
    requester_bar_number = serializers.SerializerMethodField()
    requester_year_of_call = serializers.IntegerField(source='requester.year_of_call', read_only=True)
    requester_title = serializers.CharField(source='requester.title', read_only=True)
    court_name = serializers.CharField(source='court.name', read_only=True)
    judge_name = serializers.SerializerMethodField()
    brief_type_display = serializers.CharField(source='get_brief_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    has_applied = serializers.SerializerMethodField()

    class Meta:
        model = BriefRequest
        fields = [
            'id', 'status', 'status_display', 'hearing_date', 'brief_type', 'brief_type_display',
            'case_number', 'parties', 'court', 'court_name', 'judge', 'judge_name',
            'offered_fee', 'fee_negotiable', 'deadline', 'application_count',
            'requester', 'requester_name', 'requester_bar_number',
            'requester_year_of_call', 'requester_title',
            'has_applied', 'created_at',
        ]

    def get_judge_name(self, obj):
        return obj.judge.formal_name if obj.judge else None

    def get_has_applied(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        return obj.applications.filter(applicant=request.user, is_deleted=False).exists()


class BriefApplicationSerializer(serializers.ModelSerializer):
    """Full application detail, shown to the requester."""
    applicant_name = serializers.SerializerMethodField()
    applicant_bar_number = serializers.SerializerMethodField()
    applicant_year_of_call = serializers.IntegerField(source='applicant.year_of_call', read_only=True)
    applicant_title = serializers.CharField(source='applicant.title', read_only=True)
    applicant_specializations = serializers.ListField(source='applicant.specializations', read_only=True)
    applicant_bio = serializers.CharField(source='applicant.bio', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    average_rating = serializers.SerializerMethodField()
    review_count = serializers.SerializerMethodField()

    class Meta:
        model = BriefApplication
        fields = [
            'id', 'brief_request', 'applicant', 'applicant_name', 'applicant_title',
            'applicant_bar_number', 'applicant_year_of_call', 'applicant_specializations',
            'applicant_bio', 'proposed_fee', 'message', 'status', 'status_display',
            'average_rating', 'review_count', 'created_at',
        ]
        read_only_fields = ['id', 'status', 'created_at']

    def get_average_rating(self, obj):
        result = obj.applicant.reviews_received.aggregate(avg=Avg('rating'))
        avg = result['avg']
        return round(avg, 1) if avg is not None else None

    def get_review_count(self, obj):
        return obj.applicant.reviews_received.count()

    def _viewer_connected(self, obj):
        request = self.context.get('request')
        viewer = request.user if request else None
        return is_connected(viewer, obj.applicant, obj.brief_request)

    def get_applicant_name(self, obj):
        if self._viewer_connected(obj):
            return obj.applicant.full_name
        return f"Applicant #{obj.anon_code}"

    def get_applicant_bar_number(self, obj):
        if self._viewer_connected(obj):
            return obj.applicant.bar_number
        return None


class BriefApplicationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = BriefApplication
        fields = ['proposed_fee', 'message']

    def validate(self, attrs):
        request = self.context['request']
        brief_request = self.context['brief_request']

        if brief_request.requester == request.user:
            raise serializers.ValidationError("You cannot apply to your own brief request.")

        if brief_request.status != 'open':
            raise serializers.ValidationError("This brief request is no longer open.")

        if brief_request.applications.filter(applicant=request.user, is_deleted=False).exists():
            raise serializers.ValidationError("You have already applied to this request.")

        return attrs

    def create(self, validated_data):
        return BriefApplication.objects.create(
            brief_request=self.context['brief_request'],
            applicant=self.context['request'].user,
            **validated_data,
        )


class FeeOfferSerializer(serializers.ModelSerializer):
    proposed_by_name = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    is_mine = serializers.SerializerMethodField()

    class Meta:
        model = FeeOffer
        fields = [
            'id', 'application', 'proposed_by', 'proposed_by_name',
            'amount', 'message', 'status', 'status_display', 'is_mine', 'created_at',
        ]
        read_only_fields = ['id', 'application', 'proposed_by', 'status', 'created_at']

    def get_proposed_by_name(self, obj):
        request = self.context.get('request')
        viewer = request.user if request else None
        brief_request = obj.application.brief_request
        if is_connected(viewer, obj.proposed_by, brief_request):
            return obj.proposed_by.full_name
        if obj.proposed_by_id == obj.application.applicant_id:
            return f"Applicant #{obj.application.anon_code}"
        return f"Lawyer #{brief_request.anon_code}"

    def get_is_mine(self, obj):
        request = self.context.get('request')
        return bool(request and request.user == obj.proposed_by)


class BriefRequestSerializer(RequesterIdentityMixin, serializers.ModelSerializer):
    """Full detail serializer — includes applications for the requester."""
    requester_name = serializers.SerializerMethodField()
    requester_bar_number = serializers.SerializerMethodField()
    requester_year_of_call = serializers.IntegerField(source='requester.year_of_call', read_only=True)
    requester_title = serializers.CharField(source='requester.title', read_only=True)
    court_name = serializers.CharField(source='court.name', read_only=True)
    judge_name = serializers.SerializerMethodField()
    brief_type_display = serializers.CharField(source='get_brief_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    applications = serializers.SerializerMethodField()
    my_application = serializers.SerializerMethodField()
    engagement = serializers.SerializerMethodField()

    class Meta:
        model = BriefRequest
        fields = [
            'id', 'status', 'status_display', 'hearing_date', 'brief_type', 'brief_type_display',
            'case_number', 'parties', 'instructions',
            'court', 'court_name', 'judge', 'judge_name',
            'offered_fee', 'fee_negotiable', 'deadline', 'application_count',
            'requester', 'requester_name', 'requester_bar_number',
            'requester_year_of_call', 'requester_title',
            'cause_list_entry', 'case',
            'applications', 'my_application', 'engagement',
            'created_at', 'updated_at',
        ]

    def get_judge_name(self, obj):
        return obj.judge.formal_name if obj.judge else None

    def get_applications(self, obj):
        request = self.context.get('request')
        if not request or request.user != obj.requester:
            return None
        apps = obj.applications.filter(is_deleted=False).select_related('applicant')
        return BriefApplicationSerializer(apps, many=True, context=self.context).data

    def get_my_application(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated or request.user == obj.requester:
            return None
        try:
            app = obj.applications.get(applicant=request.user, is_deleted=False)
            return BriefApplicationSerializer(app, context=self.context).data
        except BriefApplication.DoesNotExist:
            return None

    def get_engagement(self, obj):
        request = self.context.get('request')
        if not request:
            return None
        try:
            eng = obj.engagement
            if request.user in (eng.requester, eng.holding_lawyer):
                return BriefEngagementSerializer(eng, context=self.context).data
        except BriefEngagement.DoesNotExist:
            pass
        return None


class BriefRequestCreateSerializer(serializers.ModelSerializer):
    # court is derived from judge.court automatically; only required when no judge supplied
    court = serializers.PrimaryKeyRelatedField(
        queryset=Court.objects.all(),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = BriefRequest
        fields = [
            'court', 'judge', 'hearing_date',
            'case_number', 'parties', 'brief_type', 'instructions',
            'offered_fee', 'fee_negotiable', 'deadline',
            'cause_list_entry', 'case',
        ]
        extra_kwargs = {
            'judge': {'required': True, 'allow_null': False},
        }

    def validate_hearing_date(self, value):
        from django.utils.timezone import now
        if value < now().date():
            raise serializers.ValidationError("Hearing date cannot be in the past.")
        return value

    def validate(self, attrs):
        judge = attrs.get('judge')
        if judge and not attrs.get('court'):
            attrs['court'] = judge.court
        if not attrs.get('court'):
            raise serializers.ValidationError(
                {"court": "A court must be specified (or will be derived from the selected judge)."}
            )
        return attrs

    def create(self, validated_data):
        return BriefRequest.objects.create(
            requester=self.context['request'].user,
            **validated_data,
        )


class BriefRequestUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = BriefRequest
        fields = [
            'brief_type', 'instructions',
            'offered_fee', 'fee_negotiable', 'deadline',
            'case_number', 'parties',
        ]


class ProofOfCompletionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProofOfCompletion
        fields = ['id', 'engagement', 'notes', 'attachment', 'created_at']
        read_only_fields = ['id', 'engagement', 'created_at']


class BriefEngagementSerializer(serializers.ModelSerializer):
    holding_lawyer_name = serializers.CharField(source='holding_lawyer.full_name', read_only=True)
    holding_lawyer_bar_number = serializers.CharField(source='holding_lawyer.bar_number', read_only=True)
    holding_lawyer_year_of_call = serializers.IntegerField(source='holding_lawyer.year_of_call', read_only=True)
    requester_name = serializers.CharField(source='requester.full_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    has_review = serializers.SerializerMethodField()
    brief_type_display = serializers.CharField(source='brief_request.get_brief_type_display', read_only=True)
    court_name = serializers.CharField(source='brief_request.court.name', read_only=True)
    hearing_date = serializers.DateField(source='brief_request.hearing_date', read_only=True)
    case_number = serializers.CharField(source='brief_request.case_number', read_only=True)
    parties = serializers.CharField(source='brief_request.parties', read_only=True)
    proof_of_completion = serializers.SerializerMethodField()
    dispute = serializers.SerializerMethodField()

    class Meta:
        model = BriefEngagement
        fields = [
            'id', 'brief_request', 'status', 'status_display',
            'holding_lawyer', 'holding_lawyer_name', 'holding_lawyer_bar_number',
            'holding_lawyer_year_of_call',
            'requester', 'requester_name',
            'agreed_fee', 'outcome_notes', 'completed_at',
            'brief_type_display', 'court_name', 'hearing_date', 'case_number', 'parties',
            'has_review', 'proof_of_completion', 'dispute', 'created_at', 'updated_at',
        ]

    def get_has_review(self, obj):
        return hasattr(obj, 'review')

    def get_proof_of_completion(self, obj):
        try:
            return ProofOfCompletionSerializer(obj.proof_of_completion, context=self.context).data
        except ProofOfCompletion.DoesNotExist:
            return None

    def get_dispute(self, obj):
        try:
            dispute = obj.dispute
        except ObjectDoesNotExist:
            return None
        from apps.disputes.serializers import DisputeSerializer
        return DisputeSerializer(dispute, context=self.context).data


class BriefReviewSerializer(serializers.ModelSerializer):
    reviewer_name = serializers.CharField(source='reviewer.full_name', read_only=True)
    reviewee_name = serializers.CharField(source='reviewee.full_name', read_only=True)

    class Meta:
        model = BriefReview
        fields = [
            'id', 'engagement', 'reviewer', 'reviewer_name',
            'reviewee', 'reviewee_name', 'rating', 'comment', 'created_at',
        ]
        read_only_fields = ['id', 'reviewer', 'reviewee', 'created_at']

    def validate(self, attrs):
        request = self.context['request']
        engagement = attrs.get('engagement') or self.instance

        if engagement.requester != request.user:
            raise serializers.ValidationError("Only the requester can submit a review.")

        if engagement.status != 'completed':
            raise serializers.ValidationError("You can only review a completed engagement.")

        if hasattr(engagement, 'review'):
            raise serializers.ValidationError("You have already reviewed this engagement.")

        return attrs

    def create(self, validated_data):
        request = self.context['request']
        engagement = validated_data['engagement']
        return BriefReview.objects.create(
            reviewer=request.user,
            reviewee=engagement.holding_lawyer,
            **validated_data,
        )
