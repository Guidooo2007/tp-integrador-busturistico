from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import datetime, timedelta
from .models import (
    Parada, Recorrido, Viaje, Bus, Chofer, Atractivo, AtractivoXParada, 
    OrdenParada, EstadoViaje, EstadoBus
)
from .forms import OrdenParadaForm, AtractivoXParadaForm

class ControladorParada:
    @staticmethod
    def crear_parada(data):
        try:
            if Parada.objects.filter(nombre__iexact=data['nombre']).exists():
                return {'success': False, 'error': 'Ya existe una parada con este nombre.'}
            
            if Parada.objects.filter(direccion__iexact=data['direccion']).exists():
                return {'success': False, 'error': 'Ya existe una parada en esta dirección.'}

            if not data['nombre'].strip():
                return {'success': False, 'error': 'El nombre de la parada no puede estar vacío.'}

            if not data['direccion'].strip():
                return {'success': False, 'error': 'La dirección de la parada no puede estar vacía.'}

            if len(data['descripcion'].strip()) < 10:
                return {'success': False, 'error': 'La descripción debe tener al menos 10 caracteres.'}

            if not data.get('tipo_parada'):
                return {'success': False, 'error': 'Debe seleccionar un tipo de parada.'}

            parada = Parada.objects.create(**data)
            return {'success': True, 'parada': parada}

        except Exception as e:
            return {'success': False, 'error': f'Error al crear la parada: {str(e)}'}

    @staticmethod
    def listar_paradas():
        return Parada.objects.all().order_by('nombre')
    
    @staticmethod
    def eliminar_parada(parada_id):
        try:
            parada = Parada.objects.get(id=parada_id)
            nombre_parada = parada.nombre
            parada.delete()
            return True, f'La parada "{nombre_parada}" ha sido eliminada.'
        except Parada.DoesNotExist:
            return False, 'La parada no existe.'
        except Exception as e:
            return False, f'Error al eliminar la parada: {str(e)}'

class ControladorParadaRecorrido:
    @staticmethod
    def obtener_contexto_gestion():
        return {
            'form': OrdenParadaForm(),
            'paradas': OrdenParada.objects.all().select_related('parada', 'recorrido').order_by('recorrido', 'asignacion_paradas')
        }

    @staticmethod
    def procesar_peticion(request):
        if 'agregar' in request.POST:
            return ControladorParadaRecorrido._procesar_agregar(request)
        elif 'eliminar' in request.POST:
            return ControladorParadaRecorrido._procesar_eliminar(request)
        return None

    @staticmethod
    def _procesar_agregar(request):
        form = OrdenParadaForm(request.POST)
        if form.is_valid():
            try:
                ControladorParadaRecorrido._validar_orden_parada(form.cleaned_data)
                orden_parada = form.save()
                return {'success': True, 'message': 'Parada agregada exitosamente al recorrido'}
            except ValidationError as e:
                return {'success': False, 'error': str(e)}
        return {'success': False, 'error': 'Por favor, corrija los errores en el formulario'}

    @staticmethod
    def _procesar_eliminar(request):
        orden_parada_id = request.POST.get('orden_parada_id')
        try:
            orden_parada = OrdenParada.objects.get(id=orden_parada_id)
            orden_parada.delete()
            return {'success': True}
        except OrdenParada.DoesNotExist:
            return {'success': False, 'error': 'Parada no encontrada'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    @staticmethod
    def _validar_orden_parada(data):
        if OrdenParada.objects.filter(
            recorrido=data['recorrido'], 
            asignacion_paradas=data['asignacion_paradas']
        ).exists():
            raise ValidationError('Ya existe una parada con ese orden en este recorrido')

class ControladorRecorrido:
    @staticmethod
    def obtener_recorrido_y_paradas(recorrido_id):
        recorrido = get_object_or_404(Recorrido, id=recorrido_id)
        paradas = OrdenParada.objects.filter(recorrido=recorrido).select_related('parada').order_by('asignacion_paradas')
        
        paradas_procesadas = []
        for orden in paradas:
            parada_info = {
                'asignacion_paradas': orden.asignacion_paradas,
                'parada': orden.parada,
                'color': '#800080' if orden.parada.tipo_parada.nombre_tipo_parada == 'Parada Compartida' else recorrido.codigo_alfanumerico
            }
            paradas_procesadas.append(parada_info)
            
        return {
            'recorrido': recorrido,
            'paradas': paradas_procesadas
        }

class ControladorRecorridoNuevo:
    @staticmethod
    def validar_y_crear_recorrido(data):
        try:
            if Recorrido.objects.filter(codigo_alfanumerico=data['codigo_alfanumerico']).exists():
                raise ValidationError('El código alfanumérico ya existe.')
            
            if not data['codigo_alfanumerico'].startswith('#'):
                raise ValidationError('El código alfanumérico debe comenzar con #.')

            if data['hora_fin'] <= data['hora_inicio']:
                raise ValidationError('La hora de fin debe ser posterior a la hora de inicio.')

            frecuencia = datetime.strptime(str(data['frecuencia']), '%H:%M:%S').time()
            minutos_frecuencia = frecuencia.hour * 60 + frecuencia.minute
            if minutos_frecuencia < 5 or minutos_frecuencia > 60:
                raise ValidationError('La frecuencia debe estar entre 5 y 60 minutos.')

            recorrido = Recorrido.objects.create(**data)
            return recorrido, None

        except ValidationError as e:
            return None, str(e)
        except Exception as e:
            return None, f"Error inesperado: {str(e)}"

class ControladorViaje:
    @staticmethod
    def crear_viaje(data):
        viaje = Viaje(**data)
        viaje.save()
        return viaje

    @staticmethod
    def obtener_viaje(viaje_id):
        return Viaje.objects.get(id=viaje_id)

    @staticmethod
    def eliminar_viaje(viaje_id):
        viaje = Viaje.objects.get(id=viaje_id)
        viaje.delete()

class ControladorBus:
    @staticmethod
    def crear_bus(data):
        print("Datos recibidos para crear bus:", data)
        patente = data.get('patente')
        if Bus.objects.filter(patente=patente).exists():
            raise ValueError('La patente ya existe.')

        num_unidad = data.get('num_unidad')
        if Bus.objects.filter(num_unidad=num_unidad).exists():
            raise ValueError('El número de unidad ya existe.')

        bus = Bus(**data)
        bus.save()
        return bus

    @staticmethod
    def obtener_bus(bus_id):
        return Bus.objects.get(id=bus_id)

    @staticmethod
    def eliminar_bus(bus_id):
        bus = Bus.objects.get(id=bus_id)
        bus.delete()

class ControladorChofer:
    @staticmethod
    def crear_chofer(data):
        chofer = Chofer(**data)
        chofer.save()
        return chofer

    @staticmethod
    def obtener_chofer(chofer_id):
        return Chofer.objects.get(id=chofer_id)

    @staticmethod
    def eliminar_chofer(chofer_id):
        chofer = Chofer.objects.get(id=chofer_id)
        chofer.delete()

class ControladorReporteViajes:
    def generar_reporte(self):
        fecha_actual = timezone.now().date()
        viajes = Viaje.objects.filter(fecha_viaje=fecha_actual)
        
        print(f"Viajes encontrados para {fecha_actual}: {viajes.count()}")
        
        viajes_procesados = self._procesar_viajes(viajes)
        promedios = self._calcular_promedios(viajes_procesados)
        
        print(f"Viajes procesados: {viajes_procesados}")
        
        return {
            'viajes': viajes_procesados,
            'promedios': promedios,
            'today': fecha_actual,
        }

    def _procesar_viajes(self, viajes):
        viajes_procesados = []
        for viaje in viajes:
            viaje_procesado = self._procesar_viaje(viaje)
            viajes_procesados.append(viaje_procesado)
        return viajes_procesados

    def _procesar_viaje(self, viaje):
        if viaje.marca_inicio_viaje_real and viaje.marca_fin_viaje_real:
            duracion = (viaje.marca_fin_viaje_real - viaje.marca_inicio_viaje_real).total_seconds() / 60
            horario_inicio_programado_dt = timezone.make_aware(datetime.combine(viaje.fecha_viaje, viaje.horario_inicio_programado))
            demora = (viaje.marca_inicio_viaje_real - horario_inicio_programado_dt).total_seconds() / 60
        else:
            duracion = None
            demora = None

        return {
            'viaje': viaje,
            'duracion': duracion,
            'demora': demora
        }

    def _calcular_promedios(self, viajes_procesados):
        duraciones = [v['duracion'] for v in viajes_procesados if v['duracion'] is not None]
        demoras = [v['demora'] for v in viajes_procesados if v['demora'] is not None]

        duracion_promedio = sum(duraciones) / len(duraciones) if duraciones else None
        demora_promedio = sum(demoras) / len(demoras) if demoras else None

        return {
            'duracion_promedio': duracion_promedio,
            'demora_promedio': demora_promedio,
        }

class ControladorAtractivo:
    @staticmethod
    def crear_atractivo(data):
        try:
            if Atractivo.objects.filter(nombre__iexact=data['nombre']).exists():
                raise ValidationError('Ya existe un atractivo con este nombre.')

            atractivo = Atractivo.objects.create(**data)
            return {'success': True, 'atractivo': atractivo}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    @staticmethod
    def listar_atractivos():
        return Atractivo.objects.all().order_by('nombre')

    @staticmethod
    def eliminar_atractivo(atractivo_id):
        try:
            atractivo = Atractivo.objects.get(id=atractivo_id)
            nombre = atractivo.nombre
            atractivo.delete()
            return True, f'El atractivo "{nombre}" ha sido eliminado.'
        except Atractivo.DoesNotExist:
            return False, 'El atractivo no existe.'
        except Exception as e:
            return False, f'Error al eliminar el atractivo: {str(e)}'

class ControladorAtractivoXParada:
    @staticmethod
    def obtener_contexto_gestion():
        return {
            'form': AtractivoXParadaForm(),
            'asignaciones': AtractivoXParada.objects.all().select_related('parada', 'atractivo')
        }

    @staticmethod
    def agregar_atractivo_a_parada(data):
        try:
            asignacion = AtractivoXParada.objects.create(**data)
            return True, 'Atractivo asignado exitosamente a la parada.'
        except Exception as e:
            return False, str(e)

    @staticmethod
    def eliminar_asignacion(asignacion_id):
        try:
            asignacion = AtractivoXParada.objects.get(id=asignacion_id)
            asignacion.delete()
            return True, 'Asignación eliminada exitosamente.'
        except AtractivoXParada.DoesNotExist:
            return False, 'La asignación no existe.'
        except Exception as e:
            return False, str(e)

