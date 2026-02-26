@app.route('/api/scan', methods=['POST'])
def scan_invoice():
    data = request.json
    image_url = data.get("imageUrl")
    
    # NOUVEAU : On attrape les infos du menu déroulant de Wix
    categorie = data.get("categorie", "Entretien") 
    immeuble_id = data.get("immeubleId", "Sans adresse")
    porte = data.get("porte", "Bâtiment complet") # NOUVEAU : La fameuse porte !

    if not image_url:
        return jsonify({"statut": "erreur", "erreur": "URL manquante"}), 400

    try:
        # Analyse Azure (Ton code ne change pas ici)
        poller = document_analysis_client.begin_analyze_document_from_url("prebuilt-invoice", image_url)
        result = poller.result()

        invoice = result.documents[0]
        marchand = invoice.fields.get("VendorName").value if invoice.fields.get("VendorName") else "Inconnu"
        total = invoice.fields.get("InvoiceTotal").value.amount if invoice.fields.get("InvoiceTotal") else 0.0

        # Calcul des taxes
        tps = total * 0.04348 if total > 0 else 0
        tvq = total * 0.08675 if total > 0 else 0

        # NOUVEAU : On ajoute la catégorie, l'immeuble et la porte pour Supabase
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
