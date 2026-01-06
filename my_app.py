import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import io
import json
import time
import os
from pathlib import Path

# Configuration de la page
st.set_page_config(
    page_title="CoinAfrique Scraper",
    page_icon="👕",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialisation des variables de session
if 'scraped_data' not in st.session_state:
    st.session_state.scraped_data = None
if 'cleaned_data' not in st.session_state:
    st.session_state.cleaned_data = None

# ============================================
# FONCTIONS DE SCRAPING (basées sur votre code)
# ============================================

def scraping(url, pages=5):
    """
    Fonction de scraping adaptée de votre code
    """
    df = pd.DataFrame()
    
    for index_page in range(1, pages + 1):
        try:
            page_url = f'{url}?page={index_page}'
            
            # Headers pour simuler un navigateur réel
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            res = requests.get(page_url, headers=headers, timeout=10)
            res.raise_for_status()
            
            soup = BeautifulSoup(res.content, 'html.parser')
            containers = soup.find_all('div', 'col s6 m4 l3')
            
            data = []
            for container in containers:
                try:
                    type_habit = container.find('p', 'ad__card-description').a.text
                    prix = container.find('p', 'ad__card-price').a.text.strip('CFA')
                    adresse = container.find('p', 'ad__card-location').span.text
                    image = container.find('img', 'ad__card-img')['src']
                    
                    dic = {
                        "type": type_habit,
                        "prix_texte": prix + " CFA",
                        "prix_numerique": float(prix.replace(' ', '').replace(',', '')) if prix.replace(' ', '').replace(',', '').isdigit() else 0,
                        "adresse": adresse,
                        "image_url": image,
                        "page_scrapee": index_page,
                        "date_scraping": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "url_source": url
                    }
                    data.append(dic)
                except Exception as e:
                    continue
            
            if data:
                df_page = pd.DataFrame(data)
                df = pd.concat([df, df_page], ignore_index=True)
                
            # Pause pour respecter le serveur
            time.sleep(2)
            
        except requests.exceptions.RequestException as e:
            st.error(f"Erreur de connexion page {index_page}: {str(e)}")
            break
        except Exception as e:
            st.error(f"Erreur page {index_page}: {str(e)}")
            break
    
    return df

def get_available_categories():
    """
    Retourne les catégories disponibles avec gestion d'erreurs
    """
    categories = {
        "👔 Vêtements Homme": "https://sn.coinafrique.com/categorie/vetements-homme/",
        "👞 Chaussures Homme": "https://sn.coinafrique.com/categorie/chaussures-homme/",
        "👶 Vêtements Enfants": "https://sn.coinafrique.com/categorie/vetements-enfants/",
        "👟 Chaussures Enfants": "https://sn.coinafrique.com/categorie/chaussures-enfants/",
        "📱 Électronique": "https://sn.coinafrique.com/categorie/telephones",
        "💻 Informatique": "https://sn.coinafrique.com/categorie/ordinateurs"
    }
    
    # Test des URLs disponibles
    available_categories = {}
    for name, url in categories.items():
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                available_categories[name] = url
        except:
            continue
    
    return available_categories if available_categories else categories

# ============================================
# FONCTIONS DE NETTOYAGE DES DONNÉES
# ============================================

def clean_data(df):
    """
    Nettoie les données scrapées
    """
    if df is None or df.empty:
        return pd.DataFrame()
    
    df_clean = df.copy()
    
    # Nettoyage des prix
    df_clean['prix_numerique'] = pd.to_numeric(df_clean['prix_numerique'], errors='coerce')
    df_clean = df_clean[df_clean['prix_numerique'] > 0]
    
    # Extraction de la ville depuis l'adresse
    df_clean['ville'] = df_clean['adresse'].apply(lambda x: x.split(',')[0].strip() if ',' in str(x) else x)
    
    # Catégorisation par prix
    bins = [0, 5000, 10000, 20000, 50000, float('inf')]
    labels = ['Très bas', 'Bas', 'Moyen', 'Élevé', 'Très élevé']
    df_clean['categorie_prix'] = pd.cut(df_clean['prix_numerique'], bins=bins, labels=labels)
    
    # Catégorisation des produits
    def categorize_product(product_type):
        product_type = str(product_type).lower()
        if any(word in product_type for word in ['chemise', 't-shirt', 'polo']):
            return 'Hauts'
        elif any(word in product_type for word in ['pantalon', 'jean', 'short']):
            return 'Bas'
        elif any(word in product_type for word in ['chaussure', 'basket', 'sandale']):
            return 'Chaussures'
        elif any(word in product_type for word in ['costume', 'complet']):
            return 'Costumes'
        else:
            return 'Autre'
    
    df_clean['categorie_produit'] = df_clean['type'].apply(categorize_product)
    
    return df_clean

# ============================================
# DASHBOARD ET VISUALISATIONS
# ============================================

def create_dashboard(df):
    """
    Crée un dashboard interactif
    """
    if df is None or df.empty:
        st.warning("Aucune donnée à afficher")
        return
    
    st.subheader("📊 Dashboard des Données Nettoyées")
    
    # Métriques principales
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Nombre d'annonces", len(df))
    
    with col2:
        avg_price = df['prix_numerique'].mean()
        st.metric("Prix moyen", f"{avg_price:,.0f} CFA")
    
    with col3:
        min_price = df['prix_numerique'].min()
        st.metric("Prix minimum", f"{min_price:,.0f} CFA")
    
    with col4:
        max_price = df['prix_numerique'].max()
        st.metric("Prix maximum", f"{max_price:,.0f} CFA")
    
    st.markdown("---")
    
    # Graphiques
    tab1, tab2, tab3 = st.tabs(["📈 Distribution", "📍 Localisation", "🏷️ Catégories"])
    
    with tab1:
        col1, col2 = st.columns(2)
        
        with col1:
            fig = px.histogram(df, x='prix_numerique', nbins=20,
                             title='Distribution des Prix',
                             labels={'prix_numerique': 'Prix (CFA)'})
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            fig = px.box(df, x='categorie_produit', y='prix_numerique',
                        title='Prix par Catégorie de Produit')
            st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        if 'ville' in df.columns:
            ville_counts = df['ville'].value_counts().head(10)
            fig = px.bar(x=ville_counts.values, y=ville_counts.index,
                        orientation='h',
                        title='Top 10 des Villes',
                        labels={'x': 'Nombre d\'annonces', 'y': 'Ville'})
            st.plotly_chart(fig, use_container_width=True)
    
    with tab3:
        col1, col2 = st.columns(2)
        
        with col1:
            cat_counts = df['categorie_produit'].value_counts()
            fig = px.pie(values=cat_counts.values, names=cat_counts.index,
                        title='Répartition par Catégorie de Produit')
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            fig = px.scatter(df, x='prix_numerique', y='page_scrapee',
                           color='categorie_produit',
                           title='Prix vs Page de Scraping')
            st.plotly_chart(fig, use_container_width=True)
    
    # Tableau des données
    st.subheader("📋 Données Détailées")
    st.dataframe(df.head(20), use_container_width=True)

# ============================================
# FORMULAIRE D'ÉVALUATION
# ============================================

def show_evaluation_form():
    """
    Affiche le formulaire d'évaluation
    """
    st.subheader("⭐ Évaluez l'Application")
    
    with st.form("evaluation_form"):
        # Informations personnelles
        st.markdown("### Vos Informations")
        
        col1, col2 = st.columns(2)
        
        with col1:
            name = st.text_input("Nom (optionnel)")
            email = st.text_input("Email (optionnel)")
        
        with col2:
            user_type = st.selectbox(
                "Type d'utilisateur",
                ["", "Étudiant", "Professionnel", "Chercheur", "Autre"]
            )
        
        # Évaluation
        st.markdown("### Évaluation des Fonctionnalités")
        
        st.write("Notez de 1 (Très insatisfait) à 5 (Très satisfait)")
        
        col1, col2 = st.columns(2)
        
        with col1:
            scraping_ease = st.slider("Facilité du scraping", 1, 5, 3)
            data_quality = st.slider("Qualité des données", 1, 5, 3)
        
        with col2:
            dashboard_useful = st.slider("Utilité du dashboard", 1, 5, 3)
            overall_exp = st.slider("Expérience globale", 1, 5, 3)
        
        # Feedback
        st.markdown("### Votre Feedback")
        
        likes = st.text_area("Ce que vous avez aimé")
        improvements = st.text_area("Suggestions d'amélioration")
        problems = st.text_area("Problèmes rencontrés")
        
        # Recommandation
        recommend = st.radio(
            "Recommanderiez-vous cette application?",
            ["Oui", "Non", "Peut-être"]
        )
        
        # Bouton de soumission
        submitted = st.form_submit_button("Soumettre l'évaluation")
        
        if submitted:
            # Création des données d'évaluation
            evaluation_data = {
                "date": datetime.now().isoformat(),
                "user_info": {
                    "name": name,
                    "user_type": user_type
                },
                "ratings": {
                    "scraping_ease": scraping_ease,
                    "data_quality": data_quality,
                    "dashboard_useful": dashboard_useful,
                    "overall_exp": overall_exp
                },
                "feedback": {
                    "likes": likes,
                    "improvements": improvements,
                    "problems": problems
                },
                "recommendation": recommend
            }
            
            # Sauvegarde locale
            try:
                os.makedirs("evaluations", exist_ok=True)
                filename = f"evaluations/evaluation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(evaluation_data, f, ensure_ascii=False, indent=2)
                
                st.success("✅ Évaluation soumise avec succès!")
                
                # Option pour Google Forms ou Kobo
                st.info("""
                **Pour intégrer avec Google Forms ou Kobo:**
                1. Créez un formulaire sur Google Forms ou Kobo Toolbox
                2. Récupérez l'URL de soumission
                3. Modifiez la fonction pour envoyer les données via API
                """)
                
            except Exception as e:
                st.error(f"Erreur lors de la sauvegarde: {str(e)}")

# ============================================
# INTERFACE PRINCIPALE
# ============================================

def main():
    # Sidebar
    with st.sidebar:
        st.title("👕 CoinAfrique Scraper")
        st.markdown("---")
        
        # Navigation
        page = st.radio(
            "Navigation",
            ["🏠 Accueil", "🔍 Scraper", "📥 Télécharger", "📊 Dashboard", "⭐ Évaluation"]
        )
        
        st.markdown("---")
        st.caption("v1.0 • Déployé avec Streamlit")
    
    # Page d'accueil
    if page == "🏠 Accueil":
        st.title("Bienvenue sur CoinAfrique Scraper")
        
        st.markdown("""
        ## 📋 Fonctionnalités
        
        1. **🔍 Scraping de données**
           - Scrapez des annonces depuis CoinAfrique
           - Plusieurs catégories disponibles
           - Configuration du nombre de pages
        
        2. **📥 Téléchargement**
           - Exportez les données brutes
           - Formats: CSV, Excel, JSON
        
        3. **📊 Dashboard interactif**
           - Visualisations des données nettoyées
           - Statistiques et analyses
        
        4. **⭐ Évaluation**
           - Donnez votre feedback
           - Aidez-nous à améliorer l'app
        """)
        
        # Statut des URLs
        with st.expander("🔍 Vérification des URLs CoinAfrique"):
            st.write("Test de connectivité aux catégories:")
            categories = get_available_categories()
            for name, url in categories.items():
                try:
                    response = requests.get(url, timeout=5)
                    status = "✅ Connecté" if response.status_code == 200 else "❌ Erreur"
                    st.write(f"{name}: {status}")
                except:
                    st.write(f"{name}: ❌ Impossible de se connecter")
    
    # Page de scraping
    elif page == "🔍 Scraper":
        st.title("🔍 Scraper des Données")
        
        categories = get_available_categories()
        
        if not categories:
            st.error("Aucune catégorie disponible. Vérifiez votre connexion internet.")
            return
        
        col1, col2 = st.columns(2)
        
        with col1:
            selected_category = st.selectbox(
                "Sélectionnez une catégorie",
                list(categories.keys())
            )
            
            url = categories[selected_category]
            st.info(f"URL: {url}")
        
        with col2:
            pages = st.slider("Nombre de pages", 1, 10, 3)
            delay = st.slider("Délai entre les requêtes (secondes)", 1, 5, 2)
        
        if st.button("🚀 Lancer le scraping", type="primary"):
            with st.spinner(f"Scraping en cours... (pages 1-{pages})"):
                try:
                    df = scraping(url, pages)
                    
                    if df is not None and not df.empty:
                        st.session_state.scraped_data = df
                        st.session_state.cleaned_data = clean_data(df)
                        
                        st.success(f"✅ {len(df)} annonces scrapées avec succès!")
                        
                        # Aperçu
                        st.subheader("👁️ Aperçu des données")
                        st.dataframe(df.head(), use_container_width=True)
                        
                    else:
                        st.warning("Aucune donnée n'a pu être scrapée.")
                        
                except Exception as e:
                    st.error(f"Erreur lors du scraping: {str(e)}")
    
    # Page de téléchargement
    elif page == "📥 Télécharger":
        st.title("📥 Télécharger les Données")
        
        if st.session_state.scraped_data is None:
            st.warning("Aucune donnée disponible. Veuillez d'abord scraper des données.")
        else:
            tab1, tab2 = st.tabs(["Données Brutes", "Données Nettoyées"])
            
            with tab1:
                df_raw = st.session_state.scraped_data
                st.write(f"**{len(df_raw)} annonces brutes**")
                st.dataframe(df_raw.head(), use_container_width=True)
                
                # Options de téléchargement
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    csv = df_raw.to_csv(index=False)
                    st.download_button(
                        label="📥 CSV",
                        data=csv,
                        file_name=f"coin_afrique_raw_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv"
                    )
                
                with col2:
                    json_str = df_raw.to_json(orient='records', indent=2)
                    st.download_button(
                        label="📥 JSON",
                        data=json_str,
                        file_name=f"coin_afrique_raw_{datetime.now().strftime('%Y%m%d')}.json",
                        mime="application/json"
                    )
            
            with tab2:
                if st.session_state.cleaned_data is not None:
                    df_clean = st.session_state.cleaned_data
                    st.write(f"**{len(df_clean)} annonces nettoyées**")
                    st.dataframe(df_clean.head(), use_container_width=True)
                    
                    csv_clean = df_clean.to_csv(index=False)
                    st.download_button(
                        label="📥 Télécharger données nettoyées (CSV)",
                        data=csv_clean,
                        file_name=f"coin_afrique_clean_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv",
                        type="primary"
                    )
    
    # Page Dashboard
    elif page == "📊 Dashboard":
        st.title("📊 Dashboard des Données")
        
        if st.session_state.cleaned_data is not None:
            create_dashboard(st.session_state.cleaned_data)
        elif st.session_state.scraped_data is not None:
            st.info("Nettoyage des données en cours...")
            st.session_state.cleaned_data = clean_data(st.session_state.scraped_data)
            create_dashboard(st.session_state.cleaned_data)
        else:
            st.warning("Veuillez d'abord scraper des données pour afficher le dashboard.")
    
    # Page d'évaluation
    elif page == "⭐ Évaluation":
        show_evaluation_form()

# ============================================
# EXÉCUTION
# ============================================

if __name__ == "__main__":
    main()