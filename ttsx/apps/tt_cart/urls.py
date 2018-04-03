from django.conf.urls import url
from . import views
urlpatterns = [
    url(r'^add',views.add),
    url(r'^$',views.index),
    url('^edit$',views.edit),
    url('^delete$',views.delete),
]