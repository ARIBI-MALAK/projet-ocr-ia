import os
import json
from google import genai
client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
def extraire_donnees_llm(texte):
    """Identifie le type de document et extrait les champs pertinents."""
    prompt = f"""Voici le texte brut extrait par OCR d'un document (financier ou administratif) :
{texte}
Etape 1 - Identifie le type de document parmi ces categories :
- facture
- ticket_de_caisse
- attestation_scolarite
- carte_identite
- recu_paiement_bancaire
- carte_embarquement
- fiche_mesure_corporelle
- autre_document_administratif
Etape 2 - Reponds UNIQUEMENT avec un objet JSON valide, sans texte autour, sans balises markdown, avec cette structure exacte :
{{
  "type_document": "une des categories ci-dessus",
  "champs": {{
    ... les champs pertinents selon le type detecte, par exemple :
    - pour facture/ticket_de_caisse : numero_facture, date, siret, total_ht, taux_tva, total_ttc
    - pour attestation_scolarite : nom_etudiant, etablissement, annee_scolaire, niveau_classe, date_delivrance
    - pour carte_identite : nom, prenom, date_naissance, numero_document, date_expiration
    - pour recu_paiement_bancaire : lieu, date, montant, devise, moyen_paiement, numero_transaction
    - pour carte_embarquement : compagnie, nom_passager, ville_depart, ville_arrivee, vol, date, siege, heure_depart, heure_arrivee, pnr
    - pour fiche_mesure_corporelle : societe, date, poids, taille, autres_mesures
    - pour autre_document_administratif : titre_document, date, reference, autres_informations_cles
  }}
}}
Mets null pour tout champ absent du texte. N'invente aucune valeur. Reponds seulement avec le JSON."""
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
    ATTESTATION DE SCOLARITE
    Etablissement : Ecole Nationale des Sciences Appliquees
    Annee universitaire : 2025-2026
    Je soussigne, le directeur des etudes, atteste que :
    Nom et prenom : ARIBI Malak
    Est regulierement inscrit(e) en 4eme annee,
    Specialite Intelligence Artificielle et Data.
    Fait a Rabat, le 10/07/2026
    """
    resultat = extraire_donnees_llm(texte_exemple)
    print(json.dumps(resultat, indent=2, ensure_ascii=False))