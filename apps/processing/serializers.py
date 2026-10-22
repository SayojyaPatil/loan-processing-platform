from rest_framework import serializers
from .models import ProcessingJob
class ProcessingJobSerializer(serializers.ModelSerializer):
    class Meta:
        model=ProcessingJob
        fields='__all__'
        read_only_fields=['id','status','celery_task_id','attempts','error','started_at','completed_at','created_at']
