from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^create_assignmentype/$', views.create_assignmentype,
        name='create_assignmentype'),
]
