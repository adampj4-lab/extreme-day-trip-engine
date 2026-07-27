import streamlit as st
from datetime import datetime, date
import requests

st.set_page_config(page_title="Extreme Day Trip Engine", layout="wide")

st.title("✈️ Extreme Day Trip Engine — Core Engine Restored")
st.markdown("Fully restored blueprint payload with proper multi-slice parsing.")

st.sidebar.header("API Configuration")
duffel_token = st.sidebar.text_input("Duffel Access Token", type="password")

st.sidebar.header("Search Parameters")
origin = st.sidebar.text_input("Origin Airport", value="LBA")
destination = st.sidebar.text_input("Destination Airport", value="DUB")
trip_date = st.sidebar.date_input("Flight Date", value=date(2026, 8, 2))
max_budget = st.sidebar.slider("Max Budget (£)", 50.0, 500.0, 200.0, 10.0)

if st.sidebar.button("Run Full Engine Search 🚀", type="primary"):
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
        
        # Exact multi-slice structure for same-day return
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
        
        with st.spinner("Executing live query across all connected carriers..."):
            try:
                response = requests.post(
                    "https://api.duffel.com/air/offer_requests?return_offers=true",
                    json=payload,
                    headers=headers
                )
                
                if response.status_code == 201:
                    res_json = response.json()
                    offers = res_json.get("data", {}).get("offers", [])
                    st.success(f"Successfully retrieved {len(offers)} raw offers.")
                    st.session_state.raw_offers = offers
                else:
                    st.error(f"API Error [{response.status_code}]: {response.text}")
                    st.session_state.raw_offers = []
            except Exception as e:
                st.error(f"Connection Exception: {e}")
                st.session_state.raw_offers = []

if "raw_offers" in st.session_state:
    offers = st.session_state.raw_offers
    
    if not offers:
        st.warning("No offers returned for this configuration.")
    else:
        st.markdown("### Available Itineraries")
        
        match_count = 0
        for idx, offer in enumerate(offers):
            total_price = float(offer.get("total_amount", 0))
            currency = offer.get("total_currency", "GBP")
            carrier = offer.get("owner", {}).get("name", "Unknown Airline")
            slices = offer.get("slices", [])
            
            if total_price > max_budget:
                continue
                
            match_count += 1
            with st.container(border=True):
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown(f"**Match #{match_count} — {carrier}**")
                    if len(slices) >= 2:
                        out_seg = slices[0].get("segments", [{}])[0]
                        ret_seg = slices[1].get("segments", [{}])[0]
                        
                        out_dep = out_seg.get("departing_at", "")[:16].replace("T", " ")
                        out_arr = out_seg.get("arriving_at", "")[:16].replace("T", " ")
                        ret_dep = ret_seg.get("departing_at", "")[:16].replace("T", " ")
                        ret_arr = ret_seg.get("arriving_at", "")[:16].replace("T", " ")
                        
                        st.write(f"Outbound: `{out_dep}` ➔ `{out_arr}`")
                        st.write(f"Return:   `{ret_dep}` ➔ `{ret_arr}`")
                with col2:
                    st.markdown(f"### {currency} {total_price:.2f}")
                
                st.text(f"Offer ID: {offer.get('id')}")
                
        if match_count == 0:
            st.warning("Offers were returned by the API, but all exceeded your max budget slider limit. Try increasing the budget filter.")
