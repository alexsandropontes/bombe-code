"""
Streamlit Chatbot Frontend
Simple chat UI with team selection
"""
import streamlit as st
import requests
import os
from datetime import datetime

# Configuration
API_URL = os.getenv("API_URL", "http://localhost:8000")

st.set_page_config(
    page_title="Forge Chatbot POC",
    page_icon="🤖",
    layout="wide"
)

st.title("🤖 Forge Chatbot POC")
st.caption("Teste rápido de agentes - POC")

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "current_team" not in st.session_state:
    st.session_state.current_team = None
if "teams" not in st.session_state:
    st.session_state.teams = []

# Sidebar for team selection
with st.sidebar:
    st.header("⚙️ Configuração")
    
    # Refresh teams button
    if st.button("🔄 Carregar Times"):
        try:
            response = requests.get(f"{API_URL}/teams", timeout=5)
            if response.status_code == 200:
                st.session_state.teams = response.json()
                st.success(f"{len(st.session_state.teams)} time(s) encontrado(s)")
            else:
                st.error("Erro ao carregar times")
        except Exception as e:
            st.error(f"Erro: {str(e)}")
    
    # Team selection
    if st.session_state.teams:
        st.session_state.current_team = st.selectbox(
            "Selecione o Time:",
            options=st.session_state.teams,
            index=0 if st.session_state.teams else None
        )
    else:
        st.warning("Nenhum time encontrado. Clique em 'Carregar Times'")
    
    st.divider()
    
    # Clear history button
    if st.button("🗑️ Limpar Histórico"):
        st.session_state.messages = []
        st.rerun()

# Main chat area
if st.session_state.current_team:
    st.subheader(f"💬 Chat com: {st.session_state.current_team}")
    
    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if "agent" in message:
                st.caption(f"Agente: {message['agent']}")
    
    # Chat input
    if prompt := st.chat_input("Digite sua mensagem..."):
        # Add user message to history
        st.session_state.messages.append({
            "role": "user",
            "content": prompt
        })
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Send to API
        with st.chat_message("assistant"):
            with st.spinner("Processando..."):
                try:
                    response = requests.post(
                        f"{API_URL}/chat",
                        json={
                            "message": prompt,
                            "team": st.session_state.current_team,
                            "history": [
                                {"role": m["role"], "content": m["content"]}
                                for m in st.session_state.messages[-10:]  # Last 10 messages
                            ]
                        },
                        timeout=60
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        st.markdown(result["response"])
                        
                        # Add assistant response to history
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": result["response"],
                            "agent": ", ".join(result["agents_used"])
                        })
                    else:
                        st.error(f"Erro: {response.text}")
                
                except Exception as e:
                    st.error(f"Erro na requisição: {str(e)}")
else:
    st.info("👈 Selecione um time na barra lateral para começar")

# Footer
st.divider()
st.caption(
    f"POC Forge Core | {datetime.now().strftime('%Y-%m-%d %H:%M')} | "
    f"Time atual: {st.session_state.current_team or 'Nenhum'}"
)
