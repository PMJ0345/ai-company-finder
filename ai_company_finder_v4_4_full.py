import os
import streamlit as st
from openai import OpenAI
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
import tempfile
import re

# ----------------------------------------------------------
# ⚙️ CONFIGURATION
# ----------------------------------------------------------
st.set_page_config(page_title="AI Company Finder v4.5", page_icon=":robot_face:", layout="centered")

# Load API key
api_key = os.environ.get("OPENAI_API_KEY")
if not api_key:
    st.error("Missing OpenAI API key. Add it under Streamlit Cloud → Settings → Secrets as 'OPENAI_API_KEY'.")
    st.stop()

client = OpenAI(api_key=api_key)

# ----------------------------------------------------------
# 🧠 FUNCTION TO FETCH COMPANY INFO
# ----------------------------------------------------------
def get_company_info(company_name, mode="full"):
    if mode == "full":
        prompt = f"""
You are a fact-seeking AI assistant with access to your most recent knowledge.

Find and summarise the following for the company '{company_name}':

1. What types of products do they develop? (max 5 lines)
2. Which three products are their most well-known ones? (include image links if available)
3. What is their newest product, and when was it launched?
4. How many people work in their product development or R&D departments? (estimate if unknown)
5. In which countries are their development departments located?
6. Do they use external design agencies or consultants in their development work?
7. Based on their profile, describe which specific mix of services from www.mjid.dk 
   (choose from: Concept Design, Industrial Design, Mechanical Engineering, Prototype Building, User Testing, or Innovation Strategy)
   would likely create the highest value for them, and why.
8. What could probably be the best reason for the company NOT to engage with www.mjid.dk?
9. What are the 3 best counter arguments MJID.dk could use to address that concern?
10. Who should MJID.dk contact to discuss possible collaboration? Include 1–3 persons, with title, email (if public), phone number (if public), and LinkedIn profile if available.

Answer clearly and concisely in English.
If information is unavailable, write "Unknown".
"""
    else:
        prompt = f"""
Summarise the company '{company_name}' in a concise 1–2 paragraph overview that includes:
- main product types
- top 3 products
- newest product and launch date
- approximate R&D size
- use of external design agencies
- MJID.dk service fit
- any main potential objection
- 1–2 key counter-arguments MJID could use
- recommended contact persons for collaboration (if available)
"""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a fact-seeking research assistant that summarises company information clearly and concisely in English."},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content

# ----------------------------------------------------------
# 📄 FUNCTION TO GENERATE STRUCTURED PDF
# ----------------------------------------------------------
def generate_pdf_v4_5(company_name, text):
    styles = getSampleStyleSheet()
    link_style = ParagraphStyle('link_style', parent=styles['Normal'], textColor='blue', underline=True)

    doc = SimpleDocTemplate(
        tempfile.NamedTemporaryFile(delete=False, suffix=".pdf").name,
        pagesize=A4,
        rightMargin=2*cm, leftMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm
    )

    sections = {
        "Company Overview": [],
        "R&D": [],
        "External Design Use": [],
        "MJID.dk Service Fit": [],
        "Potential Objection": [],
        "Counter-Arguments": [],
        "Recommended Contacts": []
    }

    mapping = {
        "products": "Company Overview",
        "top products": "Company Overview",
        "newest product": "Company Overview",
        "r&d": "R&D",
        "development departments": "R&D",
        "external design": "External Design Use",
        "mjid.dk": "MJID.dk Service Fit",
        "objection": "Potential Objection",
        "counter": "Counter-Arguments",
        "contact": "Recommended Contacts"
    }

    for line in text.splitlines():
        assigned = False
        for keyword, section in mapping.items():
            if keyword in line.lower():
                sections[section].append(line)
                assigned = True
                break
        if not assigned:
            sections["Company Overview"].append(line)

    elements = [
        Paragraph("<b>AI Company Strategy Report</b>", styles["Title"]),
        Spacer(1, 0.5*cm),
        Paragraph(f"<b>Company:</b> {company_name}", styles["Heading2"]),
        Spacer(1, 0.3*cm)
    ]

    for title, content_lines in sections.items():
        if not content_lines:
            continue
        elements.append(Paragraph(f"<b>{title}</b>", styles["Heading3"]))
        elements.append(Spacer(1, 0.2*cm))
        if title == "Recommended Contacts":
            def hyperlink_text(line):
                line = re.sub(r'(\S+@\S+\.\S+)', r'<a href=\"mailto:\1\">\1</a>', line)
                line = re.sub(r'(https?://[^\s]+linkedin[^\s]*)', r'<a href=\"\1\">\1</a>', line)
                return line
            content_lines = [hyperlink_text(l) for l in content_lines if l.strip()]
            elements.append(Paragraph("<br/>".join(content_lines), link_style))
        else:
            elements.append(Paragraph("<br/>".join(content_lines), styles["Normal"]))
        elements.append(Spacer(1, 0.3*cm))

    elements.append(Paragraph("<i>Automatically generated by OpenAI and Streamlit</i>", styles["Italic"]))
    doc.build(elements)
    return doc.filename

# ----------------------------------------------------------
# 🌐 STREAMLIT APP
# ----------------------------------------------------------
st.title("🤖 AI Company Finder v4.5")
st.write("Retrieve company facts, product insights, R&D data, and strategic collaboration analysis for MJID.dk.")

company_name = st.text_input("🔍 Enter company name", placeholder="e.g. Grundfos, LEGO, Danfoss...")
mode = st.radio("Select report mode:", options=["Full detail", "Short summary"], horizontal=True)

if st.button("Search", use_container_width=True):
    if not company_name.strip():
        st.warning("Please enter a company name first.")
    else:
        with st.spinner("Searching online..."):
            try:
                mode_sel = "full" if mode == "Full detail" else "short"
                answer = get_company_info(company_name, mode_sel)
                st.success("✅ Information found:")
                st.markdown(answer)

                if mode_sel == "full":
                    links = re.findall(r'(https?://\S+\.(?:jpg|png|jpeg|webp))', answer)
                    if links:
                        st.write("📸 Found product images:")
                        for link in links[:3]:
                            st.image(link, width=200)

                pdf_path = generate_pdf_v4_5(company_name, answer)
                with open(pdf_path, "rb") as f:
                    st.download_button(
                        label="📄 Download as PDF",
                        data=f,
                        file_name=f"{company_name}_AI_Report.pdf",
                        mime="application/pdf"
                    )

            except Exception as e:
                st.error(f"❌ An error occurred: {e}")

st.markdown("---")
st.caption("Developed by your AI assistant 🤖 · Version 4.5 · Streamlit & OpenAI")

