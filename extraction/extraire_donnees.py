import re
import json

def extraire_donnees(texte):
    """Prend le texte brut d'une facture et retourne un dictionnaire structure."""

    donnees = {}

    # Numero de facture (ex: "Facture N : 2026-0456")
    match = re.search(r"Facture N\s*:\s*(\S+)", texte)
    donnees["numero_facture"] = match.group(1) if match else None

    # Date (format JJ/MM/AAAA)
    match = re.search(r"Date\s*:\s*(\d{2}/\d{2}/\d{4})", texte)
    donnees["date"] = match.group(1) if match else None

    # SIRET
    match = re.search(r"SIRET\s*:\s*([\d\s]+)", texte)
    donnees["siret"] = match.group(1).strip() if match else None

    # Total HT
    match = re.search(r"Total HT\s*:\s*(\d+\.\d+)", texte)
    donnees["total_ht"] = float(match.group(1)) if match else None

    # TVA (pourcentage)
    match = re.search(r"TVA\s*(\d+)%", texte)
    donnees["taux_tva"] = int(match.group(1)) if match else None

    # Total TTC
    match = re.search(r"Total TTC\s*:\s*(\d+\.\d+)", texte)
    donnees["total_ttc"] = float(match.group(1)) if match else None

    return donnees


if __name__ == "__main__":
    # Exemple avec le texte extrait par Tesseract (colle ici ton vrai resultat)
    texte_exemple = """
    FACTURE
    VIRTUO TECH SERVICE
    12 Rue de l'Innovation, Casablanca
    SIRET : 123 456 789 00012
    Facture N : 2026-0456
    Date : 08/07/2026
    Description Qte Prix Total
    Prestation conseil IT 1 150.00 150.00
    Licence logiciel annuelle 2 45.00 90.00
    Total HT : 240.00
    TVA 20% : 48.00
    Total TTC : 288.00 EUR
    Merci de votre confiance.
    """

    resultat = extraire_donnees(texte_exemple)

    print("Donnees extraites :")
    print(json.dumps(resultat, indent=2, ensure_ascii=False))