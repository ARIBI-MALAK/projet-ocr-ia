import re

# Champs considérés comme sensibles s'ils apparaissent comme clés dans le JSON extrait
CHAMPS_SENSIBLES = [
    "nom", "nom_client", "client", "nom_complet", "passager",
    "numero_carte", "numero_carte_bancaire", "carte_nationale", "cin",
    "pnr", "numero_reservation", "passeport", "numero_passeport",
    "adresse", "telephone", "email"
]

# Regex pour détecter des motifs sensibles directement dans du texte libre
PATTERNS_SENSIBLES = {
    "carte_bancaire": re.compile(r"\b(?:\d[ -]?){13,19}\b"),
    "pnr": re.compile(r"\bPNR\s*:?\s*([A-Z0-9]{5,8})\b", re.IGNORECASE),
    "cin_maroc": re.compile(r"\b[A-Z]{1,2}\d{5,6}\b"),
}


def masquer_valeur(valeur, nb_caracteres_visibles=2):
    """
    Masque une valeur en ne laissant apparaître que les derniers caractères.
    Exemple : "Rachid Benali" -> "***********li"
    """
    if not isinstance(valeur, str) or len(valeur) <= nb_caracteres_visibles:
        return "***"
    return "*" * (len(valeur) - nb_caracteres_visibles) + valeur[-nb_caracteres_visibles:]


def anonymiser_donnees(donnees: dict) -> dict:
    """
    Prend un dictionnaire de données extraites (JSON structuré, potentiellement
    imbriqué) et retourne une copie où les champs sensibles sont masqués.
    Ne modifie jamais le dictionnaire original.
    """
    donnees_anonymisees = {}

    for cle, valeur in donnees.items():
        cle_normalisee = cle.lower().strip()

        if isinstance(valeur, dict):
            donnees_anonymisees[cle] = anonymiser_donnees(valeur)
        elif cle_normalisee in CHAMPS_SENSIBLES:
            donnees_anonymisees[cle] = masquer_valeur(valeur)
        elif isinstance(valeur, str):
            valeur_masquee = valeur
            for nom_pattern, pattern in PATTERNS_SENSIBLES.items():
                valeur_masquee = pattern.sub("***MASQUÉ***", valeur_masquee)
            donnees_anonymisees[cle] = valeur_masquee
        else:
            donnees_anonymisees[cle] = valeur

    return donnees_anonymisees