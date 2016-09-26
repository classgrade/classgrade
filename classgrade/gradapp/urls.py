from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^list_assignmentypes_running/$', views.list_assignmentypes_running,
        name='list_assignmentypes_running'),
    url(r'^list_assignmentypes_archived/$', views.list_assignmentypes_archived,
        name='list_assignmentypes_archived'),
    url(r'^detail_assignmentype/(?P<pk>[0-9]+)/$',
        views.detail_assignmentype, name='detail_assignmentype'),
    url(r'^create_assignmentype/$', views.create_assignmentype,
        name='create_assignmentype'),
    url(r'^archive_assignmentype/(?P<pk>[0-9]+)/$',
        views.archive_assignmentype, name='archive_assignmentype'),
    url(r'^delete_assignmentype/(?P<pk>[0-9]+)/(?P<type_list>[0-1]+)$',
        views.delete_assignmentype, name='delete_assignmentype'),
    url(r'^update_assignmentype/(?P<assignmentype_id>[0-9]+)/$',
        views.create_assignmentype, name='update_assignmentype'),
    url(r'^validate_assignmentype_students/$',
        views.validate_assignmentype_students,
        name='validate_assignmentype_students'),
    url(r'^create_assignmentype_students/$',
        views.create_assignmentype_students,
        name='create_assignmentype_students'),
    url(r'^dashboard_student/$', views.dashboard_student,
        name='dashboard_student'),
    url(r'^upload_assignment/(?P<pk>[0-9]+)/$', views.upload_assignment,
        name='upload_assignment'),
    url(r'^eval_assignment/(?P<pk>[0-9]+)/$', views.eval_assignment,
        name='eval_assignment'),
]
