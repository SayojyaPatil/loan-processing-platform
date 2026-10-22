from rest_framework import serializers
from .models import LoanApplication

class LoanApplicationSerializer(serializers.ModelSerializer):
    document_count=serializers.IntegerField(read_only=True)
    class Meta:
        model=LoanApplication
        fields=['id','applicant_name','applicant_email','requested_amount','purpose','status','document_count','created_at','updated_at']
        read_only_fields=['id','status','created_at','updated_at','document_count']
