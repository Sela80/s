# app.py
import os
from flask import Flask, render_template, request, jsonify
# Essayer joblib en premier, car c'est souvent utilisé par sklearn
try:
    # from sklearn.externals import joblib # Pour scikit-learn < 0.23
    import joblib # Pour scikit-learn >= 0.23
    HAS_JOBLIB = True
except ImportError:
    HAS_JOBLIB = False
    import pickle
import pandas as pd

app = Flask(__name__)

# --- Charger le modèle (ou pipeline) ---
# *** MODIFIE ICI LE CHEMIN VERS TON MODELE ***
# Utilisation d'une raw string (r"") pour le chemin absolu sous Windows
MODEL_PATH = r"C:\Users\ACC\Documents\HOLD\Desktop\Bureau VSCode\01 - Les coûts de l'assurance médicale\linear_regression.pkl"

# Vérification que le fichier existe
if not os.path.exists(MODEL_PATH):
    raise FileNotFoundError(f"Le fichier du modèle n'a pas été trouvé à l'emplacement : {MODEL_PATH}")

model_pipeline = None
model_load_error = None

# --- Essayer de charger avec joblib ou pickle ---
if HAS_JOBLIB:
    try:
        print("Tentative de chargement avec joblib...")
        model_pipeline = joblib.load(MODEL_PATH)
        print("Modèle chargé avec succès avec joblib.")
    except Exception as e:
        print(f"Échec du chargement avec joblib : {e}")
        model_load_error = f"Échec du chargement avec joblib : {e}"

if model_pipeline is None:
    try:
        print("Tentative de chargement avec pickle...")
        with open(MODEL_PATH, 'rb') as file:
            model_pipeline = pickle.load(file)
        print("Modèle chargé avec succès avec pickle.")
    except Exception as e:
        print(f"Échec du chargement avec pickle : {e}")
        model_load_error = f"Échec du chargement avec pickle : {e}"

if model_pipeline is None:
    raise RuntimeError(f"Impossible de charger le modèle à partir de {MODEL_PATH}. Dernière erreur : {model_load_error}")

# --- Vérifier que l'objet chargé est utilisable ---
if not hasattr(model_pipeline, 'predict'):
    raise AttributeError(f"L'objet chargé ({type(model_pipeline)}) n'a pas de méthode 'predict'.")

print(f"Type de l'objet chargé : {type(model_pipeline)}")
# Afficher les colonnes attendues si le modèle est un Pipeline ou a cette info
if hasattr(model_pipeline, 'feature_names_in_'):
    print(f"Colonnes attendues par le modèle : {list(model_pipeline.feature_names_in_)}")
elif hasattr(model_pipeline, 'steps'):
    print("Étapes du pipeline :")
    for name, step in model_pipeline.steps:
        print(f"  - {name}: {type(step)}")
else:
    # Si le modèle ne fournit pas directement les noms de colonnes,
    # et que ce n'est pas un pipeline, tu dois t'assurer que la liste
    # 'expected_columns' dans la route /predict correspond à celle
    # utilisée lors de l'entraînement.
    print("Attention : Impossible de déterminer automatiquement les colonnes attendues.")
    print("Assure-toi que la liste 'expected_columns' dans /predict est correcte.")

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/predict', methods=['POST'])
def predict():
    if model_load_error:
        return jsonify({'error': f'Modèle non chargé au démarrage : {model_load_error}'}), 500

    try:
        data = request.get_json()

        # 1. Créer un DataFrame avec les données d'entrée (noms originaux)
        input_data_raw = pd.DataFrame({
            'age': [float(data['age'])],
            'sex': [data['sex']],       # 'male' ou 'female'
            'bmi': [float(data['bmi'])],
            'children': [int(data['children'])],
            'smoker': [data['smoker']], # 'yes' ou 'no'
            'region': [data['region']]  # 'northeast', 'northwest', 'southeast', 'southwest'
        })

        print("Données d'entrée brutes du formulaire (DataFrame) :")
        print(input_data_raw)

        # 2. Appliquer le même prétraitement que lors de l'entraînement
        #    Utiliser pd.get_dummies avec les mêmes paramètres (drop_first=True)
        #    Cela transformera les colonnes catégorielles en colonnes encodées.
        input_data_processed = pd.get_dummies(input_data_raw, drop_first=True)
        print("Données d'entrée après get_dummies (drop_first=True) :")
        print(input_data_processed)
        print("Colonnes après get_dummies :", input_data_processed.columns.tolist())

        # 3. S'assurer que toutes les colonnes attendues par le modèle sont présentes
        #    ET qu'il n'y a pas de colonnes en trop.
        #    *** ADAPTE CETTE LISTE SI NECESSAIRE ***
        #    *** VERIFIE AVEC LES LOGS AU DEMARRAGE OU TON ENTRAINEMENT ***
        #    La liste ci-dessous est basée sur le prétraitement standard.
        #    Si ton modèle LinearRegression a été entraîné avec une liste différente,
        #    remplace cette liste.
        
        expected_columns = None
        if hasattr(model_pipeline, 'feature_names_in_'):
            # Si le modèle (ou pipeline) fournit les noms, on les utilise
            expected_columns = list(model_pipeline.feature_names_in_)
            print(f"Colonnes attendues (fournies par le modèle) : {expected_columns}")
        else:
            # *** LISTE PAR DEFAUT - A VERIFIER/ADAPTER ***
            # Liste déduite du prétraitement standard avec pd.get_dummies(drop_first=True)
            # sur les colonnes ['age', 'sex', 'bmi', 'children', 'smoker', 'region']
            expected_columns = ['age', 'bmi', 'children', 'sex_male', 'smoker_yes', 'region_northwest', 'region_southeast', 'region_southwest']
            print(f"Colonnes attendues (liste par défaut utilisée) : {expected_columns}")
            print("*** Vérifiez que cette liste correspond à celle utilisée lors de l'entraînement de linear_regression.pkl ***")
        
        # Ajouter les colonnes manquantes avec la valeur 0
        for col in expected_columns:
            if col not in input_data_processed.columns:
                input_data_processed[col] = 0
                print(f"Ajout de la colonne manquante '{col}' avec la valeur 0.")

        # Réorganiser les colonnes pour qu'elles correspondent EXACTEMENT à l'entraînement
        # et supprimer les colonnes inattendues (normalement il ne devrait pas y en avoir)
        input_data_final = input_data_processed.reindex(columns=expected_columns, fill_value=0)
        print("Données d'entrée finales (réindexées) :")
        print(input_data_final)
        print("Colonnes finales :", input_data_final.columns.tolist())

        # Vérifier la forme
        print(f"Shape des données finales : {input_data_final.shape}")

        # 4. Effectuer la prédiction avec le DataFrame correctement formaté
        prediction_result = model_pipeline.predict(input_data_final)
        prediction = prediction_result[0]

        print(f"Prédiction réussie : {prediction}")
        return jsonify({'predicted_cost': float(prediction)})

    except KeyError as e:
        error_msg = f"Donnée manquante dans la requête : {e}"
        print(f"Erreur 400 : {error_msg}")
        return jsonify({'error': error_msg}), 400
    except ValueError as e:
        error_msg = f"Erreur de format ou de valeur des données : {e}"
        print(f"Erreur 400 : {error_msg}")
        return jsonify({'error': error_msg}), 400
    except Exception as e:
        error_msg = f"Erreur interne du serveur lors de la prédiction : {e}"
        print(f"Erreur 500 : {error_msg}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': error_msg}), 500

if __name__ == '__main__':
    # *** IMPORTANT ***
    # Assure-toi que ton répertoire de travail (où se trouve app.py)
    # contient le dossier 'templates' et le dossier 'static'.
    # Si tu exécutes app.py depuis un autre endroit, Flask ne trouvera pas index.html.
    # Tu peux aussi spécifier le dossier templates explicitement :
    # app = Flask(__name__, template_folder='chemin/vers/templates')
    app.run(debug=True) # Passez à debug=False en production
