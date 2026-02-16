
def handle_logout():
    if st.query_params.get("action") == "logout":
        st.session_state.clear()
        st.query_params.clear()
        st.rerun()
