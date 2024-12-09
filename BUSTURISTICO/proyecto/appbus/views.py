from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import TemplateView, ListView, DetailView, View, CreateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic.edit import FormView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib import messages
from django.http import HttpResponseRedirect, HttpResponseForbidden, JsonResponse
from django.utils import timezone
from django.contrib.auth.views import LoginView
from django.contrib.auth.models import User
from django.utils.timezone import make_aware, now
from django.core.exceptions import ValidationError
from datetime import datetime
from .forms import *
from .models import *
from django.http import HttpResponse
from .handlers import *

class IndexView(TemplateView):
    template_name = 'index.html'
    
class BaseView(TemplateView):
    template_name = 'base/base.html'
    
class RegistroUsuarioView(FormView):
    template_name = 'user/registro.html' 
    form_class = RegistroUsuarioForm 
    success_url = reverse_lazy('login')  

    def form_valid(self, form):
        form.save()  
        messages.success(self.request, "¡Cuenta creada exitosamente! Ahora puedes iniciar sesión.")
        return redirect('login')

class ListaAnotadosView(ListView):
    model = Viaje
    template_name = 'viaje/lista_anotados.html'
    context_object_name = 'viajes'

    def get_queryset(self):
        # Usamos prefetch_related para evitar múltiples consultas
        return Viaje.objects.prefetch_related('usuarios_anotados', 'bus', 'chofer').all() 

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['anotados'] = [
            (usuario, viaje) 
            for viaje in context['viajes'] 
            for usuario in viaje.usuarios_anotados.all()
        ]
        return context

class ParadaDetailView(DetailView):
    model = Parada
    template_name = 'parada/parada.html'
    context_object_name = 'parada'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        parada = self.object  
        atractivos = ControladorParada.obtener_atractivos_por_parada(parada)  
        
        context['atractivos'] = atractivos
        return context
    

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
        return Parada.objects.all().order_by('nombre')

    def post(self, request, *args, **kwargs):
        if 'eliminar' in request.POST:
            parada_id = request.POST.get('parada_id')
            try:
                parada = Parada.objects.get(id=parada_id)
                nombre_parada = parada.nombre
                parada.delete()
                messages.success(request, f'La parada "{nombre_parada}" ha sido eliminada.')
            except Parada.DoesNotExist:
                messages.error(request, 'La parada no existe.')
            except Exception as e:
                messages.error(request, f'Error al eliminar la parada: {str(e)}')
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
        try:
            if Parada.objects.filter(nombre__iexact=form.cleaned_data['nombre']).exists():
                raise ValidationError('Ya existe una parada con este nombre.')
            
            if Parada.objects.filter(direccion__iexact=form.cleaned_data['direccion']).exists():
                raise ValidationError('Ya existe una parada en esta dirección.')

            if not form.cleaned_data['nombre'].strip():
                raise ValidationError('El nombre de la parada no puede estar vacío.')

            if not form.cleaned_data['direccion'].strip():
                raise ValidationError('La dirección de la parada no puede estar vacía.')

            if len(form.cleaned_data['descripcion'].strip()) < 10:
                raise ValidationError('La descripción debe tener al menos 10 caracteres.')

            if not form.cleaned_data.get('tipo_parada'):
                raise ValidationError('Debe seleccionar un tipo de parada.')

            parada = form.save()
            messages.success(self.request, 'Parada creada exitosamente.')
            return HttpResponseRedirect(self.success_url)
        except ValidationError as e:
            messages.error(self.request, str(e))
            return self.form_invalid(form)

class GestionParadaRecorridoView(LoginRequiredMixin, UserPassesTestMixin, View):
    template_name = 'recorrido/gestion_paradas.html'
    
    def test_func(self):
        return self.request.user.is_superuser

    def get(self, request):
        context = {
            'form': OrdenParadaForm(),
            'paradas': OrdenParada.objects.all().select_related('parada', 'recorrido').order_by('recorrido', 'asignacion_paradas')
        }
        return render(request, self.template_name, context)

    def post(self, request):
        if 'agregar' in request.POST:
            form = OrdenParadaForm(request.POST)
            if form.is_valid():
                try:
                    if OrdenParada.objects.filter(
                        recorrido=form.cleaned_data['recorrido'], 
                        asignacion_paradas=form.cleaned_data['asignacion_paradas']
                    ).exists():
                        raise ValidationError('Ya existe una parada con ese orden en este recorrido')
                    orden_parada = form.save()
                    messages.success(request, 'Parada agregada exitosamente al recorrido')
                except ValidationError as e:
                    messages.error(request, str(e))
            else:
                messages.error(request, 'Por favor, corrija los errores en el formulario')
        elif 'eliminar' in request.POST:
            orden_parada_id = request.POST.get('orden_parada_id')
            try:
                orden_parada = OrdenParada.objects.get(id=orden_parada_id)
                orden_parada.delete()
                messages.success(request, 'Parada eliminada exitosamente del recorrido')
            except OrdenParada.DoesNotExist:
                messages.error(request, 'Parada no encontrada')
            except Exception as e:
                messages.error(request, str(e))
        return redirect('gestion_paradas')

class RecorridoDetailView(DetailView):
    model = Recorrido
    template_name = 'recorrido/recorrido.html'
    context_object_name = 'recorrido'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        recorrido = self.object
        paradas = OrdenParada.objects.filter(recorrido=recorrido).select_related('parada').order_by('asignacion_paradas')
        
        paradas_procesadas = []
        for orden in paradas:
            parada_info = {
                'asignacion_paradas': orden.asignacion_paradas,
                'parada': orden.parada,
                'color': '#800080' if orden.parada.tipo_parada.nombre_tipo_parada == 'Parada Compartida' else recorrido.codigo_alfanumerico
            }
            paradas_procesadas.append(parada_info)
            
        context['paradas'] = paradas_procesadas
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

class NuevoRecorridoView(FormView):
    template_name = 'recorrido/nuevorecorrido.html'
    form_class = RecorridoForm
    success_url = reverse_lazy('recorridos')

    def form_valid(self, form):
        try:
            data = form.cleaned_data
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
            messages.success(self.request, 'Recorrido creado exitosamente.')
            return super().form_valid(form)
        except ValidationError as e:
            messages.error(self.request, str(e))
            return self.form_invalid(form)

class MarcarViajeView(LoginRequiredMixin, TemplateView):
    template_name = 'chofer/marcar_viaje.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
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
                    viaje.estado_viaje = EstadoViaje.objects.get(nombre='En Curso')
                    viaje.save()
                else:
                    messages.error(request, "No puedes iniciar el viaje antes de la fecha programada.")
                return redirect('marcar_viaje')
            elif action == 'final':
                if viaje.marca_inicio_viaje_real:
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
        if 'delete' in request.POST:
            viaje_id = request.POST.get('viaje_id')
            viaje = get_object_or_404(Viaje, id=viaje_id)
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
        context['buses_habilitados'] = Bus.objects.filter(estado_bus__nombre='Habilitado')  
        return context

    def form_valid(self, form):
        viaje = form.save(commit=False)
        viaje.estado_viaje = EstadoViaje.objects.get(nombre='Por Empezar')
        viaje.save()
        return super().form_valid(form)

class EditarViajeView(UpdateView):
    model = Viaje
    template_name = 'viaje/editar_viaje.html'
    form_class = ViajeForm
    success_url = reverse_lazy('viajes')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['buses_habilitados'] = Bus.objects.filter(estado_bus__nombre='Habilitado')  
        return context

    def form_valid(self, form):
        viaje = form.save(commit=False)
        viaje.estado_viaje = EstadoViaje.objects.get(nombre='Por Empezar')
        viaje.save()
        return super().form_valid(form)

class Viajedisponibles(View):
    def get(self, request, *args, **kwargs):
        viajes = Viaje.objects.filter(fecha_viaje__gt=now().date()).order_by('fecha_viaje')
        return render(request, 'viaje/viajes_disponibles.html', {'viajes': viajes})

    def post(self, request, *args, **kwargs):
        viaje_id = kwargs.get('viaje_id')  # Obtener el ID desde los parámetros de la URL
        print(f"POST recibido con viaje_id: {viaje_id}")  # Verifica el ID en los logs

        if not viaje_id:
            messages.error(request, "No se especificó el ID del viaje.")
            return redirect('viajes_disponibles')

        viaje = get_object_or_404(Viaje, id=viaje_id)
        print(f"Detalles del viaje: {viaje.recorrido}, {viaje.fecha_viaje}, {viaje.estado_viaje}")

        if viaje.usuarios_anotados.count() >= viaje.bus.capacidad_maxima:
            messages.error(request, f"El viaje '{viaje.recorrido}' ya alcanzó su capacidad máxima.")
            return redirect('viajes_disponibles')

        if now().date() > viaje.fecha_viaje:
            messages.error(request, f"El viaje '{viaje.recorrido}' ya comenzó. No puedes anotarte.")
            return redirect('viajes_disponibles')

        if request.user in viaje.usuarios_anotados.all():
            messages.info(request, f"Ya estás anotado en el viaje '{viaje.recorrido}'.")
        else:
            viaje.usuarios_anotados.add(request.user)
            messages.success(request, f"Te has anotado exitosamente en el viaje '{viaje.recorrido}'.")

        return redirect('viajes_disponibles')
    
class BusListView(ListView):
    model = Bus
    template_name = 'bus/buses.html'
    context_object_name = 'buses'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['estados'] = EstadoBus.objects.all()
        return context

    def post(self, request, *args, **kwargs):
        if 'delete' in request.POST:
            bus_id = request.POST.get('bus_id')
            bus = get_object_or_404(Bus, id=bus_id)
            bus.delete()
            return HttpResponseRedirect(request.path)

        if 'change_status' in request.POST:
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

class ChoferLoginView(LoginView):
    template_name = 'chofer/login.html'
    form_class = LoginForm
    redirect_authenticated_user = True
    
    def form_valid(self, form):
        legajo = form.cleaned_data['password']
        response = super().form_valid(form)
        self.request.session['legajo_chofer'] = legajo
        return response

    def get_success_url(self):
        return reverse_lazy('index')
    
class ChoferListView(ListView):
    model = Chofer
    template_name = 'chofer/choferes.html'
    context_object_name = 'choferes'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = ChoferForm()
        return context

    def post(self, request, *args, **kwargs):
        if 'delete' in request.POST:
            chofer_id = request.POST.get('chofer_id')
            chofer = get_object_or_404(Chofer, id=chofer_id)
            
            try:
                user = User.objects.get(username=f"{chofer.nombre} {chofer.apellido}")
                user.delete()
            except User.DoesNotExist:
                messages.error(request, 'El usuario asociado no existe.')

            chofer.delete()
            messages.success(request, 'Chofer eliminado exitosamente.')
            return redirect('choferes')

        form = ChoferForm(request.POST)
        if form.is_valid():
            chofer = form.save()
            username = f"{chofer.nombre} {chofer.apellido}"
            password = str(chofer.legajo)
            user, created = User.objects.get_or_create(username=username)
            if created:
                user.set_password(password)
                user.first_name = chofer.nombre
                user.last_name = chofer.apellido
                user.is_staff = True
                user.save()
            messages.success(request, 'Chofer agregado exitosamente.')
            return redirect('choferes')
        return self.get(request, *args, **kwargs)

class ReporteViajesView(TemplateView):
    template_name = 'reporte/reporte_viajes.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        fecha_actual = timezone.now().date()
        viajes = Viaje.objects.filter(fecha_viaje=fecha_actual)
        
        print(f"Viajes encontrados para {fecha_actual}: {viajes.count()}")
        
        viajes_procesados = []
        for viaje in viajes:
            if viaje.marca_inicio_viaje_real and viaje.marca_fin_viaje_real:
                duracion = (viaje.marca_fin_viaje_real - viaje.marca_inicio_viaje_real).total_seconds() / 60
                horario_inicio_programado_dt = timezone.make_aware(datetime.combine(viaje.fecha_viaje, viaje.horario_inicio_programado))
                demora = (viaje.marca_inicio_viaje_real - horario_inicio_programado_dt).total_seconds() / 60
            else:
                duracion = None
                demora = None

            viajes_procesados.append({
                'viaje': viaje,
                'duracion': duracion,
                'demora': demora
            })
        
        duraciones = [v['duracion'] for v in viajes_procesados if v['duracion'] is not None]
        demoras = [v['demora'] for v in viajes_procesados if v['demora'] is not None]

        duracion_promedio = sum(duraciones) / len(duraciones) if duraciones else None
        demora_promedio = sum(demoras) / len(demoras) if demoras else None

        context.update({
            'viajes': viajes_procesados,
            'promedios': {
                'duracion_promedio': duracion_promedio,
                'demora_promedio': demora_promedio,
            },
            'today': fecha_actual,
        })
        return context

class ListaAtractivosView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    template_name = 'atractivo/lista_atractivos.html'
    context_object_name = 'atractivos'

    def test_func(self):
        return self.request.user.is_superuser

    def get_queryset(self):
        return Atractivo.objects.all().order_by('nombre')

    def post(self, request, *args, **kwargs):
        if 'eliminar' in request.POST:
            atractivo_id = request.POST.get('atractivo_id')
            try:
                atractivo = Atractivo.objects.get(id=atractivo_id)
                nombre = atractivo.nombre
                atractivo.delete()
                messages.success(request, f'El atractivo "{nombre}" ha sido eliminado.')
            except Atractivo.DoesNotExist:
                messages.error(request, 'El atractivo no existe.')
            except Exception as e:
                messages.error(request, f'Error al eliminar el atractivo: {str(e)}')
        return redirect('lista_atractivos')

class CrearAtractivoView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    template_name = 'atractivo/crear_atractivo.html'
    form_class = AtractivoForm
    success_url = reverse_lazy('lista_atractivos')

    def test_func(self):
        return self.request.user.is_superuser

    def form_valid(self, form):
        try:
            if Atractivo.objects.filter(nombre__iexact=form.cleaned_data['nombre']).exists():
                raise ValidationError('Ya existe un atractivo con este nombre.')

            atractivo = form.save()
            messages.success(self.request, 'Atractivo creado exitosamente.')
            return HttpResponseRedirect(self.success_url)
        except ValidationError as e:
            messages.error(self.request, str(e))
            return self.form_invalid(form)

class GestionAtractivosParadaView(LoginRequiredMixin, UserPassesTestMixin, View):
    template_name = 'atractivo/gestion_atractivos_parada.html'

    def test_func(self):
        return self.request.user.is_superuser

    def get(self, request):
        context = {
            'form': AtractivoXParadaForm(),
            'asignaciones': AtractivoXParada.objects.all().select_related('parada', 'atractivo')
        }
        return render(request, self.template_name, context)

    def post(self, request):
        if 'agregar' in request.POST:
            form = AtractivoXParadaForm(request.POST)
            if form.is_valid():
                try:
                    asignacion = form.save()
                    messages.success(request, 'Atractivo asignado exitosamente a la parada.')
                except Exception as e:
                    messages.error(request, str(e))
            else:
                messages.error(request, 'Por favor, corrija los errores en el formulario.')
        elif 'eliminar' in request.POST:
            asignacion_id = request.POST.get('asignacion_id')
            try:
                asignacion = AtractivoXParada.objects.get(id=asignacion_id)
                asignacion.delete()
                messages.success(request, 'Asignación eliminada exitosamente.')
            except AtractivoXParada.DoesNotExist:
                messages.error(request, 'La asignación no existe.')
            except Exception as e:
                messages.error(request, str(e))
        
        return redirect('gestion_atractivos_parada')
