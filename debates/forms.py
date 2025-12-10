from django import forms
from .models import Debate, Participante

class DebateForm(forms.ModelForm):

    grupo_a_nome = forms.CharField(max_length=100, label='Nome do grupo A', initial = 'A favor')
    participantes_a = forms.CharField(
        label='Nomes dos Participantes do Grupo A (Separados por vírgula)',
        widget=forms.Textarea
    )

    grupo_b_nome = forms.CharField(max_length=100, label='Nome do grupo B', initial = 'Contra')
    participantes_b = forms.CharField(
        label='Nomes dos Participantes do Grupo B (Separados por vírgula)',
        widget=forms.Textarea
    )

    class Meta:
        model = Debate
        fields = ['titulo', 'tempo_total_segundos']
        widgets = {
            'tempo_total_segundos': forms.NumberInput(attrs={'placeholder': 'segundos'})
        }

class ParticipanteForm(forms.ModelForm):
    class Meta:
        model = Participante
        fields = ['grupo_nome', 'participante_nome']