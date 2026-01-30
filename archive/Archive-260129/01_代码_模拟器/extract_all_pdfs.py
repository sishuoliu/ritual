import os
import pdfplumber

def extract_pdf_to_txt(pdf_path, txt_path):
    """Extract text from PDF and save to TXT file."""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            all_text = []
            for i, page in enumerate(pdf.pages):
                text = page.extract_text()
                if text:
                    all_text.append(f"--- Page {i+1} ---\n{text}")
            
            full_text = "\n\n".join(all_text)
            
            with open(txt_path, 'w', encoding='utf-8') as f:
                f.write(full_text)
            
            return True, len(pdf.pages)
    except Exception as e:
        return False, str(e)

def main():
    resources_dir = r"d:\Users\liusishuo\Desktop\MBS\ritul\resources"
    
    # Get all PDF files
    pdf_files = [f for f in os.listdir(resources_dir) if f.lower().endswith('.pdf')]
    
    print(f"Found {len(pdf_files)} PDF files to process.\n")
    
    success_count = 0
    failed_files = []
    
    for pdf_file in pdf_files:
        pdf_path = os.path.join(resources_dir, pdf_file)
        txt_filename = os.path.splitext(pdf_file)[0] + '.txt'
        txt_path = os.path.join(resources_dir, txt_filename)
        
        print(f"Processing: {pdf_file}...")
        success, result = extract_pdf_to_txt(pdf_path, txt_path)
        
        if success:
            print(f"  [OK] Success - {result} pages extracted")
            success_count += 1
        else:
            print(f"  [FAIL] Failed - {result}")
            failed_files.append((pdf_file, result))
    
    print(f"\n{'='*60}")
    print(f"Completed: {success_count}/{len(pdf_files)} files processed successfully")
    
    if failed_files:
        print(f"\nFailed files:")
        for f, err in failed_files:
            print(f"  - {f}: {err}")

if __name__ == "__main__":
    main()
