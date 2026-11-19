import json
import shutil
import zipfile
from pathlib import Path
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Restaura o sistema (banco de dados e anexos) a partir de um arquivo zip de backup.'

    def add_arguments(self, parser):
        parser.add_argument(
            'arquivo',
            type=str,
            help='Caminho para o arquivo .zip de backup.',
        )
        parser.add_argument(
            '--confirmar',
            action='store_true',
            help='Confirma a restauração sobrescrevendo dados atuais.',
        )

    def handle(self, *args, **options):
        backup_path = Path(options['arquivo'])
        if not backup_path.exists():
            raise CommandError(f"Arquivo de backup não encontrado: {backup_path}")

        if not options['confirmar']:
            self.stdout.write(
                self.style.WARNING(
                    "ATENÇÃO: A restauração substituirá os dados atuais do banco e anexos.\n"
                    "Para prosseguir de fato, execute com o parâmetro: --confirmar"
                )
            )

        with zipfile.ZipFile(backup_path, 'r') as zip_file:
            # 1. Valida manifesto
            if 'manifesto.json' not in zip_file.namelist():
                raise CommandError("Arquivo de backup inválido: 'manifesto.json' ausente.")

            manifesto = json.loads(zip_file.read('manifesto.json').decode('utf-8'))
            self.stdout.write(self.style.NOTICE(f"Informações do Backup:"))
            self.stdout.write(f"  Criado em: {manifesto.get('criado_em')}")
            self.stdout.write(f"  Motor de Banco: {manifesto.get('db_engine')}")
            self.stdout.write(f"  Arquivos: {len(zip_file.namelist())} itens no pacote")

            if not options['confirmar']:
                self.stdout.write(self.style.SUCCESS("Validação concluída em modo simulação (dry-run)."))
                return

            # 2. Restaura Banco SQLite
            if 'banco/db.sqlite3' in zip_file.namelist():
                self.stdout.write("  -> Restaurando banco de dados SQLite...")
                db_conf = settings.DATABASES['default']
                db_target = Path(db_conf['NAME'])
                # Backup de segurança antes de sobrescrever
                if db_target.exists():
                    shutil.copy2(db_target, db_target.with_suffix('.sqlite3.bak'))
                
                with open(db_target, 'wb') as f:
                    f.write(zip_file.read('banco/db.sqlite3'))
                self.stdout.write(self.style.SUCCESS("     Banco restaurado com sucesso."))

            # 3. Restaura Mídias
            media_files = [n for n in zip_file.namelist() if n.startswith('media/') and not n.endswith('/')]
            if media_files:
                self.stdout.write(f"  -> Restaurando {len(media_files)} arquivos de anexo...")
                media_root = Path(settings.MEDIA_ROOT)
                media_root.mkdir(parents=True, exist_ok=True)
                for item in media_files:
                    rel_path = Path(item).relative_to('media')
                    dest_file = media_root / rel_path
                    dest_file.parent.mkdir(parents=True, exist_ok=True)
                    with open(dest_file, 'wb') as f:
                        f.write(zip_file.read(item))
                self.stdout.write(self.style.SUCCESS("     Anexos restaurados com sucesso."))

        self.stdout.write(self.style.SUCCESS("Restauração concluída com êxito!"))
