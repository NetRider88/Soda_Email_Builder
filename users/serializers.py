from rest_framework import serializers
from .models import EmailTemplate, Category

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'color', 'created_at', 'updated_at']

class EmailTemplateSerializer(serializers.ModelSerializer):
    category_details = CategorySerializer(source='category', read_only=True)
    
    class Meta:
        model = EmailTemplate
        fields = ['id', 'name', 'design', 'html', 'category', 'category_details', 'created_at', 'updated_at']

    def validate(self, data):
        # Print the incoming data for debugging
        print("Validating data:", data)
        return data

    def create(self, validated_data):
        # Ensure required fields are present
        if 'name' not in validated_data:
            validated_data['name'] = 'Untitled Template'
        return super().create(validated_data)
