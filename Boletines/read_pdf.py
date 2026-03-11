import sys

def read_pdf(file_path):
    try:
        import fitz
        doc = fitz.open(file_path)
        for page in doc:
            print(page.get_text())
        return
    except ImportError:
        pass
        
    try:
        import PyPDF2
        reader = PyPDF2.PdfReader(file_path)
        for page in reader.pages:
            print(page.extract_text())
        return
    except Exception as e:
        print(f"Error PyPDF2: {e}")
        pass

    try:
        from pdfminer.high_level import extract_text
        text = extract_text(file_path)
        print(text)
        return
    except ImportError:
        pass

    print("No PDF library found! Please install PyMuPDF, PyPDF2 or pdfminer.six")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        read_pdf(sys.argv[1])
