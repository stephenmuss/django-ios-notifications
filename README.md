django-ios-notifications
=================

Django iOS Notifications makes it easy to send push notifications to iOS devices.


Installation
-----------------

You can install with pip: `pip install django-ios-notifications`.

You then need to add `ios_notifications` to `INSTALLED_APPS` in your settings file.

The minimum Python version supported is Python 2.6 while the minimum Django version required is 1.3.
There are also two other hard dependencies:

* `pyOpenSSL >= 0.10`
* `django-fields >= 0.1.2`


After installation, you then need to add `ios_notifications` to `INSTALLED_APPS` in your settings file.

If you want to use the API for registering devices you will also need to make the appropriate changes to your urls file:

```python
urlpatterns = patterns('',
    ...
    url(r'^ios-notifications/', include('ios_notifications.urls')),
    ...
)
```

After that you will need to run `./manage.py syncdb` to create the database tables required for django-ios-notifications.


Setting up the APN Services
-----------------

Before you can add some devices and push notifications you'll need to set up an APN Service.
An example of how to do this in a development environment follows.

Start up your development server: `./manage.py runserver` and open up the following url in a web browser:

http://127.0.0.1:8000/admin/ios_notifications/apnservice/add/.
You'll see a form to be able to create a new APN Service.

I am making the assumption that you have already created a private key and certificate.
If not I suggest you follow one of the online guides to complete this step.
One such example can be found [here](http://www.raywenderlich.com/3443/apple-push-notification-services-tutorial-part-12).

The name of the service can be any arbitrary string.

The hostname will need to be a valid hostname for one of the Apple APN Service hosts.
Currently this is `gateway.sandbox.push.apple.com` for sandbox testing and `gateway.push.apple.com` for production use.

For the certificate and private key fields paste in your certificate and key including the lines with:

```
----BEGIN CERTIFICATE-----
-----END CERTIFICATE-----
-----BEGIN RSA PRIVATE KEY-----
-----END RSA PRIVATE KEY-----
```

If your private key requires a passphrase be sure to enter it in to the `passphrase` field.
Otherwise this field can be left blank.

After this you are ready to save the APN Service.


Registering devices
-----------------

There are a few different ways you can register a device. You can either create the device in the admin interface at
http://127.0.0.1:8000/admin/ios_notifications/device/add/ or use the API provided by django-ios-notifications to do so.

If you want to add the device through the admin interface you will need to know the device's token represented by 64
hexadecimal characters (be sure to exclude any `<`, `>` and whitespace characters).

Otherwise the django-ios-notifications API provides a REST interface for you to be able to add the device;
this would normally be done by sending a request from you iOS app.

To register your device you will need to make a POST request from your device and pass the appropriate POST parameters in the request body.

To create a new device you will need to call the API at http://127.0.0.1:8000/ios-notifications/device/

There are two required POST parameters required to complete this operation:
* `token`: the device's 64 character hexadecimal token.
* `service`: The id in integer format of the APNService instance to be used for this device.

If the device already exists, the device's `is_active` attribute will be updated to `True`. Otherwise the device
will be created.

If successful the API will return the device in serialized JSON format with a status code of 201 if the device was created. If
the device already existed the response code will be 200.


Getting device details
-----------------

To fetch the details of an existing device using the REST API you should call the following URL in an HTTP GET request:

`http://127.0.0.1:8000/ios-notifications/device/<device_token>/<device_service>/` where:
* `device_token` in the device's 64 character hexadecimal token.
* `device_service` is the id in integer format of the device's related APNService model.

For example: `http://127.0.0.1:8000/ios-notifications/device/0fd12510cfe6b0a4a89dc7369d96df956f991e66131dab63398734e8000d0029/1/`.

This will return an HTTP response with the device in JSON format in the response body.


Updating devices
-----------------

The Django iOS Notifications REST interface also provides the means for you to be able to update
a device via the API.

To update a device you should call the same URL as you would above in *Getting device details*. The HTTP request method
should be PUT. You can provide any of the following PUT parameters to update the device:

* `users`: A list of user (django.contrib.auth.models.User) ids in integer formate associated with the device.
* `platform`: A string describing the device's platform. Allowed options are 'iPhone', 'iPad' and 'iPod'.
* `display`: A string describing the device's display (max 30 characters). e.g. '480x320'.

Although technically permitted, updating any of the device's other attributes through the API is not recommended.

This will return an HTTP response with the device with its updated attributes in JSON format in the response body.


Creating and sending notifications
-----------------

As with devices, there are a few different ways you can create notifications.

You can create a notification in the admin interface by going to http://127.0.0.1:8000/admin/ios_notifications/notification/add/

If you create a notification and save it by hitting `Save and continue editing` you will notice that you
are now able to push this notification by clicking the `Push now` button which has appeared.
Clicking this button will send the notification to all active devices registered with the appropriate APN Server,
so make sure that you are really ready to send it before clicking the button.

Another options is to use the built in management command provided by django-ios-notifications.
You can do this by calling `./manage.py push_ios_notification` from the command line.
You will need to provide some arguments to the command in order to create and send a notification.

There are two required options and two optional ones.

The required arguments are:

* `--message` is a string containing the main message of your notification. e.g. `--message='This is a push notification from Django iOS Notifications!'`
* `--service` is the id of the APN Service you wish to use. e.g. `--service=123`.

The optional arguments you may pass are:

* `--badge` is an integer value to represent the badge value that will appear over your app's springboard icon after receiving the notification. e.g. `--badge=2`.
* `--sound` is the sound to be played when the device receives your application. This can either be one of the built in sounds or one that you have included in your app. e.g. `--sound=default`.

Note that if you do not provide the optional arguments the default values for both are `None`. This means the device will
neither play a sound or update the badge of your app's icon when receiving the notification.

A full example: `./manage.py push_ios_notification --message='This is a push notification from Django iOS Notifications!' --service=123 --badge=1 --sound=default`.


API Authentication
-----------------

At present the REST API supports a few different modes of authentication.

If you plan to use the API then you need to specify `IOS_NOTIFICATIONS_AUTHENTICATION` in your settings.py file.

The value of `IOS_NOTIFICATIONS_AUTHENTICATION` must be one of the following strings `AuthBasic`, `AuthBasicIsStaff` or `AuthNone`.

### `AuthNone`

This is the setting to use if you don't care about protecting the API. Any request will be allowed to be processed by the API.
This is the easiest to get started with but not really recommended.


### `AuthBasic`

This will secure your API with basic access authentication. This means any request to the API will need to include an `Authorization` header.
This will do a check to see whether a user exists in your database with the supplied credentials. The user should be an instance of `django.contrib.auth.models.User`.
The value of the header will be the word `Basic` followed by a base64 encoded string of the user's username and password joined by a colon `:`.
For example, if you have a user with the username `Aladdin` and password `open sesame` you would need to base64 encode the string `Aladdin:open sesame`.
The resulting header should looks as follows `Authorization: Basic QWxhZGRpbjpvcGVuIHNlc2FtZQ==`. It is highly recommended that you only send requests
over SSL. Otherwise the user credentials will be sent unencrypted in plain text.

See [Basic access authentication](http://en.wikipedia.org/wiki/Basic_access_authentication) for more details


### `AuthBasicIsStaff`

This is the same as `AuthBasic` except that the request will only be allowed if the user is a staff user.


### `AuthOAuth`

OAuth authentication will be supported in future versions.


The Feedback Service and deactivating devices
-----------------

The Feedback Service is used to determine to which devices you should no longer push notifications.
This is normally the case once a user has uninstalled your app from his or her device.

[According to Apple](https://developer.apple.com/library/ios/#documentation/NetworkingInternet/Conceptual/RemoteNotificationsPG/CommunicatingWIthAPS/CommunicatingWIthAPS.html#//apple_ref/doc/uid/TP40008194-CH101-SW3):

> APNs monitors providers for their diligence in checking the feedback service and refraining from sending push notifications to nonexistent applications on devices.


So it is good practice to ensure that you don't push notifications to devices which no longer have your app installed.

Django iOS Notifications provides a `FeedbackService` class for you to discover to which devices you should no longer
send notifications.

You can add a FeedbackService in the admin via http://127.0.0.1:8000/admin/ios_notifications/feedbackservice/add/.
Hopefully by now it should be self-explanatory what the fields are for this class.

As with the `APNService` you will need to provide a hostname for any instances of `FeedbackService`.
For sandbox environments you can currently use `feedback.sandbox.push.apple.com` and in production you should use `feedback.push.apple.com`.

You should set the APNService relationship for FeedbackService according to your environment.

Once you have created your FeedbackService instance you can call it to deactivate any devices it informs you of.

To do this you can run the `call_feedback_service` management command. This will call the feedback service and deactivating any devices
it is informed of by the service (by setting `is_active` to `False`).

The `call_feedback_service` command takes one required argument:

* --feedback-service: The id of the FeedbackService to call. e.g. `--feedback-service=123`.

A full example: `./manage.py call_feedback_service --feedback-service=123`

__NOTE:__ You may experience some issues testing the feedback service in a sandbox enviroment.
This occurs when an app was the last push enabled app for that particular APN Service on the device 
Once the app is removed it tears down the persistent connection to the APN service. If you want to
test a feedback service, ensure that you have at least one other app on the device installed which
receives notifications from the same APN service.

In the case that you want to test an app using the sandbox APN service, I suggest you create another
dummy app in XCode and in the iOS provisioning portal with push notifications enabled. Install this app
on any devices you are testing as well as the current app. Now you should be able to uninstall your app
from the device and try pushing a notification. So long as the dummy app is still installed on your device
the next time you attempt to call the feedback service all should go according to plan and you will notice
the device in question has now been deactivated when you view it in the admin interface at
http://127.0.0.1:8000/admin/ios_notifications/device/

See [Issues with Using the Feedback Service](http://developer.apple.com/library/ios/#technotes/tn2265/_index.html
for more details)

***

This source code is released under a New BSD License. See the LICENSE file for full details.
