import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from azure.core.credentials import AzureKeyCredential
from azure.ai.formrecognizer import DocumentAnalysisClient

app = Flask(__name__)
CORS(app) 

AZURE_ENDPOINT = "https://locloom-ocr-cerveau.cognitiveservices.azure.com/"
AZURE_KEY = "44GKW9ZznKnVSXDgZLZfgaHAakBOWgy94XH0IYcYWVhlfvU9S7ORJQQJ99CBACBsN54XJ3w3AAALACOGa33E"

client = DocumentAnalysisClient(AZURE_ENDPOINT, AzureKeyCredential(AZURE_KEY))

@app.route('/api/scan', methods=['POST'])
def scan_facture():
    data = request.json
    image_url = data.get("imageUrl") # Wix va nous envoyer un lien

    if not image_url:
        return jsonify({"erreur": "Lien d'image manquant"}), 400
    
    try:
        # Azure peut lire directement depuis une URL !
        poller = client.begin_analyze_document_from_url("prebuilt-receipt", image_url)
        receipts = poller.result()
        
        if not receipts.documents:
            return jsonify({"erreur": "Aucune facture trouvee"}), 400
            
        receipt = receipts.documents[0]
        marchand = receipt.fields.get("MerchantName")
        date = receipt.fields.get("TransactionDate")
        grand_total = receipt.fields.get("Total")
        valeur_total = grand_total.value if grand_total else 0.0
        
        # Logique des taxes QC
        somme_taxes_azure = 0.0
        tax_details = receipt.fields.get("TaxDetails")
        if tax_details and tax_details.value:
            for tax in tax_details.value:
                amount_field = tax.value.get("Amount")
                if amount_field and amount_field.value:
                    somme_taxes_azure += amount_field.value.amount

        tps = round(somme_taxes_azure * (5.0 / 14.975), 2) if somme_taxes_azure > 0 else round((valeur_total / 1.14975) * 0.05, 2)
        tvq = round(somme_taxes_azure * (9.975 / 14.975), 2) if somme_taxes_azure > 0 else round((valeur_total / 1.14975) * 0.09975, 2)

        return jsonify({
            "statut": "succes",
            "marchand": marchand.value if marchand else "Inconnu",
            "date": str(date.value) if date else "Inconnue",
            "tps": tps,
            "tvq": tvq,
            "grand_total": valeur_total
        }), 200

    except Exception as e:
        return jsonify({"erreur": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
