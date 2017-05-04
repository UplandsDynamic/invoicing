from django.conf.urls import url, include
from invoicing import views
from django.conf.urls.static import static
from django.conf import settings

urlpatterns = [
    url(r'^$', views.Invoicing.as_view(), name='invoicing'),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
