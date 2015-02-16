"""
    Custom template tags for OCL Web.

    TODO: The label tags could take an optional arg to not include the href, but not
    sure if we want that anyway.
"""
import re
import dateutil.parser

from django import template
from django.template.defaultfilters import stringfilter
from django.template.base import (Node, NodeList, Template, Context)


from libs.ocl import OCLapi


register = template.Library()


@register.filter
def smart_datetime(iso8601_dt):
    """
        Return a friendly date time display.
        Currently just localized, but eventually "two days ago", etc.
    """
    dt = dateutil.parser.parse(iso8601_dt)
    return dt.strftime('%c')


@register.filter
def smart_date(iso8601_dt):
    """
        Return a friendly date display.
        Currently just localized, but eventually "two days ago", etc.
    """
    dt = dateutil.parser.parse(iso8601_dt)
    return dt.strftime('%x')


@register.inclusion_tag('includes/org_label_incl.html')
def org_label(org):
    return {'org': org}


@register.inclusion_tag('includes/user_label_incl.html')
def user_label(user):
    return {'user': user}


@register.inclusion_tag('includes/source_owner_label_incl.html')
def source_owner_label(source):
    """
    Display a label for a source owner, which can be either a user or an organization.
    Note that this tag displays the *owner* of the source, not the source.

    :param source: is the OCL source object.
    """
    from_org = source.get('owner_type') == 'organization'
    return {
        'from_org': from_org,
        'source': source,
    }


@register.inclusion_tag('includes/source_label_incl.html')
def source_label(source):
    """

    """
    return {'source': source}


@register.inclusion_tag('includes/concept_label_incl.html')
def concept_label(concept):
    return {'concept': concept}


@register.inclusion_tag('includes/field_display_incl.html')
def field_label(label, value, url=False):
    """
        Display a simple read only field value to user, like:

        field label text:    field value

        See the include template for details.
    """
    return {
        'field_label': label,
        'field_value': value,
        'is_url': url,
    }


@register.inclusion_tag('includes/simple_pager_incl.html')
def simple_pager(page, name, url=None):
    """
        Display a simple pager with N-M of P {name}[<] [>]

        :param page: is a django paginator Page object.
        :param name: is for display the item's name.
        :url: is the GET url used to invoke the other page, usually
            includes query parameters.
    """

    if url:
        # Remove existing page GET parameters
        # Should use force_text, see django-bootstrap3...
        url = re.sub(r'\?page\=[^\&]+', '?', url)
        url = re.sub(r'\&page\=[^\&]+', '', url)
        # Append proper separator
        if '?' in url:
            url += '&'
        else:
            url += '?'

    return {
        'page': page,
        'name': name,
        'url': url,
    }


class IfCanChangeNode(Node):

    def __init__(self, nodelist_true, nodelist_false, source_var):
        self.nodelist_true, self.nodelist_false = nodelist_true, nodelist_false
        self.source_var = template.Variable(source_var)

    def render(self, context):
        # Init state storage
        try:
            source = self.source_var.resolve(context)
        except template.VariableDoesNotExist:
            return ''

        user = context['user']

        can = False
        if source.get('owner_type') == 'Organization':
            # member can change
            # TODO: need a better API call to check for access
            api = OCLapi(context['request'], debug=True)
            results = api.get('orgs', source.get('owner'), 'members',
                user.username)
            if results.status_code == 204:
                can = True
            print 'ACCESS CheCK:', results.status_code

        else:
            # owned by a user
            can = True

        if can:
            return self.nodelist_true.render(context)
        else:
            return self.nodelist_false.render(context)


@register.tag('if_can_change')
def do_if_can_change(parser, token):
    """
    The ``{% if_can_change source_or_concept %}`` tag evaluates whether the current user have
    access to the specified source.

    If so, the block bracketed are output.

    ::

        {% if_can_change source %}

        {% endif_can_change %}


    """
    # {% if ... %}
    # NOTE: the source_var can also be a concept
    source_var = token.split_contents()[1]

    nodelist_true = parser.parse(('else', 'endif_can_change'))

    token = parser.next_token()
    if token.contents == 'else':
        nodelist_false = parser.parse(('endif_can_change',))
        parser.delete_first_token()
    else:
        nodelist_false = NodeList()

    return IfCanChangeNode(nodelist_true, nodelist_false, source_var)