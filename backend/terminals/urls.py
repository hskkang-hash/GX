from ninja_extra import NinjaExtraAPI
from django.urls import path
from terminals.views import TerminalsController, TerminalTypeController, \
RoutesController, LocationTypeController, DockingStationController, InfrastructureController, DeliveryHubController, FunctionController,\
QGroundControlController, DayOfWeekController
    


terminals_api = NinjaExtraAPI(urls_namespace='terminals')

terminals_api.register_controllers(
    TerminalsController,
    TerminalTypeController,
    RoutesController,
    LocationTypeController,
    DockingStationController,
    InfrastructureController,
    DeliveryHubController,
    FunctionController,
    QGroundControlController,
    DayOfWeekController
)

urlpatterns = [
    path('', terminals_api.urls),
] 