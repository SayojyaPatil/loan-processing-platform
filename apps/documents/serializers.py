from rest_framework import serializers
from .models import LoanDocument

class LoanDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model=LoanDocument
        fields=['id','loan','kind','filename','text_content','extracted_data','processed','created_at','processed_at']
        read_only_fields=['id','extracted_data','processed','created_at','processed_at']
