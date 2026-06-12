from django.db import models


class Rol(models.Model):
    id_rol = models.AutoField(primary_key=True, db_column="id_rol")
    rol = models.CharField(max_length=255, unique=True, db_column="rol")

    class Meta:
        db_table = "rol"

    def __str__(self) -> str:
        return self.rol


class Usuario(models.Model):
    id_usuario = models.AutoField(primary_key=True, db_column="id_usuario")
    nombre = models.CharField(max_length=255)
    apellido = models.CharField(max_length=255)
    email = models.CharField(max_length=255)
    telefono = models.CharField(max_length=255)
    contrasena = models.CharField(max_length=255)
    direccion = models.CharField(max_length=255)
    created_at = models.DateTimeField(null=True, blank=True, db_column="created_at")
    updated_at = models.DateTimeField(null=True, blank=True, db_column="updated_at")
    reset_token = models.CharField(max_length=255, null=True, blank=True, db_column="reset_token")
    foto_perfil = models.CharField(max_length=255, null=True, blank=True, db_column="foto_perfil")
    activo = models.IntegerField(default=1, db_column="activo")
    rol = models.ForeignKey(Rol, on_delete=models.PROTECT, db_column="id_rol")

    class Meta:
        db_table = "usuarios"

    def __str__(self) -> str:
        return f"{self.nombre} {self.apellido} ({self.email})"


class Prestador(models.Model):
    id_prestador = models.AutoField(primary_key=True, db_column="id_prestador")
    usuario = models.OneToOneField(Usuario, on_delete=models.CASCADE, db_column="id_usuario")
    descripcion = models.TextField(null=True, blank=True, db_column="descripcion")
    dias_atencion = models.CharField(max_length=255, null=True, blank=True, db_column="dias_atencion")
    horario_atencion = models.CharField(max_length=255, null=True, blank=True, db_column="horario_atencion")

    class Meta:
        db_table = "prestadores"

    def __str__(self) -> str:
        return f"Prestador {self.id_prestador}"


class Categoria(models.Model):
    id_categoria = models.AutoField(primary_key=True, db_column="id_categoria")
    nombre = models.CharField(max_length=255)
    activo = models.IntegerField(default=1, db_column="activo")

    class Meta:
        db_table = "categoria"

    def __str__(self) -> str:
        return self.nombre


class PrestadorCategoria(models.Model):
    prestador = models.ForeignKey(Prestador, on_delete=models.CASCADE, db_column="id_prestador")
    categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE, db_column="id_categoria")

    class Meta:
        db_table = "prestador_categoria"
        unique_together = (("prestador", "categoria"),)


Prestador.add_to_class(
    "categorias",
    models.ManyToManyField(Categoria, through=PrestadorCategoria, related_name="prestadores"),
)


class Servicio(models.Model):
    id_servicio = models.AutoField(primary_key=True, db_column="id_servicio")
    nombre = models.CharField(max_length=255)
    descripcion = models.TextField()
    precio_min = models.FloatField()
    precio_max = models.FloatField()
    activo = models.IntegerField(default=1, db_column="activo")
    prestador = models.ForeignKey(Prestador, on_delete=models.SET_NULL, null=True, db_column="id_prestador")
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT, db_column="id_categoria")

    class Meta:
        db_table = "servicio"

    def __str__(self) -> str:
        return self.nombre


class Contratacion(models.Model):
    id_contratacion = models.AutoField(primary_key=True, db_column="id_contratacion")
    fecha = models.DateField(db_column="fecha_programada", null=True, blank=True)
    fecha_solicitud = models.DateField(db_column="fecha_solicitud", null=True, blank=True)
    estado = models.CharField(max_length=255, db_column="estado_contratacion")
    observacion = models.TextField(null=True, blank=True, db_column="observacion")
    prestador = models.ForeignKey(Prestador, on_delete=models.PROTECT, db_column="id_prestador")
    servicio = models.ForeignKey(Servicio, on_delete=models.PROTECT, db_column="id_servicio")

    class Meta:
        db_table = "contratacion"


class MetodoPago(models.Model):
    id_metodo_pago = models.AutoField(primary_key=True, db_column="id_metodo_pago")
    forma_pago = models.CharField(max_length=255, db_column="forma_pago")

    class Meta:
        db_table = "metodos_pago"

    def __str__(self) -> str:
        return self.forma_pago


class Pago(models.Model):
    id_pago = models.AutoField(primary_key=True, db_column="id_pago")
    monto = models.FloatField()
    fecha = models.DateField(db_column="fecha_pago")
    contratacion = models.ForeignKey(Contratacion, on_delete=models.PROTECT, db_column="id_contratacion")
    metodo = models.ForeignKey(MetodoPago, on_delete=models.PROTECT, db_column="id_metodo_pago")

    class Meta:
        db_table = "pago"


class Calificacion(models.Model):
    id_calificacion = models.AutoField(primary_key=True, db_column="id_calificacion")
    puntuacion = models.IntegerField()
    comentario = models.TextField()
    contratacion = models.ForeignKey(Contratacion, on_delete=models.PROTECT, db_column="id_contratacion")
    prestador = models.ForeignKey(Prestador, on_delete=models.PROTECT, db_column="id_prestador")

    class Meta:
        db_table = "calificacion"


class ClienteContratacion(models.Model):
    cliente = models.ForeignKey(Usuario, on_delete=models.CASCADE, db_column="id_cliente")
    contratacion = models.OneToOneField(
        Contratacion,
        on_delete=models.CASCADE,
        db_column="id_contratacion",
        primary_key=True,
    )

    class Meta:
        db_table = "cliente_contratacion"
        unique_together = (("cliente", "contratacion"),)


class ClienteCalificacion(models.Model):
    cliente = models.ForeignKey(Usuario, on_delete=models.CASCADE, db_column="id_cliente")
    calificacion = models.OneToOneField(
        Calificacion,
        on_delete=models.CASCADE,
        db_column="id_calificacion",
        primary_key=True,
    )

    class Meta:
        db_table = "cliente_calificacion"
        unique_together = (("cliente", "calificacion"),)


class PasswordResetToken(models.Model):
    id = models.AutoField(primary_key=True)
    token = models.CharField(max_length=255, unique=True)
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, db_column="usuario_id")
    expiration = models.DateTimeField()

    class Meta:
        db_table = "password_reset_token"

    def is_expired(self) -> bool:
        from django.utils import timezone

        return self.expiration is not None and self.expiration <= timezone.now()
