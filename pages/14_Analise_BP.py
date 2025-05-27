import streamlit as st
import pdfplumber
import pandas as pd
from io import BytesIO
import openai
from dotenv import load_dotenv
import os
import logging
import hashlib
from pathlib import Path
import re
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.shapes import MSO_AUTO_SHAPE_TYPE
from pptx.dml.color import RGBColor
import tempfile

logging.basicConfig(level=logging.INFO)
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

st.set_page_config(page_title="📘 Análise do Balanço Patrimonial", layout="wide")
st.title("📘 Análise do Balanço Patrimonial")

st.markdown("""
Esta ferramenta permite fazer upload de múltiplos PDFs contendo demonstrações contábeis (Balanço Patrimonial, DRE, DFC) e extrair automaticamente os dados para análise detalhada.
""")

def extrair_texto_pdf_para_envio(pdf_bytes):
    try:
        with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
            texto_total = ""
            for pagina in pdf.pages:
                texto = pagina.extract_text()
                if texto:
                    texto_total += texto + "\n"
        return texto_total
    except Exception as e:
        logging.error(f"Erro ao extrair texto do PDF: {e}")
        return ""

def enviar_para_chatgpt(texto_pdf):
    prompt = f"""
    Você receberá abaixo o conteúdo completo de documentos financeiros extraídos em texto de PDFs. Os documentos podem incluir o Balanço Patrimonial, Demonstração de Resultados (DRE) e Fluxo de Caixa.

    Sua função agora é atuar como um consultor financeiro experiente.

    Seu objetivo:
    1. Analisar as demonstrações fornecidas e gerar os principais **indicadores financeiros**:
       - Liquidez Corrente, Liquidez Seca
       - Margem Bruta, Margem Operacional, Margem Líquida
       - ROE, ROA, Giro do Ativo, EBITDA, Endividamento, entre outros
    2. Identificar **pontos de atenção ou risco**, tanto operacionais quanto financeiros.
    3. Gerar um **parecer técnico** estruturado como faria um analista de investimentos.
    4. Retornar as conclusões com clareza, utilizando bullet points, quadros ou resumos numéricos sempre que possível.
    5. Organizar as seções de forma lógica e com títulos: Ex: _"Indicadores de Liquidez"_, _"Eficiência Operacional"_, _"Rentabilidade"_, _"Parecer Técnico"_.
    6. Com base nas análises e KPIs gerados, elabore o conteúdo de uma apresentação de slides (PowerPoint) com:
       - Título
       - Sumário
       - Indicadores (em formato de tabela ou bullet points)
       - Gráficos sugeridos (descreva o que mostrar em cada um)
       - Slide com Parecer Técnico
       - Slides extras se necessário

    O objetivo é apresentar essas informações de forma executiva a um cliente ou investidor.

    No final, me diga os textos e estrutura para que eu possa gerar esse PowerPoint automaticamente.

    ⚠️ Importante:
    - Sempre escreva as fórmulas de forma descritiva e legível para humanos. 
    - Evite sintaxe LaTeX como \\( \\frac{{}}{{}} \\), pois ela não será renderizada.
    - Em vez disso, use formato texto como:
      - "Liquidez Corrente = Ativo Circulante (29.199,97) ÷ Passivo Circulante (65.472,92) = 0,45"
      - "ROE = Lucro Líquido (361.147) ÷ Patrimônio Líquido (31.566,81) = 1.144,8%"

    Aqui está o conteúdo dos documentos:
    
    {texto_pdf}
    """
    try:
        response = openai.chat.completions.create(
            model="gpt-4-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4000
        )
        return response.choices[0].message.content
    except Exception as e:
        logging.error(f"Erro ao enviar para o ChatGPT: {e}")
        return ""

def gerar_apresentacao(resposta_texto, logo_bytes=None):
    prs = Presentation()
    layout_titulo = prs.slide_layouts[5]
    layout_conteudo = prs.slide_layouts[5]

    slide_titulo = prs.slides.add_slide(layout_titulo)
    if slide_titulo.shapes.title:
        slide_titulo.shapes.title.text = "ANÁLISE FINANCEIRA - GPT"
        slide_titulo.shapes.title.text_frame.paragraphs[0].font.size = Pt(36)
        slide_titulo.shapes.title.text_frame.paragraphs[0].font.bold = True
    if logo_bytes:
        try:
            image_stream = BytesIO(logo_bytes)
            slide_titulo.shapes.add_picture(image_stream, Inches(6.5), Inches(4.5), height=Inches(1))
        except Exception as e:
            logging.warning(f"Erro ao adicionar logotipo ao slide inicial: {e}")

    icones = {
        "liquidez": "📊", "eficiência": "⚙️", "rentabilidade": "💰",
        "risco": "⚠️", "parecer": "🧠", "indicadores": "📌",
        "sumário": "🗂️", "gráfico": "📈"
    }
    cores_secoes = [
        RGBColor(0, 51, 102), RGBColor(0, 102, 0),
        RGBColor(153, 0, 0), RGBColor(102, 51, 0), RGBColor(51, 0, 102)
    ]

    secoes = re.split(r"###+\s*", resposta_texto)
    cor_index = 0

    for secao in secoes:
        if not secao.strip() or "estrutura para powerpoint" in secao.lower():
            continue
        linhas = secao.strip().splitlines()
        if not linhas:
            continue
        titulo_raw = linhas[0].strip()
        conteudo = "\n".join(linhas[1:]).strip()
        if not conteudo:
            continue

        cor_secao = cores_secoes[cor_index % len(cores_secoes)]
        cor_index += 1
        titulo_lower = titulo_raw.lower()
        icone = next((ico for chave, ico in icones.items() if chave in titulo_lower), "📄")
        titulo = f"{icone} {titulo_raw.upper()}"

        slide = prs.slides.add_slide(layout_conteudo)
        title_box = slide.shapes.add_textbox(Inches(0.5), Inches(0.4), Inches(8.5), Inches(1))
        title_frame = title_box.text_frame
        title_frame.text = titulo
        title_frame.paragraphs[0].font.size = Pt(28)
        title_frame.paragraphs[0].font.bold = True
        title_frame.paragraphs[0].font.color.rgb = cor_secao

        textbox_shape = slide.shapes.add_textbox(Inches(0.5), Inches(1.2), Inches(8.5), Inches(4.5))
        textbox_frame = textbox_shape.text_frame
        textbox_frame.word_wrap = True
        for par in conteudo.split("\n"):
            p = textbox_frame.add_paragraph()
            p.text = par.strip()
            p.font.size = Pt(16)
            p.font.name = "Calibri"
        textbox_frame.paragraphs[0].text = ""

        footer_line = slide.shapes.add_shape(
            MSO_AUTO_SHAPE_TYPE.RECTANGLE,
            Inches(0), Inches(5.2), prs.slide_width, Inches(0.05)
        )
        footer_line.fill.solid()
        footer_line.fill.fore_color.rgb = RGBColor(200, 200, 200)
        footer_line.line.fill.background()

        if logo_bytes:
            try:
                image_stream = BytesIO(logo_bytes)
                slide.shapes.add_picture(image_stream, Inches(6.8), Inches(5.3), height=Inches(0.4))
            except Exception as e:
                logging.warning(f"Erro ao adicionar logotipo ao rodapé: {e}")

        footer_box = slide.shapes.add_textbox(Inches(0.3), Inches(5.25), Inches(6), Inches(0.3))
        footer_frame = footer_box.text_frame
        footer_frame.text = "Gerado por MR Consultoria"
        footer_frame.paragraphs[0].font.size = Pt(10)
        footer_frame.paragraphs[0].font.color.rgb = RGBColor(100, 100, 100)

    temp_path = tempfile.NamedTemporaryFile(delete=False, suffix=".pptx")
    prs.save(temp_path.name)
    return temp_path.name

uploaded_files = st.file_uploader("Faça upload dos PDFs com Balanço, DRE e DFC", type=["pdf"], accept_multiple_files=True)
logo_file = st.file_uploader("📌 Envie seu logotipo para incluir no PowerPoint (opcional)", type=["png", "jpg", "jpeg"])

if uploaded_files:
    forcar_envio = st.checkbox("🔁 Forçar nova consulta ao ChatGPT", value=False)

    textos_combinados = ""
    for arquivo in uploaded_files:
        conteudo = arquivo.read()
        try:
            texto_extraido = extrair_texto_pdf_para_envio(conteudo)
            textos_combinados += texto_extraido + "\n\n"
        except Exception as e:
            st.warning(f"⚠️ Erro ao processar {arquivo.name}: {e}")

    if st.button("📩 Enviar documentos para análise do GPT"):
        if not textos_combinados.strip():
            st.warning("Nenhum texto foi extraído dos PDFs enviados.")
        else:
            cache_dir = Path(".cache_chatgpt")
            cache_dir.mkdir(exist_ok=True)
            conteudo_hash = hashlib.sha256(textos_combinados.encode("utf-8")).hexdigest()
            cache_path = cache_dir / f"{conteudo_hash}.txt"

            if cache_path.exists() and not forcar_envio:
                resposta = cache_path.read_text()
                st.info("✅ Usando resposta do ChatGPT armazenada em cache.")
            else:
                with st.spinner("🔄 Enviando documentos para o ChatGPT e aguardando resposta..."):
                    resposta = enviar_para_chatgpt(textos_combinados)
                    if resposta.strip():
                        cache_path.write_text(resposta)

            if not resposta.strip():
                st.warning("A resposta do ChatGPT veio vazia. Verifique os arquivos ou tente novamente.")
            else:
                st.session_state["resposta_chatgpt"] = resposta

if "resposta_chatgpt" in st.session_state:
    resposta = st.session_state["resposta_chatgpt"]
    st.markdown("### 🧠 Parecer técnico gerado pelo ChatGPT")
    st.code(resposta, language="markdown")

    if st.button("📥 Baixar apresentação em PowerPoint"):
        logo_data = logo_file.read() if logo_file else None
        pptx_path = gerar_apresentacao(resposta, logo_data)
        with open(pptx_path, "rb") as f:
            st.download_button(
                label="📊 Download .pptx",
                data=f,
                file_name="Analise_Financeira_GPT.pptx",
                mime="application/vnd.openxmlformats-officedocument.presentationml.presentation"
            )