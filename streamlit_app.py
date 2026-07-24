import streamlit as st
from datetime import datetime, timedelta, date
import requests

st.set_page_config(page_title="Extreme Day Trip Engine (Live)", layout="wide")

st.title("✈️ Extreme Day Trip Engine — Live Duffel API")
st.markdown("Scan real-world direct routes, live market prices, and tight turnaround day trips.")

st.sidebar.header("Live API Configuration")
duffel_token = st.sidebar.text_input("Duffel Access Token", type="password", help="Enter your live or test Duffel API token here.")

st.sidebar.header("Trip Parameters")

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
        "Ibiza (IBZ)": "IBZ",
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

sorted_countries = sorted(AIRPORT_HIERARCHY.keys())
selected_country = st.sidebar.selectbox("Home Country", sorted_countries, index=sorted_countries.index("United Kingdom"))

available_airports = AIRPORT_HIERARCHY[selected_country]
sorted_airport_labels = sorted(available_airports.keys())
selected_airport_label = st.sidebar.selectbox("Home Airport", sorted_airport_labels)
home_airport = available_airports[selected_airport_label]

POPULAR_DESTINATIONS = {
    "Amsterdam (AMS)": "AMS",
    "Alicante (ALC)": "ALC",
    "Barcelona (BCN)": "BCN",
    "Copenhagen (CPH)": "CPH",
    "Dublin (DUB)": "DUB",
    "Ibiza (IBZ)": "IBZ",
    "Madrid (MAD)": "MAD",
    "Malaga (AGP)": "AGP",
    "Palma de Mallorca (PMI)": "PMI",
    "Paris Charles de Gaulle (CDG)": "CDG"
}

selected_dest_labels = st.sidebar.multiselect(
    "Destinations", 
    options=list(POPULAR_DESTINATIONS.keys()),
    default=["Dublin (DUB)", "Amsterdam (AMS)", "Ibiza (IBZ)"]
)
destinations = [POPULAR_DESTINATIONS[label] for label in selected_dest_labels]

col1, col2 = st.sidebar.columns(2)
start_date = col1.date_input("Start Date", value=date(2026, 8, 1))
end_date = col2.date_input("Window End", value=date(2026, 8, 14))

all_days_map = {"Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3, "Friday": 4, "Saturday": 5, "Sunday": 6}
selected_day_names = st.sidebar.multiselect(
    "Departure Days",
    options=list(all_days_map.keys()),
    default=list(all_days_map.keys())
)
selected_days = [all_days_map[d] for d in selected_day_names]

st.sidebar.subheader("Time & Constraints")

TIME_OPTIONS = [
    "00:00", "01:00", "02:00", "03:00", "04:00", "05:00", "06:00", "07:00", 
    "08:00", "09:00", "10:00", "11:00", "12:00", "13:00", "14:00", "15:00", 
    "16:00", "17:00", "18:00", "19:00", "20:00", "21:00", "22:00", "23:00"
]

earliest_outbound = st.sidebar.selectbox("Earliest Outbound", TIME_OPTIONS, index=5)
latest_outbound = st.sidebar.selectbox("Latest Outbound", TIME_OPTIONS, index=10)
latest_inbound = st.sidebar.selectbox("Latest Coming Home (Return)", TIME_OPTIONS, index=2)

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
    elif not destinations:
        st.error("Please select at least one destination.")
    elif not selected_days:
        st.error("Please select at least one departure day.")
    else:
        delta_days = (end_date - start_date).days
        if delta_days < 0 or delta_days > 14:
            st.error("The search date span must be between 1 and 14 days maximum.")
        else:
            dates_to_check = []
            cur = start_date
            while cur <= end_date:
                if cur.weekday() in selected_days:
                    dates_to_check.append(cur.strftime("%Y-%m-%d"))
                cur += timedelta(days=1)
                
            if not dates_to_check:
                st.warning("No dates match your selected departure days within this window.")
            else:
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
                            outbound_date_obj = datetime.strptime(dt, "%Y-%m-%d").date()
                            return_date_obj = outbound_date_obj + timedelta(days=1)
                            return_dt_str = return_date_obj.strftime("%Y-%m-%d")

                            # THE CORE FIX: Query individual independent one-way requests for Outbound and Return
                            # instead of locking them into a rigid multi-slice payload. This matches how consumer flight tools 
                            # discover separate fare buckets and assemble day trips successfully.
                            outbound_payload = {
                                "data": {
                                    "slices": [{
                                        "origin": home_airport,
                                        "destination": dest,
                                        "departure_date": dt
                                    }],
                                    "passengers": [{"type": "adult"}],
                                    "cabin_class": "economy",
                                    "max_connections": 0
                                }
                            }
                            
                            try:
                                # 1. Fetch Outbound Options
                                out_response = requests.post("https://api.duffel.com/air/offer_requests?return_offers=true", json=outbound_payload, headers=headers)
                                
                                if out_response.status_code == 201:
                                    out_data = out_response.json().get("data", {})
                                    out_offers = out_data.get("offers", [])
                                    
                                    for out_offer in out_offers:
                                        out_price = float(out_offer.get("total_amount", 0))
                                        if out_offer.get("total_currency", "GBP") != "GBP":
                                            continue
                                            
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
                                        
                                        # Now query return for both same day and next day
                                        for ret_dt in [dt, return_dt_str]:
                                            return_payload = {
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
                                            
                                            ret_response = requests.post("https://api.duffel.com/air/offer_requests?return_offers=true", json=return_payload, headers=headers)
                                            if ret_response.status_code == 201:
                                                ret_data = ret_response.json().get("data", {})
                                                ret_offers = ret_data.get("offers", [])
                                                
                                                for ret_offer in ret_offers:
                                                    ret_price = float(ret_offer.get("total_amount", 0))
                                                    if ret_offer.get("total_currency", "GBP") != "GBP":
                                                        continue
                                                        
                                                    total_price = out_price + ret_price
                                                    if total_price > max_budget:
                                                        continue
                                                        
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
                                                    
                                                    if ground_hrs >= min_ground:
                                                        carrier = out_offer.get("owner", {}).get("name", "Airline")
                                                        
                                                        trip_entry = {
                                                            "home": home_airport,
                                                            "dest": dest,
                                                            "Route": f"{home_airport} ➔ {dest} ➔ {home_airport}",
                                                            "Outbound Date": dt,
                                                            "Return Date": in_dep_naive.strftime("%Y-%m-%d"),
                                                            "Ground (hrs)": round(ground_hrs, 1),
                                                            "Total Price (£)": total_price,
                                                            "Outbound Time": f"{out_dep_time.strftime('%H:%M')} ➔ {out_arr_time.strftime('%H:%M')}",
                                                            "Return Time": f"{in_dep_naive.strftime('%H:%M')} ➔ {in_arr_time.strftime('%H:%M')}",
                                                            "Carrier": carrier,
                                                            "Offer ID": f"{out_offer.get('id')} + {ret_offer.get('id')}"
                                                        }
                                                        
                                                        if trip_entry not in all_cached_trips:
                                                            all_cached_trips.append(trip_entry)
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
            st.text(f"Duffel Verified Offer IDs: {trip['Offer ID']}")
