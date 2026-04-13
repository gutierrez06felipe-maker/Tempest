import json

from pyramid.view import view_config

from ..catalog import PRODUCTS


@view_config(route_name='home', renderer='contact:templates/mytemplate.jinja2')
def my_view(request):
    return {
        'project': 'contact',
        'products_json': json.dumps(PRODUCTS),
    }
