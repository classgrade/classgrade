from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^list_assignmentypes_new/$', views.list_assignmentypes_new,
        name='list_assignmentypes_new'),
    url(r'^list_assignmentypes_past/$', views.list_assignmentypes_past,
        name='list_assignmentypes_past'),
    url(r'^detail_assignmentype/(?P<pk>[0-9]+)/$',
        views.detail_assignmentype, name='detail_assignmentype'),
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
