import os
from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Solicitacao, Usuario

# Limite máximo de arquivo: 25 MB
TAMANHO_MAXIMO_ANEXO_BYTES = 25 * 1024 * 1024


class LoginForm(AuthenticationForm):
    """Formulário de Login com estilização Bootstrap 5."""

    username = forms.EmailField(
        label='E-mail Institucional',
        widget=forms.EmailInput(
            attrs={
                'class': 'form-control form-control-lg',
                'placeholder': 'nome@escola.edu.br',
                'autofocus': True,
                'autocomplete': 'email',
            }
        ),
    )
    password = forms.CharField(
        label='Senha',
        widget=forms.PasswordInput(
            attrs={
                'class': 'form-control form-control-lg',
                'placeholder': '••••••••',
                'autocomplete': 'current-password',
            }
        ),
    )


class SolicitacaoForm(forms.ModelForm):
    """
    Formulário para abertura de nova solicitação de impressão com upload de PDF.
    """

    arquivo = forms.FileField(
        label='Documento para Impressão (Apenas PDF)',
        help_text='Tamanho máximo permitido: 25 MB. Aceita apenas arquivos .pdf.',
        widget=forms.ClearableFileInput(
            attrs={
                'class': 'form-control',
                'accept': 'application/pdf,.pdf',
            }
        ),
    )

    class Meta:
        model = Solicitacao
        fields = [
            'setor_turma',
            'contato',
            'quantidade_copias',
            'tipo_impressao',
            'frente_verso',
            'prazo_desejado',
            'instrucoes',
        ]
        widgets = {
            'setor_turma': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Ex: 3º Ano Informática, Coordenação Pedagógica, etc.',
                }
            ),
            'contato': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Ex: (11) 98888-7777 ou email@escola.edu.br',
                }
            ),
            'quantidade_copias': forms.NumberInput(
                attrs={
                    'class': 'form-control',
                    'min': 1,
                    'value': 1,
                }
            ),
            'tipo_impressao': forms.Select(
                attrs={
                    'class': 'form-select',
                }
            ),
            'frente_verso': forms.CheckboxInput(
                attrs={
                    'class': 'form-check-input',
                    'role': 'switch',
                }
            ),
            'prazo_desejado': forms.DateInput(
                attrs={
                    'class': 'form-control',
                    'type': 'date',
                }
            ),
            'instrucoes': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 3,
                    'placeholder': 'Ex: Grampear no canto superior esquerdo, imprimir apenas páginas 1 a 10, etc.',
                }
            ),
        }

    def clean_arquivo(self):
        arquivo = self.cleaned_data.get('arquivo')
        if not arquivo:
            raise ValidationError('É obrigatório anexar um documento para solicitação de impressão.')

        # 1. Validação de extensão
        ext = os.path.splitext(arquivo.name)[1].lower()
        if ext != '.pdf':
            raise ValidationError('Formato inválido. Apenas arquivos com extensão .pdf são aceitos nesta versão.')

        # 2. Validação do tipo de conteúdo (Content Type / MIME)
        content_type = getattr(arquivo, 'content_type', '')
        if content_type and content_type != 'application/pdf' and not content_type.startswith('application/'):
            raise ValidationError('O arquivo enviado não parece ser um documento PDF válido.')

        # 3. Validação de tamanho máximo
        if arquivo.size > TAMANHO_MAXIMO_ANEXO_BYTES:
            tamanho_mb = arquivo.size / (1024 * 1024)
            raise ValidationError(
                f'O arquivo excede o limite permitido de 25 MB (tamanho enviado: {tamanho_mb:.1f} MB).'
            )

        return arquivo

    def clean_prazo_desejado(self):
        prazo = self.cleaned_data.get('prazo_desejado')
        if prazo and prazo < timezone.now().date():
            raise ValidationError('O prazo desejado não pode ser uma data retroativa (no passado).')
        return prazo

    def clean_quantidade_copias(self):
        copias = self.cleaned_data.get('quantidade_copias')
        if not copias or copias < 1:
            raise ValidationError('A quantidade de cópias deve ser de pelo menos 1 exemplar.')
        return copias
