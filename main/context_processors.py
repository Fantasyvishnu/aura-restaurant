from django.conf import settings


def restaurant(request):
    """Makes {{ restaurant.name }}, {{ restaurant.phone }}, {{ restaurant.no_show_fine }} ... available in every template.
    Edit the values in settings.py (RESTAURANT = {...}) and the whole website updates."""
    info = dict(settings.RESTAURANT)
    info['address'] = f"{info['address_line1']}, {info['address_line2']}"
    return {'restaurant': info}
