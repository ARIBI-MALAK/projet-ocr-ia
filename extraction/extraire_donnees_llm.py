import os
import json
from google import genai

client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])

def extraire_donnees_llm(texte):
    """Envoie le texte brut a Gemini et recupere un JSON structure."""

    prompt = f"""Voici le texte brut extrait par OCR d'un document financier (facture ou ticket de caisse) :

{texte}

Extrais les informations suivantes et reponds UNIQUEMENT avec un objet JSON valide, sans aucun texte autour, sans balises markdown, avec ces champs exacts :
- numero_facture (texte, ou null si absent)
- date (au format JJ/MM/AAAA, ou null si absent)
- siret (texte, ou null si absent)
- total_ht (nombre, ou null si absent)
- taux_tva (nombre entier en pourcentage, ou null si absent)
- total_ttc (nombre, le montant final a payer, ou null si absent)

Reponds seulement avec le JSON, rien d'autre."""

    reponse = client.models.generate_content(
        model="gemini-3.1-flash-lite",
        contents=prompt
    )

    reponse_texte = reponse.text.strip()
    reponse_texte = reponse_texte.replace("```json", "").replace("```", "").strip()

    try:
        donnees = json.loads(reponse_texte)
    except json.JSONDecodeError:
        donnees = {"erreur": "Impossible de parser la reponse", "reponse_brute": reponse_texte}

    return donnees


if __name__ == "__main__":
    texte_exemple = """
    SUPERMARCHE EDGE
    Ticket n 004521
    08-07-2026 14:32
    Pain complet 2.50
    Lait UHT 1L 8.90
    SOUS-TOTAL 82.90
    TVA (incl.) 13.82
    A PAYER 82.90 MAD
    """

    resultat = extraire_donnees_llm(texte_exemple)
    print(json.dumps(resultat, indent=2, ensure_ascii=False))