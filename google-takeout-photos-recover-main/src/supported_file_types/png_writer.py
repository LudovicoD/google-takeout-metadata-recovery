import os
import subprocess
from datetime import datetime

from src.supported_file_types.exceptions import ExifWriterError
from src.supported_file_types.exif_writer import ExifWriter


class PNGWriter(ExifWriter):
    _VERTICAL_DIRECTIONS = ['S', 'N']
    _HORIZONTAL_DIRECTIONS = ['W', 'E']

    @staticmethod
    def write(source_filepath: str, output_filepath: str, metadata: dict) -> None:
        exif_args = PNGWriter._get_exif_args(source_filepath, output_filepath, metadata)
        try:
            subprocess.run(exif_args, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except subprocess.CalledProcessError:
            raise ExifWriterError()

    @staticmethod
    def _get_exif_args(source_filepath: str, output_filepath: str, metadata: dict) -> list[str]:
        # Trova automaticamente exiftool.exe nella cartella principale del progetto
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../'))
        exiftool_path = os.path.join(project_root, 'exiftool.exe')
        if not os.path.exists(exiftool_path):
            exiftool_path = 'exiftool'

        exif_args = [exiftool_path, '-q', '-P']

        # Gestione sicura della data (supporta photoTakenTime o creationTime)
        time_data = metadata.get('photoTakenTime') or metadata.get('creationTime')
        if time_data and 'timestamp' in time_data:
            try:
                timestamp = int(time_data['timestamp'])
                exif_args.extend(PNGWriter._get_date_args(timestamp))
            except (ValueError, TypeError):
                pass

        # Gestione sicura dei dati GPS
        geo_data = metadata.get('geoData')
        if geo_data:
            latitude = geo_data.get('latitude')
            longitude = geo_data.get('longitude')
            altitude = geo_data.get('altitude')
            if latitude is not None and longitude is not None:
                try:
                    alt_val = float(altitude) if altitude is not None else 0.0
                    exif_args.extend(PNGWriter._get_gps_args(float(latitude), float(longitude), alt_val))
                except (ValueError, TypeError):
                    pass

        # Gestione descrizione opzionale
        description = metadata.get('description')
        if description:
            exif_args.extend(PNGWriter._get_description_args(description))

        # Gestione titolo opzionale
        title = metadata.get('title')
        if title:
            exif_args.extend(PNGWriter._get_title_args(title))

        exif_args.append(source_filepath)
        exif_args.append('-o')
        exif_args.append(output_filepath)
        return exif_args

    @staticmethod
    def _get_date_args(timestamp: int) -> list[str]:
        formatted_datetime = datetime.fromtimestamp(timestamp).strftime(ExifWriter.DATETIME_STR_FORMAT)
        return [
            f'-DateTime={formatted_datetime}',
            f'-DateTimeOriginal={formatted_datetime}',
            f'-DateTimeDigitized={formatted_datetime}'
        ]

    @staticmethod
    def _get_direction(value: float, direction: list[str]) -> str:
        if value < 0:
            return direction[0]
        if value > 0:
            return direction[1]
        return ''

    @staticmethod
    def _get_gps_args(latitude: float, longitude: float, altitude: float) -> list[str]:
        latitude_ref = PNGWriter._get_direction(latitude, PNGWriter._VERTICAL_DIRECTIONS)
        longitude_ref = PNGWriter._get_direction(longitude, PNGWriter._HORIZONTAL_DIRECTIONS)
        alt_val = round(abs(altitude), 4)
        return [
            '-GPSVersionID=2 0 0 0',
            f'-GPSLatitudeRef={latitude_ref}',
            f'-GPSLatitude={abs(latitude)}',
            f'-GPSLongitudeRef={longitude_ref}',
            f'-GPSLongitude={abs(longitude)}',
            f'-GPSAltitudeRef={alt_val}',
            f'-GPSAltitude={alt_val}',
        ]

    @staticmethod
    def _get_description_args(description: str) -> list[str]:
        return [
            f'-Description={description}',
            f'-ImageDescription={description}'
        ]

    @staticmethod
    def _get_title_args(title: str) -> list[str]:
        return [
            f'-Title={title}',
            f'-ObjectDescription={title}',
            f'-PreservedFileName={title}'
        ]