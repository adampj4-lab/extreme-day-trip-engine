import streamlit as st
from datetime import date
import requests

st.set_page_config(page_title="LBA-DUB Force Fetch", layout="wide")

st.title("✈️ LBA ➔ DUB Targeted Diagnostic")
st.markdown("Forcing a clean, unconstrained query specifically for Dublin to catch the budget fares.")

st.sidebar.header("API Configuration")
duffel_token = st.sidebar.text_input("Duffel Access Token", type="password")

if st.sidebar.button("Run Dublin Targeted Scan 🔍", type="primary"):
    if not duffel_token:
        st.error("Please provide your Duffel Access Token.")
    else:
        headers = {
            "Authorization": f"Bearer {duffel_token}",
            "Duffel-Version": "v2",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        # Exact same-day payload for LBA-DUB on August 2, 2026
        payload = {
            "data": {
                "slices": [
                    {
                        "origin": "LBA",
                        "destination": "DUB",
                        "departure_date": "2026-08-02"
                    },
                    {
                        "origin": "DUB",
                        "destination": "LBA",
                        "departure_date": "2026-08-02"
                    }
                ],
                "passengers": [{"type": "adult"}],
                "cabin_class": "economy"
            }
        }
        
        with st.spinner("Querying Duffel for LBA-DUB..."):
            try:
                response = requests.post(
                    "https://api.duffel.com/air/offer_requests?return_offers=true",
                    json=payload,
                    headers=headers
                )
                
                if response.status_code == 201:
                    data = response.json().get("data", {})
                    offers = data.get("offers", [])
                    st.success(f"API returned {len(offers)} total offers for Dublin.")
                    
                    for idx, o in enumerate(offers):
                        carrier = o.get("owner", {}).get("name", "Unknown")
                        price = o.get("total_amount")
                        currency = o.get("total_currency", "GBP")
                        
                        slices = o.get("slices", [])
                        out_seg = slices[0].get("segments", [{}])[0] if len(slices) > 0 else {}
                        ret_seg = slices[1].get("segments", [{}])[0] if len(slices) > 1 else {}
                        
                        out_dep = out_seg.get("departing_at", "")[:16].replace("T", " ")
                        ret_dep = ret_seg.get("departing_at", "")[:16].replace("T", " ")
                        
                        with st.container(border=True):
                            st.markdown(f"**Offer #{idx+1} — {carrier}** | Price: **{currency} {price}**")
                            st.write(f"Outbound: {out_dep} | Return: {ret_dep}")
                else:
                    st.error(f"API Error [{response.status_code}]: {response.text}")
            except Exception as e:
                st.error(f"Exception: {e}")
