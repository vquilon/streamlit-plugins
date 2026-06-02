import time
import streamlit as st
st.title("Bug reports")


progress = st.progress(0)
for i in range(10):
    progress.progress(i*10)
    time.sleep(0.1)
progress.progress(100)
with st._bottom:
    st.chat_input("Type here to chat")