import streamlit as st
from datetime import date
import requests

st.set_page_config(page_title="Extreme Day Trip Engine - Direct Debugger", layout="wide")

st.title("✈️ Extreme Day Trip Engine — Unfiltered Inventory Inspector")
st.markdown("Pulling raw multi-slice offers directly from Duffel with zero filtering.")

st.sidebar.header("API Configuration")
duffel_token = st.sidebar.text_input("Duffel Access Token", type="password")

st.sidebar.header("Parameters")
origin = st.sidebar.text_input("Origin", value="LBA")
destination = st.sidebar.text_input("Destination", value="DUB")
trip_date = st.sidebar.date_input("Date", value=date(2026, 8, 2))

if st.sidebar.button("Fetch Raw Unfiltered Feed 🔍", type="primary"):
    if not duffel_token:
        st.error("Please provide your Duffel Access Token.")
    else:
        headers = {
            "Authorization": f"Bearer {duffel_token}",
            "Duffel-Version": "v2",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        dt_str = trip_date.strftime("%Y-%m-%d")
        
        # Standard multi-slice payload matching the exact structure that previously worked
        payload = {
            "data": {
                "slices": [
                    {
                        "origin": origin.upper(),
                        "destination": destination.upper(),
                        "departure_date": dt_str
                    },
                    {
                        "origin": destination.upper(),
                        "destination": origin.upper(),
                        "departure_date": dt_str
                    }
                ],
                "passengers": [{"type": "adult"}],
                "cabin_class": "economy"
            }
        }
        
        with st.spinner("Querying Duffel API..."):
            try:
                response = requests.post(
                    "https://api.duffel.com/air/offer_requests?return_offers=true",
                    json=payload,
                    headers=headers
                )
                
                if response.status_code == 201:
                    res_json = response.json()
                    offers = res_json.get("data", {}).get("offers", [])
                    
                    st.success(f"Success! Total offers returned: {len(offers)}")
                    
                    for idx, offer in enumerate(offers):
                        carrier = offer.get("owner", {}).get("name", "Unknown Carrier")
                        price = offer.get("total_amount")
                        currency = offer.get("total_currency", "GBP")
                        
                        with st.container(border=True):
                            st.markdown(f"**#{idx+1} — {carrier}** | **{currency} {price}**")
                            st.json(offer)
                else:
                    st.error(f"API Error [{response.status_code}]: {response.text}")
            except Exception as e:
                st.error(f"Exception: {e}")
