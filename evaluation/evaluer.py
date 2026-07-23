import json
import os
import time

# Champs que le pipeline (regex et LLM) tente d'extraire actuellement
CHAMPS_A_COMPARER = ["type_document", "numero_facture", "date", "siret",
                     "total_ht", "taux_tva", "total_ttc"]

DOSSIERS_DOCUMENTS = ["data/factices", "data/reels"]


def trouver_chemin(nom_fichier):
    """Cherche le fichier dans les dossiers factices puis reels."""
    for dossier in DOSSIERS_DOCUMENTS:
        chemin = os.path.join(dossier, nom_fichier)
        if os.path.exists(chemin):
            return chemin
    return None


def normaliser(valeur):
    """Normalise une valeur pour comparaison (espaces, casse, types numériques)."""
    if valeur is None:
        return None
    if isinstance(valeur, (int, float)):
        return round(float(valeur), 2)
    valeur_str = str(valeur).strip().lower()
    if valeur_str in ("", "null", "none", "n/a"):
        return None
    return valeur_str


def comparer_valeurs(attendu, obtenu):
    """
    Compare une valeur attendue (vérité terrain) à une valeur obtenue (pipeline).
    Retourne une catégorie : correct_present, correct_absent, faux_positif,
    faux_negatif, erreur_valeur.
    """
    a = normaliser(attendu)
    o = normaliser(obtenu)

    if a is None and o is None:
        return "correct_absent"
    if a is None and o is not None:
        return "faux_positif"      # le pipeline invente une valeur non présente
    if a is not None and o is None:
        return "faux_negatif"      # le pipeline rate une valeur bien présente
    if a == o:
        return "correct_present"
    return "erreur_valeur"


def extraire_champs_predits(resultat):
    """
    Gère les deux formats possibles de sortie du pipeline :
    - format LLM : {"type_document": ..., "champs": {...}}
    - format regex (potentiellement plat) : {...} directement
    """
    if not isinstance(resultat, dict):
        return {}
    type_doc = resultat.get("type_document")
    champs = resultat.get("champs", resultat)
    if not isinstance(champs, dict):
        champs = {}
    fusion = dict(champs)
    fusion["type_document"] = type_doc
    return fusion


from ocr.test_ocr import extraire_texte_robuste
from extraction.extraire_donnees import extraire_donnees
from extraction.extraire_donnees_llm import extraire_donnees_llm
from anonymisation.anonymiser import anonymiser_donnees


def extraire_avec_retry_llm(texte, tentatives=2):
    """Appelle l'extraction LLM avec une nouvelle tentative en cas d'erreur reseau/API."""
    derniere_erreur = None
    for essai in range(tentatives):
        try:
            resultat = extraire_donnees_llm(texte)
            return extraire_champs_predits(resultat), None
        except Exception as e:
            derniere_erreur = str(e)
            if essai < tentatives - 1:
                time.sleep(2)
    return {}, derniere_erreur


def evaluer():
    with open("verite_terrain.json", "r", encoding="utf-8") as f:
        verite_terrain = json.load(f)

    # Compteurs : compteurs[methode][champ][categorie] = nombre
    compteurs = {
        "regex": {c: {"correct_present": 0, "correct_absent": 0,
                       "faux_positif": 0, "faux_negatif": 0, "erreur_valeur": 0,
                       "erreur_technique": 0}
                  for c in CHAMPS_A_COMPARER},
        "llm": {c: {"correct_present": 0, "correct_absent": 0,
                     "faux_positif": 0, "faux_negatif": 0, "erreur_valeur": 0,
                     "erreur_technique": 0}
                for c in CHAMPS_A_COMPARER},
    }

    # Matrice de confusion pour la classification du type de document
    matrice_confusion = {"regex": {}, "llm": {}}

    resultats_detailles = []

    for nom_fichier, verite in verite_terrain.items():
        chemin = trouver_chemin(nom_fichier)
        if chemin is None:
            print(f"⚠️  Fichier introuvable, ignoré : {nom_fichier}")
            continue

        # Ignore les documents multi-tickets trop complexes pour une comparaison
        # champ-par-champ simple (ex: ASSILAH.jpeg contient 2 billets imbriqués)
        if "billet_1" in verite:
            print(f"ℹ️  {nom_fichier} : structure multi-documents, exclu de la comparaison automatique.")
            continue

        print(f"Évaluation de {nom_fichier} ...")

        try:
            texte_brut, infos_ocr = extraire_texte_robuste(chemin)
        except Exception as e:
            texte_brut, infos_ocr = "", {"erreur_ocr": str(e)}

        for methode in ["regex", "llm"]:
            if methode == "regex":
                try:
                    resultat = extraire_donnees(texte_brut)
                    predits = extraire_champs_predits(resultat)
                    erreur = None
                except Exception as e:
                    predits = {}
                    erreur = str(e)
            else:
                predits, erreur = extraire_avec_retry_llm(texte_brut, tentatives=2)

            ligne = {"document": nom_fichier, "methode": methode, "erreur": erreur}

            type_attendu = verite.get("type_document")
            type_obtenu = predits.get("type_document") if not erreur else None
            matrice_confusion[methode].setdefault(
                normaliser(type_attendu) or "inconnu", {}
            )
            cle_obtenue = normaliser(type_obtenu) or "aucun"
            matrice_confusion[methode][normaliser(type_attendu) or "inconnu"][cle_obtenue] = (
                matrice_confusion[methode][normaliser(type_attendu) or "inconnu"].get(cle_obtenue, 0) + 1
            )

            for champ in CHAMPS_A_COMPARER:
                attendu = verite.get(champ)
                obtenu = predits.get(champ) if not erreur else None

                if erreur:
                    categorie = "erreur_technique"
                else:
                    categorie = comparer_valeurs(attendu, obtenu)

                compteurs[methode][champ][categorie] += 1
                ligne[champ] = {"attendu": attendu, "obtenu": obtenu, "categorie": categorie}

            resultats_detailles.append(ligne)

    # ---------------- Rapport texte ----------------
    print("\n" + "=" * 70)
    print("RÉSUMÉ PAR CHAMP ET PAR MÉTHODE")
    print("=" * 70)

    for champ in CHAMPS_A_COMPARER:
        print(f"\n--- Champ : {champ} ---")
        for methode in ["regex", "llm"]:
            c = compteurs[methode][champ]
            total = sum(c.values())
            corrects = c["correct_present"] + c["correct_absent"]
            taux = (corrects / total * 100) if total > 0 else 0
            print(f"  {methode.upper():6s} | Taux de réussite : {taux:5.1f}%  "
                  f"(correct_present={c['correct_present']}, correct_absent={c['correct_absent']}, "
                  f"faux_positif={c['faux_positif']}, faux_negatif={c['faux_negatif']}, "
                  f"erreur_valeur={c['erreur_valeur']}, erreur_technique={c['erreur_technique']})")

    print("\n" + "=" * 70)
    print("MATRICE DE CONFUSION — CLASSIFICATION DU TYPE DE DOCUMENT")
    print("=" * 70)
    for methode in ["regex", "llm"]:
        print(f"\n--- Méthode : {methode.upper()} ---")
        for type_reel, obtenus in matrice_confusion[methode].items():
            print(f"  Type réel = {type_reel} :")
            for type_predit, nb in obtenus.items():
                print(f"      -> prédit '{type_predit}' : {nb} fois")

    # ---------------- Sauvegarde des résultats détaillés ----------------
    with open("evaluation/resultats_evaluation.json", "w", encoding="utf-8") as f:
        json.dump({
            "compteurs": compteurs,
            "matrice_confusion": matrice_confusion,
            "details": resultats_detailles
        }, f, indent=2, ensure_ascii=False)

    print("\n✅ Résultats détaillés sauvegardés dans evaluation/resultats_evaluation.json")


if __name__ == "__main__":
    evaluer()
