rédiger la partie sur les limites du regex
 Petite nuance à noter pour ton rapport (rigueur scientifique)
Le total_ht calculé (69.08) est une estimation faite par le modèle (82.90 / 1.20), pas une donnée lue explicitement dans le texte — à mentionner comme limite/nuance si tu veux être rigoureuse : le LLM interprète parfois au-delà du texte brut, ce qui peut être un avantage (comble les trous) ou un risque (invente si le calcul implicite est faux) selon le contexte réel.
📌 À noter aussi, en toute rigueur (pour ton rapport)
Petite anomalie dans le texte OCR brut : "TVA (taux 20 pouknoo" — Tesseract a mal lu "pourcent" (à cause du chevauchement visuel qu'on avait vu sur l'image originale, souviens-toi les deux lignes qui se superposaient légèrement). Malgré ce bruit dans le texte source, Gemini a quand même correctement déduit taux_tva: 20 — ce qui montre aussi une robustesse du LLM face aux erreurs d'OCR elles-mêmes, un point intéressant à mentionner.

# Journal de bord — Projet PFA OCR + IA (VIRTUO / Groupe EDGE)

## 📋 Contexte du projet
- **Sujet** : Développement d'un moteur d'extraction de données par OCR et IA (documents financiers et administratifs)
- **Entreprise** : VIRTUO / Groupe EDGE
- **Durée** : 2 mois
- **Objectif** : PoC capable de lire un document (facture, ticket, doc administratif) et d'en extraire les données structurées en JSON, indépendamment du format d'origine

## 🛠️ Environnement technique mis en place
- Python 3.13.2
- VS Code
- Git 2.55.0 + dépôt GitHub : `github.com/ARIBI-MALAK/projet-ocr-ia` (privé)
- Environnement virtuel `venv` (à toujours activer avec `venv\Scripts\Activate.ps1` avant de travailler)
- Tesseract OCR 5.5.0 (+ pack langue française `fra.traineddata`)
- Bibliothèques Python installées : `pytesseract`, `pillow`, `opencv-python`, `streamlit`, `google-genai`

## 📁 Structure du projet

## 🔑 Clé API utilisée
- **Google Gemini** (via Google AI Studio, aistudio.google.com) — choisi car gratuit sans carte bancaire (contrairement à Claude/OpenAI qui demandent une carte)
- Stockée en variable d'environnement Windows : `GOOGLE_API_KEY` (jamais écrite en dur dans le code)
- Modèle utilisé : `gemini-3.1-flash-lite` (attention : les noms de modèles Gemini changent souvent, vérifier si erreur `NOT_FOUND`)

## 🧪 Jeu de données de test créé
Trois documents de test générés (factices, pour prototypage avant obtention de vrais documents de l'entreprise) :
1. `exemple_facture.png` — facture standard (libellés : "Facture N", "Date", "SIRET", "Total TTC")
2. `ticket_caisse.png` — ticket de caisse (libellés différents : "Ticket n", pas de SIRET, "A PAYER")
3. `facture_format2.png` — facture avec libellés différents ("Emise le", "NET A PAYER", format de date avec points)
4. `ticket_degrade.png` — version penchée/bruitée/faible contraste du ticket, pour tester le prétraitement d'image

⚠️ **À faire** : demander à l'encadrant l'accès à de VRAIS documents de l'entreprise (question posée, réponse en attente au [date]).

## 🧩 Pipeline construit

`pipeline.py` permet de choisir la méthode d'extraction via un paramètre `methode="llm"` ou `methode="regex"`.

## 📊 Résultats clés — Comparaison Regex vs LLM (à inclure dans le rapport)

| Document | Regex | LLM (Gemini) |
|---|---|---|
| exemple_facture.png (format standard) | ✅ Tous champs corrects | ✅ Tous champs corrects |
| ticket_caisse.png (libellés différents) | ❌ Tout à `null` | ✅ Tous champs corrects (sauf SIRET absent du doc, correctement mis à `null`) |
| facture_format2.png (libellés différents) | ❌ Tout à `null` | ✅ Tous champs corrects |

**Conclusion démontrée** : le regex ne fonctionne que si le document utilise exactement les libellés codés en dur — il ne généralise pas. Le LLM comprend le sens même avec des libellés différents ("A PAYER" / "NET A PAYER" / "Total TTC" reconnus comme la même notion de montant final). C'est la preuve empirique du problème central identifié dans la fiche de stage (généralisation indépendante du format).

**Point de rigueur à mentionner** : sur le ticket de caisse, Gemini a recalculé le total HT (69.08) à partir du total TTC et de la TVA, alors que cette valeur n'était pas explicitement écrite dans le texte — à documenter comme comportement du LLM (déduction contextuelle), à surveiller pour ne pas confondre extraction et interprétation/calcul.

**Comportement anti-hallucination validé** : quand une info est réellement absente du document (ex. SIRET sur un ticket de caisse), Gemini répond `null` plutôt que d'inventer une fausse valeur — testé et confirmé en comparant avec un document qui contient bien un SIRET.

## 🖥️ Interface Streamlit
- Upload d'image (PNG/JPG)
- Sélecteur radio pour choisir la méthode d'extraction (IA Gemini / Regex) — permet une démonstration en direct de la différence
- Affichage du texte brut OCR + JSON structuré

## 🚧 En cours / prochaine étape
- **Prétraitement d'image** (en cours) : objectif = améliorer l'OCR sur documents dégradés (photo penchée, faible contraste, bruit — simulateur d'un ticket froissé/mal photographié). Techniques prévues : niveaux de gris, débruitage, binarisation adaptative, redressement (deskew).
- **Classification du type de document** (en cours) : étendre le prompt LLM pour qu'il identifie d'abord le type de document (facture, ticket_de_caisse, attestation_scolarite, carte_identite, autre) puis extraie les champs pertinents selon ce type — élargit le projet au-delà des seuls documents financiers, conformément à la fiche de stage ("documents administratifs").
- **Protocole d'évaluation rigoureux** (à venir) : construire un jeu de test plus large, définir des métriques de précision par champ, comparer quantitativement regex vs LLM (taux de réussite, matrice d'erreurs).

## ⚠️ Points de vigilance / questions ouvertes avec l'encadrant
- Accès à de vrais documents de l'entreprise (anonymisation/RGPD à clarifier)
- Obligation ou non de développer un OCR "maison" vs utiliser Tesseract (fiche ambiguë sur ce point — question posée, réponse en attente)
- Compatibilité du format JSON de sortie avec le système comptable existant
- Accès éventuel à une API LLM payante côté entreprise (pour l'instant, solution de contournement gratuite avec Gemini)

## 🔒 Bonnes pratiques retenues (pour rapport et hygiène projet)
- Jamais de clé API ni token en dur dans le code (toujours variables d'environnement)
- `.gitignore` en place (`__pycache__/`, `*.pyc`, `venv/`, `debug.log`)
- Commits Git réguliers avec messages descriptifs
- Séparation claire du code en modules (ocr / extraction / interface / pipeline)


C'est un point de rigueur important pour ton rapport : le prétraitement améliore radicalement la lisibilité (de 0% à un texte majoritairement exploitable), mais n'élimine pas totalement les erreurs — ce qui est honnête et attendu. Tu peux même dire que la coexistence de ce résidu d'erreurs justifie l'intérêt du LLM en aval : un LLM peut souvent "deviner" úafe moutu → Café moulu grâce au contexte, là où un regex serait bloqué net.

Conclusion (à mettre dans notes.md et ton rapport) :
L'upscale x2 est l'amélioration la plus significative des deux réglages testés — il corrige notamment les montants avec décimales (13.82 au lieu de 1382, 14:32 au lieu de 14.42), qui étaient auparavant des erreurs graves pour un usage comptable réel. Il dégrade très légèrement un ou deux mots isolés (T*cket au lieu de Ticket), mais l'apport global est net et justifie de le garder dans la version finale du pipeline.

## 📊 Protocole d'évaluation rigoureux (regex vs LLM)

### Méthodologie
- Jeu de test : 15 documents (11 factices générés avec valeurs connues à 100%, 
  4 documents réels photographiés : reçu BIGUP, reçu paiement ONCF, fiche 
  mesure corporelle, carte d'embarquement Ryanair — un 5e document réel, 
  ASSILAH.jpeg, exclu car il contient 2 billets superposés sur une seule photo)
- Vérité terrain définie dans `verite_terrain.json` (valeur exacte attendue 
  par champ et par document)
- Script `evaluation/evaluer.py` : exécute le pipeline en mode "regex" puis 
  "llm" sur chaque document, compare au verite_terrain, classe chaque champ 
  en 5 catégories (correct_present, correct_absent, faux_positif, 
  faux_negatif, erreur_valeur)

### Résultats — taux de réussite par champ

| Champ            | Regex | LLM (Gemini) | Écart   |
|------------------|-------|--------------|---------|
| type_document    | 0.0%  | 64.3%        | +64.3   |
| numero_facture   | 35.7% | 78.6%        | +42.9   |
| date             | 28.6% | 57.1%        | +28.5   |
| total_ttc        | 35.7% | 71.4%        | +35.7   |
| siret            | 92.9% | 100%         | +7.1    |
| total_ht         | 85.7% | 92.9%        | +7.2    |
| taux_tva         | 85.7% | 100%         | +14.3   |

⚠️ Attention à l'interprétation : les taux élevés du regex sur siret/taux_tva 
sont trompeurs, car ces champs sont souvent absents (`correct_absent`). Sur 
les documents où le champ existe réellement, le regex ne le trouve qu'une 
fois sur deux.

### Élargissement du prompt LLM
Le prompt d'extraction a été étendu pour reconnaître 3 nouveaux types de 
documents (recu_paiement_bancaire, carte_embarquement, fiche_mesure_corporelle), 
en plus de facture/ticket_de_caisse/attestation_scolarite/carte_identite. 
Cet élargissement n'a cependant pas amélioré les scores sur les documents 
réels concernés — le vrai problème identifié était en amont (voir limite 
ci-dessous), pas un manque de catégories dans le prompt.

### Limite majeure identifiée : photos réelles vs documents scannés/générés
Sur 3 documents réels (OUJDA.jpeg, poids.jpeg, RYANAIR.jpeg), l'OCR (Tesseract) 
renvoie une chaîne vide, confirmé par un test isolé de pytesseract sans passer 
par le pipeline. Contrairement à ticket_degrade.png (simple inclinaison 2D + 
bruit, corrigé avec succès par notre module de prétraitement), ces photos 
présentent une **déformation de perspective** (document tenu en main, angle 
de prise de vue non perpendiculaire) que notre prétraitement actuel (gris, 
débruitage, binarisation adaptative, redressement 2D) ne corrige pas.

**Piste d'amélioration future** : ajouter une détection automatique des 4 
coins du document et une transformation de perspective (homographie) avant 
les autres étapes de prétraitement — technique standard pour les scanners 
de documents mobiles (ex. CamScanner).

### Conclusion générale
Le LLM (Gemini) surpasse largement le regex sur tous les champs testés, 
avec l'écart le plus marqné sur les champs à forte variabilité de libellés 
(type de document, numéro, date, montant total) — confirmant empiriquement 
le problème central de généralisation identifié dans la fiche de stage. 
Le regex reste rigide face à tout changement de format. La performance du 
LLM dépend cependant fortement de la qualité du texte OCR en amont : sur 
des photos réelles avec déformation de perspective, l'échec de l'OCR rend 
toute extraction impossible, quelle que soit la méthode utilisée en aval.


### Limite de robustesse OCR sur photos réelles dégradées

Sur le document réel OUJDA.jpeg (reçu de paiement photographié à la main), 
plusieurs stratégies de correction ont été testées méthodiquement :
1. Rotation seule (0°/90°/180°/270°) → échec (texte vide)
2. Modes de segmentation PSM 6 et PSM 11 → échec (texte incohérent)
3. Combinaison rotation × PSM 6 sur les 4 angles → échec systématique
4. Stratégie cascade (prétraitement × orientation × score de confiance) → 
   score de confiance nul sur toutes les combinaisons testées

Conclusion : l'échec n'est pas dû à l'orientation ni au mode de segmentation, 
mais à un cumul de facteurs de dégradation réels (texte de petite taille 
relativement à la résolution de la photo, reflets lumineux sur le carrelage 
en arrière-plan, légère courbure du papier). Une solution robuste nécessiterait 
une détection et un recadrage automatique du document dans la scène (technique 
de type "scanner mobile"), hors du périmètre raisonnable de ce projet dans le 
temps imparti. Ce cas illustre une limite réelle et documentée des moteurs 
OCR classiques (Tesseract) sur des photos non contrôlées.

Point à noter : erreur_technique=1 sur tous les champs LLM

Un document a provoqué une vraie erreur technique (pas juste un champ manqué) pendant le traitement LLM — visible sur chaque ligne du résumé. C'est probablement un souci ponctuel (quota API, ou une exception dans le pipeline sur un des 3 documents recadrés qu'on vient d'ajouter). Ce n'est pas grave en soi, mais si tu veux qu'on l'identifie précisément avant de continuer, je peux regarder le détail