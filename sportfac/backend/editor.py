"""Manager-only image connector for Jodit; existing uploads keep their URLs."""
import warnings
from io import BytesIO
from pathlib import PurePosixPath
from uuid import uuid4

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_GET
from django.views.decorators.http import require_POST
from PIL import Image
from PIL import UnidentifiedImageError

from backend.utils import manager_required


FORMATS = {"PNG": "png", "JPEG": "jpg", "WEBP": "webp", "GIF": "gif"}
EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
MAX_SIZE = 10 * 1024 * 1024


def error(message, status=400):
    return JsonResponse({"success": False, "data": {"messages": [message]}}, status=status)


@manager_required
@require_POST
def upload(request):
    files = [file for key in request.FILES for file in request.FILES.getlist(key)]
    if not files or len(files) > 10:
        return error("Sélectionnez entre une et dix images.")
    prepared = []
    for file in files:
        if file.size > MAX_SIZE:
            return error("Chaque image doit peser au maximum 10 Mo.")
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                image = Image.open(file)
                if image.format not in FORMATS:
                    return error("Formats acceptés : PNG, JPEG, GIF et WebP.")
                image.verify()
                file.seek(0)
                image = Image.open(file)
                if image.width * image.height > 25_000_000:
                    return error("L’image dépasse 25 millions de pixels.")
                image.load()
                extension = FORMATS[image.format]
                # Re-encode static images, excluding appended data and metadata.
                if getattr(image, "is_animated", False):
                    file.seek(0)
                    content = file.read()
                else:
                    output = BytesIO()
                    image.save(output, format=image.format)
                    content = output.getvalue()
        except (
            UnidentifiedImageError,
            OSError,
            ValueError,
            Image.DecompressionBombError,
            Image.DecompressionBombWarning,
        ):
            return error("Le fichier n’est pas une image valide.")
        prepared.append((extension, content))
    urls = []
    for extension, content in prepared:
        path = f"uploads/{timezone.now():%Y/%m/%d}/{uuid4().hex}.{extension}"
        name = default_storage.save(path, ContentFile(content))
        urls.append(request.build_absolute_uri(default_storage.url(name)))
    return JsonResponse({"success": True, "data": {"files": urls, "baseurl": "", "isImages": [True] * len(urls)}})


@manager_required
@require_GET
def browse(request):
    action = request.GET.get("action", "files")
    if action not in {"files", "folders"}:
        return error("Action non autorisée.", status=403)
    relative = request.GET.get("path", "").strip("/")
    path = PurePosixPath(relative)
    if ".." in path.parts or "\\" in relative or "\x00" in relative:
        return error("Dossier invalide.")
    folder = str(PurePosixPath("uploads") / path)
    try:
        directories, filenames = default_storage.listdir(folder)
    except FileNotFoundError:
        directories, filenames = [], []
    files = []
    if action == "files":
        for filename in sorted(filenames):
            if PurePosixPath(filename).suffix.lower() not in EXTENSIONS:
                continue
            url = request.build_absolute_uri(default_storage.url(f"{folder}/{filename}"))
            files.append(
                {
                    "file": url,
                    "fileIsAbsolute": True,
                    "thumb": url,
                    "thumbIsAbsolute": True,
                    "name": filename,
                    "type": "image",
                    "isImage": True,
                }
            )
    return JsonResponse(
        {
            "success": True,
            "data": {
                "sources": [
                    {
                        "name": "images",
                        "title": "Images",
                        "path": relative + "/" if relative else "",
                        "baseurl": "",
                        "files": files,
                        "folders": sorted(directories),
                    }
                ]
            },
        }
    )
