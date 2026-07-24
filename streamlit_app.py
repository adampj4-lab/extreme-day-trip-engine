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
            "Duffel-Version": "v2",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        dt_str = search_date.strftime("%Y-%m-%d")
        found_trips = []
        
        with st.spinner("Executing strict same-day return lookup for LBA -> DUB -> LBA..."):
            # CRITICAL FIX: To capture exact same-day return cheap fares (like Ryanair £38 combos), 
            # we send a single multi-slice payload with both outbound and inbound explicitly set to the SAME calendar date.
            payload = {
                "data": {
                    "slices": [
                        {
                            "origin": home_airport,
                            "destination": dest,
                            "departure_date": dt_str
                        },
                        {
                            "origin": dest,
                            "destination": home_airport,
                            "departure_date": dt_str
                        }
                    ],
                    "passengers": [{"type": "adult"}],
                    "cabin_class": "economy"
                }
            }
            
            response = requests.post("https://api.duffel.com/air/offer_requests?return_offers=true", json=payload, headers=headers)
            
            if response.status_code == 201:
                data = response.json().get("data", {})
                offers = data.get("offers", [])
                
                st.write(f"Found **{len(offers)}** total same-day round-trip offers for {dt_str}.")
                
                for offer in offers:
                    total_price = float(offer.get("total_amount", 0))
                    currency = offer.get("total_currency", "GBP")
                    
                    if currency != "GBP" or total_price > max_budget:
                        continue
                        
                    slices = offer.get("slices", [])
                    if len(slices) == 2:
                        out_slice = slices[0]
                        in_slice = slices[1]
                        
                        out_segs = out_slice.get("segments", [])
                        in_segs = in_slice.get("segments", [])
                        
                        if len(out_segs) != 1 or len(in_segs) != 1:
                            continue
                            
                        out_seg = out_segs[0]
                        in_seg = in_segs[0]
                        
                        out_dep = out_seg.get("departing_at", "")
                        out_arr = out_seg.get("arriving_at", "")
                        in_dep = in_seg.get("departing_at", "")
                        in_arr = in_seg.get("arriving_at", "")
                        
                        if out_dep and out_arr and in_dep and in_arr:
                            out_dep_time = datetime.fromisoformat(out_dep.replace("Z", "+00:00"))
                            out_arr_time = datetime.fromisoformat(out_arr.replace("Z", "+00:00"))
                            in_dep_time = datetime.fromisoformat(in_dep.replace("Z", "+00:00"))
                            in_arr_time = datetime.fromisoformat(in_arr.replace("Z", "+00:00"))
                            
                            in_dep_naive = in_dep_time.replace(tzinfo=None)
                            out_arr_naive = out_arr_time.replace(tzinfo=None)
                            
                            ground_mins = (in_dep_naive - out_arr_naive).total_seconds() / 60.0
                            ground_hrs = ground_mins / 60.0
                            
                            if ground_hrs >= min_ground:
                                carrier = offer.get("owner", {}).get("name", "Airline")
                                found_trips.append({
                                    "Route": f"{home_airport} ➔ {dest} ➔ {home_airport}",
                                    "Outbound Date": dt_str,
                                    "Return Date": dt_str,
                                    "Ground (hrs)": round(ground_hrs, 1),
                                    "Total Price (£)": total_price,
                                    "Outbound Time": f"{out_dep_time.strftime('%H:%M')} ➔ {out_arr_time.strftime('%H:%M')}",
                                    "Return Time": f"{in_dep_time.strftime('%H:%M')} ➔ {in_arr_time.strftime('%H:%M')}",
                                    "Carrier": carrier,
                                    "Offer ID": offer.get("id")
                                })
            else:
                st.error(f"API Error: {response.status_code} - {response.text}")

        st.session_state.test_trips = found_trips

if "test_trips" in st.session_state:
    trips = st.session_state.test_trips
    st.success(f"Diagnostic scan complete! Found {len(trips)} same-day matching combinations.")
    
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
            st.text(f"Offer ID: {trip['Offer ID']}")
