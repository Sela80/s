// static/js/script.js

// Fonction pour afficher une page et masquer les autres
function showPage(pageId) {
    const pages = document.querySelectorAll('.page');
    pages.forEach(page => {
        page.classList.remove('active');
        // Attendre la fin de l'animation avant de cacher complètement
        setTimeout(() => {
             if (!page.classList.contains('active')) {
                 page.style.display = 'none';
             }
        }, 500);
    });
    const targetPage = document.getElementById(pageId);
    targetPage.style.display = 'flex';
    // Attendre un peu pour que display:flex soit appliqué avant d'ajouter 'active'
    setTimeout(() => {
        targetPage.classList.add('active');
    }, 10);
}

// Fonction pour calculer et afficher le coût
async function calculateCost() {
    // Récupérer les valeurs du formulaire
    const age = parseFloat(document.getElementById('age').value);
    const bmi = parseFloat(document.getElementById('bmi').value);
    const children = parseInt(document.getElementById('children').value, 10);
    const sexElement = document.querySelector('input[name="sex"]:checked');
    const smokerElement = document.querySelector('input[name="smoker"]:checked');
    const region = document.getElementById('region').value;

    // Validation simple
    if (isNaN(age) || isNaN(bmi) || isNaN(children) || !sexElement || !smokerElement) {
        alert("Veuillez remplir tous les champs obligatoires.");
        return;
    }

    const sex = sexElement.value;
    const smoker = smokerElement.value;

    // Préparer les données à envoyer au backend
    const inputData = {
        age: age,
        sex: sex,
        bmi: bmi,
        children: children,
        smoker: smoker,
        region: region
    };

    // Référence au bouton pour animation de chargement
    const calcButton = document.querySelector('button[onclick="calculateCost()"]');
    const originalText = calcButton.innerHTML;
    calcButton.innerHTML = 'Calcul en cours... <span class="loading-spinner"></span>';
    calcButton.classList.add('loading');
    calcButton.disabled = true;

    try {
        // Envoyer la requête POST au backend Flask
        const response = await fetch('/predict', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(inputData)
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || `Erreur HTTP: ${response.status}`);
        }

        const data = await response.json();

        if (data.error) {
            throw new Error(data.error);
        }

        // Obtenir le coût prédit
        const predictedCost = data.predicted_cost;

        // Formater le coût en devise
        const formattedCost = new Intl.NumberFormat('fr-FR', {
            style: 'currency',
            currency: 'EUR',
            maximumFractionDigits: 0
        }).format(predictedCost);

        // Générer une explication simple
        let explanation = "Votre profil ";
        if (age > 50) explanation += "d'âge avancé, ";
        if (bmi > 30) explanation += "un IMC élevé, ";
        if (smoker === 'yes') explanation += "le tabagisme, ";
        if (children > 2) explanation += "un nombre d'enfants élevé, ";
        explanation += `et votre région (${region}) influencent ce coût.`;
        if (explanation.endsWith(', ')) {
            explanation = explanation.slice(0, -2) + " influencent ce coût.";
        }

        // Mettre à jour l'affichage et basculer vers la page de résultats
        document.getElementById('costDisplay').textContent = formattedCost;
        document.getElementById('costExplanation').textContent = explanation;
        showPage('resultats');

    } catch (error) {
        console.error('Erreur lors de la prédiction:', error);
        alert("Une erreur s'est produite lors du calcul : " + error.message + ". Veuillez réessayer.");
    } finally {
        // Rétablir le bouton
        calcButton.innerHTML = originalText;
        calcButton.classList.remove('loading');
        calcButton.disabled = false;
    }
}

// Optionnel: Ajouter un écouteur d'événements pour la touche Entrée dans le formulaire
document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('predictionForm');
    if (form) {
        form.addEventListener('keydown', function(event) {
            if (event.key === 'Enter') {
                event.preventDefault(); // Empêcher la soumission par défaut
                calculateCost(); // Appeler la fonction de calcul
            }
        });
    }
});