import streamlit as st
from datetime import date
import requests

st.set_page_config(page_title="Duffel Raw Dump", layout="wide")
token = st.text_input("Duffel Token", type="password")

if st.button("Dump All Raw Offers"):
    headers = {
        "Authorization": f"Bearer {token}",
        "Duffel-Version": "v2",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    payload = {
        "data": {
            "slices": [
                {"origin": "LBA", "destination": "DUB", "departure_date": "2026-08-02"},
                {"origin": "DUB", "destination": "LBA", "departure_date": "2026-08-02"}
            ],
            "passengers": [{"type": "adult"}],
            "cabin_class": "economy"
        }
    }
    
    resp = requests.post("https://api.duffel.com/air/offer_requests?return_offers=true", json=payload, headers=headers)
    if resp.status_code == 201:
        data = resp.json().get("data", {})
        offers = data.get("offers", [])
        st.write(f"Total raw offers returned by Duffel: {len(offers)}")
        
        for o in offers:
            carrier = o.get("owner", {}).get("name")
            price = o.get("total_amount")
            st.write(f"Airline: **{carrier}** | Price: **£{price}**")
            st.json(o)
    else:
        st.error(resp.text)
