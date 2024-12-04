from django.urls import path
from .views import *
from django.contrib.auth.views import LogoutView
from django.contrib.auth import views as auth_views
from . import views
from django.contrib.auth.forms import UserCreationForm

urlpatterns = [
    path('', IndexView.as_view(), name='index'),
    path('base/',BaseView.as_view(), name='base'),
    path('recorridos/',RecorridoListView.as_view(), name='recorridos'),
    path('parada/<int:pk>/', ParadaDetailView.as_view(), name='parada_detail'),
    path('nuevorecorrido/', NuevoRecorridoView.as_view(), name='nuevorecorrido'),
    path('recorridos/<int:pk>/', RecorridoDetailView.as_view(), name='recorrido_detail'),
    path('login/', ChoferLoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('marcar-viaje/', MarcarViajeView.as_view(), name='marcar_viaje'),
    path('viajes/', ViajeListView.as_view(), name='viajes'),
    path('viaje/<int:pk>/', ViajeDetailView.as_view(), name='viaje_detalle'),
    path('nuevo-bus/', CrearBusView.as_view(), name='crear_bus'),
    path('buses/', BusListView.as_view(), name='buses'),
    path('nuevo-viaje/', CrearViajeView.as_view(), name='crear_viaje'),  
    path('editar-viaje/<int:pk>/', EditarViajeView.as_view(), name='editar_viaje'),  
    path('reporte-viajes/', ReporteViajesView.as_view(), name='reporte_viajes'),
    path('choferes/', ChoferListView.as_view(), name='choferes'),
    path('recorrido/gestion-paradas/', GestionParadaRecorridoView.as_view(), name='gestion_paradas'),
    path('parada/crear/', CrearParadaView.as_view(), name='crear_parada'),
    path('paradas/', ListaParadasView.as_view(), name='lista_paradas'),
    path('atractivos/', ListaAtractivosView.as_view(), name='lista_atractivos'),
    path('atractivo/crear/', CrearAtractivoView.as_view(), name='crear_atractivo'),
    path('atractivo/gestion-paradas/', GestionAtractivosParadaView.as_view(), name='gestion_atractivos_parada'),
    path('recorridos/lista/', ListaRecorridosView.as_view(), name='lista_recorridos'),
    path('viaje/viajes_disponibles', AnotarEnViajeView.as_view(), name='viajes_disponibles'),
    path('viaje/lista_anotados', AnotarEnViajeView.as_view(), name='lista_anotados'),
    path('user/login', LoginUsuarioView.as_view(), name='login_usuario'),
    path('user/registro', RegistroUsuarioView.as_view(), name='registro'),
]