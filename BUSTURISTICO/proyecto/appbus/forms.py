from django import forms
from .models import *
from datetime import date
from django.contrib.auth.forms import AuthenticationForm

class LoginForm(AuthenticationForm):
    username = forms.CharField(label="Nombre", max_length=150, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Usuario'}))
    password = forms.CharField(label="Contraseña (Legajo)", widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Contraseña'}))

class RecorridoForm(forms.ModelForm):
    class Meta:
        model = Recorrido
        fields = ['nombre', 'codigo_alfanumerico', 'hora_inicio', 'hora_fin', 'frecuencia']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre del recorrido'
            }),
            'codigo_alfanumerico': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: #R1'
            }),
            'hora_inicio': forms.TimeInput(attrs={
                'class': 'form-control',
                'type': 'time'
            }),
            'hora_fin': forms.TimeInput(attrs={
                'class': 'form-control',
                'type': 'time'
            }),
        }
        labels = {
            'nombre': 'Nombre del Recorrido',
            'codigo_alfanumerico': 'Código Alfanumérico',
            'hora_inicio': 'Hora de Inicio',
            'hora_fin': 'Hora de Fin',
            'frecuencia': 'Frecuencia'
        }

    def clean(self):
        cleaned_data = super().clean()
        hora_inicio = cleaned_data.get('hora_inicio')
        hora_fin = cleaned_data.get('hora_fin')
        frecuencia = cleaned_data.get('frecuencia')
        codigo = cleaned_data.get('codigo_alfanumerico')

        if codigo and not codigo.startswith('#'):
            raise forms.ValidationError('El código debe comenzar con #')

        if hora_inicio and hora_fin and hora_fin <= hora_inicio:
            raise forms.ValidationError('La hora de fin debe ser posterior a la hora de inicio')

        if frecuencia:
            minutos = frecuencia.hour * 60 + frecuencia.minute
            
            if minutos < 5 or minutos > 60:
                raise forms.ValidationError('La frecuencia debe estar entre 5 y 60 minutos')

        return cleaned_data
    
    
class ViajeForm(forms.ModelForm):
    class Meta:
        model = Viaje
        fields = ('chofer', 'bus', 'recorrido', 'horario_inicio_programado', 'horario_fin_programado', 'fecha_viaje')
        
        widgets = {
            'fecha_viaje': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }
        
    def __init__(self, *args, **kwargs):
        super(ViajeForm, self).__init__(*args, **kwargs)
        # Filtrar los buses habilitados
        self.fields['bus'].queryset = Bus.objects.filter(estado_bus__nombre='Habilitado')
    def clean_fecha_viaje(self):
        fecha_viaje = self.cleaned_data.get('fecha_viaje')
        if fecha_viaje < date.today():
            raise forms.ValidationError("La fecha de viaje no puede ser anterior a la fecha actual.")
        return fecha_viaje
        
        
class BusForm(forms.ModelForm):
    class Meta:
        model = Bus
        fields = ['patente', 'num_unidad', 'fecha_compra']  # Removemos estado_bus del formulario
        widgets = {
            'patente': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ingrese la patente'}),
            'num_unidad': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Ingrese el número de unidad'}),
            'fecha_compra': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }

    def clean_num_unidad(self):
        num_unidad = self.cleaned_data.get('num_unidad')
        if num_unidad <= 0:
            raise forms.ValidationError("El número de unidad debe ser positivo.")
        return num_unidad
    
    def clean_patente(self):
        if Bus.objects.filter(patente=self.patente).exclude(id=self.id).exists():
            raise ValidationError('La patente ya existe.')

    def clean_fecha_compra(self):
        fecha_compra = self.cleaned_data.get('fecha_compra')
        if fecha_compra > date.today():
            raise forms.ValidationError("La fecha de compra no puede ser posterior a la fecha actual.")
        return fecha_compra
    
class ChoferForm(forms.ModelForm):
    class Meta:
        model = Chofer
        fields = ['nombre', 'apellido', 'legajo']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ingrese el nombre'}),
            'apellido': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ingrese el apellido'}),
            'legajo': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Ingrese el legajo'}),
        }
        
        
class OrdenParadaForm(forms.ModelForm):
    class Meta:
        model = OrdenParada
        fields = ['parada', 'recorrido', 'asignacion_paradas']
        widgets = {
            'parada': forms.Select(attrs={'class': 'form-select'}),
            'recorrido': forms.Select(attrs={'class': 'form-select'}),
            'asignacion_paradas': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'placeholder': 'Orden de la parada'
            })
        }
        labels = {
            'parada': 'Seleccionar Parada',
            'recorrido': 'Seleccionar Recorrido',
            'asignacion_paradas': 'Orden de la Parada'
        }
        
class ParadaForm(forms.ModelForm):
    class Meta:
        model = Parada
        fields = ['nombre', 'direccion', 'descripcion', 'imagen', 'tipo_parada']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'direccion': forms.TextInput(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control'}),
            'imagen': forms.FileInput(attrs={'class': 'form-control'}),
            'tipo_parada': forms.Select(attrs={'class': 'form-control'}),
        }
        
class AtractivoForm(forms.ModelForm):
    class Meta:
        model = Atractivo
        fields = ['nombre', 'descripcion', 'calificacion']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'calificacion': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 5, 'step': '0.5'}),
        }

    def clean_nombre(self):
        nombre = self.cleaned_data.get('nombre')
        if len(nombre.strip()) < 3:
            raise ValidationError('El nombre debe tener al menos 3 caracteres.')
        
        # Verificar si existe un atractivo con el mismo nombre (ignorando mayúsculas/minúsculas)
        if Atractivo.objects.filter(nombre__iexact=nombre).exists():
            raise ValidationError('Ya existe un atractivo con este nombre (sin importar mayúsculas/minúsculas).')
        
        return nombre

    def clean_descripcion(self):
        descripcion = self.cleaned_data.get('descripcion')
        if len(descripcion.strip()) < 10:
            raise ValidationError('La descripción debe tener al menos 10 caracteres.')
        return descripcion

    def clean_calificacion(self):
        calificacion = self.cleaned_data.get('calificacion')
        if calificacion < 0 or calificacion > 5:
            raise ValidationError('La calificación debe estar entre 0 y 5.')
        return calificacion

class AtractivoXParadaForm(forms.ModelForm):
    class Meta:
        model = AtractivoXParada
        fields = ['parada', 'atractivo']
        widgets = {
            'parada': forms.Select(attrs={'class': 'form-control'}),
            'atractivo': forms.Select(attrs={'class': 'form-control'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        parada = cleaned_data.get('parada')
        atractivo = cleaned_data.get('atractivo')

        if parada and atractivo:
            # Verificar si ya existe esta combinación
            if AtractivoXParada.objects.filter(parada=parada, atractivo=atractivo).exists():
                raise ValidationError('Este atractivo ya está asignado a esta parada.')
        
        return cleaned_data
