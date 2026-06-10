"""OCR command implementation"""

import os
import time
import uuid
import re
import base64
import threading
import socket
from queue import Queue
from pathlib import Path
from datetime import datetime
from typing import List, Tuple, Optional

try:
    import fitz  # PyMuPDF
    FITZ_AVAILABLE = True
except ImportError:
    FITZ_AVAILABLE = False

try:
    import pymupdf4llm
    PYMUPDF4LLM_AVAILABLE = True
except ImportError:
    PYMUPDF4LLM_AVAILABLE = False

try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False

import shutil

try:
    import pytesseract
    from PIL import Image
    TESSERACT_AVAILABLE = True
    TESSERACT_BINARY_FOUND = shutil.which('tesseract') is not None
except ImportError:
    TESSERACT_AVAILABLE = False
    TESSERACT_BINARY_FOUND = False

MISTRAL_IMPORT_ERROR = None
try:
    from mistralai.client import Mistral
    MISTRAL_AVAILABLE = True
except ImportError as e:
    # Try fallback to v1 if v2 is not found, or just capture error
    try:
        from mistralai import Mistral
        MISTRAL_AVAILABLE = True
    except ImportError as e2:
        MISTRAL_AVAILABLE = False
        MISTRAL_IMPORT_ERROR = f"v2 error: {str(e)}; v1 error: {str(e2)}"

ZAI_IMPORT_ERROR = None
try:
    from zai import ZaiClient
    ZAI_AVAILABLE = True
except ImportError as e:
    ZAI_AVAILABLE = False
    ZAI_IMPORT_ERROR = str(e)

from study_tk.core.base_tool import BaseTool
from study_tk.core.config import get_mistral_api_key, get_zai_api_key
from study_tk.commands.base_command import BaseCommand


class OCRCommand(BaseCommand, BaseTool):
    """OCR processing command"""

    def __init__(self):
        BaseTool.__init__(self)
        if MISTRAL_AVAILABLE:
            api_key = get_mistral_api_key()
            self.mistral_client = Mistral(api_key=api_key) if api_key else None
        else:
            self.mistral_client = None

        if ZAI_AVAILABLE:
            api_key = get_zai_api_key()
            self.zai_client = ZaiClient(api_key=api_key) if api_key else None
        else:
            self.zai_client = None

    def _call_with_retry(self, func, *args, max_retries=3, initial_delay=2, **kwargs):
        """Generic retry wrapper for API calls with exponential backoff"""
        last_exception = None
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                err_msg = str(e).lower()
                # Retry on DNS/connection issues/timeouts
                # [Errno -3] Temporary failure in name resolution is a common DNS issue
                # that often resolves after a short delay or retry.
                if any(x in err_msg for x in ["name resolution", "connection", "timeout", "network", "refused", "reset"]):
                    if attempt < max_retries - 1:
                        wait = initial_delay * (2 ** attempt)
                        print(f"  [Attempt {attempt + 1}/{max_retries}] Network issue: {str(e)}. Retrying in {wait}s...")
                        time.sleep(wait)
                        continue
                break
        raise last_exception

    def execute(self, args):
        """Execute OCR command"""
        provider = args.provider

        if provider == 'mistral':
            if not MISTRAL_AVAILABLE:
                print(f"Error: Mistral AI library not available ({MISTRAL_IMPORT_ERROR}).")
                print("Run: pip install mistralai")
                return
            if not self.mistral_client:
                print("\nError: MISTRAL_API_KEY not configured.")
                print("\nTo set up your API key, run:")
                print("  study-tk setup")
                return
        elif provider == 'zai':
            if not ZAI_AVAILABLE:
                print(f"Error: Z.AI SDK not available ({ZAI_IMPORT_ERROR}).")
                print("Run: pip install zai-sdk")
                return
            if not self.zai_client:
                print("\nError: ZAI_API_KEY not configured.")
                print("\nTo set up your API key, run:")
                print("  study-tk setup")
                return
        elif provider == 'tesseract':
            if not TESSERACT_AVAILABLE:
                print("Error: pytesseract or Pillow library not installed. Run: pip install pytesseract Pillow")
                return
            if not TESSERACT_BINARY_FOUND:
                print("Error: Tesseract binary not found on your system.")
                print("Please install Tesseract OCR:")
                print("  Linux: sudo apt install tesseract-ocr")
                print("  macOS: brew install tesseract")
                return
        elif provider == 'pymupdf':
            if not PYMUPDF4LLM_AVAILABLE:
                print("Error: pymupdf4llm library not installed. Run: pip install pymupdf4llm")
                return

        # Determine target files
        input_files = []
        if not args.files:
            # Default behavior if no files specified on command line
            if provider == 'tesseract':
                img_exts = ['*.jpg', '*.jpeg', '*.png', '*.webp', '*.bmp', '*.tiff']
                for ext in img_exts:
                    input_files.extend(Path('.').glob(ext))
                    input_files.extend(Path('.').glob(ext.upper()))
            else:
                input_files.extend(Path('.').glob('*.pdf'))
        else:
            for pattern in args.files:
                input_files.extend(Path('.').glob(pattern))

        # Unique files and sort
        input_files = sorted(list(set(input_files)))

        if not input_files:
            print(f"No files found matching the pattern(s): {args.files if args.files else 'default patterns'}")
            return

        # Initialize concurrent saving queue and worker
        save_queue = Queue()
        save_stats = {"images_saved": 0, "markdown_saved": 0}
        save_lock = threading.Lock()

        def save_worker():
            """Background worker for saving files concurrently"""
            while True:
                item = save_queue.get()
                if item is None:
                    save_queue.task_done()
                    break
                try:
                    if item["type"] == "markdown":
                        with open(item["path"], "w", encoding="utf-8") as f:
                            f.write(item["content"])
                        with save_lock:
                            save_stats["markdown_saved"] += 1
                    elif item["type"] == "image":
                        item["image"].save(item["path"])
                        with save_lock:
                            save_stats["images_saved"] += 1
                except Exception as e:
                    print(f"\nError saving {item['path']}: {e}")
                finally:
                    save_queue.task_done()

        save_thread = threading.Thread(target=save_worker, daemon=True)
        save_thread.start()

        # Process files
        try:
            if provider == 'tesseract':
                self._process_tesseract_images(input_files, args, save_queue)
            else:
                # Ensure output directory exists for single mode
                if args.output_mode == 'single':
                    Path(args.output).mkdir(parents=True, exist_ok=True)

                files_to_process = tqdm(input_files, desc="Processing PDFs") if TQDM_AVAILABLE else input_files
                for pdf_file in files_to_process:
                    if provider == 'mistral':
                        if args.output_mode == 'single':
                            self._process_single_pdf_mistral_flat(pdf_file, Path(args.output), args)
                        else:
                            self._process_single_pdf_mistral_separate(pdf_file, args)
                    elif provider == 'zai':
                        if args.output_mode == 'single':
                            self._process_single_pdf_zai_flat(pdf_file, Path(args.output))
                        else:
                            self._process_single_pdf_zai_separate(pdf_file)
                    elif provider == 'pymupdf':
                        if args.output_mode == 'single':
                            self._process_single_pdf_pymupdf_flat(pdf_file, Path(args.output), args)
                        else:
                            self._process_single_pdf_pymupdf_separate(pdf_file, args)

        finally:
            # Wait for all saves to complete
            save_queue.join()
            save_queue.put(None)
            save_thread.join()

        print("\nOCR processing complete!")
        if save_stats["markdown_saved"] > 0 or save_stats["images_saved"] > 0:
            print(f"Summary: {save_stats['markdown_saved']} markdown files and {save_stats['images_saved']} images saved.")

    def add_arguments(self, parser):
        """Add OCR-specific arguments"""
        parser.add_argument('files', nargs='*', default=['*.pdf'], help='Files to process (default: *.pdf)')
        parser.add_argument('--output', '-o', default='ocr_output',
                           help='Output directory (default: ocr_output)')
        parser.add_argument('--output-mode', '-m', choices=['separate', 'single'],
                           default='separate',
                           help="Output mode: 'separate' (each PDF in its own folder) or 'single' (all files in one folder, default: 'separate')")
        parser.add_argument('--provider', '-p', choices=['mistral', 'zai', 'tesseract', 'pymupdf'],
                           default='zai',
                           help="OCR provider: 'zai', 'mistral', 'tesseract' (Tesseract OCR for image folders), or 'pymupdf' (pymupdf4llm, default: 'zai')")
        parser.add_argument('--images-only', action='store_true',
                           help="Only extract images from the PDF, no markdown/text output")
        parser.add_argument('--table-format', choices=['null', 'markdown', 'html'],
                           default=None, help="Mistral only: Table output format")
        parser.add_argument('--extract-header', action='store_true',
                           help="Mistral only: Extract headers")
        parser.add_argument('--extract-footer', action='store_true',
                           help="Mistral only: Extract footers")
        parser.add_argument('--tesseract-lang', default='deu+eng',
                           help="Tesseract language (default: deu+eng)")

    def _process_tesseract_images(self, image_files: List[Path], args, save_queue: Queue):
        """Process a list of image files using Tesseract (inspired by ocr_dictionary.py)"""
        print(f"\nProcessing {len(image_files)} images with Tesseract ({args.tesseract_lang})...")
        
        # Sort files (especially if they are like page_1.jpg, page_2.jpg)
        def extract_page_number(filename: str) -> int:
            match = re.search(r"(\d+)", filename)
            return int(match.group(1)) if match else 0
        
        image_files.sort(key=lambda x: extract_page_number(x.name))

        all_text = []
        output_path = Path(args.output)
        output_path.mkdir(parents=True, exist_ok=True)
        
        file_iter = enumerate(image_files, start=1)
        if TQDM_AVAILABLE:
            file_iter = tqdm(list(file_iter), desc="Tesseract OCR")

        for i, img_path in file_iter:
            try:
                img = Image.open(img_path)
                text = pytesseract.image_to_string(img, lang=args.tesseract_lang).strip()
                
                page_num = extract_page_number(img_path.name)
                if text:
                    all_text.append(f"--- Page {page_num} ({img_path.name}) ---\n{text}")
                else:
                    all_text.append(f"--- Page {page_num} ({img_path.name}) ---\n[No text detected]")
            except Exception as e:
                print(f"  [ERROR] Failed to OCR {img_path.name}: {e}")

        combined_text = "\n\n".join(all_text)
        output_file = output_path / "tesseract_output.md"
        
        save_queue.put({
            "type": "markdown",
            "path": output_file,
            "content": combined_text
        })
        print(f"  ✓ Queued Tesseract output to: {output_file}")

    def _process_single_pdf_pymupdf_separate(self, pdf_path: Path, args):
        """Extract text and images locally using pymupdf4llm (Separate folder)"""
        print(f"\nProcessing {pdf_path.name} with pymupdf4llm...")
        try:
            base_name = pdf_path.stem
            main_folder = Path(base_name)
            main_folder.mkdir(parents=True, exist_ok=True)
            
            output_md = main_folder / f"{base_name}.md"
            image_dir = main_folder / "images"
            image_dir.mkdir(parents=True, exist_ok=True)

            md_text = pymupdf4llm.to_markdown(
                doc=str(pdf_path),
                write_images=True,
                image_path=str(image_dir)
            )
            
            if not args.images_only:
                if isinstance(md_text, bytes):
                    md_text = md_text.decode('utf-8')
                with open(output_md, 'w', encoding='utf-8') as f:
                    f.write(md_text)
                print(f"Saved: {output_md}")
            else:
                print(f"Extracted images to {image_dir}")
        except Exception as e:
            print(f"Error processing {pdf_path.name} with pymupdf4llm: {str(e)}")

    def _process_single_pdf_pymupdf_flat(self, pdf_path: Path, output_dir: Path, args):
        """Extract text and images locally using pymupdf4llm (Flat folder)"""
        print(f"\nProcessing {pdf_path.name} with pymupdf4llm...")
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
            base_name = pdf_path.stem
            output_md = output_dir / f"{base_name}.md"
            
            md_text = pymupdf4llm.to_markdown(
                doc=str(pdf_path),
                write_images=True,
                image_path=str(output_dir)
            )
            
            if not args.images_only:
                if isinstance(md_text, bytes):
                    md_text = md_text.decode('utf-8')
                with open(output_md, 'w', encoding='utf-8') as f:
                    f.write(md_text)
                print(f"Saved: {output_md}")
            else:
                print(f"Extracted images to {output_dir}")
        except Exception as e:
            print(f"Error processing {pdf_path.name} with pymupdf4llm: {str(e)}")

    def _process_single_pdf_mistral_separate(self, pdf_path: Path, args):
        """Process a single PDF file through Mistral OCR with separate folder structure"""
        print(f"\nProcessing {pdf_path.name} with Mistral...")

        try:
            # Sanitize filename for upload to avoid potential encoding issues in headers
            safe_name = re.sub(r'[^\x00-\x7F]+', '_', pdf_path.name)
            if not safe_name.strip() or safe_name == '.pdf':
                safe_name = f"doc_{uuid.uuid4().hex[:8]}.pdf"

            # Upload file
            uploaded_file = self._call_with_retry(
                self.mistral_client.files.upload,
                file={"file_name": safe_name, "content": pdf_path.read_bytes()},
                purpose="ocr"
            )

            # Process PDF
            signed_url = self._call_with_retry(
                self.mistral_client.files.get_signed_url,
                file_id=uploaded_file.id,
                expiry=1
            )
            
            pdf_response = self._call_with_retry(
                self.mistral_client.ocr.process,
                model="mistral-ocr-latest",
                document={"type": "document_url", "document_url": signed_url.url},
                table_format=args.table_format,
                extract_header=args.extract_header,
                extract_footer=args.extract_footer,
                include_image_base64=True
            )

            # Create main output folder
            base_name = pdf_path.stem
            prefix = base_name[:2].lower()
            main_folder = Path(base_name)
            main_folder.mkdir(parents=True, exist_ok=True)

            output_md = main_folder / f"{base_name}.md"
            image_dir = main_folder / "images"

            unique_hash = self._generate_unique_hash(length=8)

            # Generate markdown with images and tables
            combined_markdown = self._get_combined_markdown_mistral(
                pdf_response, output_dir=str(image_dir), prefix=prefix, unique_hash=unique_hash
            )

            # Save results
            with open(output_md, 'w', encoding='utf-8') as f:
                f.write(combined_markdown)

            print(f"Saved: {output_md}")

        except Exception as e:
            if "name resolution" in str(e).lower():
                print(f"Error processing {pdf_path.name}: Network connection issue (DNS).")
                print("If you are using a proxy, ensure it is correctly configured (e.g., HTTP_PROXY env var).")
            else:
                print(f"Error processing {pdf_path.name}: {str(e)}")

    def _process_single_pdf_mistral_flat(self, pdf_path: Path, output_dir: Path, args):
        """Process a single PDF file through Mistral OCR with flat folder structure"""
        print(f"\nProcessing {pdf_path.name} with Mistral...")

        try:
            output_dir.mkdir(parents=True, exist_ok=True)
            # Sanitize filename for upload to avoid potential encoding issues in headers
            safe_name = re.sub(r'[^\x00-\x7F]+', '_', pdf_path.name)
            if not safe_name.strip() or safe_name == '.pdf':
                safe_name = f"doc_{uuid.uuid4().hex[:8]}.pdf"

            # Upload file
            uploaded_file = self._call_with_retry(
                self.mistral_client.files.upload,
                file={"file_name": safe_name, "content": pdf_path.read_bytes()},
                purpose="ocr"
            )

            # Process PDF
            signed_url = self._call_with_retry(
                self.mistral_client.files.get_signed_url,
                file_id=uploaded_file.id,
                expiry=1
            )
            
            pdf_response = self._call_with_retry(
                self.mistral_client.ocr.process,
                model="mistral-ocr-latest",
                document={"type": "document_url", "document_url": signed_url.url},
                table_format=args.table_format,
                extract_header=args.extract_header,
                extract_footer=args.extract_footer,
                include_image_base64=True
            )

            # Use the provided output directory for both markdown and images
            base_name = pdf_path.stem
            prefix = base_name[:2].lower()

            output_md = output_dir / f"{base_name}.md"

            unique_hash = self._generate_unique_hash(length=8)

            # Generate markdown with images, putting images in the same output directory
            combined_markdown = self._get_combined_markdown_mistral(
                pdf_response, output_dir=str(output_dir), prefix=prefix, unique_hash=unique_hash
            )

            # Save results
            with open(output_md, 'w', encoding='utf-8') as f:
                f.write(combined_markdown)

            print(f"Saved: {output_md}")

        except Exception as e:
            if "name resolution" in str(e).lower():
                print(f"Error processing {pdf_path.name}: Network connection issue (DNS).")
                print("If you are using a proxy, ensure it is correctly configured (e.g., HTTP_PROXY env var).")
            else:
                print(f"Error processing {pdf_path.name}: {str(e)}")

    def _process_single_pdf_zai_separate(self, pdf_path: Path):
        """Process a single PDF file through Z.AI OCR with separate folder structure"""
        print(f"\nProcessing {pdf_path.name} with Z.AI...")

        try:
            # Read file and encode to base64
            file_bytes = pdf_path.read_bytes()
            base64_file = base64.b64encode(file_bytes).decode('utf-8')
            data_uri = f"data:application/pdf;base64,{base64_file}"

            # Call layout parsing API with retry
            response = self._call_with_retry(
                self.zai_client.layout_parsing.create,
                model="glm-ocr",
                file=data_uri
            )

            # Create main output folder
            base_name = pdf_path.stem
            main_folder = Path(base_name)
            main_folder.mkdir(parents=True, exist_ok=True)

            output_md = main_folder / f"{base_name}.md"

            markdown_content = response.md_results

            # Save results
            with open(output_md, 'w', encoding='utf-8') as f:
                f.write(markdown_content)

            print(f"Saved: {output_md}")

        except Exception as e:
            if "name resolution" in str(e).lower():
                print(f"Error processing {pdf_path.name}: Network connection issue (DNS).")
                print("If you are using a proxy, ensure it is correctly configured (e.g., HTTP_PROXY env var).")
            else:
                print(f"Error processing {pdf_path.name}: {str(e)}")

    def _process_single_pdf_zai_flat(self, pdf_path: Path, output_dir: Path):
        """Process a single PDF file through Z.AI OCR with flat folder structure"""
        print(f"\nProcessing {pdf_path.name} with Z.AI...")

        try:
            output_dir.mkdir(parents=True, exist_ok=True)
            # Read file and encode to base64
            file_bytes = pdf_path.read_bytes()
            base64_file = base64.b64encode(file_bytes).decode('utf-8')
            data_uri = f"data:application/pdf;base64,{base64_file}"

            # Call layout parsing API with retry
            response = self._call_with_retry(
                self.zai_client.layout_parsing.create,
                model="glm-ocr",
                file=data_uri
            )

            base_name = pdf_path.stem
            output_md = output_dir / f"{base_name}.md"

            markdown_content = response.md_results

            # Save results
            with open(output_md, 'w', encoding='utf-8') as f:
                f.write(markdown_content)

            print(f"Saved: {output_md}")

        except Exception as e:
            if "name resolution" in str(e).lower():
                print(f"Error processing {pdf_path.name}: Network connection issue (DNS).")
                print("If you are using a proxy, ensure it is correctly configured (e.g., HTTP_PROXY env var).")
            else:
                print(f"Error processing {pdf_path.name}: {str(e)}")

    def _generate_unique_hash(self, length=6):
        """Generate a highly unique hash of specified length"""
        now = datetime.now()
        timestamp = int(time.time() * 1000000)
        timestamp_part = str(timestamp)[-6:]
        uuid_part = str(uuid.uuid4().hex)[:4]
        combined = timestamp_part + uuid_part
        return combined[:length]

    def _parse_data_uri(self, data_uri: str):
        match = re.match(r'([^;]+);base64,(.*)', data_uri)
        if not match:
            raise ValueError(f"Invalid data URI format")
        return match.group(1), match.group(2)

    def _get_extension_from_mime(self, mime_type: str) -> str:
        mime_extensions = {
            'image/png': 'png',
            'image/jpeg': 'jpg',
            'image/jpg': 'jpg',
            'image/gif': 'gif',
            'image/webp': 'webp',
        }
        return mime_extensions.get(mime_type, 'bin')

    def _save_image_from_data_uri(self, data_uri: str, counter: int, prefix: str,
                                  unique_hash: str, output_dir: str = '.') -> Tuple[str, str]:
        os.makedirs(output_dir, exist_ok=True)
        try:
            mime_type, data = self._parse_data_uri(data_uri)
            if mime_type.startswith("data:"):
                mime_type = mime_type[5:]
        except ValueError as e:
            print(f"Skipping image {counter}: {e}")
            return f"img{counter}", f"img{counter}"

        extension = self._get_extension_from_mime(mime_type)
        short_name = f"{prefix}{counter:02d}{unique_hash}"
        filename = f"{short_name}.{extension}"
        filepath = os.path.join(output_dir, filename)

        with open(filepath, 'wb') as f:
            f.write(base64.b64decode(data))

        return short_name, filename

    def _save_table(self, table_content: str, table_id: str, output_dir: str = '.') -> str:
        """Save table content to a file and return the filename"""
        os.makedirs(output_dir, exist_ok=True)
        filepath = os.path.join(output_dir, table_id)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(table_content)
        return table_id

    def _get_combined_markdown_mistral(self, ocr_response, output_dir: str,
                               prefix: str, unique_hash: str) -> str:
        markdowns = []
        image_counter = 1
        image_mapping = {}
        table_mapping = {}

        # First pass: save all images and create mapping
        for page in ocr_response.pages:
            for img in page.images:
                if img.id not in image_mapping:
                    original_id = img.id
                    short_name, filename = self._save_image_from_data_uri(
                        img.image_base64, image_counter, prefix, unique_hash, output_dir
                    )
                    image_mapping[original_id] = (short_name, filename)
                    image_counter += 1
            
            # Save tables if any
            for tbl in getattr(page, 'tables', []):
                if tbl.id not in table_mapping:
                    filename = self._save_table(tbl.content, tbl.id, output_dir)
                    table_mapping[tbl.id] = filename

        # Second pass: replace image and table references in markdown
        for page in ocr_response.pages:
            page_md = page.markdown
            # Replace image references
            for original_id, (short_name, filename) in image_mapping.items():
                page_md = page_md.replace(
                    f"![{original_id}]({original_id})",
                    f"![{short_name}]({filename})"
                )
            
            # Replace table references
            for tbl_id, filename in table_mapping.items():
                page_md = page_md.replace(
                    f"[{tbl_id}]({tbl_id})",
                    f"[{tbl_id}]({filename})"
                )
                
            markdowns.append(page_md)

        return "\n\n".join(markdowns)
