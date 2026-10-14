import glob
import json
import os
import re
import shutil
from tqdm import tqdm

from src.supported_file_types.exceptions import ExifWriterError
from src.supported_file_types.jpg_writer import JPGWriter
from src.supported_file_types.png_writer import PNGWriter


class Metadata:
    # All keys must be lower case!!!
    _SUPPORTED_EXTENSIONS = {
        '.jpg': JPGWriter,
        '.jpeg': JPGWriter,
        '.heic': JPGWriter,
        '.tif': JPGWriter,
        '.tiff': JPGWriter,
        '.png': PNGWriter,
        '.webp': JPGWriter,
        '.gif': JPGWriter,
        '.mp4': JPGWriter
    }

    @staticmethod
    def recover(root_folder: str, output_folder: str) -> None:
        """
        Given a root_folder it will associate all files (images and videos) to their associated metadata file.
        After it will write the EXIF metadata present in the metadata file to the image/video file writing the new file
        to output_folder
        """
        files_with_metadata = Metadata._get_files_with_metadata(root_folder)
        print(f'{len(files_with_metadata)} file(s) to recover metadata')

        edited_files_count = 0

        for media_file, metadata_file in tqdm(files_with_metadata.items()):
            # Controlla se il file corrente ha il suffisso -edited o -EDIT
            base_name, _ = os.path.splitext(os.path.basename(media_file))
            if re.search(r'-(edited|EDIT)$', base_name, flags=re.IGNORECASE):
                edited_files_count += 1

            output_filepath = Metadata._get_output_filename(root_folder, output_folder, media_file)
            if metadata_file is None:
                tqdm.write(f'Skipping {media_file} as there is no metadata associated. Saving to output folder')
                Metadata._copy_file(media_file, output_filepath)
                continue

            tqdm.write(f'Recovering {media_file}')
            try:
                with open(metadata_file, encoding='utf-8') as f:
                    metadata = json.load(f)
            except Exception:
                with open(metadata_file, encoding='latin-1') as f:
                    metadata = json.load(f)

            media_file_extension = os.path.splitext(media_file)[1].lower()
            if media_file_extension not in Metadata._SUPPORTED_EXTENSIONS:
                tqdm.write(f'Extension {media_file_extension} is not supported. Saving image/video file to output folder')
                Metadata._copy_file(media_file, output_filepath)
                continue

            output_dir = os.path.dirname(output_filepath)
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)

            exif_writer = Metadata._SUPPORTED_EXTENSIONS[media_file_extension]
            try:
                exif_writer.write(media_file, output_filepath, metadata)
            except ExifWriterError:
                tqdm.write('Ignoring exif write')
                Metadata._copy_file(media_file, output_filepath)

            time_data = metadata.get('photoTakenTime') or metadata.get('creationTime')
            if time_data and 'timestamp' in time_data:
                try:
                    creation_timestamp = int(time_data['timestamp'])
                    os.utime(output_filepath, (creation_timestamp, creation_timestamp))
                except (ValueError, TypeError):
                    pass

        print('Recovery of metadata completed')
        print(f'Totale file "-edited" incontrati e processati: {edited_files_count}')

    @staticmethod
    def _get_files_with_metadata(root_folder: str) -> dict[str, str]:
        """Given a folder let's join each file with its associated metadata"""
        files = Metadata._get_non_json_files(root_folder)
        files_with_metadata = Metadata._get_metadata_files(files)

        # Let's validate if we did not miss any metadata file
        metadata_files = set(files_with_metadata.values())
        for path in glob.glob(f'{root_folder}/**', recursive=True):
            if not os.path.isfile(path):
                continue

            extension = os.path.splitext(path)[1].lower()
            if extension == '.json' and path not in metadata_files and not path.endswith('.supplemental-metadata.json'):
                tqdm.write(f'Cannot find associated image/video file with {path}')

        return files_with_metadata

    @staticmethod
    def _get_metadata_files(files: list[str]) -> dict[str, str | None]:
        """Find metadata file associated with a given file. Associate None if no metadata was found for a given file"""
        files_with_metadata = {}
        for file in files:
            found = None
            # Check both .supplemental-metadata.json and .json with various patterns
            for ext in ['.supplemental-metadata.json', '.json']:
                # 1. file + ext
                candidate = Metadata._sanitize_metadata_filename(f'{file}{ext}')
                if os.path.isfile(candidate):
                    found = candidate
                    break

                # 2. changed extension base + ext
                changed_base = os.path.splitext(file)[0]
                candidate = Metadata._sanitize_metadata_filename(f'{changed_base}{ext}')
                if os.path.isfile(candidate):
                    found = candidate
                    break

            if found:
                assert file not in files_with_metadata
                files_with_metadata[file] = found
                continue

            # 3. iOS live photo or (1) suffix case: foo(1).jpg -> foo.jpg(1).json
            filename, extension = os.path.splitext(file)
            parts = re.split(r'(\(\d+\))$', filename, maxsplit=1)
            if len(parts) == 3:
                for ext in ['.supplemental-metadata.json', '.json']:
                    candidate = Metadata._sanitize_metadata_filename(f'{parts[0]}{extension}{parts[1]}{ext}')
                    if os.path.isfile(candidate):
                        found = candidate
                        break
                if found:
                    assert file not in files_with_metadata
                    files_with_metadata[file] = found
                    continue

            # 4. Edited files fallback: e.g., foo-edited.jpg -> fallback to foo.jpg.json if specific edited json is missing
            base_name, ext_name = os.path.splitext(file)
            unedited_base_name = re.sub(r'-(edited|EDIT)$', '', base_name, flags=re.IGNORECASE)
            if unedited_base_name != base_name:
                for ext in ['.supplemental-metadata.json', '.json']:
                    candidate = Metadata._sanitize_metadata_filename(f'{unedited_base_name}{ext_name}{ext}')
                    if os.path.isfile(candidate):
                        found = candidate
                        break
                    candidate = Metadata._sanitize_metadata_filename(f'{unedited_base_name}{ext}')
                    if os.path.isfile(candidate):
                        found = candidate
                        break
                if found:
                    assert file not in files_with_metadata
                    files_with_metadata[file] = found
                    continue

            if not Metadata._is_live_photo(file):
                tqdm.write(f'Cannot find metadata for {file}')
            files_with_metadata[file] = None

        return files_with_metadata

    @staticmethod
    def _get_non_json_files(root_folder: str) -> list[str]:
        """Returns all non json files aka all images and videos"""
        files = []
        for path in glob.glob(f'{root_folder}/**', recursive=True):
            if not os.path.isfile(path):
                continue

            extension = os.path.splitext(path)[1].lower()
            if extension != '.json' and not path.endswith('.supplemental-metadata.json'):
                files.append(path)
        return files

    @staticmethod
    def _change_extension(file: str) -> str:
        """Changes the extension of a file to .json"""
        filepath = os.path.splitext(file)[0]
        filename = f'{os.path.basename(filepath)}.json'
        return os.path.join(os.path.dirname(filepath), Metadata._sanitize_metadata_filename(filename))

    @staticmethod
    def _sanitize_metadata_filename(metadata_file: str) -> str:
        """
        Google takeout truncates the filename. Maximum characters allowed are 51.
        This method sanitizes the filename to meet google's takeout criteria supporting both .json and .supplemental-metadata.json
        """
        if metadata_file.endswith('.supplemental-metadata.json'):
            ext = '.supplemental-metadata.json'
        elif metadata_file.endswith('.json'):
            ext = '.json'
        else:
            ext = ''

        if ext:
            base = metadata_file[:-len(ext)]
            dirname = os.path.dirname(base)
            basename = os.path.basename(base)
            if len(basename) > 46:
                basename = basename[:46]
            return os.path.join(dirname, f'{basename}{ext}')
        return metadata_file

    @staticmethod
    def _is_live_photo(file: str) -> bool:
        """Check if the given file is a live photo from iOS"""
        file_path = os.path.splitext(file)[0]
        return os.path.isfile(f'{file_path}.heic')

    @staticmethod
    def _copy_file(source: str, destination: str) -> None:
        output_dir_name = os.path.dirname(destination)
        if not os.path.isdir(output_dir_name):
            os.makedirs(output_dir_name)
        shutil.copy2(source, os.path.normpath(destination))

    @staticmethod
    def _get_output_filename(root_folder: str, output_folder: str, image_path: str) -> str:
        """
        Returns the output folder by just changing the name of the parent folder. For example, if root_folder is google
        and the image_path is google/takeout/photos2024/foo.jpg the resulting output folder must be
        <output_folder>/takeout/photos2024/foo.jpg
        """
        new_image_name = os.path.basename(image_path)
        image_path_dir = os.path.dirname(image_path)
        relative_to_new_image_folder = os.path.relpath(image_path_dir, root_folder)
        return os.path.join(output_folder, relative_to_new_image_folder, new_image_name)