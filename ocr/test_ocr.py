import pytesseract
from PIL import Image

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def extraire_texte(chemin_image):
    """Prend le chemin d'une image et retourne le texte brut extrait par l'OCR."""
    image = Image.open(chemin_image)
    texte = pytesseract.image_to_string(image, lang="fra")
    return texte

if __name__ == "__main__":
    texte = extraire_texte("data/exemple_facture.png")
    print("Texte extrait :")
    print(texte)