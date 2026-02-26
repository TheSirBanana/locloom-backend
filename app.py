import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from azure.core.credentials import AzureKeyCredential
from azure.ai.formrecognizer import DocumentAnalysisClient

app = Flask(__name__)
CORS(app) 

AZURE_ENDPOINT = "https://locloom-ocr-cerveau.cognitiveservices.azure.com/"
AZURE_KEY = "44GKW9ZznKnVSXDgZLZfgaHAakBOWgy94XH0IYcYWVhlfvU9S7ORJQQJ99CBACBsN54XJ3w3AAALACOGa33E"

client = DocumentAnalysisClient(
    endpoint=AZURE_ENDPOINT, 
    credential=AzureKeyCredential(AZURE_KEY)
)

@app.route('/api/scan', methods=['POST'])
def scan_facture():
    if 'image' not in request.files:
        return jsonify({"erreur": "Aucune image trouvee"}), 400
        
    file = request.files['image']
    temp_path = "temp_receipt.jpg"
    file.save(temp_path)
    
    try:
        with open(temp_path, "rb") as f:
            poller = client.begin_analyze_document("prebuilt-receipt", document=f)
        
        receipts = poller.result()
        
        if not receipts.documents:
            os.remove(temp_path)
            return jsonify({"erreur": "Aucune facture reconnue"}), 400
            
        receipt = receipts.documents[0]
        
        marchand = receipt.fields.get("MerchantName")
        date = receipt.fields.get("TransactionDate")
        grand_total = receipt.fields.get("Total")
        
        valeur_total = grand_total.value if grand_total else 0.0
        
        somme_taxes_azure = 0.0
        tax_details = receipt.fields.get("TaxDetails")
        if tax_details and tax_details.value:
            for tax in tax_details.value:
                amount_field = tax.value.get("Amount")
                if amount_field and amount_field.value:
                    somme_taxes_azure += amount_field.value.amount

        tps_finale = 0.0
        tvq_finale = 0.0

        if somme_taxes_azure > 0:
            tps_finale = round(somme_taxes_azure * (5.0 / 14.975), 2)
            tvq_finale = round(somme_taxes_azure * (9.975 / 14.975), 2)
        elif valeur_total > 0:
            sous_total = valeur_total / 1.14975
            tps_finale = round(sous_total * 0.05, 2)
            tvq_finale = round(sous_total * 0.09975, 2)

        resultat = {
            "statut": "succes",
            "marchand": marchand.value if marchand else "Non trouve",
            "date": str(date.value) if date else "Non trouvee",
            "tps": tps_finale,
            "tvq": tvq_finale,
            "total_taxes": round(tps_finale + tvq_finale, 2),
            "grand_total": valeur_total
        }
        
        if os.path.exists(temp_path):
            os.remove(temp_path)
            
        return jsonify(resultat), 200

    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        return jsonify({"erreur": str(e)}), 500

if __name__ == '__main__':
    print("Serveur API LocLoom demarre sur le port 5000...")
    app.run(debug=True, port=5000)