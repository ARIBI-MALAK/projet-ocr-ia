from ocr.test_ocr import extraire_texte
from extraction.extraire_donnees import extraire_donnees
import json

def traiter_document(chemin_image):
    """Pipeline complet : image -> texte OCR -> donnees structurees JSON."""

    # Etape 1 : OCR
    texte_brut = extraire_texte(chemin_image)

    # Etape 2 : extraction des donnees structurees
    donnees = extraire_donnees(texte_brut)

    return donnees

if __name__ == "__main__":
    resultat = traiter_document("data/exemple_facture.png")
    resultat = traiter_document("data/ticket_caisse.png")
    resultat = traiter_document("data/facture_format2.png")

    print("Resultat final :")
    print(json.dumps(resultat, indent=2, ensure_ascii=False))