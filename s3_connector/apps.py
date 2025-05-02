"""
Django app configuration for s3_connector
"""
from django.apps import AppConfig


class S3ConnectorConfig(AppConfig):
    """S3Connector app configuration"""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 's3_connector'
    verbose_name = 'S3 Connector for ActivaGroup'