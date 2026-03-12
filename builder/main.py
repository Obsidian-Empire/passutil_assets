import argparse
import logging

from pipeline import main as pipeline_main

# Настройка логирования
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def main(input_dir: str, output_dir: str, base_url: str) -> None:
    """Точка входа для синхронного запуска."""
    pipeline_main(input_dir, output_dir, base_url)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Convert PNG images to WebP format"
    )
    parser.add_argument(
        "input_dir",
        help="Input directory containing PNG files"
    )
    parser.add_argument(
        "output_dir",
        help="Output directory for WebP files")

    parser.add_argument(
        "--base-url",
        required=True,
        help="Base raw URL for blob.json entries (no trailing slash)",
    )

    args = parser.parse_args()
    main(args.input_dir, args.output_dir, args.base_url)
