import cv2
import numpy as np

def ameliorer_image(chemin_image, chemin_sortie="data/ticket_ameliore.png"):
    """
    Applique une chaîne de prétraitement à une image de document dégradée
    pour améliorer la lisibilité par l'OCR :
    1. Redimensionnement x2
    2. Niveaux de gris
    3. Débruitage
    4. Binarisation adaptative
    5. Redressement (deskew)
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


def _detecter_par_zone_claire(image, largeur_travail=700):
    """
    Detecte le document en cherchant les zones claires/peu saturees
    (papier blanc) plutot que les bords. Souvent plus robuste que la
    detection de contours quand l'arriere-plan est texture ou contraste
    (carrelage, reflets, vetements).

    Retourne un contour (array de points) ou None si rien de plausible trouve.
    """
    hauteur_orig, largeur_orig = image.shape[:2]
    ratio = largeur_orig / largeur_travail
    image_travail = cv2.resize(image, (largeur_travail, int(hauteur_orig / ratio)))

    hsv = cv2.cvtColor(image_travail, cv2.COLOR_BGR2HSV)
    # Papier blanc/clair : forte luminosite (V), faible saturation (S)
    # Seuil V releve a 220 pour exclure les sols/fonds clairs mais moins lumineux que le papier
    masque = cv2.inRange(hsv, (0, 0, 220), (180, 60, 255))

    # Nettoyage renforce : ouverture pour supprimer le bruit epars,
    # puis fermeture pour combler les trous internes au document
    noyau_ouverture = np.ones((5, 5), np.uint8)
    masque = cv2.morphologyEx(masque, cv2.MORPH_OPEN, noyau_ouverture, iterations=2)
    noyau_fermeture = np.ones((15, 15), np.uint8)
    masque = cv2.morphologyEx(masque, cv2.MORPH_CLOSE, noyau_fermeture, iterations=2)

    contours, _ = cv2.findContours(masque, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None, ratio

    plus_grand = max(contours, key=cv2.contourArea)
    aire_image_travail = largeur_travail * (hauteur_orig / ratio)

    # Le document doit couvrir une portion raisonnable de l'image, sans
    # etre non plus la quasi-totalite (sinon c'est probablement un mur clair)
    aire_relative = cv2.contourArea(plus_grand) / aire_image_travail
    if aire_relative < 0.03 or aire_relative > 0.85:
        return None, ratio

    return plus_grand, ratio


def detecter_et_recadrer_document(chemin_image, chemin_sortie="data/document_recadre_auto.png"):
    """
    Detecte automatiquement le contour du document dans une photo (meme
    prise a main levee, sous un angle) et corrige la perspective pour
    obtenir une vue "a plat", comme un scanner mobile.

    Strategie en cascade pour plus de robustesse sur de vraies photos :
    1. Detection par zone claire/blanche (papier) -> souvent le plus robuste
       sur fond texture (carrelage, tissu, reflets)
    2. Detection de contours par seuils Canny multiples -> quadrilatere precis
    3. Repli sur le plus grand contour + rectangle oriente englobant

    Retourne (chemin_sortie, contour_trouve: bool, methode: str).
    """
    image = cv2.imread(chemin_image)
    if image is None:
        raise FileNotFoundError(f"Impossible de charger l'image : {chemin_image}")

    hauteur_orig, largeur_orig = image.shape[:2]
    largeur_travail = 700
    aire_image_travail = largeur_travail * (hauteur_orig / (largeur_orig / largeur_travail))

    points = None
    methode = "aucun"

    # --- Strategie 1 : zone claire/blanche ---
    contour_clair, ratio = _detecter_par_zone_claire(image, largeur_travail)
    if contour_clair is not None:
        perimetre = cv2.arcLength(contour_clair, True)
        approx = cv2.approxPolyDP(contour_clair, 0.02 * perimetre, True)
        if len(approx) == 4:
            points = approx.reshape(4, 2).astype("float32") * ratio
            methode = "zone_claire_quadrilatere"
        else:
            rect_oriente = cv2.minAreaRect(contour_clair)
            points = cv2.boxPoints(rect_oriente).astype("float32") * ratio
            methode = "zone_claire_rectangle"

    # --- Strategie 2 : contours (seuils Canny multiples) ---
    if points is None:
        image_travail = cv2.resize(image, (largeur_travail, int(hauteur_orig / (largeur_orig / largeur_travail))))
        gris = cv2.cvtColor(image_travail, cv2.COLOR_BGR2GRAY)
        flou = cv2.GaussianBlur(gris, (5, 5), 0)
        ratio = largeur_orig / largeur_travail

        for bas, haut in [(50, 150), (30, 100), (75, 200)]:
            bords = cv2.Canny(flou, bas, haut)
            bords = cv2.dilate(bords, np.ones((5, 5), np.uint8), iterations=2)
            contours, _ = cv2.findContours(bords, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            contours = sorted(contours, key=cv2.contourArea, reverse=True)[:5]

            for contour in contours:
                perimetre = cv2.arcLength(contour, True)
                approx = cv2.approxPolyDP(contour, 0.02 * perimetre, True)
                aire = cv2.contourArea(approx)
                if len(approx) == 4 and aire > 0.15 * aire_image_travail:
                    points = approx.reshape(4, 2).astype("float32") * ratio
                    methode = "quadrilatere_precis"
                    break
            if points is not None:
                break

    # --- Strategie 3 : repli, plus grand contour global ---
    if points is None:
        image_travail = cv2.resize(image, (largeur_travail, int(hauteur_orig / (largeur_orig / largeur_travail))))
        gris = cv2.cvtColor(image_travail, cv2.COLOR_BGR2GRAY)
        flou = cv2.GaussianBlur(gris, (5, 5), 0)
        ratio = largeur_orig / largeur_travail
        bords = cv2.Canny(flou, 30, 100)
        bords = cv2.dilate(bords, np.ones((7, 7), np.uint8), iterations=3)
        contours, _ = cv2.findContours(bords, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if contours:
            plus_grand = max(contours, key=cv2.contourArea)
            if cv2.contourArea(plus_grand) >= 0.1 * aire_image_travail:
                rect_oriente = cv2.minAreaRect(plus_grand)
                points = cv2.boxPoints(rect_oriente).astype("float32") * ratio
                methode = "rectangle_englobant"

    if points is None:
        cv2.imwrite(chemin_sortie, image)
        return chemin_sortie, False, "aucun"

    points_ordonnes = _ordonner_points(points)

    (tl, tr, br, bl) = points_ordonnes
    largeur_bas = np.linalg.norm(br - bl)
    largeur_haut = np.linalg.norm(tr - tl)
    largeur_max = int(max(largeur_bas, largeur_haut))

    hauteur_droite = np.linalg.norm(tr - br)
    hauteur_gauche = np.linalg.norm(tl - bl)
    hauteur_max = int(max(hauteur_droite, hauteur_gauche))

    if largeur_max < 10 or hauteur_max < 10:
        cv2.imwrite(chemin_sortie, image)
        return chemin_sortie, False, "aucun"

    destination = np.array([
        [0, 0],
        [largeur_max - 1, 0],
        [largeur_max - 1, hauteur_max - 1],
        [0, hauteur_max - 1]
    ], dtype="float32")

    matrice_perspective = cv2.getPerspectiveTransform(points_ordonnes, destination)
    image_redressee = cv2.warpPerspective(image, matrice_perspective, (largeur_max, hauteur_max))

    cv2.imwrite(chemin_sortie, image_redressee)
    return chemin_sortie, True, methode


def _ordonner_points(points):
    """Ordonne 4 points dans l'ordre : haut-gauche, haut-droite, bas-droite, bas-gauche."""
    rect = np.zeros((4, 2), dtype="float32")
    somme = points.sum(axis=1)
    rect[0] = points[np.argmin(somme)]   # haut-gauche : x+y minimal
    rect[2] = points[np.argmax(somme)]   # bas-droite : x+y maximal
    diff = np.diff(points, axis=1)
    rect[1] = points[np.argmin(diff)]    # haut-droite : x-y minimal
    rect[3] = points[np.argmax(diff)]    # bas-gauche : x-y maximal
    return rect