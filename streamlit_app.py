import streamlit as st
from datetime import datetime, timedelta, date
import requests

st.set_page_config(page_title="Extreme Day Trip Engine (Live)", layout="wide")

st.title("✈️ Extreme Day Trip Engine — Live Duffel API")
st.markdown("Scan real-world direct routes, live market prices, and tight turnaround day trips.")

st.sidebar.header("Live API Configuration")
duffel_token = st.sidebar.text_input("Duffel Access Token", type="password", help="Enter your live or test Duffel API token here.")

st.sidebar.header("Trip Parameters")

home_airport = "LBA"
dest = "DUB"
search_date = date(2026, 8, 2)

st.sidebar.info(f"🔍 Hardcoded Test Target: **{home_airport} ➔ {dest}** on **{search_date.strftime('%Y-%m-%d')}**")

min_ground = st.sidebar.slider("Min Ground Hours", 0.0, 16.0, 0.0, 0.5)
max_budget = st.sidebar.slider("Max Total Budget (£)", 50.0, 500.0, 200.0, 10.0)

if st.sidebar.button("Test Direct LBA-DUB Fetch 🚀", type="primary"):
    if not duffel_token:
        st.error("Please provide your Duffel Access Token in the sidebar.")
    else:
        headers = {
            "Authorization": f"Bearer {duffel_token}",
            "Duffel-Version": "v1",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        dt_str = search_date.strftime("%Y-%m-%d")
        next_dt_str = (search_date + timedelta(days=1)).strftime("%Y-%m-%d")
        
        found_trips = []
        
        with st.spinner("Executing independent one-way lookups for LBA -> DUB and DUB -> LBA..."):
            out_payload = {
                "data": {
                    "slices": [{
                        "origin": home_airport,
                        "destination": dest,
                        "departure_date": dt_str
                    }],
                    "passengers": [{"type": "adult"}],
                    "cabin_class": "economy",
                    "max_connections": 0
                }
            }
            
            out_resp = requests.post("https://api.duffel.com/air/offer_requests?return_offers=true", json=out_payload, headers=headers)
            
            if out_resp.status_code == 201:
                out_data = out_resp.json().get("data", {})
                out_offers = out_data.get("offers", [])
                
                st.write(f"Found **{len(out_offers)}** outbound offers from LBA to DUB on {dt_str}.")
                
                for out_offer in out_offers:
                    out_price = float(out_offer.get("total_amount", 0))
                    out_slices = out_offer.get("slices", [])
                    if not out_slices:
                        continue
                    out_seg = out_slices[0].get("segments", [{}])[0]
                    out_dep = out_seg.get("departing_at", "")
                    out_arr = out_seg.get("arriving_at", "")
                    
                    if not out_dep or not out_arr:
                        continue
                        
                    out_dep_time = datetime.fromisoformat(out_dep.replace("Z", "+00:00"))
                    out_arr_time = datetime.fromisoformat(out_arr.replace("Z", "+00:00"))
                    
                    for ret_dt in [dt_str, next_dt_str]:
                        ret_payload = {
                            "data": {
                                "slices": [{
                                    "origin": dest,
                                    "destination": home_airport,
                                    "departure_date": ret_dt
                                }],
                                "passengers": [{"type": "adult"}],
                                "cabin_class": "economy",
                                "max_connections": 0
                            }
                        }
                        
                        ret_resp = requests.post("https://api.duffel.com/air/offer_requests?return_offers=true", json=ret_payload, headers=headers)
                        if ret_resp.status_code == 201:
                            ret_data = ret_resp.json().get("data", {})
                            ret_offers = ret_data.get("offers", [])
                            
                            for ret_offer in ret_offers:
                                ret_price = float(ret_offer.get("total_amount", 0))
                                total_price = out_price + ret_price
                                
                                ret_slices = ret_offer.get("slices", [])
                                if not ret_slices:
                                    continue
                                ret_seg = ret_slices[0].get("segments", [{}])[0]
                                in_dep = ret_seg.get("departing_at", "")
                                in_arr = ret_seg.get("arriving_at", "")
                                
                                if not in_dep or not in_arr:
                                    continue
                                    
                                in_dep_time = datetime.fromisoformat(in_dep.replace("Z", "+00:00"))
                                in_arr_time = datetime.fromisoformat(in_arr.replace("Z", "+00:00"))
                                
                                in_dep_naive = in_dep_time.replace(tzinfo=None)
                                out_arr_naive = out_arr_time.replace(tzinfo=None)
                                
                                ground_mins = (in_dep_naive - out_arr_naive).total_seconds() / 60.0
                                ground_hrs = ground_mins / 60.0
                                
                                if ground_hrs >= min_ground and total_price <= max_budget:
                                    carrier = out_offer.get("owner", {}).get("name", "Airline")
                                    found_trips.append({
                                        "Route": f"{home_airport} ➔ {dest} ➔ {home_airport}",
                                        "Outbound Date": dt_str,
                                        "Return Date": in_dep_naive.strftime("%Y-%m-%d"),
                                        "Ground (hrs)": round(ground_hrs, 1),
                                        "Total Price (£)": total_price,
                                        "Outbound Time": f"{out_dep_time.strftime('%H:%M')} ➔ {out_arr_time.strftime('%H:%M')}",
                                        "Return Time": f"{in_dep_time.strftime('%H:%M')} ➔ {in_arr_time.strftime('%H:%M')}",
                                        "Carrier": carrier,
                                        "Offer ID": f"{out_offer.get('id')} + {ret_offer.get('id')}"
                                    })
            else:
                st.error(f"API Error on Outbound Call: {out_resp.status_code} - {out_resp.text}")

        st.session_state.test_trips = found_trips

if "test_trips" in st.session_state:
    trips = st.session_state.test_trips
    st.success(f"Diagnostic scan complete! Found {len(trips)} matching combinations.")
    
    for trip in trips:
        with st.container(border=True):
            c1, c2 = st.columns([3, 1])
            with c1:
                st.markdown(f"### ✈️ {trip['Route']}")
                st.caption(f"⏱️ **{trip['Ground (hrs)']} hours** on the ground | Operated by {trip['Carrier']}")
            with c2:
                st.markdown(f"### £{trip['Total Price (£)']:.2f}")
            
            st.divider()
            col_out, col_in = st.columns(2)
            with col_out:
                st.markdown(f"**Outbound ({trip['Outbound Date']})**")
                st.write(f"🕒 {trip['Outbound Time']}")
            with col_in:
                st.markdown(f"**Return ({trip['Return Date']})**")
                st.write(f"🕒 {trip['Return Time']}")
            st.text(f"Offer IDs: {trip['Offer ID']}")
