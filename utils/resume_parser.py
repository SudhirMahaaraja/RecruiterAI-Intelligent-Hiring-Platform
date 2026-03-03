"""
Resume parser supporting PDF and DOCX formats.
"""
import os


def parse_resume(file_obj, ext):
    """Parse resume file object and extract text content."""
    
    if ext == '.pdf':
        return _parse_pdf(file_obj)
    elif ext in ('.doc', '.docx'):
        return _parse_docx(file_obj)
    else:
        return ''


def _parse_pdf(file_obj):
    """Extract text from PDF file object."""
    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(file_obj)
        text = ''
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + '\n'
        return text.strip()
    except Exception as e:
        print(f"Error parsing PDF: {e}")
        return ''


def _parse_docx(file_obj):
    """Extract text from DOCX file object."""
    try:
        from docx import Document
        import io
        
        # docx needs bytes-like obj to be passed directly
        doc = Document(io.BytesIO(file_obj.read()))
        text = '\n'.join([para.text for para in doc.paragraphs if para.text.strip()])
        return text.strip()
    except Exception as e:
        print(f"Error parsing DOCX: {e}")
        return ''

# Auto-commit: Enhance resume parsing for technical skills - 2026-03-04 17:53:54
