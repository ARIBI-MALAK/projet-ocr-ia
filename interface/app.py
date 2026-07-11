import streamlit as st
import sys
import os
import tempfile
import json

# Permet d'importer les modules ocr et extraction depuis la racine du projet
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ocr.test_ocr import extraire_texte
from extraction.extraire_donnees import extraire_donnees

st.set_page_config(page_title="Extraction OCR + IA", page_icon="📄")

st.title("📄 Extraction de données par OCR")
st.write("Dépose une facture ou un ticket de caisse pour extraire automatiquement ses données.")

fichier = st.file_uploader("Choisis une image", type=["png", "jpg", "jpeg"])

if fichier is not None:
    st.image(fichier, caption="Document depose", width=350)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
        tmp.write(fichier.getvalue())
        chemin_temp = tmp.name

    with st.spinner("Extraction en cours..."):
        texte_brut = extraire_texte(chemin_temp)
        donnees = extraire_donnees(texte_brut)

    os.remove(chemin_temp)

    st.subheader("Texte brut extrait (OCR)")
    st.text_area("Texte", texte_brut, height=200, label_visibility="collapsed")
    st.subheader("Données structurées (JSON)")
    st.json(donnees)