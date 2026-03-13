"""Streamlit UI for SDR Research Agent."""

import time

import streamlit as st
import httpx

API_BASE = "http://localhost:8000"


def main():
    st.set_page_config(page_title="SDR Research Agent", page_icon="📧", layout="centered")
    st.title("📧 SDR Research Agent")
    st.markdown("*Generate personalized cold emails from company research*")

    company_url = st.text_input(
        "Company URL",
        placeholder="https://stripe.com",
        help="Enter the company's website URL",
    )
    company_name = st.text_input("Company name (optional)", placeholder="Stripe")
    ceo_name = st.text_input("CEO / contact name (optional)", placeholder="Patrick Collison", help="Used for personalization and to search for recent mentions")
    use_sync = st.checkbox("Run synchronously (no Redis)", value=True, help="Skip queue for quick testing")

    if st.button("Generate Cold Email", type="primary"):
        if not company_url:
            st.error("Please enter a company URL")
            st.stop()

        with st.spinner("Researching company..."):
            try:
                if use_sync:
                    with httpx.Client(timeout=60) as client:
                        r = client.post(
                            f"{API_BASE}/api/v1/research/sync",
                            json={
                                "company_url": company_url,
                                "company_name": company_name or None,
                                "ceo_name": ceo_name or None,
                            },
                        )
                        r.raise_for_status()
                        data = r.json()
                else:
                    with httpx.Client(timeout=120) as client:
                        submit = client.post(
                            f"{API_BASE}/api/v1/research",
                            json={
                                "company_url": company_url,
                                "company_name": company_name or None,
                                "ceo_name": ceo_name or None,
                            },
                        )
                        submit.raise_for_status()
                        job = submit.json()
                        job_id = job["job_id"]

                        # Poll for result (worker must be running)
                        data = None
                        for _ in range(60):
                            status = client.get(f"{API_BASE}/api/v1/jobs/{job_id}")
                            status.raise_for_status()
                            s = status.json()
                            if s["status"] == "completed":
                                data = {
                                    "research": s.get("research"),
                                    "email_draft": s.get("email_draft"),
                                    "rounds": s.get("critique_rounds", 0),
                                }
                                break
                            elif s["status"] == "failed":
                                st.error(s.get("error", "Job failed"))
                                st.stop()
                            time.sleep(2)
                        if data is None:
                            st.error("Timeout. Ensure worker is running: python -m app.worker")
                            st.stop()

                # Display results
                research = data.get("research")
                draft = data.get("email_draft")

                if research:
                    st.subheader("📋 Research Summary")
                    st.write(research.get("company_summary", ""))
                    if research.get("key_topics"):
                        st.write("**Key topics:**", ", ".join(research["key_topics"]))

                if draft:
                    st.subheader("✉️ Email Draft")
                    st.text_input("Subject", value=draft.get("subject", ""), disabled=True)
                    st.text_area("Body", value=draft.get("body", ""), height=200, disabled=True)
                    if draft.get("personalization_notes"):
                        st.caption("Personalization notes: " + draft["personalization_notes"])

                st.success(f"Done! ({data.get('rounds', 0)} critique rounds)")

            except httpx.ConnectError:
                st.error("Could not connect to API. Is the server running? `uvicorn app.main:app --reload`")
            except httpx.HTTPStatusError as e:
                st.error(f"API error: {e.response.text}")
            except Exception as e:
                st.error(str(e))


if __name__ == "__main__":
    main()
