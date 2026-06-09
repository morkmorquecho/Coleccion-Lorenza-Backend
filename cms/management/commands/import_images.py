import os
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.core.files import File
from cms.models import Collection, ImageCollection


class Command(BaseCommand):
    help = 'Importa todas las imágenes de una carpeta a una colección'

    def add_arguments(self, parser):
        parser.add_argument('collection_name', type=str)
        parser.add_argument('folder_path', type=str)
        parser.add_argument('--year', type=int, default=None)
        parser.add_argument('--extensions', nargs='+', default=['jpg', 'jpeg', 'png', 'webp', 'heic', 'heif'])

    def handle(self, *args, **options):
        folder = Path(options['folder_path'])
        if not folder.is_dir():
            raise CommandError(f"No existe la carpeta: {folder}")

        try:
            collection = Collection.objects.get(name=options['collection_name'])
        except Collection.DoesNotExist:
            raise CommandError(f"Colección no encontrada: {options['collection_name']}")

        extensions = {ext.lower() for ext in options['extensions']}
        files = sorted([
            f for f in folder.iterdir()
            if f.is_file() and f.suffix.lstrip('.').lower() in extensions
        ])

        if not files:
            self.stdout.write(self.style.WARNING("No se encontraron imágenes."))
            return

        created = 0
        for file_path in files:
            with open(file_path, 'rb') as f:
                name_stem = file_path.stem  # nombre del archivo sin extensión
                obj = ImageCollection(
                    collection=collection,
                    year=options['year'],
                    name=name_stem,
                )
                obj.image_path.save(file_path.name, File(f), save=False)
                obj.save()  # dispara HEICConversionMixin
                created += 1
                self.stdout.write(f"  ✓ {file_path.name}")

        self.stdout.write(self.style.SUCCESS(f"\n{created} imágenes importadas a '{collection.name}'"))