from ocr.test_ocr import extraire_texte
from extraction.extraire_donnees_llm import extraire_donnees_llm
import json

texte_brut = extraire_texte("data/facture_format2.png")

print("Texte brut extrait par OCR :")
print(texte_brut)
print("\n--- Extraction LLM ---\n")

resultat = extraire_donnees_llm(texte_brut)
print(json.dumps(resultat, indent=2, ensure_ascii=False))