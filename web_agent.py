from datetime import datetime
import socket
import ssl
import subprocess
from langchain.agents import create_agent
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
import psutil
import requests
import streamlit as st


@tool
def check_website_status(url: str) -> str:
    """Checks if a website URL (must start with http:// or https://) is online and returns HTTP status code."""
    try:
        response = requests.get(url, timeout=5)
        return f"ONLINE (HTTP {response.status_code})"
    except Exception as e:
        return f"DOWN or Error: {str(e)}"


@tool
def get_ip_address(domain: str) -> str:
    """Finds the IP address of a domain name (e.g., google.com, microsoft.com)."""
    try:
        clean_domain = (
            domain.replace("https://", "").replace("http://", "").split("/")[0]
        )
        ip = socket.gethostbyname(clean_domain)
        return f"The IP address of {clean_domain} is {ip}"
    except Exception as e:
        return f"Could not resolve DNS for {domain}: {str(e)}"


@tool
def check_ssl_expiry(domain: str) -> str:
    """Checks the SSL/TLS certificate expiry date and remaining days for a domain (e.g., google.com)."""
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


@tool
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


@tool
def check_windows_service(service_name: str) -> str:
    """Checks the status of a Windows service using PowerShell."""
    try:
        cmd = f"Get-Service -Name '*{service_name}*' | Select-Object Name, DisplayName, Status | ConvertTo-Json"
        result = subprocess.run(
            ["powershell", "-Command", cmd],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.stdout.strip():
            return f"Service Details:\n{result.stdout.strip()}"
        return f"No Windows service found matching '{service_name}'."
    except Exception as e:
        return f"Note: PowerShell is only available on local Windows machines, not on Linux Cloud servers."


@tool
def get_recent_system_errors(count: int = 3) -> str:
    """Fetches the most recent Error or Warning events from the Windows System Event Log."""
    try:
        cmd = f"Get-EventLog -LogName System -EntryType Error,Warning -Newest {count} | Select-Object TimeGenerated, EntryType, Source, Message | ConvertTo-Json"
        result = subprocess.run(
            ["powershell", "-Command", cmd],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.stdout.strip():
            return f"Recent System Event Logs:\n{result.stdout.strip()}"
        return "No recent errors or warnings found."
    except Exception as e:
        return f"Note: Windows Event Logs are only available when running locally on Windows."


st.set_page_config(page_title="Windows AIOps Agent", page_icon="🖥️")
st.title("🖥️ Windows Admin & AIOps Agent")

# --- SIDEBAR SETTINGS ---
provider = st.sidebar.radio(
    "Select AI Provider:", ["Google Gemini", "Groq (Ultra-Fast & Free)"]
)

if provider == "Google Gemini":
    api_key = st.sidebar.text_input(
        "Enter Gemini API Key:", type="password", placeholder="AIzaSy..."
    )
    selected_model = st.sidebar.selectbox(
        "Select Model:",
        [
            "gemini-2.0-flash",
            "gemini-2.5-flash",
            "gemini-2.5-flash-lite",
            "gemini-1.5-flash",
        ],
    )
else:
    st.sidebar.markdown(
        "Get free key at: [console.groq.com](https://console.groq.com/keys)"
    )
    api_key = st.sidebar.text_input(
        "Enter Groq API Key:", type="password", placeholder="gsk_..."
    )
selected_model = st.sidebar.selectbox(
        "Select Model:", ["llama-3.1-8b-instant"]
    )

st.write(
    "I can check **Websites**, **DNS/IP**, **SSL Expiry**, **CPU/RAM**, **Windows Services**, and **Windows Event Logs**!"
)

user_query = st.text_input(
    "Ask your AIOps Agent:",
    placeholder="e.g., Check SSL expiry for microsoft.com and check current CPU/RAM usage",
)

if st.button("Run Agent"):
    if not api_key:
        st.error("దయచేసి ఎడమవైపు ఉన్న సైడ్‌బార్‌లో మీ API Key ని పేస్ట్ చేయండి!")
    elif user_query:
        clean_key = api_key.strip()
        with st.spinner(f"Executing diagnostics using {selected_model}..."):
            try:
                if provider == "Google Gemini":
                    llm = ChatGoogleGenerativeAI(
                        model=selected_model, google_api_key=clean_key
                    )
                else:
                    llm = ChatGroq(model=selected_model, groq_api_key=clean_key)

                tools = [
                    check_website_status,
                    get_ip_address,
                    check_ssl_expiry,
                    get_system_health,
                    check_windows_service,
                    get_recent_system_errors,
                ]
                agent = create_agent(llm, tools)

                response = agent.invoke({"messages": [("user", user_query)]})
                raw_content = response["messages"][-1].content

                if isinstance(raw_content, list):
                    clean_text = "\n".join(
                        [
                            item.get("text", "")
                            for item in raw_content
                            if isinstance(item, dict) and "text" in item
                        ]
                    )
                else:
                    clean_text = str(raw_content)

                st.success("Diagnostics Completed!")
                st.markdown(clean_text)
            except Exception as e:
                st.error(f"Exact Error Details: {str(e)}")
