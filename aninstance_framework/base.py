from django.views import generic
from django.shortcuts import render
from django.core.cache import caches
from django.core.cache.utils import make_template_fragment_key
from django.conf import settings
from aninstance_framework.search_forms import RightSidebarSearchForm
from django.contrib.auth.mixins import AccessMixin
from aninstance_framework import helpers, auth
from django.utils.translation import ugettext_lazy as _

''' NOTES

AUTH:
Pass LoginRequiredMixin to CLASS VIEWS that require authorization.
Pass UserPassesTestMixin to CLASS VIEWS that require user to be of a certain level, etc.
Decorate with @login_required decorator NON-CLASS-VIEWS that require authorizaton.

GENERAL:

    BELOW IS THE DEFAULT CONTEXT FOR BASE. DEFAULTS ARE DEFINED IN custom_context_processors.py (&
    therefore auto added to all contexts) unless otherwise stated.

    THE DEFAULT VALUES CAN BE OVERRIDDEN IN CHILD VIEWS AS NECESSARY


    context = { 'site_logo': None,
                'site_logo_desc': None,
                'site_logo_url': None,
                'panel_heading': None,
                'panel_footer': None,  # panel footer
                'status_message': None,
                'error_message': None,
                'footer_text': None,  # out of panel footer
                'right_sidebar_blurb': None,
                'right_sidebar_links': [
                    {'url': '', 'link_text': '', 'target': ''},
                    ]
                'right_sidebar_image': None,
                'right_sidebar_image_desc': None,
                'right_sidebar_image_url': None,
                'right_sidebar_search': False,
                'right_sidebar_search_button_text': 'Search!'
                'right_sidebar_search_placeholder_text': 'Search for',
                'left_sidebar_image': None,
                'left_sidebar_image_desc': None,
                'left_sidebar_image_url': None,
                'head_title': None,
                'tag_line': None,
                'client_timezone': None,
                'total_pages': None,
                'pagination': False,
                'param_str': None,
                'param_value': None,
                'cache_ttl': None,
                'param_str': '', # param, set up ready for use in template, e.g. href="{{ param_str}}my_value"
                                 # will append this in url if param_str = 'test': href=".../(?or&)test=my_value"
                                 # Note: NO NOT ADD to CONTEXT in each view, as it requires formatting to ensure
                                 # rest of URL is maintained intact and whether to use ? or &. Therefore, formatted
                                 # function is already added in AninstanceGenericView self.context (rather
                                 # that in context_processors.py), so in child views simply override
                                 # self.param_str and assign a new param name as needed (e.g. self.param_str = 'test'
                },
                'requested_page': None,

    '''


class AninstanceGenericView(AccessMixin, generic.View):
    """ NOTES
    Authentication & authorization:
        - Authentication for child CBVs handled by access mixin, Authenticate class and the dispatch method.
          The overriding of the dispatch method handles calling of auth class & redirect to login if not auth'd.
          To set a CBV to require auth and/or user level, simply
          add:
            self.authentication_required = True
            self.auth_level = settings.USER_LEVEL.get('<the user level>')
        to the CBV's init.
        - Defaults to NO authentication required, and user level of a basic user.
    """
    NEVER_CACHE_TTL = 0  # set to 0 to prevent caching when this TTL is selected
    CACHE_TTL = settings.DEFAULT_CACHES_TTL
    TEMPLATE_NAME = None
    FOOTER_TEXT = None  # None value means default is used, as defined in custom_context_processors.py
    PANEL_HEADING = None  # None value means default is used, as defined in custom_context_processors.py
    PANEL_FOOTER = None  # None value means default is used, as defined in custom_context_processors.py
    FRAGMENT_KEY = ''
    USE_CACHE = settings.DEFAULT_USE_TEMPLATE_FRAGMENT_CACHING  # overridden in child views!
    PAGINATION = False
    PAGINATION_ITEMS_PER_PAGE = 5
    PARAM_STR = 'default_param'
    PAGE_STR = 'p'
    STATUS_MESSAGE = None
    AUTHENTICATION_REQUIRED = False  # authorization not required for views by default. Overwrite in CVBs for auth.
    RIGHT_SIDEBAR_SEARCH_PLACEHOLDER_TEXT = _('Search for')
    RIGHT_SIDEBAR_SEARCH_BUTTON_TEXT = _('Search')
    """Define models to search
    Overwrite accordingly in child CBV (otherwise authentication error thrown).
    Indexes for models set in templates/search/indexes."""
    MODELS_TO_SEARCH = {
        '': [],  # e.g. '<url_action_param'>: ['<app.model>', '<app.another_model>']
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.fragment_key = None  # overridden with value in child view class
        if not self.USE_CACHE:
            self.CACHE_TTL = self.NEVER_CACHE_TTL
        self.requested_page = 1
        self.search_url = None
        self.authentication_required = self.AUTHENTICATION_REQUIRED  # change in child views to activate auth
        self.auth_level = auth.USER_LEVEL.get('user')  # default to required level being a basic user
        self.context = {
            'panel_heading': self.PANEL_HEADING,
            'panel_footer': self.PANEL_FOOTER,
            'cache_ttl': self.CACHE_TTL,
            'pagination': self.PAGINATION,
            'footer_text': self.FOOTER_TEXT,
            'status_message': self.STATUS_MESSAGE,
            'right_sidebar_search': False,  # false by default
            'form_right_search': RightSidebarSearchForm(  # overwrite in child view to change placeholder text
                placeholder=self.RIGHT_SIDEBAR_SEARCH_PLACEHOLDER_TEXT),
            'right_sidebar_search_button_text': self.RIGHT_SIDEBAR_SEARCH_BUTTON_TEXT,
        }

    def __str__(self):
        return 'Default view for Aninstance project.'

    def view_cacher(self, request):
        if self.USE_CACHE:
            # return cached version if cached variable set
            cached_template_fragments = caches['template_fragments']
            # child view overrides self.fragment_key
            key = make_template_fragment_key(self.FRAGMENT_KEY, [request.get_full_path()])
            if cached_template_fragments.get(key):
                print('Returning cached response ...')
                return render(request, self.TEMPLATE_NAME, self.context)  # returned to view if cached response
            else:
                # carry on with the processing. Output will be cached for subsequent requests.
                print('CACHING THE RESPONSE FOR FUTURE USE ...')
                return None  # returned to view if no cached response
        print('Not using cache for this view ...')
        return None  # returned if cache not being used (self.USE_CACHE = None )

    def dispatch(self, request, *args, **kwargs):
        # checks auth status and redirects to login if not auth'd
        if self.authentication_required and not auth.Authenticate(request, level=self.auth_level).auth():
            return self.handle_no_permission()
        return super(AninstanceGenericView, self).dispatch(request, *args, **kwargs)

    def get(self, request):
        # default shared contexts
        self.context.update({
            'param_str': helpers.update_url_param(request, param_name=self.PARAM_STR),
            'page_str': self.PAGE_STR,
        })
        # set any client session data
        helpers.set_session_data(request)
        # get requested page from URL (if any)
        self.requested_page = helpers.get_page(request)
        # SEARCH SETUP ...
        if 'q' in request.GET:
            models_param = ''.join(['&models={}'.format(m) for m in self.MODELS_TO_SEARCH.get(
                request.GET.get('action'))]) if request.GET.get('action') in self.MODELS_TO_SEARCH else ''
            self.search_url = '/search?q=+{}{}'.format(
                request.GET.get('q'),
                models_param,
            )

    def post(self, request):
        # default shared contexts
        self.context.update({
            'param_str': helpers.update_url_param(request, param_name=self.PARAM_STR),
            'cache_ttl': self.NEVER_CACHE_TTL,  # never cache post responses

        })
        # set the client's ip in their session
        request.session['ip'] = helpers.get_client_ip(request)
        # set timezone to UTC if not already set to something else
        if 'django_timezone' not in request.session:
            request.session['django_timezone'] = 'UTC'


DEFAULT_FROM_EMAIL = settings.DEFAULT_FROM_EMAIL
SITE_FQDN = settings.SITE_FQDN if not settings.DEBUG else 'localhost:8000'
