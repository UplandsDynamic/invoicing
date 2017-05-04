import datetime
from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from aninstance_framework.page_registry import PAGE_REGISTERY

DEFAULT_SITE_NAME = 'Aninstance'


def default_strings(request):
    return {
        'default_site_logo': '{}/{}'.format(settings.STATIC_URL, 'images/aninstance_logo_invoicing.png'),
        'default_site_logo_desc': _('Aninstance Invoicing Application'),
        'default_site_logo_url': '/',
        'default_footer_text': _('~ Aninstance Invoicing created by Dan Bright, at '
                                 '<a href="https://www.aninstance.com">www.aninstance.com</a> | '
                                 '<a href="https://www.github.com/aninstance/invoicing" target="_blank">'
                                 'View on Github</a> ~'),
        'default_site_name': DEFAULT_SITE_NAME,
        'default_tag_line': _('Feel free to get in touch with bug reports, suggestions, or enquires about'
                              ' subscribing to a managed instance: productions@aninstance.com'),
        'default_main_footer': _('&copy;{} {}. All Rights Reserved.'.format(datetime.datetime.now().strftime('%Y'),
                                                                            DEFAULT_SITE_NAME.title())),
        'default_panel_footer': '',
        'default_right_sidebar_blurb': '',
        'default_right_sidebar_image': '',
        'default_right_sidebar_image_desc': '',
        'default_right_sidebar_image_url': '',
        'default_right_sidebar_links': None,
        'default_left_sidebar_image': '{}/{}'.format(settings.STATIC_URL, 'images/aninstance_icon.png'),
        'default_left_sidebar_image_desc': _('Aninstance.com'),
        'default_left_sidebar_image_url': '/',
        'default_head_title': _(
            'Aninstance Invoicing | invoicing.aninstance.com'),
        'default_client_ip_blurb': _('Your origin IP address appears to be'),
        'no_client_ip_blurb': _('No client IP recorded ...'),
        'page_register': PAGE_REGISTERY,
        'client_timezone': '{}: {}'.format(_('Your timezone is set as'), request.session.get('django_timezone')),
        'pagination': False,
        'menu_items': PAGE_REGISTERY or None,
        'footer_links': ' | '.join(
            ['<a href="/{}">{}</a>'.format(x.get('path'), x.get('menu_name').title())
             for x in PAGE_REGISTERY if x.get('display_footer')]),
        'default_template_frag_cache_timeout': settings.DEFAULT_CACHES_TTL,
        'default_search_results_cache_ttl': settings.DEFAULT_SEARCH_RESULTS_CACHE_TTL,
        'search_back_link_blurb': _('Back to previous'),
        'settings': settings
    }
