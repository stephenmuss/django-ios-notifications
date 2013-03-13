# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

try:
    from django.contrib.auth import get_user_model
except ImportError:  # django < 1.5
    from django.contrib.auth.models import User
else:
    User = get_user_model()


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'APNService'
        db.create_table('ios_notifications_apnservice', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('hostname', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('certificate', self.gf('django.db.models.fields.TextField')()),
            ('private_key', self.gf('django.db.models.fields.TextField')()),
            ('passphrase', self.gf('django_fields.fields.EncryptedCharField')(max_length=101, null=True, cipher='AES', blank=True)),
        ))
        db.send_create_signal('ios_notifications', ['APNService'])

        # Adding unique constraint on 'APNService', fields ['name', 'hostname']
        db.create_unique('ios_notifications_apnservice', ['name', 'hostname'])

        # Adding model 'Notification'
        db.create_table('ios_notifications_notification', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('service', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['ios_notifications.APNService'])),
            ('message', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('badge', self.gf('django.db.models.fields.PositiveIntegerField')(default=1, null=True)),
            ('sound', self.gf('django.db.models.fields.CharField')(default='default', max_length=30, null=True)),
            ('created_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('last_sent_at', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
        ))
        db.send_create_signal('ios_notifications', ['Notification'])

        # Adding model 'Device'
        db.create_table('ios_notifications_device', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('token', self.gf('django.db.models.fields.CharField')(max_length=64)),
            ('is_active', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('deactivated_at', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('service', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['ios_notifications.APNService'])),
            ('added_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('last_notified_at', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('platform', self.gf('django.db.models.fields.CharField')(max_length=30, null=True, blank=True)),
            ('display', self.gf('django.db.models.fields.CharField')(max_length=30, null=True, blank=True)),
            ('os_version', self.gf('django.db.models.fields.CharField')(max_length=20, null=True, blank=True)),
        ))
        db.send_create_signal('ios_notifications', ['Device'])

        # Adding unique constraint on 'Device', fields ['token', 'service']
        db.create_unique('ios_notifications_device', ['token', 'service_id'])

        # Adding M2M table for field users on 'Device'
        db.create_table('ios_notifications_device_users', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('device', models.ForeignKey(orm['ios_notifications.device'], null=False)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=User)),
        ))
        db.create_unique('ios_notifications_device_users', ['device_id', 'user_id'])

        # Adding model 'FeedbackService'
        db.create_table('ios_notifications_feedbackservice', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('hostname', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('apn_service', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['ios_notifications.APNService'])),
        ))
        db.send_create_signal('ios_notifications', ['FeedbackService'])

        # Adding unique constraint on 'FeedbackService', fields ['name', 'hostname']
        db.create_unique('ios_notifications_feedbackservice', ['name', 'hostname'])


    def backwards(self, orm):
        # Removing unique constraint on 'FeedbackService', fields ['name', 'hostname']
        db.delete_unique('ios_notifications_feedbackservice', ['name', 'hostname'])

        # Removing unique constraint on 'Device', fields ['token', 'service']
        db.delete_unique('ios_notifications_device', ['token', 'service_id'])

        # Removing unique constraint on 'APNService', fields ['name', 'hostname']
        db.delete_unique('ios_notifications_apnservice', ['name', 'hostname'])

        # Deleting model 'APNService'
        db.delete_table('ios_notifications_apnservice')

        # Deleting model 'Notification'
        db.delete_table('ios_notifications_notification')

        # Deleting model 'Device'
        db.delete_table('ios_notifications_device')

        # Removing M2M table for field users on 'Device'
        db.delete_table('ios_notifications_device_users')

        # Deleting model 'FeedbackService'
        db.delete_table('ios_notifications_feedbackservice')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'ios_notifications.apnservice': {
            'Meta': {'unique_together': "(('name', 'hostname'),)", 'object_name': 'APNService'},
            'certificate': ('django.db.models.fields.TextField', [], {}),
            'hostname': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'passphrase': ('django_fields.fields.EncryptedCharField', [], {'max_length': '101', 'null': 'True', 'cipher': "'AES'", 'blank': 'True'}),
            'private_key': ('django.db.models.fields.TextField', [], {})
        },
        'ios_notifications.device': {
            'Meta': {'unique_together': "(('token', 'service'),)", 'object_name': 'Device'},
            'added_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'deactivated_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'display': ('django.db.models.fields.CharField', [], {'max_length': '30', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'last_notified_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'os_version': ('django.db.models.fields.CharField', [], {'max_length': '20', 'null': 'True', 'blank': 'True'}),
            'platform': ('django.db.models.fields.CharField', [], {'max_length': '30', 'null': 'True', 'blank': 'True'}),
            'service': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['ios_notifications.APNService']"}),
            'token': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'users': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'ios_devices'", 'null': 'True', 'symmetrical': 'False', 'to': "orm['auth.User']"})
        },
        'ios_notifications.feedbackservice': {
            'Meta': {'unique_together': "(('name', 'hostname'),)", 'object_name': 'FeedbackService'},
            'apn_service': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['ios_notifications.APNService']"}),
            'hostname': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'ios_notifications.notification': {
            'Meta': {'object_name': 'Notification'},
            'badge': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1', 'null': 'True'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_sent_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'message': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'service': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['ios_notifications.APNService']"}),
            'sound': ('django.db.models.fields.CharField', [], {'default': "'default'", 'max_length': '30', 'null': 'True'})
        }
    }

    complete_apps = ['ios_notifications']
