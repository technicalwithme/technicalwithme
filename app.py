import streamlit as st
from PIL import Image
from docx import Document
from google import genai
from google.genai import types
import json
import io

# ==========================================
# APNI API KEY YAHAN PASTE KAREIN
MY_API_KEY = "AQ.Ab8RN6ItWlGk8Jm60bjzDNpKQpfAG6XA7ZovGFLaH6b0yTg2gQ"
# ==========================================

st.set_page_config(page_title="AI Transformer Report Generator", layout="centered")
st.title("⚡ AI Transformer Report Auto-Filler")
st.write("Blank Word Format aur Handwritten Sheet upload karein. AI exact table aur headings me data fill kar dega.")

if not MY_API_KEY or MY_API_KEY == "YOUR_GEMINI_API_KEY_HERE":
    api_key = st.text_input("Gemini API Key dalein:", type="password")
else:
    api_key = MY_API_KEY
    st.success("✅ API Key loaded!")

# 1. Blank Word Format File
template_file = st.file_uploader("1. Blank Transformer Format (.docx)", type=["docx"])

# 2. Handwritten Report (Image / PDF)
uploaded_report = st.file_uploader("2. Site Engineer ki Handwritten Sheet (PDF, JPG, PNG)", type=["pdf", "jpg", "png", "jpeg"])

def get_template_text(doc):
    """Word document ke paragraphs aur tables ke structures extract karta hai"""
    structure = []
    for i, p in enumerate(doc.paragraphs):
        if p.text.strip():
            structure.append(f"Paragraph {i}: {p.text.strip()}")
            
    for t_idx, tbl in enumerate(doc.tables):
        structure.append(f"\n--- Table {t_idx} Structure ---")
        for r_idx, row in enumerate(tbl.rows):
            row_vals = [f"[Cell {c_idx}]: {cell.text.strip()}" for c_idx, cell in enumerate(row.cells)]
            structure.append(f"Row {r_idx}: " + " | ".join(row_vals))
    return "\n".join(structure)

if template_file and uploaded_report and api_key:
    if st.button("Generate Final Report"):
        with st.spinner("AI Word format aur handwritten headings ko match karke fill kar raha hai..."):
            try:
                # Load Word Template
                doc = Document(template_file)
                template_structure = get_template_text(doc)

                # Prepare File (PDF ya Compressed Image for fast upload)
                if uploaded_report.type == "application/pdf":
                    file_bytes = uploaded_report.getvalue()
                    mime_type = "application/pdf"
                else:
                    img = Image.open(uploaded_report)
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    img.thumbnail((1600, 1600))
                    buf = io.BytesIO()
                    img.save(buf, format='JPEG', quality=85)
                    file_bytes = buf.getvalue()
                    mime_type = "image/jpeg"

                client = genai.Client(api_key=api_key)
                file_part = types.Part.from_bytes(data=file_bytes, mime_type=mime_type)

                prompt = f"""
                You are an expert Electrical Engineer OCR assistant.
                
                You have two inputs:
                1. An uploaded handwritten testing report (image/PDF) written by a site engineer with various test headings (e.g. Tan-Delta, Capacitance, IR Test, Bushing test, Transformer Ratings, Dates, Remarks, Client).
                2. The structural layout of the blank Word Template:
                {template_structure}

                TASK:
                Extract the values from the handwritten document and map them directly to the corresponding Word Template locations (Paragraphs or Table Cells). Match by semantic meaning of headings.

                Return strictly a JSON object with this format:
                {{
                  "paragraph_updates": [
                    {{"index": 0, "text_to_append_or_replace": "Extracted text"}}
                  ],
                  "table_updates": [
                    {{"table_idx": 0, "row_idx": 1, "col_idx": 2, "value": "Extracted value/test reading"}}
                  ]
                }}
                """

                response = client.models.generate_content(
                    model='gemini-3.6-flash',
                    contents=[prompt, file_part],
                    config=types.GenerateContentConfig(response_mime_type="application/json")
                )

                mapping = json.loads(response.text)

                # 1. Update Paragraphs (Dates, Client, Remarks, etc.)
                for p_up in mapping.get("paragraph_updates", []):
                    idx = p_up.get("index")
                    val = p_up.get("text_to_append_or_replace", "")
                    if idx is not None and idx < len(doc.paragraphs):
                        p = doc.paragraphs[idx]
                        p.text = f"{p.text} {val}".strip()

                # 2. Update Tables (Test Results, Readings, Headings)
                for t_up in mapping.get("table_updates", []):
                    t_idx = t_up.get("table_idx", 0)
                    r_idx = t_up.get("row_idx", 0)
                    c_idx = t_up.get("col_idx", 0)
                    val = t_up.get("value", "")

                    if t_idx < len(doc.tables):
                        table = doc.tables[t_idx]
                        if r_idx < len(table.rows):
                            row = table.rows[r_idx]
                            if c_idx < len(row.cells):
                                cell = row.cells[c_idx]
                                cell.text = str(val)

                # Save output to memory
                bio = io.BytesIO()
                doc.save(bio)
                st.success("✅ Report successfully generate ho gayi!")

                st.download_button(
                    label="📥 Download Filled Word Report (.docx)",
                    data=bio.getvalue(),
                    file_name="Completed_Testing_Report.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )

            except Exception as e:
                st.error(f"Error: {e}")