import streamlit as st
from datetime import datetime, date
import requests

st.set_page_config(page_title="Extreme Day Trip Engine", layout="wide")

st.title("✈️ Extreme Day Trip Engine")
st.markdown("Back to basics: clean architecture, direct API calls, and zero hidden filtering traps.")

st.sidebar.header("API Configuration")
duffel_token = st.sidebar.text_input("Duffel Access Token", type="password")

st.sidebar.header("Search Parameters")
origin = st.sidebar.text_input("Origin Airport", value="LBA")
destination = st.sidebar.text_input("Destination Airport", value="DUB")
trip_date = st.sidebar.date_input("Flight Date", value=date(2026, 8, 2))
max_budget = st.sidebar.slider("Max Budget (£)", 50.0, 500.0, 200.0, 10.0)

if st.sidebar.button("Run Search 🚀", type="primary"):
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
        
        # We query outbound and return as independent one-ways first to ensure low-cost carriers appear, 
        # then combine them to calculate true total day-trip cost and ground time.
        outbound_payload = {
            "data": {
                "slices": [{
                    "origin": origin.upper(),
                    "destination": destination.upper(),
                    "departure_date": dt_str
                }],
                "passengers": [{"type": "adult"}],
                "cabin_class": "economy"
            }
        }
        
        return_payload = {
            "data": {
                "slices": [{
                    "origin": destination.upper(),
                    "destination": origin.upper(),
                    "departure_date": dt_str
                }],
                "passengers": [{"type": "adult"}],
                "cabin_class": "economy"
            }
        }
        
        with st.spinner("Scanning live airline inventory..."):
            try:
                # Fire both requests independently
                out_resp = requests.post("https://api.duffel.com/air/offer_requests?return_offers=true", json=outbound_payload, headers=headers)
                ret_resp = requests.post("https://api.duffel.com/air/offer_requests?return_offers=true", json=return_payload, headers=headers)
                
                if out_resp.status_code == 201 and ret_resp.status_code == 201:
                    out_offers = out_resp.json().get("data", {}).get("offers", [])
                    ret_offers = ret_resp.json().get("offers", [])
                    
                    st.success(f"Found {len(out_offers)} outbound options and {len(ret_offers)} return options.")
                    
                    st.session_state.out_offers = out_offers
                    st.session_state.ret_offers = ret_offers
                else:
                    st.error(f"API Error - Outbound: {out_resp.status_code}, Return: {ret_resp.status_code}")
                    st.session_state.out_offers = []
                    st.session_state.ret_offers = []
            except Exception as e:
                st.error(f"Connection Error: {e}")

if "out_offers" in st.session_state and "ret_offers" in st.session_state:
    outs = st.session_state.out_offers
    rets = st.session_state.ret_offers
    
    st.markdown("### Available Combinations")
    
    match_count = 0
    for out in outs:
        out_price = float(out.get("total_amount", 0))
        out_carrier = out.get("owner", {}).get("name", "Airline")
        out_seg = out.get("slices", [{}])[0].get("segments", [{}])[0]
        out_dep = out_seg.get("departing_at", "")[:16].replace("T", " ")
        out_arr = out_seg.get("arriving_at", "")[:16].replace("T", " ")
        
        for ret in rets:
            ret_price = float(ret.get("total_amount", 0))
            total_price = out_price + ret_price
            
            if total_price > max_budget:
                continue
                
            ret_carrier = ret.get("owner", {}).get("name", "Airline")
            ret_seg = ret.get("slices", [{}])[0].get("segments", [{}])[0]
            ret_dep = ret_seg.get("departing_at", "")[:16].replace("T", " ")
            ret_arr = ret_seg.get("arriving_at", "")[:16].replace("T", " ")
            
            match_count += 1
            with st.container(border=True):
                c1, c2 = st.columns([3, 1])
                with c1:
                    st.markdown(f"**Combination #{match_count}**")
                    st.write(f"Outbound ({out_carrier}): `{out_dep}` ➔ `{out_arr}`")
                    st.write(f"Return ({ret_carrier}):   `{ret_dep}` ➔ `{ret_arr}`")
                with c2:
                    st.markdown(f"### £{total_price:.2f}")
                    
    if match_count == 0:
        st.warning("No combinations match your budget for this date.")
