import streamlit as st
import sys
import os
import tempfile
import json
import time
import hashlib
import io
import pandas as pd
import altair as alt

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ocr.test_ocr import extraire_texte
from extraction.extraire_donnees import extraire_donnees
from extraction.extraire_donnees_llm import extraire_donnees_llm
from anonymisation.anonymiser import anonymiser_donnees
from preprocessing.ameliorer_image import ameliorer_image

TAILLE_MAX_MO = 15

st.set_page_config(page_title="Extraction OCR + IA", page_icon="⚡", layout="wide")

# ---------------------------------------------------------------
# FONCTIONS ROBUSTES (cache + retry + gestion d'erreurs)
# ---------------------------------------------------------------

@st.cache_data(show_spinner=False)
def _ocr_avec_cache(contenu_bytes: bytes, suffixe: str) -> str:
    """Extrait le texte OCR, mis en cache par empreinte du contenu du fichier."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffixe) as tmp:
        tmp.write(contenu_bytes)
        chemin = tmp.name
    try:
        texte = extraire_texte(chemin)
    finally:
        if os.path.exists(chemin):
            os.remove(chemin)
    return texte


@st.cache_data(show_spinner=False)
def _pretraitement_avec_cache(contenu_bytes: bytes, suffixe: str) -> bytes:
    """Applique le prétraitement d'image, mis en cache par empreinte du contenu."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffixe) as tmp:
        tmp.write(contenu_bytes)
        chemin_original = tmp.name
    chemin_sortie = chemin_original.replace(suffixe, f"_pretraite{suffixe}")
    try:
        ameliorer_image(chemin_original, chemin_sortie)
        with open(chemin_sortie, "rb") as f:
            resultat = f.read()
    finally:
        for c in (chemin_original, chemin_sortie):
            if os.path.exists(c):
                os.remove(c)
    return resultat


def extraction_llm_avec_retry(texte, tentatives=2):
    """Appelle l'extraction LLM avec une nouvelle tentative en cas d'erreur réseau/API."""
    derniere_erreur = None
    for essai in range(tentatives):
        try:
            return extraire_donnees_llm(texte), None
        except Exception as e:
            derniere_erreur = str(e)
            if essai < tentatives - 1:
                time.sleep(1.5)
    return None, derniere_erreur


def extraction_regex_securisee(texte):
    """Appelle l'extraction regex en capturant toute exception inattendue."""
    try:
        return extraire_donnees(texte), None
    except Exception as e:
        return None, str(e)


def fichier_valide(fichier_uploade) -> tuple[bool, str]:
    """Vérifie la taille et l'ouverture correcte du fichier avant traitement."""
    taille_mo = len(fichier_uploade.getvalue()) / (1024 * 1024)
    if taille_mo > TAILLE_MAX_MO:
        return False, f"Fichier trop volumineux ({taille_mo:.1f} Mo). Limite : {TAILLE_MAX_MO} Mo."
    try:
        from PIL import Image
        Image.open(io.BytesIO(fichier_uploade.getvalue())).verify()
    except Exception:
        return False, "Le fichier ne semble pas être une image valide ou est corrompu."
    return True, ""


def ajouter_a_historique(nom_fichier, methode, succes):
    """Enregistre un document traité dans l'historique de session."""
    if "historique" not in st.session_state:
        st.session_state.historique = []
    st.session_state.historique.insert(0, {
        "fichier": nom_fichier,
        "methode": methode,
        "heure": time.strftime("%H:%M:%S"),
        "succes": succes,
    })
    st.session_state.historique = st.session_state.historique[:8]

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

.stTextArea textarea {
    background-color: #151519 !important;
    color: #F5F5F7 !important;
    border: 1px solid rgba(96,165,250,0.15) !important;
    border-radius: 10px !important;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
    <h1>⚡ Extraction de données par OCR + IA</h1>
    <p>Projet de stage PFA — VIRTUO / Groupe EDGE — Pipeline OCR, prétraitement d'image et extraction intelligente</p>
</div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### ⚡ OCR + IA")
    st.caption("Projet de fin d'année — VIRTUO")
    st.divider()
    st.markdown("**🧩 Modules actifs**")
    st.markdown("- OCR (Tesseract)\n- Extraction Regex\n- Extraction IA (Gemini)\n- Prétraitement image\n- Anonymisation")
    st.divider()
    st.markdown("**🕘 Historique de session**")
    historique = st.session_state.get("historique", [])
    if historique:
        for entree in historique:
            icone = "✅" if entree["succes"] else "⚠️"
            st.markdown(f"{icone} `{entree['heure']}` — {entree['fichier']} ({entree['methode']})")
    else:
        st.caption("Aucun document traité pour l'instant.")

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
        valide, message_erreur = fichier_valide(fichier)

        if not valide:
            st.error(f"❌ {message_erreur}")
            ajouter_a_historique(fichier.name, "validation", False)
        else:
            st.image(fichier, caption="Document déposé", width=280)

            contenu_bytes = fichier.getvalue()
            suffixe = os.path.splitext(fichier.name)[1] or ".png"

            chemin_a_traiter_bytes = contenu_bytes

            if appliquer_pretraitement:
                with st.spinner("Prétraitement de l'image en cours..."):
                    try:
                        chemin_a_traiter_bytes = _pretraitement_avec_cache(contenu_bytes, suffixe)
                    except Exception as e:
                        st.warning(f"⚠️ Le prétraitement a échoué ({e}). Poursuite avec l'image originale.")

            with st.spinner("Extraction OCR en cours..."):
                try:
                    texte_brut = _ocr_avec_cache(chemin_a_traiter_bytes, suffixe)
                except Exception as e:
                    texte_brut = ""
                    st.error(f"❌ Échec de l'OCR : {e}")

            donnees_regex, erreur_regex = extraction_regex_securisee(texte_brut) if texte_brut else ({}, "Texte OCR vide")

            with st.spinner("Extraction IA (Gemini) en cours..."):
                donnees_llm, erreur_llm = extraction_llm_avec_retry(texte_brut) if texte_brut else ({}, "Texte OCR vide")

            if appliquer_anonymisation:
                if isinstance(donnees_regex, dict):
                    donnees_regex = anonymiser_donnees(donnees_regex)
                if isinstance(donnees_llm, dict):
                    donnees_llm = anonymiser_donnees(donnees_llm)

            succes_global = not erreur_regex and not erreur_llm and texte_brut
            ajouter_a_historique(fichier.name, "regex+llm", bool(succes_global))

            st.markdown('<div class="titre-section">2. Texte brut extrait (OCR)</div>', unsafe_allow_html=True)
            if not texte_brut.strip():
                st.warning("⚠️ Aucun texte n'a pu être extrait de cette image (photo trop dégradée, angle de perspective, résolution). Essaie d'activer le prétraitement, ou vérifie la netteté du document.")
            with st.expander("Voir le texte OCR", expanded=False):
                st.text_area("Texte", texte_brut, height=150, label_visibility="collapsed")

            st.markdown('<div class="titre-section">3. Comparaison des méthodes d\'extraction</div>', unsafe_allow_html=True)

            col_regex, col_llm = st.columns(2)

            with col_regex:
                st.markdown('<div class="carte">', unsafe_allow_html=True)
                st.markdown("**⚙️ Méthode : Regex (règles simples)**")
                if erreur_regex:
                    st.error(f"Erreur : {erreur_regex}")
                else:
                    st.json(donnees_regex)
                    st.download_button("⬇️ Télécharger JSON (Regex)",
                                        data=json.dumps(donnees_regex, indent=2, ensure_ascii=False),
                                        file_name=f"regex_{fichier.name}.json", mime="application/json",
                                        key="dl_regex")
                st.markdown('</div>', unsafe_allow_html=True)

            with col_llm:
                st.markdown('<div class="carte">', unsafe_allow_html=True)
                st.markdown("**🤖 Méthode : IA (Gemini)**")
                if erreur_llm:
                    st.error(f"Erreur après plusieurs tentatives : {erreur_llm}")
                else:
                    st.json(donnees_llm)
                    st.download_button("⬇️ Télécharger JSON (IA)",
                                        data=json.dumps(donnees_llm, indent=2, ensure_ascii=False),
                                        file_name=f"llm_{fichier.name}.json", mime="application/json",
                                        key="dl_llm")
                st.markdown('</div>', unsafe_allow_html=True)

            if not erreur_regex and not erreur_llm:
                def _aplatir(d):
                    if not isinstance(d, dict):
                        return {}
                    base = {"type_document": d.get("type_document")}
                    base.update(d.get("champs", {}) if isinstance(d.get("champs"), dict) else d)
                    return base

                df_export = pd.DataFrame([
                    {"méthode": "regex", **_aplatir(donnees_regex)},
                    {"méthode": "llm", **_aplatir(donnees_llm)},
                ])
                buffer_excel = io.BytesIO()
                with pd.ExcelWriter(buffer_excel, engine="openpyxl") as writer:
                    df_export.to_excel(writer, index=False, sheet_name="Extraction")
                st.download_button("📊 Télécharger comparaison (Excel)",
                                    data=buffer_excel.getvalue(),
                                    file_name=f"comparaison_{fichier.name}.xlsx",
                                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                    key="dl_excel")
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
        valide, message_erreur = fichier_valide(fichier_pretrait)
        if not valide:
            st.error(f"❌ {message_erreur}")
        else:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                tmp.write(fichier_pretrait.getvalue())
                chemin_original = tmp.name

            chemin_ameliore = chemin_original.replace(".png", "_ameliore.png")

            try:
                with st.spinner("Application du prétraitement..."):
                    ameliorer_image(chemin_original, chemin_ameliore)
                    texte_avant = extraire_texte(chemin_original)
                    texte_apres = extraire_texte(chemin_ameliore)
            except Exception as e:
                st.error(f"❌ Erreur pendant le prétraitement ou l'OCR : {e}")
                for c in (chemin_original, chemin_ameliore):
                    if os.path.exists(c):
                        os.remove(c)
                st.stop()

        col_avant, col_apres = st.columns(2)

        with col_avant:
            st.markdown('<div class="carte">', unsafe_allow_html=True)
            st.markdown("**📷 Image originale**")
            st.image(chemin_original, width=320)
            st.markdown(f"**Texte OCR obtenu** ({len(texte_avant.strip())} caractères) :")
            st.text_area("avant", texte_avant, height=180, label_visibility="collapsed", key="ta_avant")
            st.markdown('</div>', unsafe_allow_html=True)

        with col_apres:
            st.markdown('<div class="carte">', unsafe_allow_html=True)
            st.markdown("**✨ Image après prétraitement**")
            st.image(chemin_ameliore, width=320)
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
