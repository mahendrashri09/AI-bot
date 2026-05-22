import streamlit as st


def get_logs():

    upload = (
        st.file_uploader(
            "Upload logs",
            type=[
                "txt",
                "log"
            ]
        )
    )

    if upload:

        return (
            upload
            .read()
            .decode()
        )

    return (
        st.text_area(
            "Paste Logs"
        )
    )
