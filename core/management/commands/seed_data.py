from django.core.management.base import BaseCommand
from core.models import Usuario


class Command(BaseCommand):
    help = 'Cria usuários de exemplo para os 3 perfis do sistema (Administrador, Colaborador e Solicitante).'

    def handle(self, *args, **options):
        # 1. Administrador
        admin_email = 'admin@escola.edu.br'
        if not Usuario.objects.filter(email=admin_email).exists():
            Usuario.objects.create_superuser(
                email=admin_email,
                nome='Administrador do Sistema',
                password='admin123',
                perfil=Usuario.PERFIL_ADMINISTRADOR,
                setor_turma='Diretoria / TI',
                contato='admin@escola.edu.br',
            )
            self.stdout.write(self.style.SUCCESS(f'Usuário Administrador criado: {admin_email} (senha: admin123)'))
        else:
            self.stdout.write(self.style.WARNING(f'Usuário {admin_email} já existe.'))

        # 2. Colaborador
        colab_email = 'colaborador@escola.edu.br'
        if not Usuario.objects.filter(email=colab_email).exists():
            Usuario.objects.create_user(
                email=colab_email,
                nome='Operador Gráfica',
                password='colaborador123',
                perfil=Usuario.PERFIL_COLABORADOR,
                setor_turma='Setor de Impressos',
                contato='grafica@escola.edu.br',
            )
            self.stdout.write(self.style.SUCCESS(f'Usuário Colaborador criado: {colab_email} (senha: colaborador123)'))
        else:
            self.stdout.write(self.style.WARNING(f'Usuário {colab_email} já existe.'))

        # 3. Solicitante
        solic_email = 'solicitante@escola.edu.br'
        if not Usuario.objects.filter(email=solic_email).exists():
            Usuario.objects.create_user(
                email=solic_email,
                nome='João Professor',
                password='solicitante123',
                perfil=Usuario.PERFIL_SOLICITANTE,
                setor_turma='Departamento de Matemática',
                contato='joao.prof@escola.edu.br',
            )
            self.stdout.write(self.style.SUCCESS(f'Usuário Solicitante criado: {solic_email} (senha: solicitante123)'))
        else:
            self.stdout.write(self.style.WARNING(f'Usuário {solic_email} já existe.'))
