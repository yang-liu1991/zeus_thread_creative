# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Remove `managed = False` lines for those models you wish to give write DB access
# Feel free to rename the models, but don't rename db_table values or field names.
#
# Also note: You'll have to insert the output of 'django-admin.py sqlcustom [appname]'
# into your database.
from __future__ import unicode_literals

from django.db import models

class ThAdcreatives(models.Model):
    id = models.IntegerField(primary_key=True)
    account_id = models.CharField(max_length=255)
    ad_id = models.CharField(max_length=255)
    ad_name = models.CharField(max_length=255)
    ad_message = models.TextField()
    creative_id = models.CharField(max_length=255)
    image_url = models.CharField(max_length=1024)
    audit_status = models.IntegerField(default=1)
    audit_message = models.CharField(max_length=45)
    start_time = models.IntegerField()
    promoted_url = models.CharField(max_length=255)
    promoted_status = models.IntegerField(default=0)
    app_details = models.TextField(blank=True)
    created_at = models.CharField(max_length=45)
    updated_at = models.CharField(max_length=45)
    class Meta:
        managed = False
        db_table = 'th_adcreatives' 
