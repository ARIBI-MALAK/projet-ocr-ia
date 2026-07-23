import os
import pytesseract
from PIL import Image

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

LANGUES_A_TESTER = ["fra", "ara", "eng"]


def extraire_texte(chemin_image):
    """Prend le chemin d'une image et retourne le texte brut extrait par l'OCR."""
    image = Image.open(chemin_image)
    texte = pytesseract.image_to_string(image, lang="fra")
    return texte


def extraire_texte_orientation_auto(chemin_image):
    """
    Teste les 4 rotations possibles (0, 90, 180, 270 degres) et retourne
    le texte obtenu avec l'orientation qui donne le plus de caracteres.
    """
    image_originale = Image.open(chemin_image)
    meilleur_texte = ""
    meilleure_longueur = -1
    meilleur_angle = 0

    for angle in [0, 90, 180, 270]:
        image_tournee = image_originale.rotate(-angle, expand=True)
        texte = pytesseract.image_to_string(image_tournee, lang="fra")
        longueur = len(texte.strip())
        if longueur > meilleure_longueur:
            meilleure_longueur = longueur
            meilleur_texte = texte
            meilleur_angle = angle

    return meilleur_texte, meilleur_angle


def extraire_texte_robuste(chemin_image):
    """
    Strategie en cascade : teste image originale ET image pretraitee,
    chacune sur 4 orientations (0/90/180/270) ET plusieurs langues
    (francais, arabe, anglais), et garde la combinaison avec le
    meilleur score (confiance Tesseract x couverture de texte).

    Retourne (texte, infos) ou infos = dict avec variante/angle/langue/score
    retenus, utile pour du debug ou pour afficher la config gagnante.
    """
    from preprocessing.ameliorer_image import ameliorer_image

    candidats = [("original", Image.open(chemin_image))]

    chemin_pretraite = chemin_image + "__pretraite_tmp.png"
    try:
        ameliorer_image(chemin_image, chemin_pretraite)
        candidats.append(("pretraite", Image.open(chemin_pretraite)))
    except Exception:
        chemin_pretraite = None

    meilleur = {"texte": "", "score": -1, "variante": "original", "angle": 0, "langue": "fra"}

    for nom_variante, image in candidats:
        for angle in [0, 90, 180, 270]:
            image_tournee = image.rotate(-angle, expand=True)
            for langue in LANGUES_A_TESTER:
                try:
                    donnees = pytesseract.image_to_data(
                        image_tournee, lang=langue, output_type=pytesseract.Output.DICT
                    )
                except Exception:
                    continue

                texte = " ".join([t for t in donnees.get("text", []) if t.strip()])
                confiances = [int(c) for c in donnees.get("conf", []) if str(c) not in ("-1",)]
                conf_moyenne = sum(confiances) / len(confiances) if confiances else 0
                couverture = min(len(texte.strip()), 300) / 300
                score = round(conf_moyenne * couverture, 1)

                if score > meilleur["score"]:
                    meilleur = {"texte": texte, "score": score, "variante": nom_variante,
                                "angle": angle, "langue": langue}

    if chemin_pretraite and os.path.exists(chemin_pretraite):
        os.remove(chemin_pretraite)

    return meilleur["texte"], meilleur


if __name__ == "__main__":
    texte = extraire_texte("data/factices/exemple_facture.png")
    print("Texte extrait :")
    print(texte)