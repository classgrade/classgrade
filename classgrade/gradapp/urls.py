from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.index, name='index'),
    # For Prof
    url(r'^list_assignmentypes_running/$', views.list_assignmentypes_running,
        name='list_assignmentypes_running'),
    url(r'^list_assignmentypes_archived/$', views.list_assignmentypes_archived,
        name='list_assignmentypes_archived'),
    url(r'^detail_assignmentype/(?P<pk>[0-9]+)/$',
        views.detail_assignmentype, name='detail_assignmentype'),
    url(r'^show_eval_distrib/(?P<pk>[0-9]+)/$',
        views.show_eval_distrib, name='show_eval_distrib'),
    url(r'^csv_grades/(?P<pk>[0-9]+)/$', views.generate_csv_grades,
        name='generate_csv_grades'),
    url(r'^zip_assignments/(?P<pk>[0-9]+)/$', views.generate_zip_assignments,
        name='generate_zip_assignments'),
    url(r'^txt_comments/(?P<pk>[0-9]+)/$', views.generate_txt_comments,
        name='generate_txt_comments'),
    url(r'^create_assignmentype/$', views.create_assignmentype,
        name='create_assignmentype'),
    url(r'^archive_assignmentype/(?P<pk>[0-9]+)/$',
        views.archive_assignmentype, name='archive_assignmentype'),
    url(r'^delete_assignmentype/(?P<pk>[0-9]+)/(?P<type_list>[0-1]+)/$',
        views.delete_assignmentype, name='delete_assignmentype'),
    url(r'^reset_assignmentype/(?P<assignmentype_id>[0-9]+)/$',
        views.create_assignmentype, name='reset_assignmentype'),
    url(r'^modify_assignmentype/(?P<pk>[0-9]+)/$',
        views.modify_assignmentype, name='modify_assignmentype'),
    url(r'^coeff_assignmentype/(?P<pk>[0-9]+)/$',
        views.coeff_assignmentype, name='coeff_assignmentype'),
    url(r'^statement_assignmentype/(?P<pk>[0-9]+)/$',
        views.statement_assignmentype, name='statement_assignmentype'),
    url(r'^insert_question_assignmentype/(?P<pk>[0-9]+)/(?P<cd>-?\d+)/$',
        views.insert_question_assignmentype, name='insert_question'),
    url(r'^validate_assignmentype_students/$',
        views.validate_assignmentype_students,
        name='validate_assignmentype_students'),
    url(r'^create_assignmentype_students/$',
        views.create_assignmentype_students,
        name='create_assignmentype_students'),
    url(r'^supereval_assignment/(?P<assignment_pk>[0-9]+)/(?P<i>[0-9]+)/$',
        views.supereval_assignment, name='supereval_assignment'),
    url(r'^download_assignment_prof/(?P<pk>[0-9]+)/$',
        views.download_assignment_prof, name='download_assignment_prof'),
    # For students
    url(r'^dashboard_student/$', views.dashboard_student,
        name='dashboard_student'),
    url(r'^upload_assignment/(?P<pk>[0-9]+)/$', views.upload_assignment,
        name='upload_assignment'),
    url(r'^get_assignment/(?P<pk>[0-9]+)/$', views.get_assignment,
        name='get_assignment'),
    url(r'^eval_assignment/(?P<pk>[0-9]+)/(?P<i>[0-9]+)/$',
        views.eval_assignment, name='eval_assignment'),
    url(r'^download_assignment_student/(?P<pk>[0-9]+)/(?P<i>[0-9]+)/$',
        views.download_assignment_student, name='download_assignment_student'),
    url(r'^eval_evalassignment/(?P<pk>[0-9]+)/(?P<pts>-?[0-1]+)/$',
        views.eval_evalassignment, name='eval_evalassignment'),
]
