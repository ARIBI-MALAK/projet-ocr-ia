import cv2
import numpy as np

def ameliorer_image(chemin_image, chemin_sortie="data/ticket_ameliore.png"):
    """
    Applique une chaîne de prétraitement à une image de document dégradée
    pour améliorer la lisibilité par l'OCR :
    1. Niveaux de gris
    2. Débruitage
    3. Binarisation adaptative
    4. Redressement (deskew)
    """
    image = cv2.imread(chemin_image)
    if image is None:
        raise FileNotFoundError(f"Impossible de charger l'image : {chemin_image}")

    image = cv2.resize(image, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)

    gris = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    debruite = cv2.fastNlMeansDenoising(gris, h=15, templateWindowSize=7, searchWindowSize=21)

    binaire = cv2.adaptiveThreshold(
        debruite, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        blockSize=15,
        C=15
    )

    redresse = redresser_image(binaire)

    cv2.imwrite(chemin_sortie, redresse)
    print(f"Image prétraitée sauvegardée dans : {chemin_sortie}")

    return chemin_sortie


def redresser_image(image_binaire):
    """
    Détecte l'angle d'inclinaison du texte/document et corrige la rotation.
    """
    coords = np.column_stack(np.where(image_binaire > 0))

    if len(coords) == 0:
        return image_binaire

    angle = cv2.minAreaRect(coords)[-1]

    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle

    (h, w) = image_binaire.shape[:2]
    centre = (w // 2, h // 2)
    matrice_rotation = cv2.getRotationMatrix2D(centre, angle, 1.0)

    redresse = cv2.warpAffine(
        image_binaire, matrice_rotation, (w, h),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE
    )

    return redresse