import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from azure.core.credentials import AzureKeyCredential
from azure.ai.formrecognizer import DocumentAnalysisClient
from supabase import create_client, Client

app = Flask(__name__)
CORS(app) # Autorise Wix a parler a ton serveur

# --- CONFIGURATION DES CLES (A REMPLACER) ---

# AZURE
AZURE_ENDPOINT = "https://locloom-ocr-cerveau.cognitiveservices.azure.com/"
AZURE_KEY = "44GKW9ZznKnVSXDgZLZfgaHAakBOWgy94XH0IYcYWVhlfvU9S7ORJQQJ99CBACBsN54XJ3w3AAALACOGa33E"

# SUPABASE (Prends ces infos dans Settings > API de ton projet Supabase)
SUPABASE_URL = "https://cwbcyvqcmbmmddngratp.supabase.co"
SUPABASE_KEY = sb_publishable_RLeTqdxeiKPD3A_JoSkH8g_az4OjJ8a

# Initialisation des clients
azure_client = DocumentAnalysisClient(AZURE_ENDPOINT, AzureKeyCredential(AZURE_KEY))
supabase_client: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- LOGIQUE DU SERVEUR ---

@app.route('/api/scan', methods=['POST'])
def scan_facture():
    data = request.json
    image_url = data.get("imageUrl") # Wix envoie le lien de la photo

    if not image_url:
        return jsonify({"erreur": "Lien d'image manquant"}), 400
    
    try:
        # 1. Analyse par l'IA d'Azure
        poller = azure_client.begin_analyze_document_from_url("prebuilt-receipt", image_url)
        receipts = poller.result()
        
        if not receipts.documents:
            return jsonify({"erreur": "Aucune facture detectee sur l'image"}), 400
            
        receipt = receipts.documents[0]
        marchand = receipt.fields.get("MerchantName")
        date_trans = receipt.fields.get("TransactionDate")
        grand_total = receipt.fields.get("Total")
        valeur_total = grand_total.value if grand_total else 0.0
        
        # 2. Logique des taxes (Quebec)
        somme_taxes_azure = 0.0
        tax_details = receipt.fields.get("TaxDetails")
        
        if tax_details and tax_details.value:
            for tax in tax_details.value:
                amount_field = tax.value.get("Amount")
                if amount_field and amount_field.value:
                    somme_taxes_azure += amount_field.value.amount

        # Calcul des taxes au prorata si necessaire
        if somme_taxes_azure > 0:
            tps = round(somme_taxes_azure * (5.0 / 14.975), 2)
            tvq = round(somme_taxes_azure * (9.975 / 14.975), 2)
        else:
            tps = round((valeur_total / 1.14975) * 0.05, 2)
            tvq = round((valeur_total / 1.14975) * 0.09975, 2)

        # 3. ENREGISTREMENT DANS SUPABASE
        try:
            transaction_data = {
                "marchand": marchand.value if marchand else "Inconnu",
                "date_facture": str(date_trans.value) if date_trans else None,
                "total_brut": valeur_total,
                "tps": tps,
                "tvq": tvq,
                "image_url": image_url,
                "role": "proprietaire" 
            }
            supabase_client.table("transactions").insert(transaction_data).execute()
            print("Succes: Donnees sauvegardees dans Supabase")
        except Exception as e:
            print(f"Erreur Supabase: {e}")

        # 4. Reponse envoyee a Wix
        return jsonify({
            "statut": "succes",
            "marchand": marchand.value if marchand else "Inconnu",
            "date": str(date_trans.value) if date_trans else "Inconnue",
            "tps": tps,
            "tvq": tvq,
            "grand_total": valeur_total
        }), 200

    except Exception as e:
        return jsonify({"erreur": f"Erreur serveur: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

