from django import template
from django.template.defaultfilters import stringfilter

register = template.Library()


@register.filter
@stringfilter
def hex_to_rgb(value, opacity='1'):
    """Convierte un color hex (#2563eb) a rgba(37, 99, 235, opacity).
    Uso: {{ '#2563eb'|hex_to_rgb:'0.15' }} → rgba(37, 99, 235, 0.15)
    """
    value = value.lstrip('#')
    if len(value) != 6:
        return value
    try:
        r, g, b = int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)
        return f'rgba({r}, {g}, {b}, {opacity})'
    except ValueError:
        return value


@register.filter
def multiply(value, arg):
    """Multiplica dos valores. Uso: {{ item.cantidad|multiply:item.precio_unitario }}"""
    try:
        return float(value or 0) * float(arg or 0)
    except (ValueError, TypeError):
        return 0
