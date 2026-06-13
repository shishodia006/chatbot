from __future__ import annotations



import sys

from pathlib import Path



ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:

    sys.path.insert(0, str(ROOT))



import streamlit as st



from app.catalog_service import get_catalog_service

from app.chatbot import ChatMessage

from app.config import get_gemini_api_key

from app.region import (

    REGION_INVALID,

    REGION_LABELS,

    REGION_PROMPT,

    Region,

    parse_region_choice,

    region_confirmation,

)





@st.cache_resource

def get_catalog():

    return get_catalog_service()





def reset_conversation() -> None:

    st.session_state.region = None

    st.session_state.history_start = 0

    st.session_state.messages = [{"role": "assistant", "content": REGION_PROMPT}]





def main() -> None:

    st.set_page_config(

        page_title="Automat Product Assistant",

        page_icon="💧",

        layout="centered",

    )



    st.title("Automat Product Assistant")

    st.caption("Ask about irrigation products, specs, and catalog details.")



    if not get_gemini_api_key():

        st.error(

            "Gemini API key not found. Create a `.env` file in the project root with:\n\n"

            "`GEMINI_API_KEY=your_key_here`\n\n"

            "Get a key at https://aistudio.google.com/apikey"

        )

        st.stop()



    if "region" not in st.session_state:

        st.session_state.region = None

    if "history_start" not in st.session_state:

        st.session_state.history_start = 0

    if "messages" not in st.session_state:

        st.session_state.messages = [

            {"role": "assistant", "content": REGION_PROMPT}

        ]



    for msg in st.session_state.messages:

        with st.chat_message(msg["role"]):

            st.markdown(msg["content"])



    if prompt := st.chat_input("Your message..."):

        st.session_state.messages.append({"role": "user", "content": prompt})

        with st.chat_message("user"):

            st.markdown(prompt)



        with st.chat_message("assistant"):

            reply = _handle_user_message(prompt)

            st.markdown(reply)

            st.session_state.messages.append({"role": "assistant", "content": reply})



    with st.sidebar:

        st.header("Catalog")

        catalog = get_catalog()

        st.write(f"India: **{catalog.catalog_size('ind')}** products")

        st.write(f"International: **{catalog.catalog_size('int')}** products")

        region: Region | None = st.session_state.region

        if region:

            st.success(f"Active: {REGION_LABELS[region]}")

        else:

            st.info("Choose India or International to start.")

        if st.button("Change region"):

            reset_conversation()

            st.rerun()





def _handle_user_message(prompt: str) -> str:

    region: Region | None = st.session_state.region



    if region is None:

        chosen = parse_region_choice(prompt)

        if chosen is None:

            return REGION_INVALID

        st.session_state.region = chosen

        st.session_state.history_start = len(st.session_state.messages) + 1

        return region_confirmation(chosen)



    try:

        catalog = get_catalog()

        chatbot = catalog.get_chatbot(region)

        start = st.session_state.history_start

        history = [

            ChatMessage(role=m["role"], content=m["content"])

            for m in st.session_state.messages[start:-1]

            if m["role"] in ("user", "assistant")

        ]

        with st.spinner("Searching catalog..."):

            return chatbot.answer(prompt, history=history)

    except Exception as exc:

        return f"Something went wrong: {exc}"





if __name__ == "__main__":

    main()

