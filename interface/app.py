import streamlit as st
import sys
import os
import tempfile
import json
import pandas as pd
import altair as alt

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ocr.test_ocr import extraire_texte
from extraction.extraire_donnees import extraire_donnees
from extraction.extraire_donnees_llm import extraire_donnees_llm
from anonymisation.anonymiser import anonymiser_donnees
from preprocessing.ameliorer_image import ameliorer_image

st.set_page_config(page_title="Extraction OCR + IA", page_icon="⚡", layout="wide")

# ---------------------------------------------------------------
# STYLE — Palette Noir + Bleu électrique
# ---------------------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

.stApp {
    background: radial-gradient(circle at 15% 0%, #12121a 0%, #0A0A0F 55%);
    color: #F5F5F7;
}

section[data-testid="stSidebar"] {
    background-color: #101014;
}

.hero {
    padding: 2.2rem 2rem;
    border-radius: 18px;
    background: linear-gradient(135deg, rgba(59,130,246,0.18) 0%, rgba(10,10,15,0.4) 100%);
    border: 1px solid rgba(96,165,250,0.25);
    margin-bottom: 1.8rem;
    backdrop-filter: blur(6px);
}
.hero h1 {
    font-size: 2rem;
    font-weight: 800;
    margin: 0;
    background: linear-gradient(90deg, #F5F5F7, #93C5FD);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}
.hero p {
    color: #A1A1AA;
    font-size: 0.95rem;
    margin-top: 0.4rem;
}

.carte {
    background: rgba(21, 21, 25, 0.75);
    border: 1px solid rgba(96,165,250,0.15);
    border-radius: 14px;
    padding: 1.3rem 1.5rem;
    margin-bottom: 1rem;
    backdrop-filter: blur(8px);
    transition: border-color 0.2s ease, transform 0.2s ease;
}
.carte:hover {
    border-color: rgba(96,165,250,0.5);
    transform: translateY(-2px);
}

.titre-section {
    font-size: 1.05rem;
    font-weight: 700;
    margin: 0.4rem 0 0.8rem 0;
    color: #F5F5F7;
    border-left: 3px solid #3B82F6;
    padding-left: 10px;
}

.badge-ok {
    background: rgba(34,197,94,0.15);
    color: #4ADE80;
    border: 1px solid rgba(34,197,94,0.35);
    padding: 2px 12px;
    border-radius: 20px;
    font-size: 0.78rem;
    font-weight: 600;
}
.badge-ko {
    background: rgba(239,68,68,0.15);
    color: #F87171;
    border: 1px solid rgba(239,68,68,0.35);
    padding: 2px 12px;
    border-radius: 20px;
    font-size: 0.78rem;
    font-weight: 600;
}

.stTabs [data-baseweb="tab-list"] {
    gap: 6px;
}
.stTabs [data-baseweb="tab"] {
    background-color: rgba(21,21,25,0.6);
    border-radius: 10px 10px 0 0;
    color: #A1A1AA;
    border: 1px solid rgba(96,165,250,0.1);
    padding: 8px 18px;
}
.stTabs [aria-selected="true"] {
    background-color: rgba(59,130,246,0.18) !important;
    color: #F5F5F7 !important;
    border-color: rgba(96,165,250,0.4) !important;
}

div[data-testid="stMetric"] {
    background: rgba(21,21,25,0.7);
    border: 1px solid rgba(96,165,250,0.15);
    border-radius: 12px;
    padding: 0.8rem 1rem;
}

.stButton > button, .stDownloadButton > button {
    background: linear-gradient(90deg, #3B82F6, #60A5FA);
    color: #0A0A0F;
    font-weight: 700;
    border: none;
    border-radius: 10px;
    transition: transform 0.15s ease, box-shadow 0.15s ease;
}
.stButton > button:hover, .stDownloadButton > button:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 18px rgba(59,130,246,0.4);
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
    <h1>⚡ Extraction de données par OCR + IA</h1>
    <p>Projet de stage PFA — VIRTUO / Groupe EDGE — Pipeline OCR, prétraitement d'image et extraction intelligente</p>
</div>
""", unsafe_allow_html=True)

onglet_extraction, onglet_pretraitement, onglet_evaluation = st.tabs(
    ["🔍  Extraction", "🖼️  Prétraitement d'image", "📊  Évaluation"]
)

# =================================================================
# ONGLET 1 — EXTRACTION (regex vs LLM côte à côte)
# =================================================================
with onglet_extraction:
    st.markdown('<div class="titre-section">1. Charger un document</div>', unsafe_allow_html=True)

    col_upload, col_options = st.columns([2, 1])

    with col_upload:
        fichier = st.file_uploader("Choisis une image", type=["png", "jpg", "jpeg"], key="upload_extraction")

    with col_options:
        appliquer_pretraitement = st.checkbox("Appliquer le prétraitement d'image", value=False)
        appliquer_anonymisation = st.checkbox("Anonymiser les champs sensibles", value=False)

    if fichier is not None:
        st.image(fichier, caption="Document déposé", width=280)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            tmp.write(fichier.getvalue())
            chemin_temp = tmp.name

        chemin_a_traiter = chemin_temp
        chemin_pretraite = None

        if appliquer_pretraitement:
            chemin_pretraite = chemin_temp.replace(".png", "_pretraite.png")
            with st.spinner("Prétraitement de l'image en cours..."):
                ameliorer_image(chemin_temp, chemin_pretraite)
            chemin_a_traiter = chemin_pretraite

        with st.spinner("Extraction OCR + IA en cours..."):
            texte_brut = extraire_texte(chemin_a_traiter)
            donnees_regex = extraire_donnees(texte_brut)
            donnees_llm = extraire_donnees_llm(texte_brut)

            if appliquer_anonymisation:
                if isinstance(donnees_regex, dict):
                    donnees_regex = anonymiser_donnees(donnees_regex)
                if isinstance(donnees_llm, dict):
                    donnees_llm = anonymiser_donnees(donnees_llm)

        os.remove(chemin_temp)
        if chemin_pretraite and os.path.exists(chemin_pretraite):
            os.remove(chemin_pretraite)

        st.markdown('<div class="titre-section">2. Texte brut extrait (OCR)</div>', unsafe_allow_html=True)
        with st.expander("Voir le texte OCR", expanded=False):
            st.text_area("Texte", texte_brut, height=150, label_visibility="collapsed")

        st.markdown('<div class="titre-section">3. Comparaison des méthodes d\'extraction</div>', unsafe_allow_html=True)

        col_regex, col_llm = st.columns(2)

        with col_regex:
            st.markdown('<div class="carte">', unsafe_allow_html=True)
            st.markdown("**⚙️ Méthode : Regex (règles simples)**")
            st.json(donnees_regex)
            st.markdown('</div>', unsafe_allow_html=True)

        with col_llm:
            st.markdown('<div class="carte">', unsafe_allow_html=True)
            st.markdown("**🤖 Méthode : IA (Gemini)**")
            st.json(donnees_llm)
            st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info("Dépose une facture ou un ticket de caisse pour lancer l'extraction.")

# =================================================================
# ONGLET 2 — PRÉTRAITEMENT (avant / après)
# =================================================================
with onglet_pretraitement:
    st.markdown('<div class="titre-section">Comparer l\'OCR avant / après prétraitement</div>', unsafe_allow_html=True)
    st.caption("Utile pour les documents dégradés : penchés, bruités, mal éclairés.")

    fichier_pretrait = st.file_uploader("Choisis une image dégradée", type=["png", "jpg", "jpeg"], key="upload_pretraitement")

    if fichier_pretrait is not None:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            tmp.write(fichier_pretrait.getvalue())
            chemin_original = tmp.name

        chemin_ameliore = chemin_original.replace(".png", "_ameliore.png")

        with st.spinner("Application du prétraitement..."):
            ameliorer_image(chemin_original, chemin_ameliore)
            texte_avant = extraire_texte(chemin_original)
            texte_apres = extraire_texte(chemin_ameliore)

        col_avant, col_apres = st.columns(2)

        with col_avant:
            st.markdown('<div class="carte">', unsafe_allow_html=True)
            st.markdown("**📷 Image originale**")
            st.image(chemin_original, use_container_width=True)
            st.markdown(f"**Texte OCR obtenu** ({len(texte_avant.strip())} caractères) :")
            st.text_area("avant", texte_avant, height=180, label_visibility="collapsed", key="ta_avant")
            st.markdown('</div>', unsafe_allow_html=True)

        with col_apres:
            st.markdown('<div class="carte">', unsafe_allow_html=True)
            st.markdown("**✨ Image après prétraitement**")
            st.image(chemin_ameliore, use_container_width=True)
            st.markdown(f"**Texte OCR obtenu** ({len(texte_apres.strip())} caractères) :")
            st.text_area("apres", texte_apres, height=180, label_visibility="collapsed", key="ta_apres")
            st.markdown('</div>', unsafe_allow_html=True)

        gain = len(texte_apres.strip()) - len(texte_avant.strip())
        if gain > 0:
            st.markdown(f'<span class="badge-ok">+{gain} caractères récupérés grâce au prétraitement</span>', unsafe_allow_html=True)
        elif gain == 0:
            st.markdown('<span class="badge-ko">Aucun gain mesuré sur ce document</span>', unsafe_allow_html=True)
        else:
            st.markdown(f'<span class="badge-ko">{gain} caractères (le prétraitement a dégradé le résultat ici)</span>', unsafe_allow_html=True)

        os.remove(chemin_original)
        os.remove(chemin_ameliore)
    else:
        st.info("Dépose une image dégradée (ex: ticket_degrade.png) pour voir l'effet du prétraitement.")

# =================================================================
# ONGLET 3 — ÉVALUATION (résultats du protocole regex vs LLM)
# =================================================================
with onglet_evaluation:
    st.markdown('<div class="titre-section">Résultats du protocole d\'évaluation</div>', unsafe_allow_html=True)
    st.caption("Comparaison automatique regex vs LLM sur 15 documents, par rapport à la vérité terrain.")

    chemin_resultats = os.path.join(os.path.dirname(__file__), "..", "evaluation", "resultats_evaluation.json")

    if os.path.exists(chemin_resultats):
        with open(chemin_resultats, "r", encoding="utf-8") as f:
            resultats = json.load(f)

        compteurs = resultats["compteurs"]
        champs = list(compteurs["regex"].keys())

        lignes_tableau = []
        taux_regex_liste = []
        taux_llm_liste = []

        for champ in champs:
            for methode in ["regex", "llm"]:
                c = compteurs[methode][champ]
                total = sum(c.values())
                corrects = c["correct_present"] + c["correct_absent"]
                taux = round((corrects / total * 100), 1) if total > 0 else 0
                if methode == "regex":
                    taux_regex_liste.append(taux)
                else:
                    taux_llm_liste.append(taux)
            lignes_tableau.append({
                "Champ": champ,
                "Regex (%)": taux_regex_liste[-1],
                "LLM (%)": taux_llm_liste[-1],
            })

        col_stat1, col_stat2, col_stat3 = st.columns(3)
        with col_stat1:
            st.metric("Documents évalués", len(resultats["details"]) // 2)
        with col_stat2:
            st.metric("Taux moyen Regex", f"{round(sum(taux_regex_liste)/len(taux_regex_liste), 1)}%")
        with col_stat3:
            st.metric("Taux moyen LLM", f"{round(sum(taux_llm_liste)/len(taux_llm_liste), 1)}%",
                       delta=f"+{round(sum(taux_llm_liste)/len(taux_llm_liste) - sum(taux_regex_liste)/len(taux_regex_liste), 1)} pts")

        st.markdown("**Taux de réussite par champ**")

        df_long = pd.DataFrame(lignes_tableau).melt(
            id_vars="Champ", value_vars=["Regex (%)", "LLM (%)"],
            var_name="Méthode", value_name="Taux"
        )

        graphique = alt.Chart(df_long).mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
            x=alt.X("Champ:N", title=None, axis=alt.Axis(labelAngle=-30, labelColor="#A1A1AA", labelLimit=200)),
            y=alt.Y("Taux:Q", title="Taux de réussite (%)", scale=alt.Scale(domain=[0, 100]),
                    axis=alt.Axis(labelColor="#A1A1AA", titleColor="#A1A1AA", gridColor="#26262e")),
            color=alt.Color("Méthode:N",
                             scale=alt.Scale(domain=["Regex (%)", "LLM (%)"], range=["#64748B", "#3B82F6"]),
                             legend=alt.Legend(title=None, labelColor="#F5F5F7", orient="top")),
            xOffset="Méthode:N",
            tooltip=["Champ", "Méthode", "Taux"]
        ).properties(height=340, background="transparent").configure_view(strokeWidth=0)

        st.altair_chart(graphique, use_container_width=True)

        st.markdown("**Détail par champ**")
        df_affichage = pd.DataFrame(lignes_tableau).set_index("Champ")
        st.dataframe(df_affichage, use_container_width=True)

        with st.expander("Voir le détail document par document"):
            for ligne in resultats["details"]:
                methode_label = "🤖 LLM" if ligne["methode"] == "llm" else "⚙️ Regex"
                st.markdown(f"**{ligne['document']}** — {methode_label}")
                cols = st.columns(len(champs))
                for i, champ in enumerate(champs):
                    info = ligne.get(champ, {})
                    cat = info.get("categorie", "")
                    ok = cat in ("correct_present", "correct_absent")
                    badge = '<span class="badge-ok">✓</span>' if ok else '<span class="badge-ko">✗</span>'
                    with cols[i]:
                        st.markdown(f"{champ}<br>{badge}", unsafe_allow_html=True)
                st.divider()
    else:
        st.warning("Aucun résultat d'évaluation trouvé. Lance d'abord `python -m evaluation.evaluer` pour générer `evaluation/resultats_evaluation.json`.")
