from django.conf.urls import url, include
from django.conf.urls.static import static
from django.conf import settings
from django.contrib import admin
from django.contrib.auth import views as auth_views
from aninstance_framework import search, tz
from django.views.generic.base import RedirectView
from rest_framework import routers
from rest_framework.authtoken import views as rest_auth_views
from invoicing.api import ClientViewSet  # API

# REST API framework
router = routers.DefaultRouter()
router.register(r'invoicing/client', ClientViewSet)
# URL patterns
urlpatterns = [
    ### INCLUDES
    # Invoicing app
    url(r'^invoicing/', include('invoicing.urls')),
    # Admin section
    url(r'^adminardo/', admin.site.urls),
    # Search
    url(r'^search/?$', search.AninstanceSearchView.as_view(), name='search_view'),
    ### ROUTING
    # Set timezone
    url(r'^set_timezone/$', tz.SetTimeZone.as_view(), name='set_timezone'),
    # Authorization
    url(r'^accounts/password_change/$', auth_views.password_change,
        {'template_name': 'registration/password_change_form.html'}, name='password_change'),
    url(r'^accounts/password_change/done/$', auth_views.password_change_done,
        {'template_name': 'registration/password_change_done.html'}, name='password_change_done'),
    url(r'^accounts/password_reset/$', auth_views.password_reset,
        {'template_name': 'registration/password_reset_form.html'}, name='password_reset'),
    url(r'^accounts/password_reset/done$', auth_views.password_reset_done,
        {'template_name': 'registration/password_reset_done.html'}, name='password_reset_done'),
    url(r'^accounts/reset/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$',
        auth_views.password_reset_confirm,
        {'template_name': 'registration/password_reset_confirm.html'}, name='password_reset_confirm'),
    url(r'^accounts/reset/done$', auth_views.password_reset_complete,
        {'template_name': 'registration/password_reset_complete.html'}, name='password_reset_complete'),
    url(r'^accounts/login/$', auth_views.login,
        {'template_name': 'registration/login.html'}, name='login'),
    url(r'^accounts/logout/$', auth_views.logout,
        {'template_name': 'registration/logged_out.html'}, name='logout'),
    ### DEFAULT: Pages app urls.py serves everything not listed above - HAS TO COME LAST IN LIST!)
    #url(r'^', include('pages.urls')),
    ### PROTECT MEDIA PROTECTED DIR
    url(r'^media/protected/', RedirectView.as_view(url='/')),
    url(r'^/?$', include('invoicing.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
