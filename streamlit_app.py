import streamlit as st
from datetime import date
import requests

st.set_page_config(page_title="Extreme Day Trip Engine - Independent Scan", layout="wide")

st.title("✈️ Extreme Day Trip Engine — Independent One-Way Splitter")
st.markdown("Bypassing round-trip bundle constraints to inspect raw independent carrier availability.")

st.sidebar.header("API Configuration")
duffel_token = st.sidebar.text_input("Duffel Access Token", type="password")

if st.sidebar.button("Run Independent One-Way Scan 🔍", type="primary"):
    if not duffel_token:
        st.error("Please provide your Duffel Access Token.")
    else:
        headers = {
            "Authorization": f"Bearer {duffel_token}",
            "Duffel-Version": "v2",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        dt_str = "2026-08-02"
        
        # Query Outbound LBA -> DUB independently
        out_payload = {
            "data": {
                "slices": [{"origin": "LBA", "destination": "DUB", "departure_date": dt_str}],
                "passengers": [{"type": "adult"}],
                "cabin_class": "economy"
            }
        }
        
        # Query Inbound DUB -> LBA independently
        ret_payload = {
            "data": {
                "slices": [{"origin": "DUB", "destination": "LBA", "departure_date": dt_str}],
                "passengers": [{"type": "adult"}],
                "cabin_class": "economy"
            }
        }
        
        with st.spinner("Fetching separate one-way feeds..."):
            try:
                out_resp = requests.post("https://api.duffel.com/air/offer_requests?return_offers=true", json=out_payload, headers=headers)
                ret_resp = requests.post("https://api.duffel.com/air/offer_requests?return_offers=true", json=ret_payload, headers=headers)
                
                col_a, col_b = st.columns(2)
                
                with col_a:
                    st.subheader("Outbound: LBA ➔ DUB")
                    if out_resp.status_code == 201:
                        out_offers = out_resp.json().get("data", {}).get("offers", [])
                        st.write(f"Found {len(out_offers)} one-way offers.")
                        for o in out_offers:
                            carrier = o.get("owner", {}).get("name")
                            price = o.get("total_amount")
                            seg = o.get("slices", [{}])[0].get("segments", [{}])[0]
                            dep = seg.get("departing_at", "")[11:16]
                            arr = seg.get("arriving_at", "")[11:16]
                            st.markdown(f"- **{carrier}**: {dep} ➔ {arr} (**£{price}**)")
                    else:
                        st.error(out_resp.text)
                        
                with col_b:
                    st.subheader("Return: DUB ➔ LBA")
                    if ret_resp.status_code == 201:
                        ret_offers = ret_resp.json().get("data", {}).get("offers", [])
                        st.write(f"Found {len(ret_offers)} one-way offers.")
                        for o in ret_offers:
                            carrier = o.get("owner", {}).get("name")
                            price = o.get("total_amount")
                            seg = o.get("slices", [{}])[0].get("segments", [{}])[0]
                            dep = seg.get("departing_at", "")[11:16]
                            arr = seg.get("arriving_at", "")[11:16]
                            st.markdown(f"- **{carrier}**: {dep} ➔ {arr} (**£{price}**)")
                    else:
                        st.error(ret_resp.text)
                        
            except Exception as e:
                st.error(f"Exception: {e}")
