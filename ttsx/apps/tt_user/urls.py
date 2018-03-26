from django.conf.urls import url
from . import views
urlpatterns = [
    url(r'^register$',views.RegisterView.as_view()),
    url(r'^login',views.LoginView.as_view()),
    url(r'logout',views.logout_user),
    url('^active/(.+)$',views.active),
    url(r'^exists$',views.exists),
    url(r'info',views.info),
    url(r'order',views.order),
    url(r'site',views.SiteView.as_view()),
    url(r'^area$',views.area)
]