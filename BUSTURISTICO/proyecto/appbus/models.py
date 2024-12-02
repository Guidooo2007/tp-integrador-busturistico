

from django.db import models
from django.core.exceptions import ValidationError

class EstadoBus(models.Model):
    nombre = models.CharField(max_length=50)
    descripcion = models.TextField()

    def __str__(self):
        return self.nombre

class EstadoViaje(models.Model):
    nombre = models.CharField(max_length=50)
    descripcion = models.TextField()

    def __str__(self):
        return self.nombre
    
    

class Recorrido(models.Model):
    nombre = models.CharField(max_length=100)
    codigo_alfanumerico = models.CharField(max_length=10)
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()
    frecuencia = models.TimeField()

    def __str__(self):
        return self.nombre

class Parada(models.Model):
    nombre = models.CharField(max_length=100)
    direccion = models.CharField(max_length=150)
    descripcion = models.TextField()
    imagen = models.ImageField(upload_to="media/images/") 
    tipo_parada = models.ForeignKey('TipoParada', on_delete=models.CASCADE)

    def __str__(self):
        return self.nombre

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

class TipoParada(models.Model):
    nombre_tipo_parada = models.CharField(max_length=100)
    descripcion = models.TextField()

    def __str__(self):
        return self.nombre_tipo_parada

class Atractivo(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField()
    calificacion = models.FloatField()
 
    def __str__(self):
        return self.nombre

class AtractivoXParada(models.Model):
    parada = models.ForeignKey(Parada, on_delete=models.CASCADE)
    atractivo = models.ForeignKey(Atractivo, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('parada', 'atractivo')

class OrdenParada(models.Model):
    parada = models.ForeignKey(Parada, on_delete=models.CASCADE)
    recorrido = models.ForeignKey(Recorrido, on_delete=models.CASCADE)
    asignacion_paradas = models.IntegerField()

    class Meta:
        unique_together = ('parada', 'recorrido')

class Bus(models.Model):
    patente = models.CharField(max_length=10, unique=True)
    num_unidad = models.IntegerField(unique=True)
    fecha_compra = models.DateField()
    estado_bus = models.ForeignKey(EstadoBus, on_delete=models.CASCADE)
    
    def clean(self):
        # Validar si la patente ya existe
        if Bus.objects.filter(patente=self.patente).exclude(id=self.id).exists():
            raise ValidationError('La patente ya existe.')

        # Validar si el número de unidad ya existe
        if Bus.objects.filter(num_unidad=self.num_unidad).exclude(id=self.id).exists():
            raise ValidationError('El número de unidad ya existe.')


    def save(self, *args, **kwargs):
        self.full_clean()  # Llama a clean() antes de guardar
        super().save(*args, **kwargs)


    def __str__(self):
        return f'Unidad {self.num_unidad} - {self.patente}'

class Chofer(models.Model):
    legajo = models.IntegerField(unique=True)
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)

    def __str__(self):
        return f'{self.nombre}'  + ' ' + f'{self.apellido}'

class Viaje(models.Model):
    chofer = models.ForeignKey(Chofer, on_delete=models.CASCADE)
    bus = models.ForeignKey(Bus, on_delete=models.CASCADE)
    recorrido = models.ForeignKey(Recorrido, on_delete=models.CASCADE)
    estado_viaje = models.ForeignKey(EstadoViaje, on_delete=models.CASCADE)
    horario_inicio_programado = models.TimeField()
    horario_fin_programado = models.TimeField()
    fecha_viaje = models.DateField()
    marca_inicio_viaje_real = models.DateTimeField(null=True, blank=True)
    marca_fin_viaje_real = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f'Viaje {self.id} - {self.recorrido.nombre}'


