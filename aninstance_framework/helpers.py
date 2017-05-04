from datetime import datetime
import pytz
from django.utils.html import conditional_escape
import docutils.core
import re
from ipware.ip import get_ip

def set_session_data(request):
    # set the client's ip in their session
    request.session['ip'] = get_client_ip(request)
    # set timezone to UTC if not already set to something else
    if 'django_timezone' not in request.session:
        request.session['django_timezone'] = 'UTC'


def get_page(request):
    if 'p' in request.GET and \
                    request.GET.get('p') is not '' and \
            is_num(request.GET.get('p')):
        return int(request.GET.get('p', 1))
    else:
        return 1  # return 1 as default


def get_client_ip(request):
    # x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    # if x_forwarded_for:
    #     ip = x_forwarded_for.split(',')[0]
    # else:
    #     ip = request.META.get('REMOTE_ADDR')
    # return ip
    ip = get_ip(request)
    if ip is not None:
        return ip
    else:
        return None


def utc_to_local(value, client_timezone, autoescape=True):
    # takes utc string (in format %Y-%m-%dT%H:%M:%S), returns formatted string in client's tz
    if autoescape:
        esc = conditional_escape
    else:
        esc = lambda x: x
    value = value.strip('Z')
    # turn it into datetime obj (and if appending "Z" to indicate UTC, strip the thing!)
    dt_object = datetime.strptime(value.strip('Z'), '%Y-%m-%dT%H:%M:%S')
    # make TZ aware and set tz to UTC (we already know it's UTC)
    tz_aware_datetime = pytz.utc.localize(dt_object)
    # return converted to client timezone & format with strftime for presentation
    return tz_aware_datetime.astimezone(
        pytz.timezone(client_timezone)).strftime('%d %B %Y %H:%M:%S')


def format_utc_str_for_template(value, autoescape=True):
    # takes utc str, formats for display
    if autoescape:
        esc = conditional_escape
    else:
        esc = lambda x: x
    # converts to dt obj
    value = '{}Z'.format(value) if 'Z' not in value else value
    dt_object = datetime.strptime(value, '%Y-%m-%dT%H:%M:%SZ')
    return '{} UTC'.format(dt_object.strftime('%d %B %Y %H:%M:%S'))


def local_to_utc(value):
    # converts time aware str to UTC str
    dt_object = datetime.strptime(value, '%Y-%m-%dT%H:%M:%S %z')
    # returns in format e.g. "2016-09-29T13:41:36Z +0000" (or change to %Z for timezone codes)
    return dt_object.astimezone(pytz.UTC).strftime('%Y-%m-%dT%H:%M:%S %z')


def is_num(value):
    try:
        return int(value)
    except (ValueError, TypeError):
        return False


def update_url_param(request, param_name):
    # function to update request.GET params, retaining all existing params,
    # with "param_name" added and/or retained with value cleared, ready to pass to template
    # for template logic (e.g. looping values) to apply new value if required.
    try:
        existing_params = dict(request.GET)  # convert immutable querydict to mutable dict
    except AttributeError:
        existing_params = None
    if not existing_params:
        return '?{}='.format(param_name)
    else:  # if existing params
        existing_str = ''
        existing_params.pop(param_name, None)  # pop off existing param_name if exists
        for p, v in existing_params.items():  # always strip p (page) (handled in 'get' method & views)
            if p != 'p':
                existing_str += '{}{}&'.format(p, '={}'.format(v[0]) if v[0] else '')
        return '?{}{}='.format(existing_str, param_name)


def remove_url_param(request, param):
    # function to remove a param from the path
    original = request.get_full_path()
    return re.sub(r'{param}=.*(?=&)&?|{param}=.*(?!=&)'.format(param=param), '', original)


def strip_url_params(request):
    # function to remove all params from a path
    original = request.get_full_path()
    return re.sub(r'\?.*', '', original)


def sanitize_url_param(param):
    # function to sanitise a url param
    return re.sub('[^A-z0-9|\-]', '', param) if param else None


def sanitize_post_data(data):
    # function to sanitize post data
    return re.sub('[^A-z0-9|\-|)|(|,]', '', data) if data else None


def format_data_for_display(data, file_formatting, media_type):
    try:
        if media_type == 'raw':
            if file_formatting == 'rst':
                # use docutils to convert from .rst to html
                return docutils.core.publish_parts(data, writer_name='html')['html_body']
            elif file_formatting == 'txt':
                # simple text file formatting for html
                data = re.sub(r'(http[s]?)://(.+)', r'<a href="\1://\2" target="_blank">\2</a>',
                              data)  # put links into anchor tags
                data = re.sub(r'[\n|\r]', r'<br>', data)  # replace newlines & returns with an html break
                return data
    except Exception as e:
        print(e)
    return None


def phrase_check(string):
    return re.compile(r'\b({0})\b'.format(string), flags=re.IGNORECASE).search
