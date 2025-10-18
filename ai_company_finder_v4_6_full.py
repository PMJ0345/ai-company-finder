import os
import re
import datetime
import requests
import tempfile
import streamlit as st
from openai import OpenAI
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

# ----------------------------------------------------------
# App configuration
# ----------------------------------------------------------
st.set_page_config(page_title="AI Company Finder v4.6", page_icon=":robot_face:", layout="centered")

api_key = os.environ.get("OPENAI_API_KEY")
if not api_key:
    st.error("Missing OpenAI API key. Add it under Streamlit Cloud → Settings → Secrets as 'OPENAI_API_KEY'.")
    st.stop()

client = OpenAI(api_key=api_key)

# ----------------------------------------------------------
# Questions shown before each answer
# ----------------------------------------------------------
QUESTIONS = [
    "1. What types of products do they develop?",
    "2. Which three products are their most well-known ones?",
    "3. What is their newest product, and when was it launched?",
    "4. How many people work in their product development or R&D departments?",
    "5. In which countries are their development departments located?",
    "6. Do they use external design agencies or consultants in their development work?",
    "7. Based on their profile, which specific mix of services from www.mjid.dk would likely create the highest value for them, and why?",
    "8. What could probably be the best reason for the company NOT to engage with www.mjid.dk?",
    "9. What are the 3 best counter arguments MJID.dk could use to address that concern?",
    "10. Who should MJID.dk contact to discuss possible collaboration? (include name, title, email, phone, LinkedIn if available)"
]

# ----------------------------------------------------------
# Get company info (full text answering all 10 Qs)
# ----------------------------------------------------------
def get_company_info(company_name: str) -> str:
   prompt = f"""Answer the following 10 questions about the company '{company_name}' clearly and factually in English.
Prefix each answer with the corresponding question number, e.g. "1. …", "2. …", etc.

{os.linesep.join(QUESTIONS)}
"""

Prefix each answer with the corresponding question number, e.g. "1. …", "2. …", etc.

{os.linesep.join(QUESTIONS)}
\"\"\"
    resp = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a fact-seeking research assistant that provides concise, structured answers to company-related questions."},
            {"role": "user", "content": prompt},
        ],
    )
    return resp.choices[0].message.content

# ----------------------------------------------------------
# Try to download a small company logo via Clearbit using the main domain
# ----------------------------------------------------------
def get_company_logo(company_name: str):
    try:
        domain_prompt = f"What is the main website domain of the company '{company_name}'? Return only the domain, e.g., lego.com"
        dresp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": domain_prompt}],
        )
        domain = re.sub(r"[^a-zA-Z0-9.\-]", "", (dresp.choices[0].message.content or "").strip())
        if "." not in domain:
            return None
        logo_url = f"https://logo.clearbit.com/{domain}"
        r = requests.get(logo_url, timeout=8)
        if r.status_code == 200 and r.content:
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
            tmp.write(r.content)
            tmp.close()
            return tmp.name
    except Exception:
        return None
    return None

# ----------------------------------------------------------
# Generate compact PDF with headings, initials, date, and optional logo
# ----------------------------------------------------------
def generate_pdf_v4_6(company_name: str, text: str, user_initials: str, logo_path: str | None) -> str:
    styles = getSampleStyleSheet()
    base = styles["Normal"]
    base.fontSize = 9
    base.leading = 11  # compact line spacing
    small = ParagraphStyle('small', parent=base, spaceAfter=4)
    h2 = ParagraphStyle('h2', parent=styles["Heading2"], fontSize=12, spaceAfter=6)
    h3 = ParagraphStyle('h3', parent=styles["Heading3"], fontSize=10, spaceAfter=3)
    link_style = ParagraphStyle('link_style', parent=small, textColor='blue', underline=True)

    filename = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf").name
    doc = SimpleDocTemplate(
        filename,
        pagesize=A4,
        rightMargin=1.5*cm, leftMargin=1.5*cm,
        topMargin=1.5*cm, bottomMargin=1.5*cm
    )

    elements = []

    # Header with initials and date
    date_str = datetime.date.today().strftime("%d %b %Y")
    header = f"<b>Prepared by:</b> {user_initials} &nbsp;&nbsp; <b>Date:</b> {date_str}"
    elements.append(Paragraph(header, small))
    elements.append(Spacer(1, 0.2*cm))
    elements.append(Paragraph("<b>AI Company Strategy Report</b>", h2))
    elements.append(Paragraph(f"<b>Company:</b> {company_name}", h3))

    # Logo (small, under company line)
    if logo_path:
        try:
            elements.append(Image(logo_path, width=2.5*cm, height=2.5*cm))
        except Exception:
            pass
    elements.append(Spacer(1, 0.3*cm))

    # Split the model answer by numbered questions "1.", "2.", ...
    parts = re.split(r"(?=\n?\d+\.)", text)
    for part in parts:
        if not part.strip():
            continue
        m = re.match(r"(\d+)\.\s*(.*)", part.strip(), re.DOTALL)
        if m:
            qnum, answer = m.groups()
            if qnum.isdigit():
                idx = int(qnum) - 1
                if 0 <= idx < len(QUESTIONS):
                    elements.append(Paragraph(f"<b>{QUESTIONS[idx]}</b>", h3))
            elements.append(Paragraph(answer.strip(), small))
            elements.append(Spacer(1, 0.2*cm))
        else:
            elements.append(Paragraph(part.strip(), small))

    elements.append(Spacer(1, 0.3*cm))
    elements.append(Paragraph("<i>Automatically generated by OpenAI and Streamlit (v4.6)</i>", small))
    doc.build(elements)
    return filename

# ----------------------------------------------------------
# Streamlit UI
# ----------------------------------------------------------
st.title("AI Company Finder v4.6")
st.write("Generates a structured company insight report for MJID.dk — with questions shown, logo, initials, and date.")

user_initials = st.text_input("Enter your initials (e.g. PMJ)", max_chars=6)
company_name = st.text_input("Enter company name", placeholder="e.g. Grundfos, LEGO, Danfoss...")

if st.button("Search & Generate Report", use_container_width=True):
    if not company_name.strip():
        st.warning("Please enter a company name first.")
    elif not user_initials.strip():
        st.warning("Please enter your initials.")
    else:
        with st.spinner("Generating company insights..."):
            try:
                # 1) Get answers
                answer = get_company_info(company_name)
                st.success("Report generated.")
                st.markdown(answer)

                # 2) Try logo
                st.caption("Attempting to download logo…")
                logo_path = get_company_logo(company_name)
                if logo_path:
                    st.image(logo_path, width=100, caption="Company logo")
                else:
                    st.write("(Logo not found)")

                # 3) Build PDF
                pdf_path = generate_pdf_v4_6(company_name, answer, user_initials, logo_path)
                with open(pdf_path, "rb") as f:
                    st.download_button(
                        label="Download PDF Report",
                        data=f,
                        file_name=f"{company_name}_AI_Report.pdf",
                        mime="application/pdf",
                    )
            except Exception as e:
                st.error(f"An error occurred: {e}")

st.markdown('---')
st.caption("Developed for MJID.dk · v4.6 · Streamlit & OpenAI")
