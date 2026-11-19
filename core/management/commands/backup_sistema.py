import os
import io
import json
import sqlite3
import zipfile
from datetime import datetime
from pathlib import Path
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = 'Executa rotina completa de backup: banco de dados (SQLite/dump JSON) e pasta de anexos (media).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output-dir',
            type=str,
            default=str(settings.BASE_DIR / 'backups'),
            help='Diretório onde os arquivos de backup serão armazenados (padrão: backups/).',
        )
        parser.add_argument(
            '--no-media',
            action='store_true',
            help='Executa backup apenas do banco de dados, excluindo os anexos de mídia.',
        )
        parser.add_argument(
            '--keep',
            type=int,
            default=7,
            help='Quantidade de backups mais recentes a manter (política de retenção, padrão: 7).',
        )

    def handle(self, *args, **options):
        output_dir = Path(options['output_dir'])
        output_dir.mkdir(parents=True, exist_ok=True)

        include_media = not options['no_media']
        keep = options['keep']

        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f"backup_sistema_{timestamp}.zip"
        backup_filepath = output_dir / backup_filename

        self.stdout.write(self.style.NOTICE(f"Iniciando rotina de backup: {backup_filename}"))

        manifest = {
            'criado_em': timezone.now().isoformat(),
            'timestamp': timestamp,
            'django_settings_module': os.environ.get('DJANGO_SETTINGS_MODULE', ''),
            'inclui_media': include_media,
            'arquivos_incluidos': [],
        }

        with zipfile.ZipFile(backup_filepath, 'w', compression=zipfile.ZIP_DEFLATED) as zip_file:
            # 1. Backup do Banco de Dados
            db_conf = settings.DATABASES['default']
            db_engine = db_conf.get('ENGINE', '')
            manifest['db_engine'] = db_engine

            if 'sqlite3' in db_engine:
                db_path = Path(db_conf['NAME'])
                if db_path.exists():
                    self.stdout.write("  -> Criando snapshot consistente do SQLite...")
                    # Snapshot consistente via API de backup do SQLite
                    temp_db_path = output_dir / f"temp_{timestamp}.sqlite3"
                    try:
                        src_conn = sqlite3.connect(db_path)
                        dst_conn = sqlite3.connect(temp_db_path)
                        with dst_conn:
                            src_conn.backup(dst_conn)
                        dst_conn.close()
                        src_conn.close()

                        zip_file.write(temp_db_path, arcname="banco/db.sqlite3")
                        manifest['arquivos_incluidos'].append("banco/db.sqlite3")
                    finally:
                        if temp_db_path.exists():
                            temp_db_path.unlink()

            # 2. Dump em JSON (Portabilidade)
            self.stdout.write("  -> Exportando dados relacionais em JSON (dumpdata)...")
            dump_buffer = io.StringIO()
            call_command(
                'dumpdata',
                natural_foreign=True,
                natural_primary=True,
                exclude=['contenttypes', 'auth.permission'],
                stdout=dump_buffer,
            )
            zip_file.writestr("banco/dados_dump.json", dump_buffer.getvalue())
            manifest['arquivos_incluidos'].append("banco/dados_dump.json")

            # 3. Backup dos Arquivos de Mídia (Anexos de Impressão)
            if include_media and hasattr(settings, 'MEDIA_ROOT') and os.path.exists(settings.MEDIA_ROOT):
                self.stdout.write("  -> Compactando pasta de anexos e mídias...")
                media_root = Path(settings.MEDIA_ROOT)
                media_count = 0
                for root, _, files in os.walk(media_root):
                    for file in files:
                        if file == '.gitkeep':
                            continue
                        file_path = Path(root) / file
                        arcname = Path("media") / file_path.relative_to(media_root)
                        zip_file.write(file_path, arcname=str(arcname))
                        media_count += 1

                manifest['total_arquivos_media'] = media_count
                self.stdout.write(f"     Arquivos de mídia incluídos: {media_count}")

            # 4. Grava Manifesto
            zip_file.writestr("manifesto.json", json.dumps(manifest, indent=2, ensure_ascii=False))

        file_size_kb = backup_filepath.stat().st_size / 1024
        self.stdout.write(
            self.style.SUCCESS(
                f"Backup concluído com sucesso: {backup_filepath.name} ({file_size_kb:.2f} KB)"
            )
        )

        # 5. Política de Retenção
        self.aplicar_politica_retencao(output_dir, keep)

    def aplicar_politica_retencao(self, output_dir: Path, keep: int):
        """Remove backups antigos além do limite configurado."""
        if keep <= 0:
            return

        backups = sorted(
            [f for f in output_dir.glob("backup_sistema_*.zip") if f.is_file()],
            key=lambda x: x.stat().st_mtime,
            reverse=True,
        )

        if len(backups) > keep:
            excedentes = backups[keep:]
            self.stdout.write(self.style.WARNING(f"Aplicando retenção (manter {keep}): removendo {len(excedentes)} backup(s) antigo(s)..."))
            for b in excedentes:
                b.unlink()
                self.stdout.write(f"  Removido: {b.name}")
