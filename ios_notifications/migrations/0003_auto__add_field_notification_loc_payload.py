# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

try:
    from django.contrib.auth import get_user_model
except ImportError:  # django < 1.5
    from django.contrib.auth.models import User
else:
    User = get_user_model()

# With the default User model these will be 'auth.User' and 'auth.user'
# but for having a custom User model and instead of using orm['auth.User']
# we can use orm[user_orm_label]
user_orm_label = '%s.%s' % (User._meta.app_label, User._meta.object_name)
user_model_label = '%s.%s' % (User._meta.app_label, User._meta.module_name)

class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Notification.loc_payload'
        db.add_column(u'ios_notifications_notification', 'loc_payload',
                      self.gf('django.db.models.fields.CharField')(default='', max_length=240, blank=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Notification.loc_payload'
        db.delete_column(u'ios_notifications_notification', 'loc_payload')


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
		# Instead of 'auth.user', to support custom user models
        user_model_label: {
            'Meta': {
                'object_name': User.__name__,
                'db_table': "'%s'" % User._meta.db_table
            },
            User._meta.pk.attname: (
                'django.db.models.fields.AutoField', [],
                {'primary_key': 'True',
                'db_column': "'%s'" % User._meta.pk.column}
            ),
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
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'passphrase': ('django_fields.fields.EncryptedCharField', [], {'max_length': '110', 'null': 'True', 'block_type': "'MODE_CBC'", 'cipher': "'AES'", 'blank': 'True'}),
            'private_key': ('django.db.models.fields.TextField', [], {})
        },
        'ios_notifications.device': {
            'Meta': {'unique_together': "(('token', 'service'),)", 'object_name': 'Device'},
            'added_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'deactivated_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'display': ('django.db.models.fields.CharField', [], {'max_length': '30', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'last_notified_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'os_version': ('django.db.models.fields.CharField', [], {'max_length': '20', 'null': 'True', 'blank': 'True'}),
            'platform': ('django.db.models.fields.CharField', [], {'max_length': '30', 'null': 'True', 'blank': 'True'}),
            'service': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['ios_notifications.APNService']"}),
            'token': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'users': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'ios_devices'", 'null': 'True', 'symmetrical': 'False', 'to': "orm['%s']" % user_orm_label})
        },
        'ios_notifications.feedbackservice': {
            'Meta': {'unique_together': "(('name', 'hostname'),)", 'object_name': 'FeedbackService'},
            'apn_service': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['ios_notifications.APNService']"}),
            'hostname': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'ios_notifications.notification': {
            'Meta': {'object_name': 'Notification'},
            'badge': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'custom_payload': ('django.db.models.fields.CharField', [], {'max_length': '240', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_sent_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'loc_payload': ('django.db.models.fields.CharField', [], {'max_length': '240', 'blank': 'True'}),
            'message': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'service': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['ios_notifications.APNService']"}),
            'sound': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'})
        }
    }

    complete_apps = ['ios_notifications']
