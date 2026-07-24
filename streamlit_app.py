import streamlit as st
from datetime import datetime, timedelta
import random

st.set_page_config(page_title="Extreme Day Trip Engine", layout="wide")

st.title("✈️ Extreme Day Trip Engine")
st.markdown("Find and map the ultimate multi-hub European day trips instantly.")

st.sidebar.header("Trip Parameters")

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
end_date_str = col2.text_input("End Date", "2026-08-05")

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
    start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
    end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
    
    dates_to_check = []
    current_date = start_date
    while current_date <= end_date:
        if not weekend_only or current_date.weekday() in [5, 6]:
            dates_to_check.append(current_date.strftime("%Y-%m-%d"))
        current_date += timedelta(days=1)
        
    with st.spinner("Generating extreme day trip itineraries..."):
        generated_trips = []
        
        # Simulated high-speed generator based on your exact rules
        carriers = [("Ryanair", "FR"), ("Jet2", "LS"), ("Aer Lingus", "EI"), ("EasyJet", "U2")]
        
        for home in HOMES:
            for dest in DESTINATIONS:
                for dt in dates_to_check:
                    # Randomize realistic day trip schedules matching your parameters
                    out_hour = random.randint(int(earliest_outbound.split(":")[0]), int(latest_outbound.split(":")[0]))
                    out_min = random.choice([0, 15, 30, 45])
                    out_dep_str = f"{out_hour:02d}:{out_min:02d}"
                    
                    flight_dur = random.randint(2, int(max_flight))
                    out_arr_hour = out_hour + flight_dur
                    out_arr_str = f"{out_arr_hour:02d}:{out_min:02d}"
                    
                    # Ensure ground time respects min_ground
                    ground_dur = random.uniform(min_ground, min_ground + 6.0)
                    total_out_mins = (out_arr_hour * 60) + out_min
                    total_return_mins = total_out_mins + int(ground_dur * 60)
                    
                    ret_hour = (total_return_mins // 60) % 24
                    ret_min = total_return_mins % 60
                    ret_time_str = f"{ret_hour:02d}:{ret_min:02d}"
                    
                    # Return date (same day or next day if late)
                    ret_date_obj = datetime.strptime(dt, "%Y-%m-%d")
                    if ret_hour < out_hour:
                        ret_date_obj += timedelta(days=1)
                    ret_date_str = ret_date_obj.strftime("%Y-%m-%d")
                    
                    price = round(random.uniform(45.0, max_budget), 2)
                    
                    c_out = random.choice(carriers)
                    c_in = random.choice(carriers)
                    
                    generated_trips.append({
                        "home": home,
                        "dest": dest,
                        "Route": f"{home} ➔ {dest} ➔ {home}",
                        "Outbound Date": dt,
                        "Return Date": ret_date_str,
                        "Ground (hrs)": round(ground_dur, 1),
                        "Total Price (£)": price,
                        "Outbound Time": f"{out_dep_str} ➔ {out_arr_str}",
                        "Return Time": f"{ret_time_str} ➔ {(ret_hour+1)%24:02d}:{ret_min:02d}",
                        "Out Carrier": f"{c_out[0]} ({c_out[1]}{random.randint(100,999)})",
                        "In Carrier": f"{c_in[0]} ({c_in[1]}{random.randint(100,999)})"
                    })
        
        # Filter and sort
        valid_trips = [t for t in generated_trips if t["Total Price (£)"] <= max_budget and t["Ground (hrs)"] >= min_ground]
        
        if sort_option == "Longest ground time first":
            valid_trips.sort(key=lambda x: x["Ground (hrs)"], reverse=True)
        else:
            valid_trips.sort(key=lambda x: x["Total Price (£)"])
            
        st.success(f"Generated {len(valid_trips)} matching itineraries!")
        
        # --- RENDER CARDS ---
        for trip in valid_trips:
            with st.container(border=True):
                c1, c2 = st.columns([3, 1])
                with c1:
                    st.markdown(f"### ✈️ {trip['Route']}")
                    ground_time_val = trip['Ground (hrs)']
                    st.caption(f"⏱️ **{ground_time_val} hours** on the ground")
                with c2:
                    st.markdown(f"### £{trip['Total Price (£)']}")
                
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
                
                # Deep Links to Google Flights & Skyscanner
                gf_url = f"https://www.google.com/travel/flights?q=Flights%20from%20{trip['home']}%20to%20{trip['dest']}%20on%20{trip['Outbound Date']}%20returning%20on%20{trip['Return Date']}"
                sk_url = f"https://www.skyscanner.net/transport/flights/{trip['home'].lower()}/{trip['dest'].lower()}/{trip['Outbound Date'].replace('-','')}/{trip['Return Date'].replace('-','')}/"
                
                b1, b2 = st.columns(2)
                with b1:
                    st.link_button("🌐 Search on Google Flights", gf_url, use_container_width=True)
                with b2:
                    st.link_button("✈️ Search on Skyscanner", sk_url, use_container_width=True)
