import streamlit as st
import requests
import xml.etree.ElementTree as ET

st.title("CM-CreateFATableau — CMCancelFieldActivityTableau")
st.markdown("Calls the internal OUAF SOAP service with WS-Security UsernameToken")

# --- Constants from the WSDL ---
SERVICE_URL = "https://stl-dccbadb020.lac1.biz:6510/ouaf/webservices/CM-CreateFATableau"  # no ?WSDL here
TARGET_NS   = "http://ouaf.oracle.com/webservices/cm/CM-CreateFATableau"
SOAP_ACTION = "http://stl-u26ccb-20.lac1.biz/webservices/CM-CreateFATableau#CMCancelFieldActivityTableau"  # literal from WSDL
OPERATION   = "CMCancelFieldActivityTableau"
SOAP_VERSION = "1.1"  # The WSDL binding is SOAP 1.1

# TLS verification: True (system trust) or path to internal CA bundle PEM
TLS_VERIFY = True  # e.g., "/etc/ssl/certs/internal-root-ca.pem"

# --- Request UI ---
c1, c2 = st.columns(2)
with c1:
    fa_id = st.text_input("Field Activity ID (faId)", value="")
with c2:
    fa_cancel_reason = st.text_input("Cancel Reason (faCancelReason, ≤8 chars)", value="")

c3, c4 = st.columns(2)
with c3:
    cancel_fa = st.checkbox("cancelFA", value=True)
with c4:
    fa_cancellability = st.selectbox("faCancellability (optional)", ["(not set)", "true", "false"], index=0)

a1, a2 = st.columns(2)
with a1:
    username = st.text_input("Username (WS-Security)")
with a2:
    password = st.text_input("Password (WS-Security)", type="password")

def build_wsse_header(user: str, pwd: str) -> str:
    """
    Minimal WS-Security UsernameToken 1.0 header.
    Many OUAF setups accept plain text password without Nonce/Timestamp.
    """
    # You can add Nonce/Created if your environment requires it.
    # Password 'Type' explicitly marked as PasswordText for clarity.
    return f"""
    <wsse:Security soapenv:mustUnderstand="1"
      xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd">
      <wsse:UsernameToken>
        <wsse:Username>{(user or '').strip()}</wsse:Username>
        <wsse:Password
          Type="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-username-token-profile-1.0#PasswordText">
          {(pwd or '').strip()}
        </wsse:Password>
      </wsse:UsernameToken>
    </wsse:Security>
    """.strip()

def build_envelope():
    ns_decl = f'xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:tns="{TARGET_NS}"'
    wsse = build_wsse_header(username, password)

    # Optional fields rendering
    reason_xml = f"<tns:faCancelReason>{fa_cancel_reason}</tns:faCancelReason>" if fa_cancel_reason else ""
    canc_xml = f"<tns:cancelFA>{str(cancel_fa).lower()}</tns:cancelFA>"  # default is true if omitted
    cancellability_xml = ""
    if fa_cancellability in ("true", "false"):
        cancellability_xml = f"<tns:faCancellability>{fa_cancellability}</tns:faCancellability>"

    return f"""<?xml version="1.0" encoding="utf-8"?>
    <soapenv:Envelope {ns_decl}>
      <soapenv:Header>
        {wsse}
      </soapenv:Header>
      <soapenv:Body>
        <tns:{OPERATION}>
          <tns:input>
            <tns:faId>{fa_id}</tns:faId>
            {canc_xml}
            {reason_xml}
            {cancellability_xml}
          </tns:input>
        </tns:{OPERATION}>
      </soapenv:Body>
    </soapenv:Envelope>
    """

def parse_response(xml_bytes: bytes):
    ns = {
        "soapenv": "http://schemas.xmlsoap.org/soap/envelope/",
        "tns": TARGET_NS,
        # OUAF fault element namespace:
        "ouaf": "http://ouaf.oracle.com/"
    }
    root = ET.fromstring(xml_bytes)

    # 1) Handle SOAP Fault (generic)
    fault = root.find(".//soapenv:Fault", ns)
    if fault is not None:
        faultcode = fault.findtext("faultcode") or ""
        faultstring = fault.findtext("faultstring") or ""
        detail_text = ET.tostring(fault.find("detail"), encoding="unicode") if fault.find("detail") is not None else ""
        return {"ok": False, "message": f"SOAP Fault: {faultcode} - {faultstring}", "detail": detail_text}

    # 2) Happy-path: output/errorInformation
    out_el = root.find(f".//tns:{OPERATION}/tns:output", ns)
    if out_el is None:
        return {"ok": True, "message": "No <output> element found. Check service logs / OUAF configs.", "detail": ET.tostring(root, encoding="unicode")}

    in_error = out_el.findtext("tns:errorInformation/tns:inError", default="", namespaces=ns)
    msg_text = out_el.findtext("tns:errorInformation/tns:messageText", default="", namespaces=ns)
    fa_id_out = out_el.findtext("tns:faId", default="", namespaces=ns)
    # errorReference details (optional)
    cat_num = out_el.findtext("tns:errorInformation/tns:errorReference/tns:messageCategoryNumber", default="", namespaces=ns)
    msg_num = out_el.findtext("tns:errorInformation/tns:errorReference/tns:messageNumber", default="", namespaces=ns)

    if (in_error or "").lower() == "true":
        return {
            "ok": False,
            "message": f"Service returned inError=true",
            "detail": f"messageText={msg_text} category={cat_num} number={msg_num} faId={fa_id_out}"
        }
    else:
        return {
            "ok": True,
            "message": "Cancellation call completed.",
            "detail": f"messageText={msg_text or '(none)'} faId={fa_id_out or '(none)'}"
        }

if st.button("Call CMCancelFieldActivityTableau"):
    if not username or not password:
        st.error("Username and Password are required for WS-Security UsernameToken.")
    elif not fa_id:
        st.error("Please provide a Field Activity ID (faId).")
    else:
        envelope = build_envelope()
        headers = {
            "Content-Type": "text/xml; charset=utf-8",  # SOAP 1.1
            "SOAPAction": SOAP_ACTION,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
        }

        try:
            with st.spinner("Calling service..."):
                resp = requests.post(
                    SERVICE_URL,
                    data=envelope.encode("utf-8"),
                    headers=headers,
                    timeout=60,
                    verify=TLS_VERIFY
                )

            st.write(f"HTTP {resp.status_code}")
            st.code(resp.text, language="xml")

            try:
                result = parse_response(resp.content)
                if resp.status_code == 200 and result["ok"]:
                    st.success(result["message"])
                    if result.get("detail"):
                        st.caption(result["detail"])
                else:
                    # Show either parsed error or HTTP error
                    msg = result["message"] if "message" in result else f"HTTP {resp.status_code}"
                    st.error(msg)
                    if result.get("detail"):
                        st.caption(result["detail"])
            except ET.ParseError:
                st.error("Response is not valid XML or namespaces mismatch.")
        except requests.exceptions.SSLError as ssl_err:
            st.error(f"TLS/SSL error. Ensure the internal CA is trusted. Details: {ssl_err}")
        except Exception as e:
            st.error(f"Request failed: {e}")
