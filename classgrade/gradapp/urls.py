from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^create_assignmentype/$', views.create_assignmentype,
        name='create_assignmentype'),
    url(r'^update_assignmentype/(?P<assignmentype_id>[0-9]+)/$',
        views.create_assignmentype, name='update_assignmentype'),
    url(r'^validate_assignmentype_students/$',
        views.validate_assignmentype_students,
        name='validate_assignmentype_students'),
    url(r'^create_assignmentype_students/$',
        views.create_assignmentype_students,
        name='create_assignmentype_students'),
]
