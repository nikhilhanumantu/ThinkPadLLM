import os
import re
import requests
from PIL import Image
import pytesseract
from pdf2image import convert_from_path
import PyPDF2

# On Windows, set Tesseract path if needed
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'


def extract_text_via_gemini(file_path: str) -> dict:
    """Fallback OCR using Gemini's multi-modal capabilities, with OpenRouter as second fallback."""
    # Try Gemini first
    try:
        import os
        from google import genai
        
        client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))
        uploaded_file = client.files.upload(file=file_path)
        
        prompt = "Extract all readable text from this file verbatim. Maintain layout, structure, headings, and lists where possible. Clean up messy formatting. Return only the extracted text."
        
        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=[uploaded_file, prompt]
        )
        
        extracted_text = response.text.strip()
        
        try:
            client.files.delete(name=uploaded_file.name)
        except:
            pass
            
        if extracted_text:
            return {
                "success": True,
                "text": extracted_text,
                "confidence": 99.0,
                "word_count": len(extracted_text.split()),
                "method": "gemini_multimodal"
            }
        
        raise Exception("Gemini returned empty text")
    except Exception as gemini_err:
        print(f"[OCR] Gemini OCR failed: {gemini_err}")

    # Fallback to OpenRouter (Claude Opus 4.7 Fast) with vision
    try:
        import base64
        import mimetypes
        
        api_key = os.getenv('OPENROUTER_API_KEY')
        if not api_key or api_key == 'your_openrouter_api_key_here':
            return {"success": False, "text": "", "error": "Both Gemini and OpenRouter keys unavailable"}

        mime_type, _ = mimetypes.guess_type(file_path)
        if not mime_type:
            mime_type = "image/png"

        with open(file_path, 'rb') as f:
            image_b64 = base64.b64encode(f.read()).decode('utf-8')

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:5000",
            "X-Title": "ThinkPadLLM"
        }
        payload = {
            "model": "anthropic/claude-opus-4.7:fast",
            "messages": [{
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime_type};base64,{image_b64}"}
                    },
                    {
                        "type": "text",
                        "text": "Extract all readable text from this image verbatim. Maintain layout, structure, headings, and lists where possible. Clean up messy formatting. Return only the extracted text."
                    }
                ]
            }]
        }

        print("[OCR] Falling back to OpenRouter (Claude Opus 4.7 Fast) for OCR...")
        response = requests.post("https://openrouter.ai/api/v1/chat/completions",
                                 headers=headers, json=payload, timeout=120)
        response.raise_for_status()
        data = response.json()
        extracted_text = data['choices'][0]['message']['content'].strip()

        if extracted_text:
            return {
                "success": True,
                "text": extracted_text,
                "confidence": 95.0,
                "word_count": len(extracted_text.split()),
                "method": "openrouter_vision"
            }
        return {"success": False, "text": "", "error": "OpenRouter returned empty text"}
    except Exception as or_err:
        return {"success": False, "text": "", "error": f"All OCR fallbacks failed: {str(or_err)}"}

def extract_text_from_image(file_path: str) -> dict:
    """Extract text from an image. Tries AI-based OCR first (Gemini → OpenRouter), falls back to Tesseract."""
    # Try AI-based OCR first (handles handwriting much better)
    ai_result = extract_text_via_gemini(file_path)
    if ai_result.get('success') and ai_result.get('text'):
        return ai_result

    # Fallback to Tesseract OCR
    try:
        img = Image.open(file_path)
        img = img.convert('RGB')
        
        ocr_data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
        
        words = []
        total_conf = 0
        word_count = 0
        for i, word in enumerate(ocr_data['text']):
            conf = int(ocr_data['conf'][i])
            if conf > 30 and word.strip():
                words.append(word)
                total_conf += conf
                word_count += 1
        
        avg_confidence = (total_conf / word_count) if word_count > 0 else 0
        
        full_text = pytesseract.image_to_string(img, config='--psm 3')
        cleaned_text = clean_ocr_text(full_text)
        
        if cleaned_text.strip():
            return {
                "success": True,
                "text": cleaned_text,
                "confidence": round(avg_confidence, 2),
                "word_count": len(cleaned_text.split()),
                "method": "tesseract"
            }
    except Exception as e:
        print(f"[OCR] Tesseract also failed: {e}")

    # All methods failed
    return ai_result  # Return the AI error for debugging


def extract_text_from_pdf(file_path: str) -> dict:
    """Extract text from PDF - tries text extraction first, then AI OCR, then Tesseract."""
    try:
        extracted_text = ""
        
        # Try direct text extraction first (for digital PDFs)
        with open(file_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    extracted_text += text + "\n\n"
        
        # If we got meaningful text, return it
        if len(extracted_text.strip()) > 50:
            cleaned = clean_ocr_text(extracted_text)
            return {
                "success": True,
                "text": cleaned,
                "confidence": 95.0,
                "word_count": len(cleaned.split()),
                "method": "digital_pdf"
            }
    except Exception as e:
        print(f"[OCR] PyPDF2 extraction failed: {e}")

    # Try AI-based OCR (Gemini → OpenRouter)
    ai_result = extract_text_via_gemini(file_path)
    if ai_result.get('success') and ai_result.get('text'):
        return ai_result

    # Last resort: Convert PDF pages to images and Tesseract OCR
    try:
        images = convert_from_path(file_path, dpi=200)
        all_text = ""
        for img in images:
            text = pytesseract.image_to_string(img, config='--psm 3')
            all_text += text + "\n\n"
        
        cleaned = clean_ocr_text(all_text)
        if cleaned.strip():
            return {
                "success": True,
                "text": cleaned,
                "confidence": 80.0,
                "word_count": len(cleaned.split()),
                "method": "ocr_pdf"
            }
    except Exception as e:
        print(f"[OCR] Tesseract PDF OCR also failed: {e}")

    return ai_result or {"success": False, "text": "", "error": "All PDF extraction methods failed"}


def clean_ocr_text(text: str) -> str:
    """Clean and normalize OCR extracted text."""
    if not text:
        return ""
    
    # Remove excessive whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r' {3,}', ' ', text)
    
    # Fix common OCR errors
    text = text.replace('|', 'I')
    text = text.replace('0', 'O') if False else text  # Only in specific contexts
    
    # Remove non-printable characters
    text = re.sub(r'[^\x20-\x7E\n]', ' ', text)
    
    # Clean up line endings
    text = '\n'.join(line.strip() for line in text.split('\n'))
    
    return text.strip()


def allowed_file(filename: str, allowed_extensions: set = None) -> bool:
    """Check if a file extension is allowed."""
    if allowed_extensions is None:
        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'webp'}
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions


def get_file_type(filename: str) -> str:
    """Get the type of file based on extension."""
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    if ext in {'jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp'}:
        return 'image'
    elif ext == 'pdf':
        return 'pdf'
    else:
        return 'unknown'
