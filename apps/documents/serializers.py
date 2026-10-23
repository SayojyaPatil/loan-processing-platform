from rest_framework import serializers
from apps.loans.permissions import visible_loans
from .models import LoanDocument

class LoanDocumentSerializer(serializers.ModelSerializer):
    def validate_loan(self, loan):
        if not visible_loans(self.context['request'].user).filter(pk=loan.pk).exists():
            raise serializers.ValidationError('Loan not found or access denied.')
        if loan.status != 'draft':
            raise serializers.ValidationError('Documents can only be added to draft loans.')
        return loan

    def validate(self, attrs):
        content = attrs.get('text_content', '')
        if len(content.encode('utf-8')) > 1024 * 1024:
            raise serializers.ValidationError({'text_content': 'Maximum 1 MiB.'})
        filename = attrs.get('filename', '')
        if filename and not filename.lower().endswith(('.pdf', '.txt', '.jpg', '.jpeg', '.png')):
            raise serializers.ValidationError({'filename': 'Unsupported document extension.'})
        if self.instance and 'loan' in attrs and attrs['loan'].pk != self.instance.loan_id:
            raise serializers.ValidationError({'loan': 'Changing a document loan is not allowed.'})
        return attrs

    class Meta:
        model=LoanDocument
        fields=['id','loan','kind','filename','text_content','extracted_data','processed','created_at','processed_at']
        read_only_fields=['id','extracted_data','processed','created_at','processed_at']
