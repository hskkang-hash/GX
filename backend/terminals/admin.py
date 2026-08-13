from django.contrib import admin
from terminals.models import Terminal, TerminalType, Routes, RouteTerminal

admin.site.register(Terminal)
admin.site.register(TerminalType)
admin.site.register(Routes)
admin.site.register(RouteTerminal) 