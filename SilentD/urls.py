from django.conf.urls import patterns, url
from SilentD import views
from django.views.generic import TemplateView

urlpatterns = patterns(
    '',
    url(r'^register/$', views.register, name='register'),
    url(r'^logout/$', views.user_logout, name='logout'),
    url(r'^file_upload/$', views.file_upload, name='file_upload'),
    url(r'^data/$', views.data, name='data'),
    url(r'^create/$', views.create_project, name='create_project'),
    url(r'^primer_validator/$', views.primer_validator, name='primer_validator'),
    url(r'^gene_seeker/$', views.gene_seeker, name='gene_seeker'),
    url(r'^snp/$', views.snp, name='snp'),
    url(r'^miseq/$', views.miseq, name='miseq'),
    url(r'^database/$', views.database, name='database'),
    url(r'^index',  TemplateView.as_view(template_name='SilentD/index.html'), name='index'),
    url(r'^links/', TemplateView.as_view(template_name='SilentD/links.html'), name='links'),
    url(r'^contact/', TemplateView.as_view(template_name='SilentD/info.html'), name='contact'),
    url(r'^documentation/', TemplateView.as_view(template_name='SilentD/documentation.html'), name='documentation'),
    url(r'^mlst/$', views.mlst, name='mlst'),
    url(r'^amr/$', views.amr, name='amr')
)
