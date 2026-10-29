from io import BytesIO
from uuid import uuid4

from django.core.files.base import ContentFile
from PIL import Image, ImageOps, UnidentifiedImageError

from apps.accounts.api.utils.exceptions import CustomValidationException


MAX_AVATAR_SIZE = 5 * 1024 * 1024  # 5 MB
MAX_AVATAR_PIXELS = 20_000_000


def sanitize_profile_image(upload):
    """
    Validate and sanitize an uploaded profile image.
    Only JPEG and PNG formats are allowed.
    """

    if upload.size > MAX_AVATAR_SIZE:
        raise CustomValidationException(
            code="image_too_large",
            message="Image size exceeds the maximum allowed limit.",
            details={
                "field": "image",
                "max_size": "5 MB",
            },
        )

    try:
        with Image.open(upload) as image:
            image_format = image.format

            if image_format not in {"JPEG", "PNG"}:
                raise CustomValidationException(
                    code="unsupported_image_format",
                    message="Only JPG and PNG images are allowed.",
                    details={
                        "field": "image",
                        "allowed_formats": ["JPG", "PNG"],
                    },
                )

            if image.width * image.height > MAX_AVATAR_PIXELS:
                raise CustomValidationException(
                    code="image_dimensions_too_large",
                    message="Image dimensions exceed the maximum allowed limit.",
                    details={
                        "field": "image",
                        "max_pixels": MAX_AVATAR_PIXELS,
                    },
                )

            image.verify()

        upload.seek(0)

        with Image.open(upload) as image:
            image.load()
            image = ImageOps.exif_transpose(image)

            if image_format == "JPEG" and image.mode not in {"RGB", "L"}:
                image = image.convert("RGB")

            output = BytesIO()
            image.save(
                output,
                format=image_format,
                optimize=True,
            )

    except CustomValidationException:
        raise

    except (
        Image.DecompressionBombError,
        OSError,
        UnidentifiedImageError,
        ValueError,
    ) as exc:
        raise CustomValidationException(
            code="invalid_image",
            message="The uploaded image is invalid or corrupted.",
            details={
                "field": "image",
            },
        ) from exc

    finally:
        upload.seek(0)

    extension = "jpg" if image_format == "JPEG" else "png"

    return ContentFile(
        output.getvalue(),
        name=f"{uuid4().hex}.{extension}",
    )