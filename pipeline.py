from ocr.test_ocr import extraire_texte
from extraction.extraire_donnees import extraire_donnees
from extraction.extraire_donnees_llm import extraire_donnees_llm
import json

def traiter_document(chemin_image, methode="llm"):
    """Pipeline complet : image -> texte OCR -> donnees structurees JSON.

    methode : "regex" ou "llm"
    """

    texte_brut = extraire_texte(chemin_image)

    if methode == "llm":
        donnees = extraire_donnees_llm(texte_brut)
    else:
        donnees = extraire_donnees(texte_brut)

    return donnees, texte_brut


if __name__ == "__main__":
    resultat, texte = traiter_document("data/ticket_caisse.png", methode="llm")

    print("Resultat final :")
    print(json.dumps(resultat, indent=2, ensure_ascii=False))