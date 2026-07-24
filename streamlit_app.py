import streamlit as st
import requests
import time
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import urllib.parse

st.set_page_config(page_title="Extreme Day Trip Engine", layout="wide")

st.title("✈️ Extreme Day Trip Engine")
st.markdown("Find the ultimate multi-hub European day trips with custom ground times and late returns.")

st.sidebar.header("Trip Parameters")

duffel_token = st.sidebar.text_input("Duffel API Token", type="password")

homes_input = st.sidebar.text_input("Home Airports (comma-separated)", "LBA, MAN, EMA")
HOMES = [h.strip().upper() for h in homes_input.split(",") if h.strip()]

dest_choice = st.sidebar.radio("Destination Mode", ["Top European Hubs ('ANYWHERE')", "Custom List"])
if dest_choice == "Top European Hubs ('ANYWHERE')":
    DESTINATIONS = ["DUB", "AMS", "BCN", "AGP", "PMI", "ALC", "CDG", "CPH", "MXP"]
else:
    dests_input = st.sidebar.text_input("Destination Codes (comma-separated)", "DUB, BCN, AMS")
    DESTINATIONS = [d.strip().upper() for d in dests_input.split(",") if d.strip()]

col1, col2 = st.sidebar.columns(2)
start_date_str = col1.text_input("Start Date", "2026-08-01")
end_date_str = col2.text_input("End Date", "2026-08-10")

st.sidebar.subheader("Time & Constraints")
earliest_outbound = st.sidebar.text_input("Earliest Outbound", "05:00")
latest_outbound = st.sidebar.text_input("Latest Outbound", "10:00")
latest_return = st.sidebar.text_input("Latest Return Limit", "03:00")

min_ground = st.sidebar.slider("Min Ground Hours", 4.0, 16.0, 8.0, 0.5)
max_flight = st.sidebar.slider("Max Flight Duration (hrs)", 2.0, 6.0, 4.0, 0.5)

if "max_budget" not in st.session_state:
    st.session_state.max_budget = 200.0

max_budget = st.sidebar.slider(
    "Max Total Budget (£)", 
    50.0, 500.0, 
    key="max_budget", 
    step=10.0
)

sort_option = st.sidebar.selectbox("Sort Results By", ["Cheapest total price first", "Longest ground time first"])
weekend_only = st.sidebar.checkbox("Weekends Only (Sat/Sun)", value=False)

if st.sidebar.button("Run Engine 🚀", type="primary"):
    if not duffel_token:
        st.error("Please enter your Duffel API Token.")
    else:
        url = "https://api.duffel.com/air/offer_requests"
        headers = {
            "Authorization": f"Bearer {duffel_token}",
            "Duffel-Version": "v2",
            "Content-Type": "application/json"
        }
        
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
        
        dates_to_check = []
        current_date = start_date
        while current_date <= end_date:
            if not weekend_only or current_date.weekday() in [5, 6]:
                dates_to_check.append(current_date.strftime("%Y-%m-%d"))
            current_date += timedelta(days=1)
            
        with st.spinner(f"Scanning {len(dates_to_check)} dates across {len(HOMES)} homes and {len(DESTINATIONS)} destinations..."):
            paired_trips = []
            
            def fetch_route_offers(home, dest, flight_date):
                dt_obj = datetime.strptime(flight_date, "%Y-%m-%d")
                next_date_str = (dt_obj + timedelta(days=1)).strftime("%Y-%m-%d")
                
                out_payload = {"data": {"slices": [{"origin": home, "destination": dest, "departure_date": flight_date}], "passengers": [{"type": "adult"}], "cabin_class": "economy"}}
                in_payload_same = {"data": {"slices": [{"origin": dest, "destination": home, "departure_date": flight_date}], "passengers": [{"type": "adult"}], "cabin_class": "economy"}}
                in_payload_next = {"data": {"slices": [{"origin": dest, "destination": home, "departure_date": next_date_str}], "passengers": [{"type": "adult"}], "cabin_class": "economy"}}
                
                try:
                    time.sleep(0.05)
                    out_resp = requests.post(url, headers=headers, json=out_payload, timeout=20)
                    in_resp_same = requests.post(url, headers=headers, json=in_payload_same, timeout=20)
                    in_resp_next = requests.post(url, headers=headers, json=in_payload_next, timeout=20)
                except:
                    return []
                
                local_trips = []
                if out_resp.status_code == 201:
                    out_offers = out_resp.json()["data"].get("offers", [])
                    all_in_offers = []
                    if in_resp_same.status_code == 201:
                        all_in_offers.extend(in_resp_same.json()["data"].get("offers", []))
                    if in_resp_next.status_code == 201:
                        all_in_offers.extend(in_resp_next.json()["data"].get("offers", []))
                        
                    for out_offer in out_offers:
                        out_seg = out_offer["slices"][0]["segments"][0]
                        out_dep = datetime.fromisoformat(out_seg["departing_at"])
                        out_arr = datetime.fromisoformat(out_seg["arriving_at"])
                        out_dur = (out_arr - out_dep).total_seconds() / 3600
                        out_carrier = out_seg.get("marketing_carrier", {}).get("name", "Airline")
                        out_flight_num = f"{out_seg.get('marketing_carrier', {}).get('iata_code', '')}{out_seg.get('flight_number', '')}"
                        
                        min_out = datetime.strptime(earliest_outbound, "%H:%M").time()
                        max_out = datetime.strptime(latest_outbound, "%H:%M").time()
                        
                        if not (min_out <= out_dep.time() <= max_out) or out_dur > max_flight:
                            continue
                            
                        out_price = float(out_offer["total_amount"])
                        
                        for in_offer in all_in_offers:
                            in_seg = in_offer["slices"][0]["segments"][0]
                            in_dep = datetime.fromisoformat(in_seg["departing_at"])
                            in_arr = datetime.fromisoformat(in_seg["arriving_at"])
                            in_dur = (in_arr - in_dep).total_seconds() / 3600
                            in_carrier = in_seg.get("marketing_carrier", {}).get("name", "Airline")
                            in_flight_num = f"{in_seg.get('marketing_carrier', {}).get('iata_code', '')}{in_seg.get('flight_number', '')}"
                            
                            if in_dur > max_flight:
                                continue
                            
                            return_limit = datetime.strptime(latest_return, "%H:%M").time()
                            is_next_day_cutoff = return_limit <= datetime.strptime("06:00", "%H:%M").time()
                            in_flight_date_str = in_seg["departing_at"].split("T")[0]
                            
                            if in_flight_date_str == flight_date:
                                pass
                            elif in_flight_date_str == next_date_str:
                                if is_next_day_cutoff and in_dep.time() > return_limit:
                                    continue
                            else:
                                continue
                            
                            ground_hours = (in_dep - out_arr).total_seconds() / 3600
                            if ground_hours < min_ground:
                                continue
                            
                            in_price = float(in_offer["total_amount"])
                            total_price = out_price + in_price
                            if total_price > max_budget:
                                continue
                            
                            local_trips.append({
                                "home": home,
                                "dest": dest,
                                "Route": f"{home} ➔ {dest} ➔ {home}",
                                "Outbound Date": flight_date,
                                "Return Date": in_flight_date_str,
                                "Ground (hrs)": round(ground_hours, 1),
                                "Total Price (£)": round(total_price, 2),
                                "Outbound Time": f"{out_dep.strftime('%H:%M')} ➔ {out_arr.strftime('%H:%M')}",
                                "Return Time": f"{in_dep.strftime('%H:%M')} ➔ {in_arr.strftime('%H:%M')}",
                                "Out Carrier": f"{out_carrier} ({out_flight_num})",
                                "In Carrier": f"{in_carrier} ({in_flight_num})"
                            })
                return local_trips

            tasks = [(h, d, dt) for h in HOMES for d in DESTINATIONS for dt in dates_to_check]
            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = [executor.submit(fetch_route_offers, h, d, dt) for h, d, dt in tasks]
                for future in as_completed(futures):
                    paired_trips.extend(future.result())
            
            unique_trips = {}
            for t in paired_trips:
                key = (t["Route"], t["Outbound Date"], t["Return Date"], t["Outbound Time"], t["Return Time"])
                if key not in unique_trips or t["Total Price (£)"] < unique_trips[key]["Total Price (£)"]:
                    unique_trips[key] = t
            paired_trips = list(unique_trips.values())
            
            if sort_option == "Longest ground time first":
                paired_trips.sort(key=lambda x: x["Ground (hrs)"], reverse=True)
            else:
                paired_trips.sort(key=lambda x: x["Total Price (£)"])
                
            st.success(f"Found {len(paired_trips)} unique matching trips!")
            
            # --- RENDER CARD LAYOUT ---
            for trip in paired_trips:
                with st.container(border=True):
                    c1, c2 = st.columns([3, 1])
                    with c1:
                        st.markdown(f"### ✈️ {trip['Route']}")
                        st.caption(f"⏱️ **{trip['Ground (hrs)'])} hours** on the ground")
                    with c2:
                        st.markdown(f"### £{trip['Total Price (£)]']}")
                    
                    st.divider()
                    
                    col_out, col_in = st.columns(2)
                    with col_out:
                        st.markdown(f"**Outbound ({trip['Outbound Date']})**")
                        st.write(f"🕒 {trip['Outbound Time']}")
                        st.text(f"Carrier: {trip['Out Carrier']}")
                    with col_in:
                        st.markdown(f"**Return ({trip['Return Date']})**")
                        st.write(f"🕒 {trip['Return Time']}")
                        st.text(f"Carrier: {trip['In Carrier']}")
                    
                    st.divider()
                    
                    # Generate Deep Links
                    gf_url = f"https://www.google.com/travel/flights?q=Flights%20from%20{trip['home']}%20to%20{trip['dest']}%20on%20{trip['Outbound Date']}%20returning%20on%20{trip['Return Date']}"
                    sk_url = f"https://www.skyscanner.net/transport/flights/{trip['home'].lower()}/{trip['dest'].lower()}/{trip['Outbound Date'].replace('-','')}/{trip['Return Date'].replace('-','')}/"
                    
                    b1, b2 = st.columns(2)
                    with b1:
                        st.link_button("🌐 Search on Google Flights", gf_url, use_container_width=True)
                    with b2:
                        st.link_button("✈️ Search on Skyscanner", sk_url, use_container_width=True)
