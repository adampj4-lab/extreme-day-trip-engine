import streamlit as st
from datetime import datetime, timedelta
import requests

st.set_page_config(page_title="Extreme Day Trip Engine (Live)", layout="wide")

st.title("✈️ Extreme Day Trip Engine — Live Duffel API")
st.markdown("Scan real-world direct routes, live market prices, and tight turnaround day trips.")

st.sidebar.header("Live API Configuration")
duffel_token = st.sidebar.text_input("Duffel Access Token", type="password", help="Enter your live or test Duffel API token here.")

st.sidebar.header("Trip Parameters")

# Hierarchical Airport Selection: Alphabetized Country & Airport Lists
AIRPORT_HIERARCHY = {
    "Denmark": {
        "Copenhagen (CPH)": "CPH"
    },
    "France": {
        "Paris Charles de Gaulle (CDG)": "CDG",
        "Paris Orly (ORY)": "ORY"
    },
    "Ireland": {
        "Cork (ORK)": "ORK",
        "Dublin (DUB)": "DUB",
        "Shannon (SNN)": "SNN"
    },
    "Italy": {
        "Milan Malpensa (MXP)": "MXP",
        "Rome Fiumicino (FCO)": "FCO"
    },
    "Netherlands": {
        "Amsterdam Schiphol (AMS)": "AMS"
    },
    "Spain": {
        "Alicante (ALC)": "ALC",
        "Barcelona (BCN)": "BCN",
        "Madrid (MAD)": "MAD",
        "Malaga (AGP)": "AGP",
        "Palma de Mallorca (PMI)": "PMI"
    },
    "United Kingdom": {
        "Birmingham (BHX)": "BHX",
        "Doncaster Sheffield (DSA)": "DSA",
        "East Midlands (EMA)": "EMA",
        "Humberside (HUY)": "HUY",
        "Leeds Bradford (LBA)": "LBA",
        "Liverpool (LPL)": "LPL",
        "London Gatwick (LGW)": "LGW",
        "London Heathrow (LHR)": "LHR",
        "London Stansted (STN)": "STN",
        "Manchester (MAN)": "MAN",
        "Newcastle (NCL)": "NCL"
    }
}

# Sort countries alphabetically
sorted_countries = sorted(AIRPORT_HIERARCHY.keys())
selected_country = st.sidebar.selectbox("Home Country", sorted_countries, index=sorted_countries.index("United Kingdom"))

# Sort airports alphabetically within the selected country
available_airports = AIRPORT_HIERARCHY[selected_country]
sorted_airport_labels = sorted(available_airports.keys())
selected_airport_label = st.sidebar.selectbox("Home Airport", sorted_airport_labels)
home_airport = available_airports[selected_airport_label]

destinations_input = st.sidebar.text_input("Destination Codes (comma-separated)", "DUB, AMS, BCN, AGP, PMI, ALC, CPH, MXP")
destinations = [d.strip().upper() for d in destinations_input.split(",") if d.strip()]

col1, col2 = st.sidebar.columns(2)
start_date_str = col1.text_input("Start Date", "2026-08-01")
end_date_str = col2.text_input("Max 14-Day Window End", "2026-08-14")

st.sidebar.subheader("Time & Constraints")
earliest_outbound = st.sidebar.text_input("Earliest Outbound", "05:00")
latest_outbound = st.sidebar.text_input("Latest Outbound", "10:00")

min_ground = st.sidebar.slider("Min Ground Hours", 4.0, 16.0, 8.0, 0.5)

if "max_budget" not in st.session_state:
    st.session_state.max_budget = 200.0

max_budget = st.sidebar.slider(
    "Max Total Budget (£)", 
    50.0, 500.0, 
    key="max_budget", 
    step=10.0
)

sort_option = st.sidebar.selectbox("Sort Results By", ["Cheapest total price first", "Longest ground time first"])

st.sidebar.info("🔒 Enforcing **Direct Flights Only** and **1 Adult**.")

if st.sidebar.button("Fetch Live Fares 🚀", type="primary"):
    if not duffel_token:
        st.error("Please provide your Duffel Access Token in the sidebar.")
    else:
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
        
        delta_days = (end_date - start_date).days
        if delta_days < 0 or delta_days > 14:
            st.error("The search date span must be between 1 and 14 days maximum.")
        else:
            dates_to_check = []
            cur = start_date
            while cur <= end_date:
                dates_to_check.append(cur.strftime("%Y-%m-%d"))
                cur += timedelta(days=1)
                
            headers = {
                "Authorization": f"Bearer {duffel_token}",
                "Duffel-Version": "v1",
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            
            all_cached_trips = []
            
            total_calls = len(destinations) * len(dates_to_check)
            progress_text = st.empty()
            progress_bar = st.progress(0)
            completed_calls = 0
            
            with st.spinner(f"Querying live Duffel API across {len(destinations)} destinations and {len(dates_to_check)} dates from {home_airport}..."):
                for dest in destinations:
                    for dt in dates_to_check:
                        payload = {
                            "data": {
                                "slices": [
                                    {
                                        "origin": home_airport,
                                        "destination": dest,
                                        "departure_date": dt
                                    },
                                    {
                                        "origin": dest,
                                        "destination": home_airport,
                                        "departure_date": dt
                                    }
                                ],
                                "passengers": [{"type": "adult"}],
                                "cabin_class": "economy",
                                "max_connections": 0
                            }
                        }
                        
                        try:
                            response = requests.post("https://api.duffel.com/air/offer_requests?return_offers=true", json=payload, headers=headers)
                            if response.status_code == 201:
                                data = response.json().get("data", {})
                                offers = data.get("offers", [])
                                
                                for offer in offers:
                                    total_price = float(offer.get("total_amount", 0))
                                    currency = offer.get("total_currency", "GBP")
                                    
                                    if currency != "GBP":
                                        continue
                                        
                                    slices = offer.get("slices", [])
                                    if len(slices) == 2:
                                        out_slice = slices[0]
                                        in_slice = slices[1]
                                        
                                        out_seg = out_slice.get("segments", [{}])[0]
                                        in_seg = in_slice.get("segments", [{}])[0]
                                        
                                        out_dep = out_seg.get("departing_at", "")
                                        out_arr = out_seg.get("arriving_at", "")
                                        in_dep = in_seg.get("departing_at", "")
                                        in_arr = in_seg.get("arriving_at", "")
                                        
                                        if out_dep and out_arr and in_dep and in_arr:
                                            out_dep_time = datetime.fromisoformat(out_dep.replace("Z", "+00:00"))
                                            out_arr_time = datetime.fromisoformat(out_arr.replace("Z", "+00:00"))
                                            in_dep_time = datetime.fromisoformat(in_dep.replace("Z", "+00:00"))
                                            in_arr_time = datetime.fromisoformat(in_arr.replace("Z", "+00:00"))
                                            
                                            out_str_time = out_dep_time.strftime("%H:%M")
                                            out_hour = out_dep_time.hour
                                            
                                            earliest_h = int(earliest_outbound.split(":")[0])
                                            latest_h = int(latest_outbound.split(":")[0])
                                            
                                            if earliest_h <= out_hour <= latest_h:
                                                ground_mins = (in_dep_time - out_arr_time).total_seconds() / 60.0
                                                ground_hrs = ground_mins / 60.0
                                                
                                                if ground_hrs >= min_ground and total_price <= max_budget:
                                                    owner = offer.get("owner", {}).get("name", "Airline")
                                                    
                                                    all_cached_trips.append({
                                                        "home": home_airport,
                                                        "dest": dest,
                                                        "Route": f"{home_airport} ➔ {dest} ➔ {home_airport}",
                                                        "Outbound Date": dt,
                                                        "Return Date": dt,
                                                        "Ground (hrs)": round(ground_hrs, 1),
                                                        "Total Price (£)": total_price,
                                                        "Outbound Time": f"{out_str_time} ➔ {out_arr_time.strftime('%H:%M')}",
                                                        "Return Time": f"{in_dep_time.strftime('%H:%M')} ➔ {in_arr_time.strftime('%H:%M')}",
                                                        "Carrier": owner,
                                                        "Offer ID": offer.get("id")
                                                    })
                        except Exception:
                            continue
                            
                        completed_calls += 1
                        progress_bar.progress(min(completed_calls / total_calls, 1.0))
                
                progress_text.empty()
                progress_bar.empty()
                st.session_state.cached_trips = all_cached_trips

if "cached_trips" in st.session_state:
    valid_trips = st.session_state.cached_trips
    
    if sort_option == "Longest ground time first":
        valid_trips.sort(key=lambda x: x["Ground (hrs)"], reverse=True)
    else:
        valid_trips.sort(key=lambda x: x["Total Price (£)"])
        
    st.success(f"Found {len(valid_trips)} live direct itineraries matching your criteria!")
    
    for trip in valid_trips:
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
            
            st.divider()
            st.text(f"Duffel Verified Live Offer ID: {trip['Offer ID']}")
