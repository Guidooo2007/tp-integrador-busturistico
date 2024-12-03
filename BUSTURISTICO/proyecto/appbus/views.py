from django.shortcuts import render,redirect, get_object_or_404
from django.views.generic import TemplateView, ListView, DetailView, View,CreateView
import requests
from typing import Any
from django.contrib.auth.views import LoginView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic.edit import FormView, UpdateView, DeleteView
from django.urls import reverse_lazy
from .forms import *
from .models import *
from django.utils import timezone
from django.http import HttpResponseRedirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import Avg
from datetime import datetime
from django.contrib.auth.models import User

# Create your views here.

class IndexView(TemplateView):
    template_name = 'index.html'
    
class BaseView(TemplateView):
    template_name = 'base/base.html'
    


    
class ParadaDetailView(DetailView):
    model = Parada
    template_name = 'parada/parada.html'
    context_object_name = 'parada'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['atractivos'] = AtractivoXParada.objects.filter(parada=self.object).select_related('atractivo')
        return context
    
#NUEVA VISTA
class ControladorParada:
    @staticmethod
    def crear_parada(data):
        try:
            # Validaciones adicionales
            if Parada.objects.filter(nombre__iexact=data['nombre']).exists():
                return {
                    'success': False, 
                    'error': 'Ya existe una parada con este nombre.'
                }
            
            if Parada.objects.filter(direccion__iexact=data['direccion']).exists():
                return {
                    'success': False, 
                    'error': 'Ya existe una parada en esta dirección.'
                }

            # Validar que los campos requeridos no estén vacíos
            if not data['nombre'].strip():
                return {
                    'success': False, 
                    'error': 'El nombre de la parada no puede estar vacío.'
                }

            if not data['direccion'].strip():
                return {
                    'success': False, 
                    'error': 'La dirección de la parada no puede estar vacía.'
                }

            # Validar que la descripción tenga un mínimo de caracteres
            if len(data['descripcion'].strip()) < 10:
                return {
                    'success': False, 
                    'error': 'La descripción debe tener al menos 10 caracteres.'
                }

            # Validar que se haya seleccionado un tipo de parada
            if not data.get('tipo_parada'):
                return {
                    'success': False, 
                    'error': 'Debe seleccionar un tipo de parada.'
                }

            # Si todas las validaciones pasan, crear la parada
            parada = Parada.objects.create(**data)
            return {'success': True, 'parada': parada}

        except Exception as e:
            return {'success': False, 'error': f'Error al crear la parada: {str(e)}'}

    @staticmethod
    def listar_paradas():
        """Obtiene todas las paradas ordenadas por nombre"""
        return Parada.objects.all().order_by('nombre')
    
    @staticmethod
    def eliminar_parada(parada_id):
        """Elimina una parada específica"""
        try:
            parada = Parada.objects.get(id=parada_id)
            nombre_parada = parada.nombre
            parada.delete()
            return True, f'La parada "{nombre_parada}" ha sido eliminada.'
        except Parada.DoesNotExist:
            return False, 'La parada no existe.'
        except Exception as e:
            return False, f'Error al eliminar la parada: {str(e)}'


from django.http import HttpResponseForbidden, HttpResponseRedirect
from django.urls import reverse_lazy

class ListaParadasView(ListView):
    template_name = 'parada/lista_paradas.html'
    context_object_name = 'paradas'

    def dispatch(self, request, *args, **kwargs):
        
        if not request.user.is_authenticated:
            return HttpResponseRedirect(reverse_lazy('base'))  
        
       
        if not request.user.is_superuser:
            return HttpResponseForbidden("No tienes permiso para acceder a esta página.")
        
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return ControladorParada.listar_paradas()

    def post(self, request, *args, **kwargs):
        if 'eliminar' in request.POST:
            parada_id = request.POST.get('parada_id')
            ControladorParada.eliminar_parada(parada_id)
        return HttpResponseRedirect(reverse_lazy('lista_paradas'))


class CrearParadaView(CreateView):
    template_name = 'parada/crear_parada.html'
    form_class = ParadaForm
    success_url = reverse_lazy('lista_paradas')

    def dispatch(self, request, *args, **kwargs):
        
        if not request.user.is_authenticated:
            return HttpResponseRedirect(reverse_lazy('base'))  
        
       
        if not request.user.is_superuser:
            return HttpResponseForbidden("No tienes permiso para acceder a esta página.")
        
        return super().dispatch(request, *args, **kwargs)


    def form_valid(self, form):
        response = ControladorParada.crear_parada(form.cleaned_data)
        if response.get('success'):
            messages.success(self.request, 'Parada creada exitosamente.')
            return HttpResponseRedirect(self.success_url)  
        else:
            messages.error(self.request, response.get('error'))
            return self.form_invalid(form)
    
    
class GestionParadaRecorridoView(LoginRequiredMixin, UserPassesTestMixin, View):
    template_name = 'recorrido/gestion_paradas.html'
    
    def test_func(self):
        return self.request.user.is_superuser

    def get(self, request):
        context = ControladorParadaRecorrido.obtener_contexto_gestion()
        return render(request, self.template_name, context)

    def post(self, request):
        resultado = ControladorParadaRecorrido.procesar_peticion(request)
        
        return redirect('gestion_paradas')

class ControladorParadaRecorrido:
    @staticmethod
    def obtener_contexto_gestion():
        """Obtiene el contexto necesario para la vista de gestión"""
        return {
            'form': OrdenParadaForm(),
            'paradas': OrdenParada.objects.all().select_related('parada', 'recorrido').order_by('recorrido', 'asignacion_paradas')
        }

    @staticmethod
    def procesar_peticion(request):
        """Procesa las peticiones POST para agregar o eliminar paradas"""
        if 'agregar' in request.POST:
            return ControladorParadaRecorrido._procesar_agregar(request)
        elif 'eliminar' in request.POST:
            return ControladorParadaRecorrido._procesar_eliminar(request)
        return None

    @staticmethod
    def _procesar_agregar(request):
        """Procesa la petición para agregar una parada"""
        form = OrdenParadaForm(request.POST)
        if form.is_valid():
            try:
                ControladorParadaRecorrido._validar_orden_parada(form.cleaned_data)
                orden_parada = form.save()
                messages.success(request, 'Parada agregada exitosamente al recorrido')
            except ValidationError as e:
                messages.error(request, str(e))
        else:
            messages.error(request, 'Por favor, corrija los errores en el formulario')
        return None

    @staticmethod
    def _procesar_eliminar(request):
        """Procesa la petición para eliminar una parada"""
        orden_parada_id = request.POST.get('orden_parada_id')
        try:
            orden_parada = OrdenParada.objects.get(id=orden_parada_id)
            orden_parada.delete()
            return JsonResponse({'success': True})
        except OrdenParada.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Parada no encontrada'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

    @staticmethod
    def _validar_orden_parada(data):
        """Valida los datos de una orden de parada"""
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
        
        # Procesar el color de las paradas
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

class RecorridoDetailView(DetailView):
    model = Recorrido
    template_name = 'recorrido/recorrido.html'
    context_object_name = 'recorrido'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        datos = ControladorRecorrido.obtener_recorrido_y_paradas(self.object.id)
        context['paradas'] = datos['paradas']
        return context

    
class ListaRecorridosView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    template_name = 'recorrido/lista_recorridos.html'   
    context_object_name = 'recorridos'

    def test_func(self):
        return self.request.user.is_superuser

    def get_queryset(self):
        return Recorrido.objects.all().order_by('nombre')  

    def post(self, request, *args, **kwargs):
        if 'eliminar' in request.POST:  
            recorrido_id = request.POST.get('recorrido_id')
            recorrido = get_object_or_404(Recorrido, id=recorrido_id)
            recorrido.delete()
            messages.success(request, 'Recorrido eliminado exitosamente.')
            return redirect('lista_recorridos')  

class RecorridoListView(ListView):
    model = Recorrido
    template_name = 'recorrido/recorridos.html'
    context_object_name = 'recorridos'


class ControladorRecorridoNuevo:
    @staticmethod
    def validar_y_crear_recorrido(data):
        try:
            # Validaciones personalizadas
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

            # Crear el recorrido
            recorrido = Recorrido.objects.create(**data)
            return recorrido, None

        except ValidationError as e:
            return None, str(e)
        except Exception as e:
            return None, f"Error inesperado: {str(e)}"

class NuevoRecorridoView(FormView):
    template_name = 'recorrido/nuevorecorrido.html'
    form_class = RecorridoForm
    success_url = reverse_lazy('recorridos')

    def form_valid(self, form):
        data = form.cleaned_data
        recorrido, error = ControladorRecorridoNuevo.validar_y_crear_recorrido(data)
        
        if error:
            messages.error(self.request, error)
            return self.form_invalid(form)
        
        messages.success(self.request, 'Recorrido creado exitosamente.')
        return super().form_valid(form)
    

    

class MarcarViajeView(LoginRequiredMixin, TemplateView):
    template_name = 'chofer/marcar_viaje.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            # Obtener el legajo de la sesión
            legajo = self.request.session.get('legajo_chofer')
            print(f"Legajo en sesión: {legajo}")
            
            chofer = Chofer.objects.get(legajo=legajo)
            print(f"Chofer encontrado: {chofer}") 
            
            viajes_chofer = Viaje.objects.filter(chofer=chofer)
            print(f"Viajes del chofer: {viajes_chofer}")
            
            viaje = viajes_chofer.last()
            print(f"Último viaje encontrado: {viaje}")
            
            
            context['viaje'] = viaje
            
        except Chofer.DoesNotExist:
            print("ERROR: No se encontró el chofer")
            context['viaje'] = None
        except Exception as e:
            print(f"ERROR: {str(e)}")
            context['viaje'] = None
        
        return context

    def post(self, request, *args, **kwargs):
        try:
            legajo = request.session.get('legajo_chofer')
            chofer = Chofer.objects.get(legajo=legajo)
            viaje_id = request.POST.get('id')
            viaje = get_object_or_404(Viaje, id=viaje_id, chofer=chofer)
            action = request.POST.get('action')

            fecha_actual = timezone.now().date()
            tiempo_actual = timezone.localtime(timezone.now()).time()
            print(f"Fecha actual: {fecha_actual}, Hora actual: {tiempo_actual}")
            print(f"Fecha programada: {viaje.fecha_viaje}, Hora programada: {viaje.horario_inicio_programado}")
            if action == 'inicio' and not viaje.marca_inicio_viaje_real:
                if fecha_actual == viaje.fecha_viaje and tiempo_actual >= viaje.horario_inicio_programado:
                    viaje.marca_inicio_viaje_real = timezone.now()
                    viaje.estado_viaje = EstadoViaje.objects.get(nombre='En Curso')  # Cambiar el estado a "En Curso"
                    viaje.save()
                else:
                    messages.error(request, "No puedes iniciar el viaje antes de la fecha programada.")
                return redirect('marcar_viaje')
            elif action == 'final':
            
                
                if viaje.marca_inicio_viaje_real:  # Verificar que el viaje comenzo
                    viaje.marca_fin_viaje_real = timezone.now()
                    viaje.estado_viaje = EstadoViaje.objects.get(nombre='Finalizado')
                    viaje.save()
                    messages.success(request, "Viaje finalizado correctamente.")
                else:
                    messages.error(request, "Debes iniciar el viaje antes de finalizarlo.")
                return redirect('marcar_viaje')

        except (Chofer.DoesNotExist, Viaje.DoesNotExist, EstadoViaje.DoesNotExist):
            pass

        return redirect('marcar_viaje')
    
    
class ViajeListView(ListView):
    model = Viaje
    template_name = 'viaje/viaje.html'
    context_object_name = 'viajes'

    def get_queryset(self):
        return Viaje.objects.all().select_related(
            'chofer', 
            'bus', 
            'recorrido', 
            'estado_viaje'
        ).order_by('-fecha_viaje')
        
    def post(self, request, *args, **kwargs):
        if 'delete' in request.POST:  # Para eliminar un viaje
            viaje_id = request.POST.get('viaje_id')
            viaje = get_object_or_404(Viaje, id=viaje_id)  # Cambiado de Bus a Viaje
            viaje.delete()
            return HttpResponseRedirect(request.path)
        
class ViajeDetailView(DetailView):
    model = Viaje
    template_name = 'viaje/viaje_detalle.html'
    context_object_name = 'viaje'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        viaje = self.object
        return context
    
class CrearViajeView(FormView):
    template_name = 'viaje/crear_viaje.html'
    form_class = ViajeForm
    success_url = reverse_lazy('viajes')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Filtra los buses que están habilitados
        context['buses_habilitados'] = Bus.objects.filter(estado_bus__nombre='Habilitado')  
        return context

    def form_valid(self, form):
        viaje = form.save(commit=False)  # No guardamos aún en la base de datos
        viaje.estado_viaje = EstadoViaje.objects.get(nombre='Por Empezar')  # Establecer el estado predeterminado
        viaje.save()  # Ahora guardamos el viaje
        return super().form_valid(form)

class EditarViajeView(UpdateView):
    model = Viaje
    template_name = 'viaje/editar_viaje.html'
    form_class = ViajeForm
    success_url = reverse_lazy('viajes')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Filtra los buses que están habilitados
        context['buses_habilitados'] = Bus.objects.filter(estado_bus__nombre='Habilitado')  
        return context

    def form_valid(self, form):
        viaje = form.save(commit=False)  # No guardamos aún en la base de datos
        viaje.estado_viaje = EstadoViaje.objects.get(nombre='Por Empezar')  # Establecer el estado predeterminado
        viaje.save()  # Ahora guardamos el viaje
        return super().form_valid(form)


    
class BusListView(ListView):
    model = Bus
    template_name = 'bus/buses.html'  # Nombre del template que mostraría la lista de buses
    context_object_name = 'buses'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['estados'] = EstadoBus.objects.all()  # Pasar los estados de bus al template
        return context

    def post(self, request, *args, **kwargs):
        if 'delete' in request.POST:  # Para eliminar un bus
            bus_id = request.POST.get('bus_id')
            bus = get_object_or_404(Bus, id=bus_id)
            bus.delete()
            return HttpResponseRedirect(request.path)  # Redirigir a la misma página después de eliminar

        if 'change_status' in request.POST:  # Para cambiar el estado del bus
            bus_id = request.POST.get('bus_id')
            estado_bus_id = request.POST.get('estado_bus')
            bus = get_object_or_404(Bus, id=bus_id)
            estado_bus = EstadoBus.objects.get(id=estado_bus_id)
            bus.estado_bus = estado_bus
            bus.save()
            return HttpResponseRedirect(request.path)
        
class CrearBusView(CreateView):
    model = Bus
    form_class = BusForm
    template_name = 'bus/crear_bus.html'
    success_url = reverse_lazy('buses')

    def form_valid(self, form):
        bus = form.save(commit=False)
        estado_habilitado = EstadoBus.objects.get(nombre='Habilitado')
        bus.estado_bus = estado_habilitado
        messages.success(self.request, 'Bus creado con éxito')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Por favor corrige los errores en el formulario.')
        return super().form_invalid(form)
    
    
class BusController:
    @staticmethod
    def crear_bus(data):
        print("Datos recibidos para crear bus:", data)
        # Validar si la patente es válida
        patente = data.get('patente')
        if Bus.objects.filter(patente=patente).exists():
            raise ValueError('La patente ya existe.')

        # Validar si el número de unidad es válido
        num_unidad = data.get('num_unidad')
        if Bus.objects.filter(num_unidad=num_unidad).exists():
            raise ValueError('El número de unidad ya existe.')


        # Crear y guardar el bus
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
        
        
    
class ViajeController:
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

class ChoferLoginView(LoginView):
    template_name = 'chofer/login.html'
    form_class = LoginForm
    redirect_authenticated_user = True
    
    def form_valid(self, form):
        # Guarda el legajo (contraseña original) en la sesión antes de que se hashee
        legajo = form.cleaned_data['password']
        response = super().form_valid(form)
        self.request.session['legajo_chofer'] = legajo
        return response

    def get_success_url(self):
        return reverse_lazy('index')
    
class ChoferListView(ListView):
    model = Chofer
    template_name = 'chofer/choferes.html'  # Nombre del template que vamos a mostrar
    context_object_name = 'choferes'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = ChoferForm()  # Añadimos el formulario al contexto
        return context

    def post(self, request, *args, **kwargs):
        if 'delete' in request.POST:  # Verificamos si se solicitó eliminar un chofer
            chofer_id = request.POST.get('chofer_id')
            chofer = get_object_or_404(Chofer, id=chofer_id)
            
            try:
                user = User.objects.get(username=f"{chofer.nombre} {chofer.apellido}")
                user.delete()  # Eliminar el usuario asociado
            except User.DoesNotExist:
                messages.error(request, 'El usuario asociado no existe.')

            chofer.delete()  # Eliminar el chofer
            messages.success(request, 'Chofer eliminado exitosamente.')
            return redirect('choferes')  # Redirigimos a la misma página

        
        
        
        form = ChoferForm(request.POST)
        if form.is_valid():
            chofer = form.save()  # Guardamos el nuevo chofer
            # Crear el usuario asociado al chofer
            username = f"{chofer.nombre} {chofer.apellido}"
            password = str(chofer.legajo)  # Usar el legajo como contraseña
            user, created = User.objects.get_or_create(username=username)
            if created:
                user.set_password(password)  # Establecer la contraseña
                user.first_name = chofer.nombre
                user.last_name = chofer.apellido
                user.is_staff = True  # Dar permisos de staff
                user.save()  # Guardar el usuario
            messages.success(request, 'Chofer agregado exitosamente.')
            return redirect('choferes')  # Redirigimos a la misma página
        return self.get(request, *args, **kwargs)  

class ChoferController:
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
    


    
class ReporteViajesView(TemplateView):
    template_name = 'reporte/reporte_viajes.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        controlador = ControladorReporteViajes()
        context.update(controlador.generar_reporte())
        return context

class ControladorReporteViajes:
    def generar_reporte(self):
        fecha_actual = timezone.now().date()
        viajes = Viaje.objects.filter(fecha_viaje=fecha_actual)
        
        # Debug: imprimir cantidad de viajes encontrados
        print(f"Viajes encontrados para {fecha_actual}: {viajes.count()}")
        
        viajes_procesados = self._procesar_viajes(viajes)
        promedios = self._calcular_promedios(viajes_procesados)
        
        # Debug: imprimir viajes procesados
        print(f"Viajes procesados: {viajes_procesados}")
        
        return {
            'viajes': viajes_procesados,
            'promedios': promedios,
            'today': fecha_actual,  # Agregamos la fecha al contexto
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
            # Validaciones adicionales si son necesarias
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

class ListaAtractivosView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    template_name = 'atractivo/lista_atractivos.html'
    context_object_name = 'atractivos'

    def test_func(self):
        return self.request.user.is_superuser

    def get_queryset(self):
        return ControladorAtractivo.listar_atractivos()

    def post(self, request, *args, **kwargs):
        if 'eliminar' in request.POST:
            atractivo_id = request.POST.get('atractivo_id')
            success, message = ControladorAtractivo.eliminar_atractivo(atractivo_id)
            if success:
                messages.success(request, message)
            else:
                messages.error(request, message)
        return redirect('lista_atractivos')

class CrearAtractivoView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    template_name = 'atractivo/crear_atractivo.html'
    form_class = AtractivoForm
    success_url = reverse_lazy('lista_atractivos')

    def test_func(self):
        return self.request.user.is_superuser

    def form_valid(self, form):
        response = ControladorAtractivo.crear_atractivo(form.cleaned_data)
        if response['success']:
            messages.success(self.request, 'Atractivo creado exitosamente.')
            return HttpResponseRedirect(self.success_url)
        else:
            messages.error(self.request, response['error'])
            return self.form_invalid(form)

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

class GestionAtractivosParadaView(LoginRequiredMixin, UserPassesTestMixin, View):
    template_name = 'atractivo/gestion_atractivos_parada.html'

    def test_func(self):
        return self.request.user.is_superuser

    def get(self, request):
        context = ControladorAtractivoXParada.obtener_contexto_gestion()
        return render(request, self.template_name, context)

    def post(self, request):
        if 'agregar' in request.POST:
            form = AtractivoXParadaForm(request.POST)
            if form.is_valid():
                success, message = ControladorAtractivoXParada.agregar_atractivo_a_parada(form.cleaned_data)
                if success:
                    messages.success(request, message)
                else:
                    messages.error(request, message)
            else:
                messages.error(request, 'Por favor, corrija los errores en el formulario.')
        elif 'eliminar' in request.POST:
            asignacion_id = request.POST.get('asignacion_id')
            success, message = ControladorAtractivoXParada.eliminar_asignacion(asignacion_id)
            if success:
                messages.success(request, message)
            else:
                messages.error(request, message)
        
        return redirect('gestion_atractivos_parada')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = AtractivoXParadaForm()
        context['asignaciones'] = AtractivoXParada.objects.select_related('parada', 'atractivo').all()
        return context
