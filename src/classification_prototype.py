"""
Classification Prototype - Percentile-Based Approach
Tests different classification strategies for GA4 data
"""
import pandas as pd
import numpy as np

def load_all_brands():
    """Load output data for all brands."""
    brands = {}
    for brand in ['Iiyama', 'Bushido', 'Koszulkowy']:
        try:
            df = pd.read_csv(f'Output/{brand}/Landing_Page_Final.csv')
            brands[brand] = df
            print(f"Loaded {brand}: {len(df)} products")
        except Exception as e:
            print(f"Failed to load {brand}: {e}")
    return brands


def classify_percentile(df, revenue_col='Item revenue', purchases_col='Items purchased', 
                         sessions_col='Sessions', frequency_col='calc_frequency'):
    """
    Percentile-based classification:
    - Star: Top 25% revenue AND top 25% frequency
    - Cash Cow: Top 25% revenue AND bottom 75% frequency  
    - Hidden Gem: Bottom 75% revenue AND top 25% frequency AND min transactions/sessions
    - Slacker: Everything else
    """
    # Calculate percentiles
    rev_75 = df[revenue_col].quantile(0.75)
    freq_75 = df[frequency_col].quantile(0.75)
    
    # Min transaction threshold (at least some activity)
    min_purchases = df[purchases_col].quantile(0.25)  # At least 25th percentile
    min_sessions = df[sessions_col].quantile(0.25)
    
    def classify(row):
        rev = row[revenue_col] if not pd.isna(row[revenue_col]) else 0
        freq = row[frequency_col] if not pd.isna(row[frequency_col]) else 0
        purch = row[purchases_col] if not pd.isna(row[purchases_col]) else 0
        sess = row[sessions_col] if not pd.isna(row[sessions_col]) else 0
        
        is_high_rev = rev >= rev_75
        is_high_freq = freq >= freq_75
        has_activity = purch >= min_purchases or sess >= min_sessions
        
        if is_high_rev and is_high_freq:
            return 'Star'
        elif is_high_rev and not is_high_freq:
            return 'Cash Cow'
        elif not is_high_rev and is_high_freq and has_activity:
            return 'Hidden Gem'
        else:
            return 'Slacker'
    
    return df.apply(classify, axis=1), {
        'revenue_75th': rev_75,
        'frequency_75th': freq_75,
        'min_purchases': min_purchases,
        'min_sessions': min_sessions
    }


def classify_median_std(df, revenue_col='Item revenue', purchases_col='Items purchased',
                        frequency_col='calc_frequency'):
    """
    Median + Standard Deviation approach:
    - Star: Revenue > median + 0.5*std AND Frequency > median + 0.5*std
    - Cash Cow: Revenue > median AND Frequency <= median
    - Hidden Gem: Revenue <= median AND Frequency > median + 0.5*std AND purchases > median
    - Slacker: Everything else
    """
    rev_median = df[revenue_col].median()
    rev_std = df[revenue_col].std()
    freq_median = df[frequency_col].median()
    freq_std = df[frequency_col].std()
    purch_median = df[purchases_col].median()
    
    def classify(row):
        rev = row[revenue_col] if not pd.isna(row[revenue_col]) else 0
        freq = row[frequency_col] if not pd.isna(row[frequency_col]) else 0
        purch = row[purchases_col] if not pd.isna(row[purchases_col]) else 0
        
        is_high_rev = rev > rev_median + 0.5 * rev_std
        is_above_rev_median = rev > rev_median
        is_high_freq = freq > freq_median + 0.5 * freq_std
        is_above_purch_median = purch > purch_median
        
        if is_high_rev and is_high_freq:
            return 'Star'
        elif is_above_rev_median and not is_high_freq:
            return 'Cash Cow'
        elif not is_above_rev_median and is_high_freq and is_above_purch_median:
            return 'Hidden Gem'
        else:
            return 'Slacker'
    
    return df.apply(classify, axis=1), {
        'revenue_median': rev_median,
        'revenue_std': rev_std,
        'frequency_median': freq_median,
        'frequency_std': freq_std,
        'purchases_median': purch_median
    }


def calculate_conversion_rate(df):
    """Add conversion rate: Items purchased / Items viewed."""
    df['conversion_rate'] = df['Items purchased'].fillna(0) / df['Items viewed'].replace(0, np.nan)
    df['conversion_rate'] = df['conversion_rate'].fillna(0)
    return df


def compare_classifications(df, brand_name):
    """Compare different classification approaches."""
    print(f"\n{'='*60}")
    print(f"CLASSIFICATION COMPARISON: {brand_name}")
    print('='*60)
    
    # Current (absolute)
    current = df['ga4_class'].value_counts()
    print("\n1. CURRENT (Absolute Thresholds):")
    print(current.to_string())
    
    # Percentile-based
    percentile_class, percentile_params = classify_percentile(df)
    print("\n2. PERCENTILE-BASED (75th percentile):")
    print(percentile_class.value_counts().to_string())
    print(f"   Thresholds: Rev≥{percentile_params['revenue_75th']:.0f}, Freq≥{percentile_params['frequency_75th']:.2f}")
    
    # Median + std
    median_class, median_params = classify_median_std(df)
    print("\n3. MEDIAN + STD:")
    print(median_class.value_counts().to_string())
    print(f"   Rev threshold: {median_params['revenue_median']:.0f} + 0.5*{median_params['revenue_std']:.0f}")
    
    return {
        'current': current.to_dict(),
        'percentile': percentile_class.value_counts().to_dict(),
        'median_std': median_class.value_counts().to_dict(),
        'params_percentile': percentile_params,
        'params_median': median_params
    }


if __name__ == '__main__':
    brands = load_all_brands()
    
    results = {}
    for brand, df in brands.items():
        # Add conversion rate
        df = calculate_conversion_rate(df)
        results[brand] = compare_classifications(df, brand)
        
        # Show conversion rate stats
        print(f"\nConversion Rate (Items purchased/viewed) for {brand}:")
        print(df['conversion_rate'].describe())
