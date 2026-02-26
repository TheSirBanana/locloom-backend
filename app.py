import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from supabase import create_client, Client
from azure.core.credentials import AzureKeyCredential
from azure.ai.formrecognizer import DocumentAnalysisClient

# 1. Initialisation de l'application
app = Flask(__name__)
CORS(app)

# AZURE
AZURE_ENDPOINT = "https://locloom-ocr-cerveau.cognitiveservices.azure.com/"
AZURE_KEY = "44GKW9ZznKnVSXDgZLZfgaHAakBOWgy94XH0IYcYWVhlfvU9S7ORJQQJ99CBACBsN54XJ3w3AAALACOGa33E"

# SUPABASE
SUPABASE_URL = "https://cwbcyvqcmbmmddngratp.supabase.co"
SUPABASE_KEY = "sb_publishable_RLeTqdxeiKPD3A_JoSkH8g_az4OjJ8a"

# Initialisation du client Azure
document_analysis_client = DocumentAnalysisClient(
    endpoint=AZURE_ENDPOINT, credential=AzureKeyCredential(AZURE_KEY)
)

# 4. La route principale pour scanner
@app.route('/api/scan', methods=['POST'])
def scan_invoice():
    data = request.json
    image_url = data.get("imageUrl")
    
    # On attrape les infos du menu déroulant de Wix
    categorie = data.get("categorie", "Entretien") 
    immeuble_id = data.get("immeubleId", "Sans adresse")
    porte = data.get("porte", "Bâtiment complet")

    if not image_url:
        return jsonify({"statut": "erreur", "erreur": "URL manquante"}), 400

    try:
        # Analyse Azure
        poller = document_analysis_client.begin_analyze_document_from_url("prebuilt-invoice", image_url)
        result = poller.result()

        invoice = result.documents[0]
        marchand = invoice.fields.get("VendorName").value if invoice.fields.get("VendorName") else "Inconnu"
        
        # Gestion sécuritaire du total
        total_field = invoice.fields.get("InvoiceTotal")
        total = total_field.value.amount if total_field else 0.0

        # Calcul des taxes (Québec)
        tps = total * 0.04348 if total > 0 else 0
        tvq = total * 0.08675 if total > 0 else 0

        # Enregistrement dans Supabase
        transaction_data = {
            "marchand": marchand,
            "total_brut": total,
            "tps": tps,
            "tvq": tvq,
            "image_url": image_url,
            "categorie": categorie,
            "immeuble_id": immeuble_id,
            "porte": porte
        }
        
        supabase.table("transactions").insert(transaction_data).execute()

        return jsonify({
            "statut": "succes",
            "marchand": marchand,
            "grand_total": total,
            "tps": tps,
            "tvq": tvq
        })

    except Exception as e:
        return jsonify({"statut": "erreur", "erreur": str(e)}), 500

# 5. Démarrage du serveur
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
