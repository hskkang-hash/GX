from django.db.models import Func, DateTimeField, CharField
from django.db.models.functions import Cast

class JSONExtractText(Func):
    function = "->>"
    template = "%(expressions)s ->> '%(key)s'"

    def __init__(self, expression, key, **extra):
        super().__init__(expression, key=key, **extra)


class JSONExtractDateTime(Func):
    """
    Extract datetime from JSON field and handle timezone properly.
    Subtracts 7 hours to compensate for Django's automatic timezone conversion.
    """
    function = 'CAST'
    # Cast to timestamp
    template = "((%(expressions)s ->> '%(key)s')::timestamp)"
    output_field = DateTimeField()

    def __init__(self, expression, key, **extra):
        super().__init__(expression, key=key, **extra)