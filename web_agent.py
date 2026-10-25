from datetime import datetime
import socket
import ssl
import psutil
import requests
import streamlit as st


def check_website_status(url: str) -> str:
    """Checks if a website URL is online and returns HTTP status code."""
    try:
        response = requests.get(url, timeout=5)
        return f"ONLINE (HTTP {response.status_code})"
    except Exception as e:
        return f"DOWN or Error: {str(e)}"


def check_ssl_expiry(domain: str) -> str:
    """Checks the SSL/TLS certificate expiry date and remaining days for a domain."""
    try:
        clean_domain = (
            domain.replace("https://", "").replace("http://", "").split("/")[0]
        )
        context = ssl.create_default_context()
        with socket.create_connection((clean_domain, 443), timeout=5) as sock:
            with context.wrap_socket(
                sock, server_hostname=clean_domain
            ) as ssock:
                cert = ssock.getpeercert()
                expiry_str = cert["notAfter"]
                expiry_date = datetime.strptime(
                    expiry_str, "%b %d %H:%M:%S %Y %Z"
                )
                days_left = (expiry_date - datetime.utcnow()).days
                return f"SSL for {clean_domain} expires on {expiry_date.strftime('%Y-%m-%d')} ({days_left} days remaining)."
    except Exception as e:
        return f"SSL check failed for {domain}: {str(e)}"


def get_system_health() -> str:
    """Gets current system CPU usage percentage and RAM usage details."""
    try:
        cpu = psutil.cpu_percent(interval=1)
        ram = psutil.virtual_memory()
        used_gb = round(ram.used / (1024**3), 2)
        total_gb = round(ram.total / (1024**3), 2)
        return f"CPU Usage: {cpu}%, RAM Usage: {ram.percent}% ({used_gb} GB used out of {total_gb} GB)"
    except Exception as e:
        return f"Failed to get system stats: {str(e)}"


st.set_page_config(
    page_title="Lightning Fast Cloud AIOps", page_icon="⚡", layout="centered"
)
st.title("⚡ Lightning Fast Cloud AIOps Dashboard")

st.markdown(
    "ఈ డాష్‌బోర్డ్ పూర్తిగా **API Keys, Model Not Found (404) మరియు Quota Errors** లేకుండా ఎంతో వేగంగా పనిచేస్తుంది!"
)

target_url = st.text_input(
    "Enter Website/Domain:",
    placeholder="e.g., https://www.microsoft.com or google.com",
)

st.markdown("---")

col1, col2 = st.columns(2)

with col1:
    if st.button("🌐 Check Website Status", use_container_width=True):
        if target_url:
            with st.spinner("Checking website..."):
                res = check_website_status(target_url)
                st.success(res)
        else:
            st.warning("దయచేసి వెబ్‌సైట్ యూరల్ ఎంటర్ చేయండి.")

    if st.button("📊 Check System Health", use_container_width=True):
        with st.spinner("Fetching server stats..."):
            res = get_system_health()
            st.info(res)

with col2:
    if st.button("🔒 Check SSL Expiry", use_container_width=True):
        if target_url:
            with st.spinner("Checking SSL certificate..."):
                res = check_ssl_expiry(target_url)
                st.success(res)
        else:
            st.warning("దయచేసి డొమైన్ ఎంటర్ చేయండి.")
