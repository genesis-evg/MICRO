from django.db import models


STATUS_CHOICES = [
    ('CONFIGURADO', 'Configurado'),
    ('EM_ANDAMENTO', 'Em Andamento'),
    ('PAUSADO', 'Pausado'),
    ('ENCERRADO', 'Encerrado'),
]


class Participante(models.Model):
    grupo_nome = models.CharField(max_length=100)
    participante_nome = models.CharField(max_length=100)
   

    def __str__(self):
        return f"{self.participante_nome} ({self.grupo_nome})"
        

class Debate(models.Model):
    titulo = models.CharField(max_length=200)
    tempo_total_segundos = models.IntegerField()

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='CONFIGURADO'
    )
    participante_ativo = models.ForeignKey(
        'Participante',
        on_delete=models.SET_NULL,
        null = True,
        blank=True,
        related_name='debates_ativos'
    )

    data_criacao = models.DateTimeField(auto_now_add=True) 

    def __str__(self):
        return self.titulo
    

Participante.add_to_class('debate', models.ForeignKey(Debate, on_delete=models.CASCADE, null=True)) 


class Tempo(models.Model):
    participante = models.OneToOneField(
        Participante,
        on_delete=models.CASCADE,
        primary_key=True
    )
    tempo_acumulado_ms = models.BigIntegerField(default=0) 

    def __str__(self):
        return f"Tempo de {self.participante.participante_nome}"