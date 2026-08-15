import pandas as pd
import numpy as np

DISTRICT_TO_PROVINCE = {
    # Koshi Province
    "Bhojpur": "Koshi", "Dhankuta": "Koshi", "Ilam": "Koshi", "Jhapa": "Koshi", "Khotang": "Koshi", "Morang": "Koshi", "Okhaldhunga": "Koshi", "Panchthar": "Koshi", "Sankhuwasabha": "Koshi", "Solukhumbu": "Koshi", "Sunsari": "Koshi", "Taplejung": "Koshi", "Terhathum": "Koshi", "Udayapur": "Koshi",
    # Madhesh Province
    "Bara": "Madhesh", "Dhanusha": "Madhesh", "Mahottari": "Madhesh", "Parsa": "Madhesh", "Rautahat": "Madhesh", "Saptari": "Madhesh", "Sarlahi": "Madhesh", "Siraha": "Madhesh",
    # Bagmati Province
    "Bhaktapur": "Bagmati", "Chitwan": "Bagmati", "Dhading": "Bagmati", "Dolakha": "Bagmati", "Kathmandu": "Bagmati", "Kavrepalanchok": "Bagmati", "Lalitpur": "Bagmati", "Makwanpur": "Bagmati", "Nuwakot": "Bagmati", "Ramechhap": "Bagmati", "Rasuwa": "Bagmati", "Sindhuli": "Bagmati", "Sindhupalchok": "Bagmati",
    # Gandaki Province
    "Baglung": "Gandaki", "Gorkha": "Gandaki", "Kaski": "Gandaki", "Lamjung": "Gandaki", "Manang": "Gandaki", "Mustang": "Gandaki", "Myagdi": "Gandaki", "Nawalpur": "Gandaki", "Parbat": "Gandaki", "Syangja": "Gandaki", "Tanahun": "Gandaki",
    # Lumbini Province
    "Arghakhanchi": "Lumbini", "Banke": "Lumbini", "Bardiya": "Lumbini", "Dang": "Lumbini", "Gulmi": "Lumbini", "Kapilvastu": "Lumbini", "Parasi": "Lumbini", "Palpa": "Lumbini", "Pyuthan": "Lumbini", "Rolpa": "Lumbini", "Rupandehi": "Lumbini", "East Rukum": "Lumbini",
    # Karnali Province
    "Dailekh": "Karnali", "Dolpa": "Karnali", "Humla": "Karnali", "Jajarkot": "Karnali", "Jumla": "Karnali", "Kalikot": "Karnali", "Mugu": "Karnali", "Salyan": "Karnali", "Surkhet": "Karnali", "West Rukum": "Karnali",
    # Sudurpashchim Province
    "Achham": "Sudurpashchim", "Baitadi": "Sudurpashchim", "Bajhang": "Sudurpashchim", "Bajura": "Sudurpashchim", "Dadeldhura": "Sudurpashchim", "Darchula": "Sudurpashchim", "Doti": "Sudurpashchim", "Kailali": "Sudurpashchim", "Kanchanpur": "Sudurpashchim"
}

def load_and_clean_data(filepath):
    df = pd.read_csv(filepath)
    # Parse dates (assume DD/MM/YYYY based on the info)
    df['Date'] = pd.to_datetime(df['Date'], format='%d/%m/%Y', errors='coerce')
    df = df.dropna(subset=['Date'])
    
    # Map province
    df['Province'] = df['District'].map(DISTRICT_TO_PROVINCE)
    df['Province'] = df['Province'].fillna('Unknown')
    
    # Sort chronologically for each city
    df = df.sort_values(by=['City', 'Date']).reset_index(drop=True)
    return df

def feature_engineering(df):
    """
    Creates temporal and rolling features.
    Assumes df is already sorted by City and Date.
    """
    df = df.copy()
    
    # Temporal features
    df['Year'] = df['Date'].dt.year
    df['Month'] = df['Date'].dt.month
    df['Day'] = df['Date'].dt.day
    df['DayOfYear'] = df['Date'].dt.dayofyear
    
    # Cyclical features
    df['Month_sin'] = np.sin(2 * np.pi * df['Month']/12)
    df['Month_cos'] = np.cos(2 * np.pi * df['Month']/12)
    df['DayOfYear_sin'] = np.sin(2 * np.pi * df['DayOfYear']/365.25)
    df['DayOfYear_cos'] = np.cos(2 * np.pi * df['DayOfYear']/365.25)
    
    # Group by City to create lag and rolling features
    grouped = df.groupby('City')
    
    # Lag features
    df['Temp_2m_lag1'] = grouped['Temp_2m'].shift(1)
    df['Precip_lag1'] = grouped['Precip'].shift(1)
    df['RH_2m_lag1'] = grouped['RH_2m'].shift(1)
    
    # Rolling means (3-day and 7-day)
    df['Temp_2m_roll3'] = grouped['Temp_2m'].rolling(window=3, min_periods=1).mean().reset_index(level=0, drop=True)
    df['Temp_2m_roll7'] = grouped['Temp_2m'].rolling(window=7, min_periods=1).mean().reset_index(level=0, drop=True)
    
    df['Precip_roll3'] = grouped['Precip'].rolling(window=3, min_periods=1).mean().reset_index(level=0, drop=True)
    df['RH_2m_roll3'] = grouped['RH_2m'].rolling(window=3, min_periods=1).mean().reset_index(level=0, drop=True)
    
    # Create target columns (if not already present or for non-temperature targets)
    df['Precip_tomorrow'] = grouped['Precip'].shift(-1)
    df['RH_2m_tomorrow'] = grouped['RH_2m'].shift(-1)
    
    # Drop NaNs created by lagging/shifting if we are preparing for training
    # But for actual inference, we'll keep the last row which will have NaN targets
    
    return df
